## MODIFIED Requirements

### Requirement: 线性度服务初始化

系统应当提供服务类接口进行线性度计算。

#### Scenario: 创建线性度服务
- **WHEN** 实例化 LinearityService
- **THEN** 可指定满量程（full_scale）
- **AND** 可提供 ROIConfig, FilterConfig, DepthConversionConfig

### Requirement: BFSL线性度计算

系统应当使用BFSL方法计算线性度。

#### Scenario: 标准线性度计算
- **WHEN** 提供实际值和测量值序列
- **THEN** 进行零点归一化（相对值计算）
- **AND** 进行最小二乘线性拟合
- **AND** 计算最大偏差
- **AND** 线性度 = 最大偏差 / 满量程 × 100%

#### Scenario: 返回 LinearityResult 对象
- **WHEN** 完成线性度计算
- **THEN** 返回 LinearityResult 包含：
  - linearity: 线性度百分比
  - max_deviation: 最大正偏差
  - min_deviation: 最小负偏差
  - abs_max_deviation: 绝对最大偏差
  - rms_error: RMS误差
  - mae: 平均绝对误差
  - r_squared: R²决定系数
  - slope: 拟合斜率
  - intercept: 拟合截距

#### Scenario: 指定满量程
- **WHEN** 指定 full_scale 参数
- **THEN** 使用指定值计算线性度百分比

#### Scenario: 自动满量程
- **WHEN** 未指定满量程
- **THEN** 使用默认值 41.0mm

#### Scenario: 数据验证
- **WHEN** 数据点少于2个
- **THEN** 抛出 ValueError "数据点不足"

#### Scenario: 数据长度不匹配
- **WHEN** actual_values 和 measured_values 长度不同
- **THEN** 抛出 ValueError "数据长度不匹配"

### Requirement: 补偿效果评估

系统应当能够评估补偿前后的效果对比。

#### Scenario: 计算补偿效果
- **WHEN** 提供实际值、补偿前测量值、补偿后测量值
- **THEN** 分别计算补偿前后的线性度
- **AND** 计算改善幅度（%）= (before - after) / before × 100%
- **AND** 返回 CompensationEffectResult 对象

#### Scenario: CompensationEffectResult 内容
- **WHEN** 返回补偿效果结果
- **THEN** 包含 before: LinearityResult
- **AND** 包含 after: LinearityResult
- **AND** 包含 improvement: float (改善幅度%)
- **AND** 包含原始数据数组用于绘图分析

### Requirement: 批量线性度计算

系统应当支持批量处理多张深度图。

#### Scenario: 处理测试目录
- **WHEN** 调用 calculate_from_directory(test_dir, model)
- **THEN** 读取所有图像文件（支持PNG和TIF格式）
- **AND** 从CSV读取对应的实际位移值
- **AND** 计算每张图的平均测量值
- **AND** 应用补偿（如提供模型）
- **AND** 计算整体线性度

#### Scenario: 进度回调
- **WHEN** 提供 progress_callback 函数
- **THEN** 定期调用回调报告进度
- **AND** 回调参数为 (current, total, message)

#### Scenario: 生成报告
- **WHEN** 指定输出路径
- **THEN** 生成详细的线性度报告文本文件
- **AND** 包含补偿前后对比数据

### Requirement: 零点归一化

系统应当提供零点归一化功能。

#### Scenario: 转换为相对值
- **WHEN** 调用 normalize_to_relative(values)
- **THEN** 返回相对值数组
- **AND** 第一个元素为0
- **AND** 保持相对差值不变

### Requirement: 深度转换系数设置

系统应当支持自定义深度转换系数。

#### Scenario: 使用自定义系数
- **WHEN** 指定 DepthConversionConfig
- **THEN** 使用指定的 offset 和 scale_factor 进行深度转换

#### Scenario: 使用默认系数
- **WHEN** 未指定配置
- **THEN** 使用默认值（offset=32768, scale_factor=1.6）

## 技术说明

### BFSL计算流程
```python
# 1. 零点归一化
actual_rel = actual - actual[0]
measured_rel = measured - measured[0]

# 2. 线性拟合
slope, intercept = np.polyfit(actual_rel, measured_rel, 1)

# 3. 计算偏差
predicted = slope * actual_rel + intercept
deviations = measured_rel - predicted

# 4. 线性度
linearity = max(|deviations|) / full_scale × 100%
```

### 线性度结果参数说明

| 参数 | 单位 | 说明 |
|------|------|------|
| 线性度 | % | 最大偏差/满量程×100%，越小越好 |
| 最大正偏差 | mm | 测量值高于拟合线的最大距离 |
| 最大负偏差 | mm | 测量值低于拟合线的最大距离 |
| 绝对最大偏差 | mm | max(\|正偏差\|, \|负偏差\|) |
| RMS误差 | mm | 偏差的均方根值，反映整体偏离程度 |
| MAE | mm | 平均绝对误差 |
| R² | - | 决定系数，越接近1拟合越好 |
| 斜率 | - | 拟合直线斜率，理想值为1 |
| 截距 | mm | 拟合直线截距，理想值为0 |

### RMS误差含义
RMS误差表示测量值与最佳拟合直线之间偏差的均方根值，反映系统的整体偏离程度。
计算公式：RMS = √(Σ(偏差²)/n)

### 支持的图像格式
- PNG格式 (*.png)
- TIF/TIFF格式 (*.tif, *.tiff)

### 相关文件
- `compcodeultimate/core/linearity.py` - 线性度计算实现
- `compcodeultimate/services/linearity_service.py` - 线性度服务
- `compcodeultimate/linearity_calc.py` - 批量计算脚本
