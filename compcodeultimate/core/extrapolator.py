# -*- coding: utf-8 -*-
"""
线性外推模块
提供超出模型范围的线性外推功能
"""

import numpy as np
from scipy.interpolate import splev
from typing import Union, Optional, Tuple, Dict

from ..data.models import CompensationModel, ExtrapolateConfig


# 默认外推配置
DEFAULT_EXTRAPOLATE_CONFIG = ExtrapolateConfig(
    enabled=True,
    max_low=2.0,
    max_high=2.0,
    output_min=0.0,
    output_max=43.0,
    clamp_output=True
)


def apply_extrapolation(measured_values: Union[float, np.ndarray],
                        model: CompensationModel,
                        config: Optional[ExtrapolateConfig] = None) -> np.ndarray:
    """
    带线性外推的补偿函数
    
    在模型有效范围内使用样条插值，
    超出范围时使用边界点的导数进行线性外推
    
    参数:
        measured_values: 测量值（标量或数组）
        model: 补偿模型
        config: 外推配置
    
    返回:
        补偿后的值数组
    """
    if config is None:
        config = DEFAULT_EXTRAPOLATE_CONFIG
    
    measured_arr = np.atleast_1d(np.array(measured_values, dtype=np.float64))
    is_scalar = np.ndim(measured_values) == 0
    
    inverse_model = model.get_inverse_model_tuple()
    t, c, k = inverse_model
    x_min, x_max = t[k], t[-k-1]  # 模型有效范围
    
    result = np.zeros_like(measured_arr, dtype=np.float64)
    
    # 范围内的值：使用样条插值
    in_range = (measured_arr >= x_min) & (measured_arr <= x_max)
    if np.any(in_range):
        result[in_range] = splev(measured_arr[in_range], inverse_model)
    
    # 低端外推
    below_range = measured_arr < x_min
    if np.any(below_range):
        result[below_range] = _extrapolate_low(
            measured_arr[below_range], 
            inverse_model, 
            x_min, 
            config.max_low
        )
    
    # 高端外推
    above_range = measured_arr > x_max
    if np.any(above_range):
        result[above_range] = _extrapolate_high(
            measured_arr[above_range], 
            inverse_model, 
            x_max, 
            config.max_high
        )
    
    # 输出范围限制
    if config.clamp_output:
        result = np.clip(result, config.output_min, config.output_max)
    
    return result[0] if is_scalar else result


def _extrapolate_low(values: np.ndarray, 
                     inverse_model: Tuple, 
                     x_min: float,
                     max_dist: float) -> np.ndarray:
    """低端线性外推"""
    # 计算低端斜率（样条导数）
    slope = float(splev(x_min, inverse_model, der=1))
    y_min = float(splev(x_min, inverse_model))
    
    # 计算外推距离并限制
    extrapolate_dist = x_min - values
    extrapolate_dist_clamped = np.minimum(extrapolate_dist, max_dist)
    
    # 线性外推
    return y_min - slope * extrapolate_dist_clamped


def _extrapolate_high(values: np.ndarray, 
                      inverse_model: Tuple, 
                      x_max: float,
                      max_dist: float) -> np.ndarray:
    """高端线性外推"""
    # 计算高端斜率（样条导数）
    slope = float(splev(x_max, inverse_model, der=1))
    y_max = float(splev(x_max, inverse_model))
    
    # 计算外推距离并限制
    extrapolate_dist = values - x_max
    extrapolate_dist_clamped = np.minimum(extrapolate_dist, max_dist)
    
    # 线性外推
    return y_max + slope * extrapolate_dist_clamped


def get_extrapolation_stats(measured_values: Union[float, np.ndarray],
                             model: CompensationModel) -> Dict[str, Union[int, float, Tuple]]:
    """
    获取外推统计信息
    
    参数:
        measured_values: 测量值数组
        model: 补偿模型
    
    返回:
        外推统计信息字典
    """
    measured_arr = np.atleast_1d(np.array(measured_values, dtype=np.float64))
    
    x_min, x_max = model.x_range
    
    below_range = measured_arr < x_min
    above_range = measured_arr > x_max
    in_range = (measured_arr >= x_min) & (measured_arr <= x_max)
    
    stats = {
        'total_count': len(measured_arr),
        'in_range_count': int(np.sum(in_range)),
        'below_range_count': int(np.sum(below_range)),
        'above_range_count': int(np.sum(above_range)),
        'model_range': (float(x_min), float(x_max)),
        'data_range': (float(measured_arr.min()), float(measured_arr.max())),
        'below_range_max_dist': 0.0,
        'above_range_max_dist': 0.0
    }
    
    if np.any(below_range):
        stats['below_range_max_dist'] = float(x_min - measured_arr[below_range].min())
    
    if np.any(above_range):
        stats['above_range_max_dist'] = float(measured_arr[above_range].max() - x_max)
    
    return stats


def calculate_extended_range(model: CompensationModel, 
                              config: ExtrapolateConfig) -> Tuple[float, float]:
    """
    计算包含外推的扩展范围
    
    参数:
        model: 补偿模型
        config: 外推配置
    
    返回:
        (extended_min, extended_max) 元组
    """
    x_min, x_max = model.x_range
    extended_min = x_min - config.max_low
    extended_max = x_max + config.max_high
    return (extended_min, extended_max)
