# Change: 更新规格以反映 v3.0 分层架构

## Why
代码已从 v2.1 重构到 v3.0，采用了清晰的分层架构（数据层/核心层/服务层/接口层），但 openspec 规格仍基于旧版本代码结构。需要更新规格以准确反映当前实现状态。

## What Changes

### 架构变化
- **分层架构**: 引入 data/core/services/interfaces 四层架构
- **服务层 API**: 新增 CalibrationService, CompensationService, LinearityService, RepeatabilityService
- **数据模型标准化**: 使用 dataclass 定义 CompensationModel, CalibrationResult, LinearityResult 等
- **配置对象化**: FilterConfig, ROIConfig, ExtrapolateConfig, NormalizeConfig, DepthConversionConfig

### 功能增强
- **归一化功能**: 输出归一化配置，支持自动偏移计算
- **外推功能完善**: 增强的外推统计和扩展范围计算
- **数据质量检测**: 异常点检测、平面标准差警告
- **X位置重复精度**: 新增 X 方向位置重复精度分析功能

### 文件结构变化
- **模块化**: 从单一文件拆分为多个专用模块
  - `core/spline_model.py` - 样条模型构建
  - `core/compensator.py` - 补偿功能
  - `core/extrapolator.py` - 外推功能
  - `core/calibrator.py` - 标定处理  
  - `core/linearity.py` - 线性度计算
- **数据层**: `data/models.py`, `data/io.py`, `data/converters.py`
- **服务层**: `services/*_service.py`
- **接口层**: `interfaces/cli.py`, `interfaces/ui_adapter.py`

## Impact
- Affected specs: project, depth-compensation, calibration, linearity-calc, repeatability-calc, ui-application
- Affected code: 整个 compcodeultimate 模块（已重构完成）
- **BREAKING**: API 从函数调用变为服务类接口
- Migration: 需要从 `from compcodeultimate import CompensationService` 导入服务类
