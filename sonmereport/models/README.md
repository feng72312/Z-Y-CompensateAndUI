# 补偿模型文件说明

本目录包含多种补偿方法的示例模型文件。

## 文件列表

| 文件 | 方法 | 存储大小 | 精度 | 推荐场景 |
|------|------|----------|------|----------|
| `polynomial_3.json` | 3阶多项式 | ~100B | 0.01% | 嵌入式设备 |
| `polynomial_2.json` | 2阶多项式 | ~80B | 0.1% | 极简存储 |
| `lut_interp_42.json` | 查找表+插值 | ~800B | 0.0001% | 实时处理 |

## 使用方法

### Python 使用多项式模型

```python
import json
import numpy as np

# 加载模型
with open('polynomial_3.json', 'r') as f:
    model = json.load(f)

coeffs = model['coefficients']

# 补偿单个值
def compensate(x):
    return np.polyval(coeffs, x)

# 补偿数组
x_values = np.array([0.0, 5.0, 10.0])
y_values = np.polyval(coeffs, x_values)
```

### Python 使用查找表模型

```python
import json
import numpy as np

# 加载模型
with open('lut_interp_42.json', 'r') as f:
    model = json.load(f)

x_min = model['x_min']
x_max = model['x_max']
y_table = np.array(model['y_table'])
n = len(y_table)

def compensate(x):
    # 计算浮点索引
    idx = (x - x_min) / (x_max - x_min) * (n - 1)
    idx = np.clip(idx, 0, n - 1)
    
    # 线性插值
    i0 = int(np.floor(idx))
    i1 = min(i0 + 1, n - 1)
    frac = idx - i0
    
    return y_table[i0] * (1 - frac) + y_table[i1] * frac
```

### C 使用多项式模型

```c
// 3阶多项式系数
const float a = 1.2e-7f;
const float b = -2.5e-5f;
const float c = 0.9998f;
const float d = 22.05f;

float compensate(float x) {
    return a*x*x*x + b*x*x + c*x + d;
}
```

### C 使用查找表模型

```c
#define LUT_SIZE 42
const float x_min = -24.0956f;
const float x_max = 17.5476f;
const float y_table[LUT_SIZE] = {
    0.9998f, 1.9997f, 2.9996f, /* ... */
};

float compensate(float x) {
    float idx = (x - x_min) / (x_max - x_min) * (LUT_SIZE - 1);
    if (idx < 0) idx = 0;
    if (idx > LUT_SIZE - 1) idx = LUT_SIZE - 1;
    
    int i0 = (int)idx;
    int i1 = (i0 + 1 < LUT_SIZE) ? i0 + 1 : i0;
    float frac = idx - i0;
    
    return y_table[i0] * (1.0f - frac) + y_table[i1] * frac;
}
```

## 精度对比

使用相同的测试数据，各方法的性能对比：

| 方法 | 线性度 | 最大偏差 | 存储减少 |
|------|--------|----------|----------|
| 三次样条(原) | ~0.000001% | ~0.0001mm | 基准 |
| 查找表+插值 | ~0.0001% | ~0.01mm | 47% |
| 3阶多项式 | ~0.01% | ~0.1mm | 93% |
| 2阶多项式 | ~0.1% | ~1mm | 95% |

## 建议

1. **精度优先**：使用原三次样条模型
2. **存储优先**：使用3阶多项式（减少93%存储）
3. **速度优先**：使用查找表+插值（O(1)复杂度）

