## MODIFIED Requirements

### Requirement: 补偿服务初始化

系统应当提供服务类接口进行补偿操作。

#### Scenario: 创建补偿服务
- **WHEN** 实例化 CompensationService
- **THEN** 可选地提供初始模型
- **AND** 可选地提供外推配置
- **AND** 可选地提供归一化配置
- **AND** 可选地提供深度转换配置

#### Scenario: 加载已有模型
- **WHEN** 调用 load_model(model_path)
- **THEN** 从JSON文件加载模型
- **AND** 自动计算归一化偏移（如启用）
- **AND** 返回加载的模型对象

### Requirement: 补偿模型构建

系统应当能够基于标定数据构建补偿模型。

#### Scenario: 正常构建模型
- **WHEN** 提供至少4个标定点（实际值和测量值对）
- **THEN** 系统构建三次样条插值模型
- **AND** 生成正向模型（实际值→测量值）
- **AND** 生成逆向模型（测量值→实际值）
- **AND** 存储标定数据用于分析

#### Scenario: 动态阶数调整
- **WHEN** 数据点少于默认阶数+1
- **THEN** 自动降低样条阶数 k = min(3, len-1)
- **AND** 确保模型可以成功构建

#### Scenario: 数据点不足
- **WHEN** 提供少于 k+1 个标定点（k为调整后的阶数）
- **THEN** 系统抛出 ValueError "数据点不足"

#### Scenario: 数据包含无效值
- **WHEN** 标定数据包含NaN或Inf
- **THEN** 系统抛出 ValueError "数据无效"

#### Scenario: 数据包含重复值
- **WHEN** 实际值或测量值存在重复
- **THEN** 系统抛出 ValueError "存在重复"

### Requirement: 单值补偿

系统应当能够对单个测量值进行补偿。

#### Scenario: 范围内补偿
- **WHEN** 测量值在模型有效范围内
- **AND** 外推未启用或禁用
- **THEN** 使用样条插值计算补偿后的实际值

#### Scenario: 超出范围启用外推
- **WHEN** 测量值超出模型范围
- **AND** 启用了线性外推功能（ExtrapolateConfig.enabled=True）
- **AND** 超出距离在允许的外推范围内（max_low/max_high）
- **THEN** 使用边界处导数进行线性外推计算补偿值

#### Scenario: 超出范围禁用外推
- **WHEN** 测量值超出模型范围
- **AND** 未启用线性外推
- **THEN** 使用样条插值的边界外推（ext=0）

#### Scenario: 标量返回类型一致性
- **WHEN** 输入为标量（float或int）
- **THEN** 返回 Python `float` 类型
- **AND** `isinstance(result, float)` 返回 True
- **AND** 无论外推是否启用，类型保持一致

#### Scenario: 数组返回类型
- **WHEN** 输入为数组（np.ndarray）
- **THEN** 返回 `np.ndarray` 类型

### Requirement: 批量补偿

系统应当能够对多个测量值进行批量补偿。

#### Scenario: 批量补偿数组
- **WHEN** 提供测量值数组
- **THEN** 对每个值应用补偿（向量化处理）
- **AND** 返回相同长度和形状的补偿后数组

### Requirement: 深度图像素补偿

系统应当能够对整张深度图进行逐像素补偿。

#### Scenario: 正常补偿深度图
- **WHEN** 提供16位深度图数组
- **THEN** 将灰度值转换为毫米值
- **AND** 应用补偿模型（含外推）
- **AND** 应用归一化偏移（如启用）
- **AND** 将结果转换回灰度值
- **AND** 保持无效像素（65535）不变

#### Scenario: 统计补偿信息
- **WHEN** 完成深度图补偿
- **THEN** 返回 CompensationResult 对象包含：
  - total_pixels: 总像素数
  - valid_pixels: 有效像素数
  - in_range_pixels: 范围内像素数
  - extrapolated_pixels: 外推像素数
  - compensated_pixels: 已补偿像素数
  - out_of_range_pixels: 超出范围像素数
  - compensation_rate: 补偿率（%）

### Requirement: 外推配置

系统应当支持灵活的外推配置。

#### Scenario: 设置外推参数
- **WHEN** 创建 ExtrapolateConfig 对象
- **THEN** 可配置是否启用外推（enabled）
- **AND** 可配置低端最大外推距离（max_low，默认2.0mm）
- **AND** 可配置高端最大外推距离（max_high，默认2.0mm）
- **AND** 可配置输出值范围（output_min, output_max）
- **AND** 可配置是否限制输出范围（clamp_output）

#### Scenario: 获取外推统计
- **WHEN** 调用 get_extrapolation_stats
- **THEN** 返回外推统计信息：
  - total_count: 总数量
  - in_range_count: 范围内数量
  - below_range_count: 低于范围数量
  - above_range_count: 高于范围数量
  - below_range_max_dist: 低端最大外推距离
  - above_range_max_dist: 高端最大外推距离

#### Scenario: 计算扩展范围
- **WHEN** 启用外推
- **THEN** calculate_extended_range 返回包含外推的扩展范围
- **AND** extended_min = x_min - max_low
- **AND** extended_max = x_max + max_high

### Requirement: 归一化配置

系统应当支持输出归一化功能。

#### Scenario: 自动偏移计算
- **WHEN** 启用归一化且 auto_offset=True
- **THEN** 根据模型 y_range 自动计算偏移量
- **AND** offset = target_center - (y_min + y_max) / 2

#### Scenario: 手动偏移设置
- **WHEN** 启用归一化且 auto_offset=False
- **THEN** 使用 manual_offset 作为偏移量

#### Scenario: 禁用归一化
- **WHEN** normalize.enabled=False
- **THEN** 偏移量为0，不修改输出

### Requirement: 模型持久化

系统应当能够保存和加载补偿模型。

#### Scenario: 保存模型
- **WHEN** 请求保存模型
- **THEN** 将模型参数保存为JSON格式
- **AND** 包含 version="2.2"
- **AND** 包含节点、系数、阶数、有效范围
- **AND** 包含标定点数据（actual_values, measured_values）
- **AND** 包含正向模型参数（可选）

#### Scenario: 加载模型
- **WHEN** 提供有效的JSON模型文件
- **THEN** 解析并恢复 CompensationModel 对象
- **AND** 模型可用于补偿计算

## ADDED Requirements

### Requirement: 批量图像补偿

系统应当支持批量处理多张图像。

#### Scenario: 批量补偿目录
- **WHEN** 调用 compensate_batch(input_dir, output_dir)
- **THEN** 处理输入目录下所有 PNG 文件
- **AND** 保存补偿后图像到输出目录
- **AND** 返回 BatchProcessResult 包含：
  - total_files: 总文件数
  - success_count: 成功数量
  - failed_files: 失败文件列表
  - total_compensation_rate: 总体补偿率

#### Scenario: 进度回调
- **WHEN** 提供 progress_callback 函数
- **THEN** 定期调用回调报告进度
- **AND** 回调参数为 (current, total, message)

### Requirement: 模型信息查询

系统应当能够查询模型状态和信息。

#### Scenario: 检查模型加载状态
- **WHEN** 调用 model_loaded 属性
- **THEN** 返回模型是否已加载（bool）

#### Scenario: 获取模型信息
- **WHEN** 调用 get_model_info()
- **THEN** 返回字典包含：
  - calibration_points: 标定点数量
  - input_range: 输入范围 (x_min, x_max)
  - output_range: 输出范围 (y_min, y_max)
  - version: 模型版本

## 技术说明

### 深度转换公式
```
深度(mm) = (灰度值 - OFFSET) × SCALE_FACTOR / 1000
灰度值 = 深度(mm) × 1000 / SCALE_FACTOR + OFFSET
```

### 模型JSON格式
```json
{
  "model_type": "cubic_spline",
  "version": "2.2",
  "knots": [...],
  "coefficients": [...],
  "k": 3,
  "x_range": [min, max],
  "y_range": [min, max],
  "calibration_points": 9,
  "actual_values": [...],
  "measured_values": [...],
  "forward_knots": [...],
  "forward_coefficients": [...]
}
```

### 配置对象
- **ExtrapolateConfig**: 外推配置
- **NormalizeConfig**: 归一化配置
- **DepthConversionConfig**: 深度转换配置

### 相关文件
- `compcodeultimate/core/spline_model.py` - 样条模型构建
- `compcodeultimate/core/compensator.py` - 补偿功能
- `compcodeultimate/core/extrapolator.py` - 外推功能
- `compcodeultimate/data/converters.py` - 深度转换工具函数
- `compcodeultimate/data/io.py` - 模型读写
- `compcodeultimate/services/compensation_service.py` - 补偿服务
- `compcodeultimate/config.py` - 配置参数
