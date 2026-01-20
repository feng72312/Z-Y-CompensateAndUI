## MODIFIED Requirements

### Requirement: 完整流程标签页

系统应当提供完整的标定和测试流程界面。

#### Scenario: 配置输入路径
- **WHEN** 用户点击浏览按钮
- **THEN** 显示目录选择对话框
- **AND** 可选择标定目录、测试目录、输出目录

#### Scenario: 配置参数设置
- **WHEN** 用户需要调整参数
- **THEN** 可设置满量程、异常值阈值、中值滤波窗口
- **AND** 可设置深度转换偏移量和缩放因子
- **AND** 可设置是否启用滤波

#### Scenario: 配置外推参数
- **WHEN** 用户需要配置外推功能
- **THEN** 可设置是否启用外推
- **AND** 可设置低端高端最大外推距离（max_low, max_high）
- **AND** 可设置输出值范围限制（output_min, output_max）

#### Scenario: 配置归一化参数
- **WHEN** 用户需要配置归一化功能
- **THEN** 可设置是否启用归一化
- **AND** 可设置目标中心点（target_center）
- **AND** 可选择自动或手动偏移计算
- **AND** 显示计算出的偏移量

#### Scenario: 配置ROI设置
- **WHEN** 用户需要限制分析区域
- **THEN** 可选择全部图像或X方向或Y方向或自定义ROI
- **AND** 可设置起始和结束坐标

#### Scenario: 运行标定流程
- **WHEN** 用户点击开始标定
- **THEN** 在后台线程执行处理标定数据
- **AND** 建立补偿模型
- **AND** 处理测试数据
- **AND** 计算线性度
- **AND** 计算每张图像平面的标准差
- **AND** 计算补偿前后标准差的平均值
- **AND** 实时显示日志
- **AND** 完成后显示结果指标

#### Scenario: 显示补偿结果
- **WHEN** 完整流程执行完成
- **THEN** 显示补偿前线性度（%）
- **AND** 显示补偿后线性度（%）
- **AND** 显示补偿前最大偏差（mm）
- **AND** 显示补偿后最大偏差（mm）
- **AND** 显示补偿前RMS误差（mm）
- **AND** 显示补偿后RMS误差（mm）
- **AND** 显示补偿前图像平面标准差平均值（mm）
- **AND** 显示补偿后图像平面标准差平均值（mm）
- **AND** 显示改善幅度（%）
- **AND** 显示R²决定系数

### Requirement: 补偿模式标签页

系统应当提供模型加载和批量补偿功能。

#### Scenario: 加载补偿模型
- **WHEN** 用户选择JSON模型文件
- **AND** 点击加载模型
- **THEN** 调用 CompensationService.load_model
- **AND** 显示模型信息（标定点数、输入输出范围）
- **AND** 模型状态更新为已加载
- **AND** 显示归一化偏移量（如启用）

#### Scenario: 配置外推参数
- **WHEN** 用户需要处理超范围值
- **THEN** 可设置是否启用外推
- **AND** 可设置低端高端最大外推距离
- **AND** 可设置输出值范围限制

#### Scenario: 配置归一化参数
- **WHEN** 用户需要配置输出归一化
- **THEN** 可启用/禁用归一化
- **AND** 可设置目标中心点
- **AND** 可选择自动偏移或手动偏移
- **AND** 实时显示计算的偏移量

#### Scenario: 批量补偿处理
- **WHEN** 模型已加载
- **AND** 用户指定输入输出目录
- **AND** 点击批量补偿
- **THEN** 处理输入目录下所有PNG文件
- **AND** 保存补偿后图像到输出目录
- **AND** 显示处理进度和统计
- **AND** 显示补偿率、外推像素数等信息

#### Scenario: 单个补偿处理
- **WHEN** 模型已加载
- **AND** 用户选择单个PNG文件
- **AND** 点击单个补偿
- **THEN** 补偿该图像并保存
- **AND** 显示补偿统计信息

### Requirement: 线性度计算标签页

系统应当提供线性度计算功能。

#### Scenario: 配置输入路径
- **WHEN** 用户选择测试目录
- **AND** 可选地选择模型文件
- **THEN** 准备线性度计算

#### Scenario: 配置参数
- **WHEN** 用户调整参数
- **THEN** 可设置满量程
- **AND** 可设置是否启用滤波
- **AND** 可设置深度转换系数

#### Scenario: 运行线性度计算
- **WHEN** 用户点击开始计算
- **THEN** 在后台线程执行
- **AND** 计算补偿前线性度
- **AND** 如提供模型，计算补偿后线性度
- **AND** 实时显示日志
- **AND** 完成后显示结果

#### Scenario: 显示计算结果
- **WHEN** 计算完成
- **THEN** 显示线性度、最大偏差、RMS误差、R²等指标
- **AND** 如有补偿模型，显示补偿前后对比

### Requirement: Y-Z重复精度标签页

系统应当提供Y-Z重复精度计算功能。

#### Scenario: 配置输入
- **WHEN** 用户选择图像目录
- **THEN** 准备重复精度计算

#### Scenario: 配置参数
- **WHEN** 用户调整参数
- **THEN** 可设置是否启用滤波
- **AND** 可设置深度转换系数
- **AND** 可设置ROI

#### Scenario: 运行计算
- **WHEN** 用户点击开始计算
- **THEN** 在后台线程执行
- **AND** 计算重复精度指标
- **AND** 实时显示日志
- **AND** 完成后显示结果

#### Scenario: 显示结果
- **WHEN** 计算完成
- **THEN** 显示图像数量、平均深度、标准差
- **AND** 显示重复精度±3σ、6σ、极差
- **AND** 显示图像内平均标准差

## ADDED Requirements

### Requirement: X位置重复精度标签页

系统应当提供X方向位置重复精度分析功能。

#### Scenario: 配置输入
- **WHEN** 用户选择图像目录
- **THEN** 准备X位置重复精度计算

#### Scenario: 配置参数
- **WHEN** 用户调整参数
- **THEN** 可设置深度转换系数
- **AND** 可设置空间分辨率（mm/pixel）
- **AND** 可设置拟合类型（圆形或椭圆）
- **AND** 可设置固定直径（0=自动检测）
- **AND** 可启用动态ROI

#### Scenario: 运行计算
- **WHEN** 用户点击开始计算
- **THEN** 在后台线程执行
- **AND** 检测每张图像的中心位置
- **AND** 计算X方向位置重复精度
- **AND** 实时显示日志
- **AND** 完成后显示结果

#### Scenario: 显示结果
- **WHEN** 计算完成
- **THEN** 显示图像数量、平均X位置
- **AND** 显示X方向重复精度（±3σ, 6σ, 极差）
- **AND** 显示每张图像的检测结果

### Requirement: 界面样式和布局

系统应当提供现代化的用户界面。

#### Scenario: 应用主题样式
- **WHEN** 应用启动
- **THEN** 应用 clam 或 vista 主题（如可用）
- **AND** 定义自定义样式（标题、卡片、按钮等）

#### Scenario: 响应式布局
- **WHEN** 窗口尺寸改变
- **THEN** 界面元素自动调整
- **AND** 最小尺寸 1000x700

#### Scenario: 窗口居中
- **WHEN** 应用启动
- **THEN** 窗口在屏幕中央显示

### Requirement: 后台任务处理

系统应当在后台线程执行耗时操作。

#### Scenario: 启动后台任务
- **WHEN** 用户点击执行按钮
- **THEN** 在独立线程中运行任务
- **AND** 禁用相关按钮防止重复提交
- **AND** 实时更新日志输出

#### Scenario: 任务完成
- **WHEN** 后台任务完成
- **THEN** 重新启用按钮
- **AND** 更新结果显示
- **AND** 显示完成消息

#### Scenario: 错误处理
- **WHEN** 任务执行出错
- **THEN** 显示错误消息框
- **AND** 记录错误日志
- **AND** 恢复界面状态

### Requirement: 日志输出

系统应当提供实时日志输出功能。

#### Scenario: 线程安全日志
- **WHEN** 后台任务需要输出日志
- **THEN** 使用 queue 机制安全传递消息
- **AND** 主线程定期刷新日志显示
- **AND** 自动滚动到最新内容

#### Scenario: 日志格式
- **WHEN** 输出日志
- **THEN** 包含时间戳
- **AND** 使用统一格式

## 技术说明

### 服务层集成
UI 通过服务类进行操作：
- CalibrationService - 标定流程
- CompensationService - 补偿操作
- LinearityService - 线性度计算
- RepeatabilityService - 重复精度计算

### 配置管理
所有参数使用配置对象：
- FilterConfig
- ROIConfig
- ExtrapolateConfig
- NormalizeConfig
- DepthConversionConfig

### 相关文件
- `ui/app.py` - 主界面实现
- `compcodeultimate/services/` - 服务层API
- `compcodeultimate/config.py` - 默认配置参数
