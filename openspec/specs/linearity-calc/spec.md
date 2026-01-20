# 线性度计算模块

## 概述

线性度计算模块使用BFSL（Best Fit Straight Line）方法评估深度测量的线性度，支持补偿前后的对比分析。

## Requirements

### Requirement: BFSL线性度计算

系统应当使用BFSL方法计算线性度。

#### Scenario: 标准线性度计算
- **WHEN** 提供实际值和测量值序列
- **THEN** 进行零点归一化（相对值计算）
- **AND** 进行最小二乘线性拟合
- **AND** 计算最大偏差
- **AND** 线性度 = 最大偏差 / 满量程 × 100%

#### Scenario: 指定满量程
- **WHEN** 指定满量程参数
- **THEN** 使用指定值计算线性度百分比

#### Scenario: 自动满量程
- **WHEN** 未指定满量程
- **THEN** 使用实际值范围作为满量程

### Requirement: 线性度指标计算

系统应当计算多个线性度相关指标。

#### Scenario: 计算所有指标
- **WHEN** 完成线性度计算
- **THEN** 返回线性度百分比
- **AND** 返回最大正负偏差
- **AND** 返回RMS误差
- **AND** 返回平均绝对误差MAE
- **AND** 返回决定系数R²
- **AND** 返回拟合斜率和截距

### Requirement: 补偿效果评估

系统应当能够评估补偿前后的效果对比。

#### Scenario: 计算补偿效果
- **WHEN** 提供实际值、补偿前测量值、补偿后测量值
- **THEN** 分别计算补偿前后的线性度
- **AND** 计算改善幅度（%）

### Requirement: 批量线性度计算

系统应当支持批量处理多张深度图。

#### Scenario: 处理测试目录
- **WHEN** 指定包含深度图和CSV的测试目录
- **THEN** 读取所有图像文件（支持PNG和TIF格式）
- **AND** 从CSV读取对应的实际位移值
- **AND** 计算每张图的平均测量值
- **AND** 计算整体线性度

#### Scenario: 应用补偿模型
- **WHEN** 提供补偿模型文件
- **THEN** 同时计算补偿前后的线性度

#### Scenario: 生成报告
- **WHEN** 指定输出路径
- **THEN** 生成详细的线性度报告文本文件

### Requirement: 深度转换系数设置

系统应当支持自定义深度转换系数。

#### Scenario: 使用自定义系数
- **WHEN** 指定偏移量和缩放因子
- **THEN** 使用指定系数进行深度转换

#### Scenario: 使用默认系数
- **WHEN** 未指定系数
- **THEN** 使用配置文件中的默认值

## 技术说明

### BFSL计算流程
```python
# 1. 零点归一化
actual_rel = actual - actual[0]
measured_rel = measured - measured[0]

# 2. 线性拟合
slope, intercept = polyfit(actual_rel, measured_rel, 1)

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
- `compcodeultimate/compensator.py` - calculate_linearity函数
- `compcodeultimate/linearity_calc.py` - 批量线性度计算
