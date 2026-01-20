## ADDED Requirements

### Requirement: C++20 补偿服务

系统应当提供C++20接口进行补偿操作。

#### Scenario: 创建补偿服务
- **WHEN** 实例化 `CompensationService`
- **THEN** 服务处于未加载模型状态
- **AND** 可设置外推和归一化配置

#### Scenario: 加载补偿模型
- **WHEN** 调用 `load_model(path)`
- **THEN** 从JSON文件加载模型
- **AND** 解析样条参数（knots, coefficients, k）
- **AND** 验证模型有效性
- **AND** 抛出 `ModelLoadError` 如果文件无效

#### Scenario: 单值补偿
- **WHEN** 调用 `compensate(measured_value)`
- **AND** 模型已加载
- **THEN** 返回补偿后的实际值（double）
- **AND** 应用外推（如启用且超范围）
- **AND** 应用归一化偏移（如启用）

#### Scenario: 批量补偿
- **WHEN** 调用 `compensate(std::span<const double>)`
- **THEN** 返回 `std::vector<double>` 包含补偿后的值
- **AND** 保持输入数组长度
- **AND** 支持并行执行（可选）

#### Scenario: 带状态的补偿
- **WHEN** 调用 `compensate_with_status(value)`
- **THEN** 返回 `std::pair<double, CompensateResult>`
- **AND** CompensateResult 指示是否外推/钳位

#### Scenario: 未加载模型
- **WHEN** 调用补偿方法但模型未加载
- **THEN** 抛出 `std::logic_error`

### Requirement: C++20 标定服务

系统应当提供C++20接口进行标定操作。

#### Scenario: 创建标定服务
- **WHEN** 实例化 `CalibrationService`
- **THEN** 可选地提供配置对象

#### Scenario: 处理标定数据
- **WHEN** 调用 `build_model(actual_values, measured_values)`
- **AND** 提供至少4个标定点
- **THEN** 构建三次样条模型
- **AND** 返回 `CompensationModel` 对象
- **AND** 存储标定数据用于分析

#### Scenario: 数据验证
- **WHEN** 标定数据少于4个点
- **THEN** 抛出 `InvalidDataError("Data points insufficient")`

#### Scenario: 数据包含无效值
- **WHEN** 标定数据包含 NaN 或 Inf
- **THEN** 抛出 `InvalidDataError("Data contains NaN/Inf")`

#### Scenario: 数据包含重复值
- **WHEN** actual_values 或 measured_values 存在重复
- **THEN** 抛出 `InvalidDataError("Duplicate values found")`

#### Scenario: 进度回调
- **WHEN** 提供 `std::function<void(int, int, std::string)>` 回调
- **THEN** 定期调用回调报告进度

### Requirement: C++20 线性度服务

系统应当提供C++20接口进行线性度计算。

#### Scenario: 创建线性度服务
- **WHEN** 实例化 `LinearityService`
- **THEN** 可指定满量程（默认41.0mm）

#### Scenario: 计算线性度
- **WHEN** 调用 `calculate_linearity(actual, measured)`
- **THEN** 执行零点归一化
- **AND** 执行最小二乘线性拟合
- **AND** 计算最大偏差和线性度
- **AND** 返回 `LinearityResult` 结构体

#### Scenario: LinearityResult 内容
- **WHEN** 返回线性度结果
- **THEN** 包含 linearity（百分比）
- **AND** 包含 max_deviation, min_deviation
- **AND** 包含 rms_error, mae
- **AND** 包含 r_squared, slope, intercept

#### Scenario: 补偿效果评估
- **WHEN** 调用 `calculate_compensation_effect(actual, before, after)`
- **THEN** 分别计算补偿前后线性度
- **AND** 计算改善幅度（%）
- **AND** 返回 `CompensationEffectResult`

#### Scenario: 数据长度不匹配
- **WHEN** actual 和 measured 长度不同
- **THEN** 抛出 `std::invalid_argument`

### Requirement: C++20 重复精度服务

系统应当提供C++20接口进行重复精度计算。

#### Scenario: 创建重复精度服务
- **WHEN** 实例化 `RepeatabilityService`
- **THEN** 服务就绪

#### Scenario: 计算重复精度
- **WHEN** 调用 `calculate_repeatability(image_means)`
- **THEN** 计算标准差（1σ）
- **AND** 计算重复精度（±3σ, 6σ）
- **AND** 计算极差（peak-to-peak）
- **AND** 返回 `RepeatabilityResult`

#### Scenario: RepeatabilityResult 内容
- **WHEN** 返回重复精度结果
- **THEN** 包含 image_count
- **AND** 包含 mean_depth, std_dev
- **AND** 包含 repeatability_3sigma, repeatability_6sigma
- **AND** 包含 peak_to_peak
- **AND** 包含 within_image_std（可选）

### Requirement: 三次样条插值

系统应当提供三次B样条插值功能。

#### Scenario: 拟合样条
- **WHEN** 调用 `CubicSpline::fit(x, y, k)`
- **AND** x, y 长度相同且 >= k+1
- **THEN** 返回 `CubicSpline` 对象
- **AND** 存储节点向量和系数

#### Scenario: 评估样条
- **WHEN** 调用 `spline.evaluate(x)`
- **THEN** 返回插值结果（double）
- **AND** x在范围内使用样条插值
- **AND** x超范围使用边界外推（默认）

#### Scenario: 批量评估
- **WHEN** 调用 `spline.evaluate(std::span<const double>)`
- **THEN** 返回 `std::vector<double>`
- **AND** 长度与输入相同

#### Scenario: 计算导数
- **WHEN** 调用 `spline.derivative(x, order)`
- **THEN** 返回指定阶的导数值
- **AND** order=1 返回一阶导数（用于外推）

#### Scenario: 数据不足
- **WHEN** 数据点数 < k+1
- **THEN** 抛出 `std::invalid_argument`

### Requirement: JSON 模型序列化

系统应当支持 JSON 格式的模型持久化。

#### Scenario: 序列化模型
- **WHEN** 调用 `model.to_json()`
- **THEN** 返回 `nlohmann::json` 对象
- **AND** 包含所有模型参数
- **AND** 格式与Python版本兼容

#### Scenario: 反序列化模型
- **WHEN** 调用 `CompensationModel::from_json(j)`
- **THEN** 解析JSON并构建模型
- **AND** 验证必需字段存在
- **AND** 抛出异常如果格式无效

#### Scenario: 保存到文件
- **WHEN** 调用 `model.save(path)`
- **THEN** 将JSON写入文件
- **AND** 使用适当的缩进（2空格）

#### Scenario: 从文件加载
- **WHEN** 调用 `CompensationModel::load(path)`
- **THEN** 读取文件并解析JSON
- **AND** 返回模型对象

### Requirement: 外推配置

系统应当支持外推配置。

#### Scenario: 默认配置
- **WHEN** 创建 `ExtrapolateConfig` 不提供参数
- **THEN** enabled = true
- **AND** max_low = 2.0, max_high = 2.0
- **AND** output_min = 0.0, output_max = 43.0
- **AND** clamp_output = true

#### Scenario: 自定义配置
- **WHEN** 使用指定初始化器
- **THEN** 覆盖指定字段
- **AND** 其他字段使用默认值

```cpp
ExtrapolateConfig config{
    .max_low = 3.0  // 覆盖
    // 其他使用默认值
};
```

#### Scenario: 应用外推
- **WHEN** 测量值超出模型范围
- **AND** 外推距离 <= max_low/max_high
- **AND** enabled = true
- **THEN** 使用线性外推计算
- **AND** 如果 clamp_output=true，限制输出范围

### Requirement: 归一化配置

系统应当支持输出归一化配置。

#### Scenario: 默认配置
- **WHEN** 创建 `NormalizeConfig` 不提供参数
- **THEN** enabled = false
- **AND** target_center = 0.0
- **AND** auto_offset = true

#### Scenario: 自动偏移计算
- **WHEN** enabled = true 且 auto_offset = true
- **THEN** 根据模型 y_range 计算偏移
- **AND** offset = target_center - (y_min + y_max) / 2

#### Scenario: 手动偏移
- **WHEN** enabled = true 且 auto_offset = false
- **THEN** 使用 manual_offset 值

### Requirement: 性能要求

系统应当满足性能指标。

#### Scenario: 单次补偿性能
- **WHEN** 调用 `compensate(value)` 1000次
- **THEN** 平均耗时 < 1μs
- **AND** 使用 -O3 优化编译

#### Scenario: 批量补偿性能
- **WHEN** 补偿 10000个值
- **THEN** 总耗时 < 10ms
- **AND** 吞吐量 > 100万次/秒

#### Scenario: 模型加载性能
- **WHEN** 加载典型模型（9个标定点）
- **THEN** 耗时 < 100ms

### Requirement: Qt 集成支持

系统应当提供 Qt 友好的封装。

#### Scenario: Qt 补偿服务
- **WHEN** 实例化 `QtCompensationService`
- **THEN** 继承自 `QObject`
- **AND** 提供信号/槽接口

#### Scenario: 异步标定
- **WHEN** 调用 `QtCalibrationService::processAsync()`
- **THEN** 在后台线程执行标定
- **AND** 发射 `progressChanged(int, int, QString)` 信号
- **AND** 完成时发射 `calibrationCompleted(result)` 信号

#### Scenario: 类型转换
- **WHEN** 需要 `QVector<double>` <-> `std::vector<double>` 转换
- **THEN** 提供辅助函数 `toQt()` 和 `fromQt()`

### Requirement: 错误处理

系统应当提供清晰的错误处理机制。

#### Scenario: 异常层次
- **WHEN** 发生错误
- **THEN** 抛出派生自 `CompensationError` 的异常
- **AND** 提供描述性错误消息

#### Scenario: 异常类型
- **WHEN** 模型加载失败
- **THEN** 抛出 `ModelLoadError`
- **WHEN** 数据无效
- **THEN** 抛出 `InvalidDataError`
- **WHEN** JSON格式错误
- **THEN** 抛出 `JsonParseError`

#### Scenario: 错误码
- **WHEN** 调用 `compensate_with_status()`
- **THEN** 返回错误码而非异常
- **AND** 错误码包括：Success, OutOfRange, Extrapolated, Clamped

### Requirement: 内存管理

系统应当提供安全的内存管理。

#### Scenario: RAII 原则
- **WHEN** 使用任何服务类
- **THEN** 资源在构造函数中获取
- **AND** 在析构函数中自动释放
- **AND** 无需手动内存管理

#### Scenario: 移动语义
- **WHEN** 移动服务对象
- **THEN** 支持移动构造和移动赋值
- **AND** 原对象处于有效但未指定状态

#### Scenario: 拷贝控制
- **WHEN** 尝试拷贝服务对象
- **THEN** 编译失败（拷贝被删除）
- **OR** 深拷贝所有资源（如果支持）

### Requirement: 平台支持

系统应当支持多平台编译。

#### Scenario: Windows 支持
- **WHEN** 使用 MSVC 19.29+ 编译
- **THEN** 编译成功无警告
- **AND** 所有测试通过

#### Scenario: Linux 支持
- **WHEN** 使用 GCC 10+ 或 Clang 12+ 编译
- **THEN** 编译成功无警告
- **AND** 所有测试通过

#### Scenario: macOS 支持
- **WHEN** 使用 Clang 12+ (Xcode 13+) 编译
- **THEN** 编译成功无警告
- **AND** 所有测试通过

## 技术说明

### 构建要求
- **C++标准**：C++20
- **编译器**：GCC 10+, Clang 12+, MSVC 19.29+
- **构建工具**：CMake 3.20+

### 依赖库
- **nlohmann/json**：JSON处理（header-only）
- **Google Test**：单元测试（可选）

### 性能指标
- 单次补偿：< 1μs（-O3优化）
- 批量补偿：> 100万次/秒
- 模型加载：< 100ms

### API 示例

**基础补偿**：
```cpp
#include <depth_compensation/depth_compensation.hpp>
using namespace depth_compensation;

CompensationService service;
service.load_model("model.json");

// 单值
double result = service.compensate(10.5);

// 批量
std::vector<double> measured = {1.0, 2.0, 3.0};
auto results = service.compensate(measured);
```

**标定**：
```cpp
CalibrationService calib;
std::vector<double> actual = {0, 5, 10, 15, 20};
std::vector<double> measured = {0.05, 5.02, 10.01, 15.03, 19.98};

auto model = calib.build_model(actual, measured);
model.save("model.json");
```

**线性度**：
```cpp
LinearityService linearity(41.0);  // 满量程
auto result = linearity.calculate_linearity(actual, measured);
std::cout << "线性度: " << result.linearity << "%\n";
std::cout << "RMS误差: " << result.rms_error << "mm\n";
```

### 相关文件
- `cpp_interface/include/depth_compensation/` - 头文件
- `cpp_interface/src/` - 实现文件
- `cpp_interface/tests/` - 单元测试
- `cpp_interface/examples/` - 示例代码
