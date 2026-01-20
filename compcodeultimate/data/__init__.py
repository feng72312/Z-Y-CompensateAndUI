# -*- coding: utf-8 -*-
"""
数据层模块
提供数据模型定义、文件读写、单位转换功能
"""

from .models import (
    CompensationModel,
    CalibrationResult,
    LinearityResult,
    CompensationResult,
    ROIConfig,
    FilterConfig,
    ExtrapolateConfig,
    NormalizeConfig,
    DepthConversionConfig
)

from .io import (
    read_depth_image,
    save_depth_image,
    load_model,
    save_model,
    parse_csv,
    get_image_files
)

from .converters import (
    gray_to_mm,
    mm_to_gray,
    gray_to_mm_vectorized,
    mm_to_gray_vectorized
)

__all__ = [
    # Models
    'CompensationModel',
    'CalibrationResult', 
    'LinearityResult',
    'CompensationResult',
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
    'parse_csv',
    'get_image_files',
    # Converters
    'gray_to_mm',
    'mm_to_gray',
    'gray_to_mm_vectorized',
    'mm_to_gray_vectorized'
]
