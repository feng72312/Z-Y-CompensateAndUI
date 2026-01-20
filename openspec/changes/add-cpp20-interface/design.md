# Design: C++20 深度补偿接口

## Context

从Python实现（v3.0）迁移到C++20，需要：
- 重新实现核心算法（三次样条、滤波、线性度计算）
- 保持与Python版本的功能对等
- 确保性能满足实时要求（< 1μs单次补偿）
- 提供易用的现代C++接口

**约束条件**：
- 无Python依赖
- 最小化第三方库
- 支持Qt集成
- 二进制兼容性（跨编译器）

## Goals / Non-Goals

### Goals
✅ **功能完整性**：实现全部Python功能  
✅ **性能优化**：单次补偿 < 1μs  
✅ **易用性**：现代C++接口，RAII，异常安全  
✅ **可测试性**：完整单元测试覆盖  
✅ **可移植性**：Windows/Linux/macOS  
✅ **Qt友好**：提供Qt集成示例  

### Non-Goals
❌ 不提供Python绑定（现有Python实现已足够）  
❌ 不支持GPU加速（暂不需要）  
❌ 不实现图像处理（仅数值补偿）  

## Decisions

### 1. 三次样条插值实现

**决策**：自实现三次B样条插值，移植SciPy的`splrep`/`splev`算法

**算法选择**：
```
方案A：使用第三方库（Eigen/GSL）
  ✅ 成熟稳定
  ❌ 重量级依赖（Eigen 100MB+）
  ❌ 增加构建复杂度

方案B：自实现三次B样条 ✓ (选择)
  ✅ 轻量级（~500行代码）
  ✅ 完全控制，易优化
  ✅ 与Python实现算法一致
  ❌ 需要仔细验证正确性
```

**实现细节**：
```cpp
class CubicSpline {
public:
    // 构建样条（等同于scipy.interpolate.splrep）
    static CubicSpline fit(
        std::span<const double> x,
        std::span<const double> y,
        int k = 3  // 样条阶数
    );
    
    // 评估样条（等同于scipy.interpolate.splev）
    double evaluate(double x) const;
    std::vector<double> evaluate(std::span<const double> x) const;
    
    // 计算导数（用于外推）
    double derivative(double x, int order = 1) const;

private:
    std::vector<double> knots_;      // 节点向量
    std::vector<double> coefficients_; // 系数
    int k_;                           // 阶数
};
```

**验证策略**：
- 与Python实现的结果对比（相同输入，误差 < 1e-10）
- 边界条件测试
- 性能基准测试

### 2. JSON处理

**决策**：使用 nlohmann/json（header-only库）

**对比**：
```
方案A：nlohmann/json ✓ (选择)
  ✅ Header-only，易集成
  ✅ 现代C++ API（类似Python dict）
  ✅ 成熟稳定，广泛使用
  ❌ 编译时间稍长

方案B：rapidjson
  ✅ 更快的解析速度
  ❌ C风格API，不够现代
  ❌ 错误处理不够友好

方案C：自实现
  ✅ 轻量级
  ❌ 开发成本高
  ❌ 边界情况处理复杂
```

**使用示例**：
```cpp
#include <nlohmann/json.hpp>
using json = nlohmann::json;

// 序列化模型
json j = {
    {"model_type", "cubic_spline"},
    {"version", "2.2"},
    {"knots", model.knots()},
    {"coefficients", model.coefficients()},
    {"k", model.order()},
    {"x_range", {model.x_min(), model.x_max()}},
    {"y_range", {model.y_min(), model.y_max()}}
};

// 反序列化
auto model = CompensationModel::from_json(j);
```

### 3. 配置管理

**决策**：使用结构体 + 指定初始化器（C++20）

**设计**：
```cpp
// 现代C++20风格
struct ExtrapolateConfig {
    bool enabled = true;
    double max_low = 2.0;   // mm
    double max_high = 2.0;  // mm
    double output_min = 0.0;
    double output_max = 43.0;
    bool clamp_output = true;
};

// 使用
ExtrapolateConfig config{
    .enabled = true,
    .max_low = 3.0  // 覆盖默认值
};
```

**对比Builder模式**：
```cpp
// Builder模式（更冗长）
auto config = ExtrapolateConfig::Builder()
    .enabled(true)
    .maxLow(3.0)
    .build();
```

**选择理由**：
- ✅ 简洁直观
- ✅ 编译期检查
- ✅ 默认值清晰
- ❌ 需要C++20支持

### 4. 错误处理策略

**决策**：异常 + 错误码混合

**异常**（不可恢复错误）：
```cpp
class CompensationError : public std::runtime_error {
public:
    explicit CompensationError(const std::string& msg)
        : std::runtime_error(msg) {}
};

class ModelLoadError : public CompensationError { ... };
class InvalidDataError : public CompensationError { ... };

// 使用
try {
    model.load("model.json");
} catch (const ModelLoadError& e) {
    // 处理加载失败
}
```

**错误码**（可预期错误）：
```cpp
enum class CompensateResult {
    Success,
    OutOfRange,      // 超出模型范围
    Extrapolated,    // 使用了外推
    Clamped          // 输出被限制
};

struct CompensateOutput {
    double value;
    CompensateResult result;
};

// 使用
auto [value, result] = service.compensate_with_status(measured);
if (result == CompensateResult::OutOfRange) {
    // 处理超范围情况
}
```

### 5. 内存管理

**决策**：智能指针 + RAII

**原则**：
```cpp
// ✅ 使用智能指针
class CompensationService {
private:
    std::unique_ptr<CompensationModel> model_;  // 独占所有权
};

// ✅ RAII管理资源
class ModelFile {
public:
    explicit ModelFile(const std::string& path);
    ~ModelFile();  // 自动关闭文件
    
    ModelFile(const ModelFile&) = delete;  // 禁止拷贝
    ModelFile(ModelFile&&) = default;      // 允许移动
};

// ❌ 避免裸指针
// CompensationModel* model = new CompensationModel();  // NO!
```

### 6. 性能优化

**策略**：

**A. 避免拷贝**：
```cpp
// 使用 std::span（C++20）避免拷贝
std::vector<double> compensate(std::span<const double> measured);

// 移动语义
std::vector<double> result = service.compensate(std::move(data));
```

**B. 编译期计算**：
```cpp
constexpr double OFFSET = 32768.0;
constexpr double SCALE_FACTOR = 1.6;

constexpr double gray_to_mm(uint16_t gray) {
    return ((gray - OFFSET) * SCALE_FACTOR) / 1000.0;
}
```

**C. 缓存友好**：
```cpp
// 连续内存布局
struct CalibrationPoint {
    double actual;
    double measured;
};
std::vector<CalibrationPoint> points;  // 缓存友好
```

**D. 可选并行**：
```cpp
#include <execution>

// 批量补偿支持并行
std::transform(
    std::execution::par,  // 并行执行
    measured.begin(), measured.end(),
    result.begin(),
    [&](double m) { return service.compensate(m); }
);
```

### 7. Qt集成设计

**信号/槽支持**：
```cpp
// Qt友好的进度回调
class QtCalibrationService : public QObject {
    Q_OBJECT
signals:
    void progressChanged(int current, int total, QString message);
    void calibrationCompleted(CalibrationResult result);
    void errorOccurred(QString error);

public:
    void processCalibrationDataAsync(
        const QVector<double>& actual,
        const QVector<double>& measured
    );
};
```

**类型转换**：
```cpp
// std::vector <-> QVector 转换
template<typename T>
QVector<T> toQt(const std::vector<T>& vec) {
    return QVector<T>(vec.begin(), vec.end());
}

template<typename T>
std::vector<T> fromQt(const QVector<T>& vec) {
    return std::vector<T>(vec.begin(), vec.end());
}
```

## Risks / Trade-offs

### Risk 1: 算法移植正确性

**风险**：自实现样条插值可能与SciPy存在差异

**缓解措施**：
- ✅ 逐函数对比Python输出
- ✅ 建立回归测试套件
- ✅ 使用相同测试数据验证
- ✅ 边界条件详尽测试

**验收标准**：
- 相同输入下，补偿结果误差 < 1e-10
- 所有Python单元测试在C++版本通过

### Risk 2: 性能不达标

**风险**：C++实现未达到 < 1μs 目标

**缓解措施**：
- ✅ 早期性能基准测试
- ✅ Profile热点代码
- ✅ 使用优化编译选项（-O3）
- ✅ 考虑使用SIMD优化

**回退方案**：
- 若单次补偿 > 1μs，提供批量接口分摊开销

### Risk 3: ABI兼容性

**风险**：不同编译器生成的二进制不兼容

**缓解措施**：
- ✅ 提供纯C接口（extern "C"）作为stable ABI
- ✅ 使用Pimpl模式隐藏实现细节
- ✅ 文档明确编译器要求

### Trade-off 1: 依赖 vs 实现复杂度

**选择**：最小化依赖，自实现核心算法

**代价**：
- ❌ 开发时间增加（~2周）
- ❌ 需要更多测试验证

**收益**：
- ✅ 部署简单，无复杂依赖
- ✅ 完全控制，易于优化
- ✅ 代码库轻量（< 5000行）

### Trade-off 2: 功能完整性 vs 开发速度

**选择**：实现全部功能（标定+补偿+评估）

**代价**：
- ❌ 初始版本交付时间长（~1月）

**收益**：
- ✅ 一次性满足所有需求
- ✅ API一致性更好
- ✅ 避免后续breaking changes

## Migration Plan

### Phase 1: 核心功能（Week 1-2）
1. 三次样条插值实现
2. 补偿模型加载/保存
3. 单值/批量补偿接口
4. 单元测试覆盖

### Phase 2: 扩展功能（Week 3-4）
1. 外推配置
2. 归一化配置
3. 标定功能
4. 线性度/重复精度评估

### Phase 3: 集成和示例（Week 5）
1. Qt集成示例
2. 文档完善
3. 性能基准测试
4. 发布v1.0

**验收标准**：
- ✅ 所有功能与Python对等
- ✅ 单次补偿 < 1μs
- ✅ 单元测试覆盖 > 90%
- ✅ Qt集成示例可运行

## Open Questions

1. **JSON库选择**：nlohmann/json vs rapidjson？
   - 建议：nlohmann/json（易用性优先）

2. **构建系统**：支持哪些构建工具？
   - CMake（必须）
   - Bazel（可选）
   - vcpkg/conan（依赖管理）

3. **文档工具**：Doxygen vs Sphinx？
   - 建议：Doxygen（C++标准）

4. **发布方式**：header-only vs 编译库？
   - 建议：提供两种选项
   - header-only：开发便捷
   - 编译库：编译时间短

5. **版本策略**：C++版本与Python版本如何对应？
   - 建议：独立版本号（v1.0开始）
   - 在文档中标注对应的Python版本
