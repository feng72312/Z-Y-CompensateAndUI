# 深度补偿核心模块

## 概述

深度补偿核心模块提供深度图的补偿功能，使用三次样条插值模型将测量值转换为实际值，提高测量精度。

## Requirements

### Requirement: 补偿模型构建

系统应当能够基于标定数据构建补偿模型。

#### Scenario: 正常构建模型
- **WHEN** 提供至少4个标定点（实际值和测量值对）
- **THEN** 系统构建三次样条插值模型
- **AND** 生成正向模型（实际值→测量值）
- **AND** 生成逆向模型（测量值→实际值）

#### Scenario: 数据点不足
- **WHEN** 提供少于4个标定点
- **THEN** 系统抛出错误提示"数据点不足"

#### Scenario: 数据包含无效值
- **WHEN** 标定数据包含NaN或Inf
- **THEN** 系统抛出错误提示"数据无效"

### Requirement: 单值补偿

系统应当能够对单个测量值进行补偿。

#### Scenario: 范围内补偿
- **WHEN** 测量值在模型有效范围内
- **THEN** 使用样条插值计算补偿后的实际值

#### Scenario: 超出范围启用外推
- **WHEN** 测量值超出模型范围
- **AND** 启用了线性外推功能
- **AND** 超出距离在允许的外推范围内
- **THEN** 使用边界处的线性外推计算补偿值

#### Scenario: 超出范围禁用外推
- **WHEN** 测量值超出模型范围
- **AND** 未启用线性外推
- **THEN** 返回边界值（钳位处理）

### Requirement: 批量补偿

系统应当能够对多个测量值进行批量补偿。

#### Scenario: 批量补偿数组
- **WHEN** 提供测量值数组
- **THEN** 对每个值应用补偿
- **AND** 返回相同长度的补偿后数组

### Requirement: 深度图像素补偿

系统应当能够对整张深度图进行逐像素补偿。

#### Scenario: 正常补偿深度图
- **WHEN** 提供16位深度图数组
- **THEN** 将灰度值转换为毫米值
- **AND** 应用补偿模型
- **AND** 将结果转换回灰度值
- **AND** 保持无效像素（65535）不变

#### Scenario: 统计补偿信息
- **WHEN** 完成深度图补偿
- **THEN** 返回统计信息（有效像素数、范围内像素数、补偿率）

### Requirement: 模型持久化

系统应当能够保存和加载补偿模型。

#### Scenario: 保存模型
- **WHEN** 请求保存模型
- **THEN** 将模型参数保存为JSON格式
- **AND** 包含节点、系数、阶数、有效范围等信息

#### Scenario: 加载模型
- **WHEN** 提供有效的JSON模型文件
- **THEN** 解析并恢复模型参数
- **AND** 模型可用于补偿计算

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
  "y_range": [min, max]
}
```

### 相关文件
- `compcodeultimate/compensator.py` - 补偿模型实现
- `compcodeultimate/utils.py` - 深度转换工具函数
- `compcodeultimate/config.py` - 配置参数
