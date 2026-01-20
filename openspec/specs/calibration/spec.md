# 标定处理模块

## 概述

标定处理模块负责处理深度图的平面校准和滤波处理，为补偿模型提供高质量的标定数据。

## Requirements

### Requirement: 深度图读取

系统应当能够读取16位PNG深度图。

#### Scenario: 正常读取
- **WHEN** 提供有效的16位PNG文件路径
- **THEN** 读取并返回uint16数组

#### Scenario: 文件不存在
- **WHEN** 文件路径无效
- **THEN** 抛出文件未找到错误

### Requirement: ROI提取

系统应当能够从深度图中提取感兴趣区域(ROI)。

#### Scenario: 指定ROI区域
- **WHEN** 指定X起始、Y起始、宽度、高度
- **THEN** 提取对应区域的子图像

#### Scenario: 使用全图
- **WHEN** 宽度或高度设为-1
- **THEN** 使用图像完整尺寸

#### Scenario: X方向ROI
- **WHEN** 仅指定X方向范围
- **THEN** X方向裁剪，Y方向使用全部

#### Scenario: Y方向ROI
- **WHEN** 仅指定Y方向范围
- **THEN** Y方向裁剪，X方向使用全部

### Requirement: 有效像素提取

系统应当能够识别和提取有效像素。

#### Scenario: 过滤无效值
- **WHEN** 处理深度图
- **THEN** 排除值为65535的无效像素
- **AND** 返回有效像素数组和掩码

#### Scenario: 有效像素不足
- **WHEN** 有效像素比例低于10%
- **THEN** 标记处理失败

### Requirement: 平面校准

系统应当能够去除深度图的平面倾斜。

#### Scenario: 平面拟合
- **WHEN** 启用平面校准
- **THEN** 对有效像素进行平面拟合
- **AND** 从原始值中减去拟合平面
- **AND** 保留真实的深度偏差

### Requirement: 滤波处理

系统应当提供多种滤波处理方法。

#### Scenario: 异常值去除
- **WHEN** 启用3σ异常值去除
- **THEN** 计算有效像素的均值和标准差
- **AND** 将超出3σ范围的像素标记为无效

#### Scenario: 中值滤波
- **WHEN** 启用中值滤波
- **THEN** 使用指定窗口大小进行中值滤波
- **AND** 无效像素使用有效均值填充（不是0）

#### Scenario: 高斯滤波
- **WHEN** 启用高斯滤波
- **THEN** 使用指定sigma进行高斯平滑

### Requirement: CSV数据读取

系统应当能够读取标定位移数据。

#### Scenario: 读取位移CSV
- **WHEN** 提供CSV文件
- **THEN** 读取"实际累计位移(mm)"列
- **AND** 与PNG文件按序号匹配

## 技术说明

### 滤波参数默认值
- 异常值阈值：3σ
- 中值滤波窗口：3×3
- 高斯滤波sigma：1.0

### 关键修复（v2.1）
滤波时无效像素使用有效像素均值填充，而非0，避免边界像素灰度值被拉低。

### 相关文件
- `compcodeultimate/calibrator.py` - 平面校准和滤波
- `compcodeultimate/utils.py` - 深度图读取、ROI提取
