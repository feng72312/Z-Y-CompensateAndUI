# -*- coding: utf-8 -*-
"""
深度图补偿系统 - compcodeultimate

版本: v3.0 (重构版)
架构: 分层架构（数据层/核心层/服务层/接口层）

快速开始:
    from compcodeultimate import CompensationService, CalibrationService
    
    # 加载模型并补偿
    service = CompensationService()
    service.load_model('model.json')
    result = service.compensate_image('input.png', 'output.png')
    
    # 标定流程
    calib = CalibrationService()
    result = calib.process_calibration_data('./calib_data')
    calib.save_model('model.json')
"""

__version__ = '3.0.0'
__author__ = 'Depth Compensation Team'

# 服务层 API（推荐使用）
from .services import (
    CalibrationService,
    CompensationService,
    LinearityService,
    RepeatabilityService
)

# 数据模型
from .data.models import (
    CompensationModel,
    CalibrationResult,
    LinearityResult,
    CompensationResult,
    CompensationEffectResult,
    RepeatabilityResult,
    BatchProcessResult,
    # 配置类
    ROIConfig,
    FilterConfig,
    ExtrapolateConfig,
    NormalizeConfig,
    DepthConversionConfig
)

# 数据IO
from .data.io import (
    read_depth_image,
    save_depth_image,
    load_model,
    save_model
)

# 单位转换
from .data.converters import (
    gray_to_mm,
    mm_to_gray
)

# 核心算法（高级用户）
from .core import (
    build_compensation_model,
    apply_compensation,
    compensate_image_pixels,
    calibrate_image,
    calculate_linearity,
    calculate_compensation_effect
)

# 接口层
from .interfaces import (
    UICallbacks,
    UIAdapterInterface,
    BaseController
)

__all__ = [
    # Version
    '__version__',
    # Services (主要API)
    'CalibrationService',
    'CompensationService',
    'LinearityService',
    'RepeatabilityService',
    # Models
    'CompensationModel',
    'CalibrationResult',
    'LinearityResult',
    'CompensationResult',
    'CompensationEffectResult',
    'RepeatabilityResult',
    'BatchProcessResult',
    # Configs
    'ROIConfig',
    'FilterConfig',
    'ExtrapolateConfig',
    'NormalizeConfig',
    'DepthConversionConfig',
    # IO
    'read_depth_image',
    'save_depth_image',
    'load_model',
    'save_model',
    # Converters
    'gray_to_mm',
    'mm_to_gray',
    # Core (advanced)
    'build_compensation_model',
    'apply_compensation',
    'compensate_image_pixels',
    'calibrate_image',
    'calculate_linearity',
    'calculate_compensation_effect',
    # Interface
    'UICallbacks',
    'UIAdapterInterface',
    'BaseController'
]
