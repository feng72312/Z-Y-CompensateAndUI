## MODIFIED Requirements

### Requirement: 重复精度服务初始化

系统应当提供服务类接口进行重复精度计算。

#### Scenario: 创建重复精度服务
- **WHEN** 实例化 RepeatabilityService
- **THEN** 可选地提供 ROIConfig 配置
- **AND** 可选地提供 FilterConfig 配置
- **AND** 可选地提供 DepthConversionConfig 配置
- **AND** 默认启用滤波

### Requirement: 重复精度计算

系统应当能够计算深度测量的重复精度。

#### Scenario: 计算目录重复精度
- **WHEN** 调用 calculate_repeatability(image_dir)
- **THEN** 读取目录下所有图像
- **AND** 应用 ROI 提取
- **AND** 应用滤波处理（如启用）
- **AND** 计算每张图像的平均深度值
- **AND** 计算所有图像平均值的标准差
- **AND** 返回 RepeatabilityResult 对象

#### Scenario: RepeatabilityResult 内容
- **WHEN** 返回重复精度结果
- **THEN** 包含 image_count: 图像数量
- **AND** 包含 mean_depth: 平均深度值（mm）
- **AND** 包含 std_dev: 标准差1σ（mm）
- **AND** 包含 repeatability_3sigma: 重复精度±3σ（mm）
- **AND** 包含 repeatability_6sigma: 重复精度6σ（mm）
- **AND** 包含 peak_to_peak: 极差（mm）
- **AND** 包含 within_image_std: 图像内平均标准差（mm）
- **AND** 包含 image_means: 每张图像的平均值列表

#### Scenario: 进度回调
- **WHEN** 提供 progress_callback 函数
- **THEN** 处理每张图像时调用回调
- **AND** 回调参数为 (current, total, message)

### Requirement: 重复精度指标

系统应当计算多个重复精度相关指标。

#### Scenario: 计算所有指标
- **WHEN** 完成重复精度计算
- **THEN** 返回图像数量
- **AND** 返回平均深度值（mm）
- **AND** 返回标准差1σ（mm）
- **AND** 返回重复精度±3σ（mm）
- **AND** 返回重复精度6σ（mm）
- **AND** 返回极差Peak-to-Peak（mm）
- **AND** 返回图像内平均标准差（mm）

### Requirement: ROI设置

系统应当支持灵活的ROI设置。

#### Scenario: 全图分析
- **WHEN** 选择全部图像模式（width=-1, height=-1）
- **THEN** 使用整张图像进行分析

#### Scenario: X方向ROI
- **WHEN** 仅指定X方向范围
- **THEN** X方向裁剪，Y方向使用全部

#### Scenario: Y方向ROI
- **WHEN** 仅指定Y方向范围
- **THEN** Y方向裁剪，X方向使用全部

#### Scenario: 自定义ROI
- **WHEN** 指定X和Y方向范围
- **THEN** 提取指定矩形区域

### Requirement: 滤波处理

系统应当支持可选的滤波处理。

#### Scenario: 启用滤波
- **WHEN** FilterConfig.enabled=True
- **THEN** 对每张图像应用标准滤波流程
- **AND** 包括异常值去除和中值滤波

#### Scenario: 禁用滤波
- **WHEN** FilterConfig.enabled=False
- **THEN** 直接使用原始深度值

### Requirement: 深度转换系数

系统应当支持自定义深度转换系数。

#### Scenario: 使用自定义系数
- **WHEN** 指定 DepthConversionConfig
- **THEN** 使用指定系数进行深度转换

#### Scenario: 使用默认系数
- **WHEN** 未指定配置
- **THEN** 使用默认值（offset=32768, scale_factor=1.6）

### Requirement: 报告生成

系统应当能够生成重复精度报告。

#### Scenario: 生成报告文件
- **WHEN** 指定输出路径
- **THEN** 生成详细的重复精度报告
- **AND** 包含测试参数、主要指标、逐图像详细数据

## ADDED Requirements

### Requirement: 图像平面标准差统计

系统应当计算图像内部的平面标准差。

#### Scenario: 计算图像内标准差
- **WHEN** 处理每张图像
- **THEN** 计算图像 ROI 内有效像素的标准差
- **AND** 记录到结果中

#### Scenario: 平均标准差计算
- **WHEN** 完成所有图像处理
- **THEN** 计算所有图像标准差的平均值
- **AND** 作为图像平整度/噪声指标

## 技术说明

### 深度转换公式
```
深度(mm) = (灰度值 - 偏移量) × 缩放因子 / 1000
```

### 重复精度结果参数说明

| 参数 | 单位 | 说明 |
|------|------|------|
| 图像数量 | 张 | 参与计算的有效图像数 |
| 平均深度值 | mm | 所有图像平均深度的均值 |
| 标准差(1σ) | mm | 图像间平均深度的标准差 |
| 重复精度(±3σ) | mm | 3×标准差，覆盖99.73%的测量 |
| 重复精度(6σ) | mm | 6×标准差，全分布宽度 |
| 极差(Peak-to-Peak) | mm | 最大值-最小值 |
| 图像内平均标准差 | mm | 单张图像内像素值的平均标准差 |

### 重复精度定义
- **1σ**: 标准差，表示68.27%的测量值分布范围
- **±3σ**: 99.73%的测量值分布范围，工业常用指标
- **6σ**: 全分布宽度（±3σ × 2）
- **极差**: 最大值 - 最小值，表示测量波动范围

### 支持的图像格式
- PNG格式 (*.png)
- TIF/TIFF格式 (*.tif, *.tiff)

### 相关文件
- `compcodeultimate/services/repeatability_service.py` - 重复精度服务
- `compcodeultimate/repeatability_calc.py` - 重复精度计算脚本
