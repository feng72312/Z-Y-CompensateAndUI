# Change: 添加 C++20 产品接口

## Why

Python实现适合研发和原型验证，但产品集成需要C++接口：
- **集成需求**：同事需要将补偿功能集成到C++/Qt项目
- **性能要求**：实时系统要求单次补偿 < 1μs
- **部署约束**：生产环境可能无Python运行时
- **依赖管理**：避免Python依赖（NumPy/SciPy/Pillow）带来的部署复杂度

## What Changes

### 新增 C++20 接口库

**实现方式**：纯C++20重新实现核心算法（选项A）

**功能范围**（完整功能集）：
- ✅ 补偿功能：加载模型 + 单值/数组补偿
- ✅ 外推配置：线性外推，可配置距离和范围
- ✅ 归一化配置：自动/手动偏移
- ✅ 标定功能：从标定数据构建模型
- ✅ 线性度评估：BFSL方法计算
- ✅ 重复精度评估：Y-Z重复精度计算

**技术栈**：
- **标准**：C++20（使用 concepts, ranges, span, constexpr 增强）
- **构建**：CMake 3.20+
- **JSON**：轻量级第三方库（nlohmann/json 或自实现）
- **样条插值**：自实现三次样条（基于SciPy算法移植）
- **接口风格**：现代C++（智能指针、RAII、异常安全）

### 架构设计

```
cpp_interface/
├── include/
│   └── depth_compensation/
│       ├── core/
│       │   ├── spline.hpp          # 三次样条插值
│       │   ├── compensator.hpp     # 补偿功能
│       │   ├── calibrator.hpp      # 标定功能
│       │   └── evaluator.hpp       # 线性度/重复精度
│       ├── models/
│       │   ├── compensation_model.hpp
│       │   ├── calibration_result.hpp
│       │   └── configs.hpp
│       ├── io/
│       │   └── model_io.hpp        # JSON模型读写
│       └── depth_compensation.hpp  # 主头文件
├── src/
│   ├── core/                       # 核心算法实现
│   ├── models/                     # 数据模型实现
│   └── io/                         # IO实现
├── tests/
│   └── unit_tests/                 # Google Test单元测试
├── examples/
│   ├── basic_compensation.cpp
│   ├── calibration_flow.cpp
│   └── qt_integration.cpp          # Qt集成示例
└── CMakeLists.txt
```

### API 设计示例

```cpp
#include <depth_compensation/depth_compensation.hpp>

using namespace depth_compensation;

// 1. 补偿使用（最常用）
CompensationService service;
service.load_model("model.json");

// 单值补偿
double compensated = service.compensate(measured_value);

// 批量补偿
std::vector<double> measured = {1.0, 2.0, 3.0};
auto compensated = service.compensate(measured);

// 2. 标定流程
CalibrationService calib;
CalibrationConfig config{
    .filter_enabled = true,
    .outlier_std_factor = 3.0
};

auto result = calib.process_calibration_data(
    actual_values, measured_values, config);
result.model.save("model.json");

// 3. 线性度评估
LinearityService linearity;
auto result = linearity.calculate_linearity(
    actual_values, measured_values, 41.0);
std::cout << "线性度: " << result.linearity << "%\n";
```

## Impact

### Affected Specs
- **新增**: cpp-interface（新规格）
- **更新**: project.md（添加C++技术栈说明）

### Affected Code
- **新增**: `cpp_interface/` 目录（全新C++代码库）
- **不影响**: 现有Python实现保持不变

### Breaking Changes
- ❌ 无Breaking Changes（新增功能，不修改现有API）

### Migration
对于C++用户：
```bash
# 1. 构建C++库
cd cpp_interface && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .

# 2. 集成到项目
target_link_libraries(your_app depth_compensation)
```

对于Python用户：
- 无影响，继续使用现有API

## 技术决策要点

### 1. 样条插值实现
- **决策**：自实现三次样条，移植SciPy的splrep/splev算法
- **理由**：避免引入重量级数学库，保持零依赖目标

### 2. JSON处理
- **选项A**：nlohmann/json（header-only，现代API）
- **选项B**：自实现轻量级解析器
- **推荐**：选项A（成熟稳定，易用）

### 3. 内存管理
- **决策**：使用智能指针（`std::unique_ptr`, `std::shared_ptr`）
- **理由**：自动内存管理，异常安全

### 4. 错误处理
- **决策**：异常 + 错误码混合
- **理由**：
  - 异常用于不可恢复错误（模型加载失败）
  - 错误码用于可预期错误（范围外补偿）

### 5. 性能优化
- **向量化**：使用`std::span`减少拷贝
- **constexpr**：编译期计算常量
- **并行**：可选的`std::execution::par`支持

## 依赖关系
- **必需**：C++20编译器（GCC 10+, Clang 12+, MSVC 19.29+）
- **可选**：nlohmann/json（JSON处理）
- **测试**：Google Test（单元测试）
- **构建**：CMake 3.20+
