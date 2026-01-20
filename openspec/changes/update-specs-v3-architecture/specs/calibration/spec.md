## MODIFIED Requirements

### Requirement: 标定服务初始化

系统应当提供服务类接口进行标定操作。

#### Scenario: 创建标定服务
- **WHEN** 实例化 CalibrationService
- **THEN** 可选地提供 FilterConfig 滤波配置
- **AND** 可选地提供 ROIConfig 区域配置
- **AND** 可选地提供 DepthConversionConfig 深度转换配置

### Requirement: 标定数据处理

系统应当能够处理标定目录并建立补偿模型。

#### Scenario: 处理标定数据
- **WHEN** 调用 process_calibration_data(calib_dir)
- **THEN** 自动发现目录下的 PNG 文件和 CSV 文件
- **AND** 逐张处理标定图像
- **AND** 应用 ROI 提取
- **AND** 应用滤波处理（如启用）
- **AND** 应用平面校准
- **AND** 计算平均深度值
- **AND** 跳过无效图像（有效像素<10%）
- **AND** 建立补偿模型
- **AND** 返回处理结果字典

#### Scenario: 进度回调
- **WHEN** 提供 progress_callback 函数
- **THEN** 处理每张图像时调用回调
- **AND** 回调参数为 (current, total, message)

#### Scenario: 标定数据不足
- **WHEN** 有效图像少于4张
- **THEN** 抛出 ValueError "数据点不足"

### Requirement: 深度图读取

系统应当能够读取16位PNG深度图。

#### Scenario: 正常读取
- **WHEN** 提供有效的16位PNG文件路径
- **THEN** 读取并返回uint16数组

#### Scenario: 文件不存在
- **WHEN** 文件路径无效
- **THEN** 抛出 FileNotFoundError

#### Scenario: 支持多种格式
- **WHEN** 文件为 TIF/TIFF 格式
- **THEN** 同样能正确读取

### Requirement: ROI提取

系统应当能够从深度图中提取感兴趣区域(ROI)。

#### Scenario: 使用 ROIConfig 对象
- **WHEN** 提供 ROIConfig(x, y, width, height)
- **THEN** 提取对应区域的子图像

#### Scenario: 使用全图
- **WHEN** width=-1 或 height=-1
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
- **THEN** 排除值为无效值（默认65535）的像素
- **AND** 返回有效像素数组和掩码

#### Scenario: 有效像素不足
- **WHEN** 有效像素比例低于10%
- **THEN** 跳过该图像
- **AND** 记录到跳过列表

### Requirement: 平面校准

系统应当能够去除深度图的平面倾斜。

#### Scenario: 平面拟合
- **WHEN** 启用平面校准
- **THEN** 对有效像素进行3D平面拟合
- **AND** 从原始值中减去拟合平面
- **AND** 保留真实的深度偏差

### Requirement: 滤波处理

系统应当提供多种滤波处理方法。

#### Scenario: 使用 FilterConfig 对象
- **WHEN** 提供 FilterConfig 配置
- **THEN** 根据配置决定是否启用滤波
- **AND** 配置包含：outlier_std_factor, median_filter_size, gaussian_filter_sigma

#### Scenario: 异常值去除
- **WHEN** 启用滤波（FilterConfig.enabled=True）
- **THEN** 计算有效像素的均值和标准差
- **AND** 将超出 outlier_std_factor × σ 范围的像素标记为无效

#### Scenario: 中值滤波
- **WHEN** 启用滤波
- **THEN** 使用 median_filter_size 窗口进行中值滤波
- **AND** 无效像素使用有效均值填充（关键修复v2.1）
- **AND** 滤波后恢复无效像素标记

#### Scenario: 高斯滤波
- **WHEN** 启用滤波
- **THEN** 使用 gaussian_filter_sigma 进行高斯平滑

### Requirement: CSV数据读取

系统应当能够读取标定位移数据。

#### Scenario: 自动发现CSV
- **WHEN** 调用 get_image_files(directory)
- **THEN** 自动查找目录下的CSV文件
- **AND** 读取"实际累计位移(mm)"列
- **AND** 与PNG文件按序号匹配

#### Scenario: CSV文件缺失
- **WHEN** 目录下没有CSV文件
- **THEN** 抛出 FileNotFoundError

## ADDED Requirements

### Requirement: 模型保存

系统应当能够保存建立的补偿模型。

#### Scenario: 保存到文件
- **WHEN** 调用 save_model(filepath)
- **THEN** 将内部模型保存为 JSON 文件
- **AND** 模型包含完整的标定数据

### Requirement: 数据质量检测

系统应当能够检测标定数据质量。

#### Scenario: 异常点检测
- **WHEN** config.ANOMALY_DETECTION_ENABLED=True
- **AND** 测量增量与实际增量偏差超过阈值
- **THEN** 记录警告日志
- **AND** 标记可能的异常点

#### Scenario: 平面标准差警告
- **WHEN** config.PLANE_STD_WARNING_ENABLED=True
- **AND** 图像平面标准差超过阈值
- **THEN** 记录警告日志
- **AND** 提示数据质量问题

## 技术说明

### 滤波参数默认值
- 异常值阈值：3σ
- 中值滤波窗口：3×3
- 高斯滤波sigma：1.0

### 关键修复（v2.1）
滤波时无效像素使用有效像素均值填充，而非0，避免边界像素灰度值被拉低。

### 配置对象结构
```python
@dataclass
class FilterConfig:
    enabled: bool = True
    outlier_std_factor: float = 3.0
    median_filter_size: int = 3
    gaussian_filter_sigma: float = 1.0

@dataclass
class ROIConfig:
    x: int = 0
    y: int = 0
    width: int = -1
    height: int = -1
```

### 相关文件
- `compcodeultimate/core/calibrator.py` - 平面校准和滤波
- `compcodeultimate/core/spline_model.py` - 模型构建
- `compcodeultimate/data/io.py` - 文件读写
- `compcodeultimate/services/calibration_service.py` - 标定服务
