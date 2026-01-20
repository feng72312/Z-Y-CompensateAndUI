# -*- coding: utf-8 -*-
"""
核心算法层
提供补偿、校准、线性度计算等核心算法
"""

from .spline_model import (
    build_compensation_model,
    get_model_range,
    get_model_output_range,
    is_in_model_range
)

from .compensator import (
    apply_compensation,
    compensate_image_pixels,
    calculate_normalization_offset,
    get_normalize_config
)

from .calibrator import (
    calibrate_image,
    fit_plane,
    apply_filters,
    filter_outliers,
    apply_median_filter,
    apply_gaussian_filter,
    get_roi,
    get_valid_pixels
)

from .linearity import (
    calculate_linearity,
    calculate_compensation_effect,
    normalize_to_relative
)

from .extrapolator import (
    apply_extrapolation,
    get_extrapolation_stats,
    calculate_extended_range
)

__all__ = [
    # Spline Model
    'build_compensation_model',
    'get_model_range',
    'get_model_output_range',
    'is_in_model_range',
    # Compensator
    'apply_compensation',
    'compensate_image_pixels',
    'calculate_normalization_offset',
    'get_normalize_config',
    # Calibrator
    'calibrate_image',
    'fit_plane',
    'apply_filters',
    'filter_outliers',
    'apply_median_filter',
    'apply_gaussian_filter',
    'get_roi',
    'get_valid_pixels',
    # Linearity
    'calculate_linearity',
    'calculate_compensation_effect',
    'normalize_to_relative',
    # Extrapolator
    'apply_extrapolation',
    'get_extrapolation_stats',
    'calculate_extended_range'
]
