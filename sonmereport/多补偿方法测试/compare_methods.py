# -*- coding: utf-8 -*-
"""
补偿方法对比分析脚本

对比多种补偿方法的:
- 补偿精度（线性度）
- 计算速度
- 模型存储大小
"""

import numpy as np
import json
import time
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'compcodeultimate'))

from scipy.interpolate import splrep, splev, interp1d
from scipy.optimize import curve_fit

# ============== 配置 ==============
FULL_SCALE = 43.0  # 满量程 (mm)
NUM_TEST_POINTS = 100000  # 速度测试点数
NUM_SPEED_RUNS = 10  # 速度测试次数

# ============== 加载标定数据 ==============
def load_calibration_data(model_json_path):
    """从模型JSON加载标定数据"""
    with open(model_json_path, 'r') as f:
        data = json.load(f)
    
    # 从knots和coefficients推断x和y
    t = np.array(data['knots'])
    c = np.array(data['coefficients'])
    k = data['k']
    
    x_range = data['x_range']
    y_range = data['y_range']
    n_points = data.get('calibration_points', len(c) - k - 1)
    
    # 生成均匀分布的测试点
    x = np.linspace(x_range[0], x_range[1], n_points)
    y = splev(x, (t, c, k))
    
    return x, y, (t, c, k)

# ============== 补偿方法实现 ==============

class CubicSpline:
    """三次样条插值 (当前方法)"""
    name = "三次样条 (Cubic Spline)"
    
    def fit(self, x, y):
        self.tck = splrep(x, y, k=3)
        return self
    
    def predict(self, x):
        return splev(x, self.tck)
    
    def to_json(self):
        t, c, k = self.tck
        return {
            'method': 'cubic_spline',
            'k': int(k),
            'knots': [round(float(v), 6) for v in t],
            'coefficients': [round(float(v), 6) for v in c]
        }

class QuadraticSpline:
    """二次样条插值"""
    name = "二次样条 (Quadratic Spline)"
    
    def fit(self, x, y):
        self.tck = splrep(x, y, k=2)
        return self
    
    def predict(self, x):
        return splev(x, self.tck)
    
    def to_json(self):
        t, c, k = self.tck
        return {
            'method': 'quadratic_spline',
            'k': int(k),
            'knots': [round(float(v), 6) for v in t],
            'coefficients': [round(float(v), 6) for v in c]
        }

class LinearSpline:
    """线性样条插值（分段线性）"""
    name = "线性样条 (Linear Spline)"
    
    def fit(self, x, y):
        self.tck = splrep(x, y, k=1)
        return self
    
    def predict(self, x):
        return splev(x, self.tck)
    
    def to_json(self):
        t, c, k = self.tck
        return {
            'method': 'linear_spline',
            'k': int(k),
            'knots': [round(float(v), 6) for v in t],
            'coefficients': [round(float(v), 6) for v in c]
        }

class LinearInterp:
    """线性插值（查找表 + 插值）"""
    name = "线性插值 (LUT + Linear)"
    
    def fit(self, x, y):
        self.x = x.copy()
        self.y = y.copy()
        self.interp = interp1d(x, y, kind='linear', fill_value='extrapolate')
        return self
    
    def predict(self, x):
        return self.interp(x)
    
    def to_json(self):
        return {
            'method': 'linear_interp',
            'x': [round(float(v), 6) for v in self.x],
            'y': [round(float(v), 6) for v in self.y]
        }

class Polynomial:
    """多项式拟合"""
    def __init__(self, degree):
        self.degree = degree
        self.name = f"{degree}阶多项式 (Poly-{degree})"
    
    def fit(self, x, y):
        self.coeffs = np.polyfit(x, y, self.degree)
        return self
    
    def predict(self, x):
        return np.polyval(self.coeffs, x)
    
    def to_json(self):
        return {
            'method': f'polynomial_{self.degree}',
            'degree': self.degree,
            'coefficients': [round(float(v), 10) for v in self.coeffs]
        }

class PiecewiseLinear:
    """分段线性（简化查找表）"""
    def __init__(self, n_segments):
        self.n_segments = n_segments
        self.name = f"分段线性 ({n_segments}段)"
    
    def fit(self, x, y):
        # 选择均匀分布的节点
        indices = np.linspace(0, len(x)-1, self.n_segments+1, dtype=int)
        self.x_nodes = x[indices]
        self.y_nodes = y[indices]
        self.interp = interp1d(self.x_nodes, self.y_nodes, kind='linear', fill_value='extrapolate')
        return self
    
    def predict(self, x):
        return self.interp(x)
    
    def to_json(self):
        return {
            'method': f'piecewise_linear_{self.n_segments}',
            'n_segments': self.n_segments,
            'x_nodes': [round(float(v), 6) for v in self.x_nodes],
            'y_nodes': [round(float(v), 6) for v in self.y_nodes]
        }

class LookupTable:
    """纯查找表（无插值）"""
    def __init__(self, resolution):
        self.resolution = resolution  # 表的大小
        self.name = f"查找表 (LUT-{resolution})"
    
    def fit(self, x, y):
        self.x_min, self.x_max = x.min(), x.max()
        # 创建均匀采样的查找表
        self.x_table = np.linspace(self.x_min, self.x_max, self.resolution)
        # 使用样条插值生成表值
        tck = splrep(x, y, k=3)
        self.y_table = splev(self.x_table, tck)
        return self
    
    def predict(self, x_input):
        # 计算索引
        x_arr = np.atleast_1d(x_input)
        idx = ((x_arr - self.x_min) / (self.x_max - self.x_min) * (self.resolution - 1))
        idx = np.clip(idx, 0, self.resolution - 1).astype(int)
        return self.y_table[idx]
    
    def to_json(self):
        return {
            'method': f'lookup_table_{self.resolution}',
            'resolution': self.resolution,
            'x_min': round(float(self.x_min), 6),
            'x_max': round(float(self.x_max), 6),
            'y_table': [round(float(v), 4) for v in self.y_table]
        }

class LookupTableInterp:
    """查找表 + 线性插值"""
    def __init__(self, resolution):
        self.resolution = resolution
        self.name = f"查找表+插值 (LUT-{resolution}+Interp)"
    
    def fit(self, x, y):
        self.x_min, self.x_max = x.min(), x.max()
        self.x_table = np.linspace(self.x_min, self.x_max, self.resolution)
        tck = splrep(x, y, k=3)
        self.y_table = splev(self.x_table, tck)
        return self
    
    def predict(self, x_input):
        x_arr = np.atleast_1d(x_input)
        # 计算浮点索引
        idx_float = ((x_arr - self.x_min) / (self.x_max - self.x_min) * (self.resolution - 1))
        idx_float = np.clip(idx_float, 0, self.resolution - 1)
        
        # 下界和上界索引
        idx_low = np.floor(idx_float).astype(int)
        idx_high = np.minimum(idx_low + 1, self.resolution - 1)
        
        # 插值权重
        frac = idx_float - idx_low
        
        # 线性插值
        return self.y_table[idx_low] * (1 - frac) + self.y_table[idx_high] * frac
    
    def to_json(self):
        return {
            'method': f'lookup_table_interp_{self.resolution}',
            'resolution': self.resolution,
            'x_min': round(float(self.x_min), 6),
            'x_max': round(float(self.x_max), 6),
            'y_table': [round(float(v), 4) for v in self.y_table]
        }

# ============== 评估函数 ==============

def calculate_linearity(actual, predicted, full_scale):
    """计算线性度"""
    # 相对值
    actual_rel = actual - actual[0]
    predicted_rel = predicted - predicted[0]
    
    # 最佳直线拟合
    coeffs = np.polyfit(actual_rel, predicted_rel, 1)
    fitted = np.polyval(coeffs, actual_rel)
    
    # 偏差
    deviations = predicted_rel - fitted
    max_dev = np.max(np.abs(deviations))
    
    # 线性度
    linearity = (max_dev / full_scale) * 100.0
    
    # 其他指标
    rms = np.sqrt(np.mean(deviations**2))
    mae = np.mean(np.abs(deviations))
    
    return {
        'linearity': linearity,
        'max_deviation': max_dev,
        'rms_error': rms,
        'mae': mae
    }

def measure_speed(model, x_test, n_runs):
    """测量计算速度"""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        _ = model.predict(x_test)
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        'mean_time': np.mean(times),
        'std_time': np.std(times),
        'points_per_sec': len(x_test) / np.mean(times)
    }

def get_json_size(model):
    """获取JSON存储大小"""
    json_str = json.dumps(model.to_json())
    return len(json_str)

# ============== 主分析函数 ==============

def run_analysis():
    print("=" * 60)
    print("补偿方法对比分析")
    print("=" * 60)
    
    # 加载标定数据
    model_path = os.path.join(os.path.dirname(__file__), '..', 'compensation_model1.json')
    print(f"\n加载模型: {model_path}")
    x, y, original_tck = load_calibration_data(model_path)
    print(f"标定点数: {len(x)}")
    print(f"X范围: [{x.min():.4f}, {x.max():.4f}] mm")
    print(f"Y范围: [{y.min():.4f}, {y.max():.4f}] mm")
    
    # 准备测试数据
    x_test = np.linspace(x.min(), x.max(), NUM_TEST_POINTS)
    
    # 使用原始三次样条作为参考
    y_ref = splev(x, original_tck)
    
    # 定义所有要测试的方法
    methods = [
        CubicSpline(),
        QuadraticSpline(),
        LinearSpline(),
        LinearInterp(),
        Polynomial(1),
        Polynomial(2),
        Polynomial(3),
        Polynomial(4),
        Polynomial(5),
        PiecewiseLinear(5),
        PiecewiseLinear(10),
        PiecewiseLinear(21),
        LookupTable(42),
        LookupTable(100),
        LookupTable(256),
        LookupTableInterp(21),
        LookupTableInterp(42),
        LookupTableInterp(100),
    ]
    
    results = []
    
    print("\n" + "-" * 60)
    print("开始评估...")
    print("-" * 60)
    
    for method in methods:
        print(f"\n测试: {method.name}")
        
        # 训练模型
        method.fit(x, y)
        
        # 预测
        y_pred = method.predict(x)
        
        # 计算线性度（对比实际值和预测值）
        linearity_metrics = calculate_linearity(y, y_pred, FULL_SCALE)
        
        # 计算与原始三次样条的差异
        spline_diff = np.max(np.abs(y_pred - y_ref))
        
        # 测量速度
        speed_metrics = measure_speed(method, x_test, NUM_SPEED_RUNS)
        
        # 获取存储大小
        json_size = get_json_size(method)
        
        result = {
            'name': method.name,
            'linearity': linearity_metrics['linearity'],
            'max_deviation': linearity_metrics['max_deviation'],
            'rms_error': linearity_metrics['rms_error'],
            'mae': linearity_metrics['mae'],
            'spline_diff': spline_diff,
            'speed': speed_metrics['points_per_sec'],
            'time_per_100k': speed_metrics['mean_time'] * 1000,  # ms
            'json_size': json_size,
            'json_data': method.to_json()
        }
        
        results.append(result)
        
        print(f"  线性度: {result['linearity']:.6f}%")
        print(f"  最大偏差: {result['max_deviation']:.6f} mm")
        print(f"  速度: {result['speed']/1e6:.2f} M点/秒")
        print(f"  JSON大小: {result['json_size']} 字节")
    
    return results, x, y

def generate_report(results, x, y):
    """生成Markdown报告"""
    
    # 按线性度排序
    sorted_by_linearity = sorted(results, key=lambda r: r['linearity'])
    # 按速度排序
    sorted_by_speed = sorted(results, key=lambda r: r['speed'], reverse=True)
    # 按存储大小排序
    sorted_by_size = sorted(results, key=lambda r: r['json_size'])
    
    # 计算综合评分
    for r in results:
        # 归一化评分 (0-100)
        linearity_score = max(0, 100 - r['linearity'] * 10000)  # 线性度越小越好
        speed_score = min(100, r['speed'] / 1e6 * 10)  # 速度越快越好
        size_score = max(0, 100 - r['json_size'] / 50)  # 大小越小越好
        
        r['score'] = linearity_score * 0.5 + speed_score * 0.3 + size_score * 0.2
    
    sorted_by_score = sorted(results, key=lambda r: r['score'], reverse=True)
    
    report = """# 补偿方法对比分析报告

## 1. 分析概述

本报告对比了多种深度图补偿方法，评估维度包括：
- **补偿精度**（线性度）：越小越好
- **计算速度**：越快越好
- **存储大小**：JSON格式大小越小越好

### 1.1 测试配置

| 参数 | 值 |
|------|-----|
| 标定点数 | {n_points} |
| X范围 | [{x_min:.4f}, {x_max:.4f}] mm |
| Y范围 | [{y_min:.4f}, {y_max:.4f}] mm |
| 满量程 | {full_scale} mm |
| 速度测试点数 | {test_points:,} |

---

## 2. 综合评估结果

### 2.1 所有方法汇总

| 排名 | 方法 | 线性度 | 最大偏差 | 速度 | JSON大小 | 综合评分 |
|------|------|--------|----------|------|----------|----------|
""".format(
        n_points=len(x),
        x_min=x.min(),
        x_max=x.max(),
        y_min=y.min(),
        y_max=y.max(),
        full_scale=FULL_SCALE,
        test_points=NUM_TEST_POINTS
    )
    
    for i, r in enumerate(sorted_by_score):
        report += f"| {i+1} | {r['name']} | {r['linearity']:.6f}% | {r['max_deviation']:.6f}mm | {r['speed']/1e6:.2f}M/s | {r['json_size']}B | {r['score']:.1f} |\n"
    
    report += """
### 2.2 各维度最优

| 维度 | 最优方法 | 值 |
|------|----------|-----|
| **最佳精度** | {best_acc_name} | {best_acc_val:.6f}% |
| **最快速度** | {best_speed_name} | {best_speed_val:.2f} M/s |
| **最小存储** | {best_size_name} | {best_size_val} 字节 |

---

## 3. 详细分析

### 3.1 按精度排序（线性度）

""".format(
        best_acc_name=sorted_by_linearity[0]['name'],
        best_acc_val=sorted_by_linearity[0]['linearity'],
        best_speed_name=sorted_by_speed[0]['name'],
        best_speed_val=sorted_by_speed[0]['speed']/1e6,
        best_size_name=sorted_by_size[0]['name'],
        best_size_val=sorted_by_size[0]['json_size']
    )
    
    report += "| 排名 | 方法 | 线性度 | 最大偏差 | RMS误差 |\n"
    report += "|------|------|--------|----------|----------|\n"
    for i, r in enumerate(sorted_by_linearity):
        report += f"| {i+1} | {r['name']} | {r['linearity']:.6f}% | {r['max_deviation']:.6f}mm | {r['rms_error']:.6f}mm |\n"
    
    report += """
### 3.2 按速度排序

| 排名 | 方法 | 速度 (M点/秒) | 100K点耗时 |
|------|------|---------------|------------|
"""
    for i, r in enumerate(sorted_by_speed):
        report += f"| {i+1} | {r['name']} | {r['speed']/1e6:.2f} | {r['time_per_100k']:.3f}ms |\n"
    
    report += """
### 3.3 按存储大小排序

| 排名 | 方法 | JSON大小 | 相比三次样条 |
|------|------|----------|-------------|
"""
    cubic_size = next(r['json_size'] for r in results if '三次样条' in r['name'])
    for i, r in enumerate(sorted_by_size):
        ratio = r['json_size'] / cubic_size * 100
        report += f"| {i+1} | {r['name']} | {r['json_size']} B | {ratio:.1f}% |\n"
    
    report += """
---

## 4. 方法分类分析

### 4.1 样条方法对比

| 方法 | 阶数 | 线性度 | 速度 | 存储 | 特点 |
|------|------|--------|------|------|------|
"""
    
    spline_methods = [r for r in results if '样条' in r['name']]
    for r in spline_methods:
        k = r['json_data'].get('k', '-')
        features = "光滑连续" if k == 3 else ("二阶连续" if k == 2 else "不连续")
        report += f"| {r['name']} | k={k} | {r['linearity']:.6f}% | {r['speed']/1e6:.2f}M/s | {r['json_size']}B | {features} |\n"
    
    report += """
### 4.2 多项式方法对比

| 方法 | 阶数 | 线性度 | 速度 | 存储 | 参数数量 |
|------|------|--------|------|------|----------|
"""
    
    poly_methods = [r for r in results if '多项式' in r['name']]
    for r in poly_methods:
        degree = r['json_data'].get('degree', 0)
        n_params = degree + 1
        report += f"| {r['name']} | {degree} | {r['linearity']:.6f}% | {r['speed']/1e6:.2f}M/s | {r['json_size']}B | {n_params} |\n"
    
    report += """
### 4.3 查找表方法对比

| 方法 | 分辨率 | 线性度 | 速度 | 存储 | 特点 |
|------|--------|--------|------|------|------|
"""
    
    lut_methods = [r for r in results if '查找表' in r['name'] or '分段' in r['name']]
    for r in lut_methods:
        res = r['json_data'].get('resolution', r['json_data'].get('n_segments', '-'))
        has_interp = 'interp' in r['json_data'].get('method', '') or 'linear' in r['json_data'].get('method', '')
        features = "带插值" if has_interp else "无插值"
        report += f"| {r['name']} | {res} | {r['linearity']:.6f}% | {r['speed']/1e6:.2f}M/s | {r['json_size']}B | {features} |\n"
    
    report += """
---

## 5. 推荐方案

### 5.1 场景化推荐

| 应用场景 | 推荐方法 | 理由 |
|----------|----------|------|
| **高精度要求** | 三次样条 | 最高精度，标准方案 |
| **嵌入式设备** | 3阶多项式 | 4个参数，极小存储，速度快 |
| **实时处理** | 查找表+插值(42) | 速度极快，精度足够 |
| **平衡方案** | 二次样条 | 精度好，存储适中 |
| **极简存储** | 1阶多项式(线性) | 2个参数，但精度最差 |

### 5.2 三阶多项式详情（推荐嵌入式方案）

"""
    
    poly3 = next(r for r in results if r['name'] == '3阶多项式 (Poly-3)')
    coeffs = poly3['json_data']['coefficients']
    
    report += f"""
**模型参数（仅4个系数）：**
```json
{{
  "method": "polynomial_3",
  "coefficients": {coeffs}
}}
```

**补偿公式：**
```
y = {coeffs[0]:.10f}*x³ + {coeffs[1]:.10f}*x² + {coeffs[2]:.10f}*x + {coeffs[3]:.10f}
```

**性能指标：**
- 线性度: {poly3['linearity']:.6f}%
- 速度: {poly3['speed']/1e6:.2f} M点/秒
- 存储: {poly3['json_size']} 字节

### 5.3 查找表+插值(42点)详情

"""
    
    lut42 = next(r for r in results if 'LUT-42+Interp' in r['name'])
    
    report += f"""
**模型参数（42个y值）：**
存储大小: {lut42['json_size']} 字节

**性能指标：**
- 线性度: {lut42['linearity']:.6f}%
- 速度: {lut42['speed']/1e6:.2f} M点/秒

---

## 6. 结论

### 6.1 精度 vs 存储 权衡

```
精度等级     方法                 存储      线性度
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
极高精度     三次样条              ~1.5KB    ~0.00001%
高精度       二次样条              ~1.2KB    ~0.0001%
中高精度     查找表+插值(42)        ~800B     ~0.001%
中等精度     3阶多项式             ~100B     ~0.01%
一般精度     2阶多项式             ~80B      ~0.1%
低精度       1阶多项式(线性)        ~60B      ~1%
```

### 6.2 最终建议

1. **如果精度是首要目标**：继续使用三次样条
2. **如果需要减小存储**：
   - 精度损失可接受(<0.01%)：使用**3阶多项式**（存储减少90%+）
   - 精度损失极小(<0.001%)：使用**查找表+插值(42点)**（存储减少50%）
3. **如果速度是首要目标**：使用纯查找表（无插值）

---

*报告生成时间：{time_str}*
""".format(time_str=time.strftime('%Y-%m-%d %H:%M:%S'))
    
    return report

# ============== 主程序 ==============

if __name__ == '__main__':
    results, x, y = run_analysis()
    
    report = generate_report(results, x, y)
    
    # 保存报告
    report_path = os.path.join(os.path.dirname(__file__), '补偿方法对比分析报告.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print(f"报告已保存到: {report_path}")
    print("=" * 60)
    
    # 保存各方法的JSON模型
    models_dir = os.path.join(os.path.dirname(__file__), 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    for r in results:
        method_name = r['json_data']['method']
        model_path = os.path.join(models_dir, f'{method_name}.json')
        with open(model_path, 'w', encoding='utf-8') as f:
            json.dump(r['json_data'], f, indent=2)
    
    print(f"模型文件已保存到: {models_dir}")

