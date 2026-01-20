# 深度图补偿系统 - 项目概述

## 目的

本系统是深度相机校准和补偿的完整解决方案，用于提高深度测量的线性度和精度。系统可以：
- 建立补偿模型（基于标定数据）
- 应用补偿模型（提高测量精度）
- 评估测量质量（线性度、重复精度）

## 技术栈

### 核心算法（Python）
- **NumPy**: 数值计算
- **SciPy**: 三次样条插值、滤波处理
- **Pillow**: 深度图读写（16位PNG）

### 图形界面
- **Tkinter**: 跨平台GUI框架

### 产品集成（C++20）
- **纯C++20**: 无Python依赖
- **三次样条**: 自实现（移植SciPy算法）
- **JSON解析**: nlohmann/json（header-only）
- **构建系统**: CMake 3.20+
- **测试框架**: Google Test

## 架构设计 (v3.0)

### Python 分层架构

```
compcodeultimate/
├── data/                  # 数据层
│   ├── models.py          # 数据模型定义（使用 dataclass）
│   ├── io.py              # 文件读写
│   └── converters.py      # 单位转换
├── core/                  # 核心算法层
│   ├── spline_model.py    # 样条模型构建
│   ├── compensator.py     # 补偿功能
│   ├── extrapolator.py    # 外推功能
│   ├── calibrator.py      # 标定处理
│   └── linearity.py       # 线性度计算
├── services/              # 服务层（业务流程编排）
│   ├── calibration_service.py
│   ├── compensation_service.py
│   ├── linearity_service.py
│   └── repeatability_service.py
└── interfaces/            # 接口层
    ├── cli.py             # 命令行接口
    └── ui_adapter.py      # UI 适配器接口
```

### C++ 接口架构

```
cpp_interface/
├── include/depth_compensation/
│   ├── core/              # 核心算法
│   │   ├── spline.hpp
│   │   ├── compensator.hpp
│   │   ├── calibrator.hpp
│   │   └── evaluator.hpp
│   ├── models/            # 数据模型
│   │   ├── compensation_model.hpp
│   │   ├── configs.hpp
│   │   └── results.hpp
│   ├── io/                # IO功能
│   │   └── model_io.hpp
│   └── depth_compensation.hpp  # 主头文件
├── src/                   # 实现文件
├── tests/                 # 单元测试
└── examples/              # 示例代码
```

### API 使用示例

**Python**:
```python
from compcodeultimate import CompensationService, CalibrationService

# 标定流程
calib = CalibrationService()
result = calib.process_calibration_data('./calib_data')
calib.save_model('model.json')

# 加载模型并补偿
comp = CompensationService()
comp.load_model('model.json')
result = comp.compensate_image('input.png', 'output.png')
```

**C++20**:
```cpp
#include <depth_compensation/depth_compensation.hpp>
using namespace depth_compensation;

// 标定流程
CalibrationService calib;
auto model = calib.build_model(actual_values, measured_values);
model.save("model.json");

// 加载模型并补偿
CompensationService comp;
comp.load_model("model.json");
double result = comp.compensate(measured_value);
```

## 项目约定

### 代码风格
- **Python**：中文注释，snake_case，使用 dataclass 和类型提示
- **C++**：英文注释，snake_case，使用 concepts 和 ranges
- 类名使用PascalCase
- 配置参数使用UPPER_SNAKE_CASE

### 深度转换公式
```
深度值(mm) = (灰度值 - OFFSET) × SCALE_FACTOR / 1000
```
默认参数：
- OFFSET = 32768
- SCALE_FACTOR = 1.6
- 无效像素值 = 65535

### 文件格式
- 深度图：16位无符号整数 PNG
- 位移数据：CSV文件，包含"实际累计位移(mm)"列
- 补偿模型：JSON格式（Python和C++兼容）

## 领域知识

### 线性度（BFSL方法）
Best Fit Straight Line方法计算线性度：
1. 零点归一化（相对值）
2. 最小二乘线性拟合
3. 计算与拟合线的最大偏差
4. 线性度 = 最大偏差 / 满量程 × 100%

### 补偿模型
使用三次样条插值建立测量值到实际值的映射：
- 正向模型：实际值 → 测量值
- 逆向模型：测量值 → 实际值（用于补偿）
- 动态阶数调整：k = min(3, 数据点数-1)

### 外推功能
超出模型范围时的线性外推：
- 低端外推：x < x_min，使用边界斜率
- 高端外推：x > x_max，使用边界斜率
- 外推限制：max_low, max_high 控制外推距离
- 输出限制：可选的输出范围钳位

### 归一化功能
输出归一化选项：
- 自动偏移：基于模型 y_range 自动计算
- 手动偏移：用户指定偏移量
- 目标中心：归一化后的中心点（通常为0）

### 滤波处理
1. 3σ异常值去除
2. 中值滤波（去除椒盐噪声）
3. 高斯滤波（平滑）
4. 平面拟合校准（去除倾斜）

**关键修复（v2.1）**: 滤波时使用有效像素均值填充无效区域，避免边界像素被拉低。

## 重要约束

### 数据要求
- 标定数据至少4个点（三次样条要求）
- 标定数据需覆盖测量量程
- 深度图必须是16位PNG格式

### 性能指标
- 典型补偿后线性度：< 0.05%
- 典型改善幅度：> 70%
- Python标量输入补偿：< 1μs
- C++单次补偿：< 1μs（-O3优化）
- C++批量补偿：> 100万次/秒

### 类型一致性
- Python标量输入函数必须返回 Python `float` 类型
- Python数组输入函数返回 `np.ndarray` 类型
- C++使用标准类型：`double`, `std::vector<double>`

## 外部依赖

### Python环境
```
numpy>=1.20
scipy>=1.7
pillow>=9.0
```

### C++环境
```
C++20 编译器：
- GCC 10+ 
- Clang 12+
- MSVC 19.29+ (Visual Studio 2019 16.10+)

构建工具：
- CMake 3.20+

依赖库：
- nlohmann/json (header-only, 可选通过vcpkg/conan安装)
- Google Test (测试，可选)
```

## 版本历史

- **v3.1** (2026-01): C++20接口添加
- **v3.0** (2026-01): 分层架构重构，服务层引入
- **v2.1** (2025-12): 滤波填充Bug修复
- **v2.0** (2025-12): uint16下溢修复，样条优化
- **v1.0** (2025-12): 初始版本

## 使用场景

### Python 实现适用于：
- 研发和原型验证
- 数据分析和可视化
- GUI应用（Tkinter）
- 离线批处理

### C++ 实现适用于：
- 产品集成（嵌入式系统）
- 实时处理（高性能要求）
- Qt/C++项目集成
- 无Python运行时环境
