# -*- coding: utf-8 -*-
"""
补偿模块
提供核心补偿功能：点补偿和图像补偿
"""

import numpy as np
from scipy.interpolate import splev
from typing import Optional, Union

from ..data.models import (
    CompensationModel, 
    CompensationResult, 
    ExtrapolateConfig,
    NormalizeConfig
)
from ..data.converters import gray_to_mm_vectorized, mm_to_gray_vectorized
from .extrapolator import apply_extrapolation, calculate_extended_range


# 默认无效值
DEFAULT_INVALID_VALUE = 65535


def apply_compensation(measured_values: Union[float, np.ndarray],
                       model: CompensationModel,
                       extrapolate_config: Optional[ExtrapolateConfig] = None) -> Union[float, np.ndarray]:
    """
    应用补偿模型
    
    参数:
        measured_values: 测量值（单个值或数组）
        model: 补偿模型
        extrapolate_config: 外推配置（可选）
    
    返回:
        补偿后的值
        - 输入为标量时返回 float
        - 输入为数组时返回 np.ndarray
    """
    if extrapolate_config is not None and extrapolate_config.enabled:
        return apply_extrapolation(measured_values, model, extrapolate_config)
    
    # 不使用外推，直接使用样条插值
    # 检测输入是否为标量，保持返回类型一致性
    is_scalar = np.ndim(measured_values) == 0
    inverse_model = model.get_inverse_model_tuple()
    result = splev(measured_values, inverse_model, ext=0)
    return float(result) if is_scalar else result


def compensate_image_pixels(depth_array: np.ndarray,
                             model: CompensationModel,
                             invalid_value: int = DEFAULT_INVALID_VALUE,
                             extrapolate_config: Optional[ExtrapolateConfig] = None,
                             normalize_offset: float = 0.0,
                             depth_offset: float = 32768,
                             depth_scale_factor: float = 1.6) -> CompensationResult:
    """
    对深度图进行逐像素补偿（向量化优化版本）
    
    参数:
        depth_array: 深度图数组（灰度值）
        model: 补偿模型
        invalid_value: 无效像素值
        extrapolate_config: 外推配置
        normalize_offset: 归一化偏移量（mm）
        depth_offset: 深度转换偏移量
        depth_scale_factor: 深度转换缩放因子
    
    返回:
        CompensationResult 对象
    """
    # 默认外推配置
    if extrapolate_config is None:
        extrapolate_config = ExtrapolateConfig(enabled=True)
    
    # 获取模型范围
    x_min, x_max = model.x_range
    
    # 创建输出数组
    compensated = depth_array.copy().astype(np.uint16)
    
    # 标记有效像素
    valid_mask = (depth_array != invalid_value)
    valid_gray = depth_array[valid_mask]
    
    if valid_gray.size == 0:
        # 没有有效像素
        return _create_empty_result(depth_array, invalid_value, extrapolate_config.enabled, normalize_offset)
    
    # 向量化转换为毫米
    measured_mm = gray_to_mm_vectorized(valid_gray, depth_offset, depth_scale_factor)
    
    # 判断在范围内的像素
    in_range_mask = (measured_mm >= x_min) & (measured_mm <= x_max)
    in_range_count = int(np.sum(in_range_mask))
    
    # 计算需要补偿的像素（范围内 + 外推范围内）
    if extrapolate_config.enabled:
        extended_min, extended_max = calculate_extended_range(model, extrapolate_config)
        compensate_mask = (measured_mm >= extended_min) & (measured_mm <= extended_max)
    else:
        compensate_mask = in_range_mask
    
    compensate_count = int(np.sum(compensate_mask))
    extrapolate_count = compensate_count - in_range_count if extrapolate_config.enabled else 0
    
    # 执行补偿
    if compensate_count > 0:
        # 提取需要补偿的测量值
        to_compensate = measured_mm[compensate_mask]
        
        # 应用补偿
        compensated_mm = apply_compensation(to_compensate, model, extrapolate_config)
        
        # 应用归一化偏移
        if normalize_offset != 0.0:
            compensated_mm = compensated_mm + normalize_offset
        
        # 转换回灰度值
        compensated_gray = mm_to_gray_vectorized(compensated_mm, depth_offset, depth_scale_factor)
        
        # 填充结果
        temp_gray = valid_gray.copy()
        temp_gray[compensate_mask] = compensated_gray
        compensated[valid_mask] = temp_gray
    
    # 统计信息
    total_pixels = depth_array.size
    valid_pixels = int(np.sum(valid_mask))
    
    return CompensationResult(
        compensated_array=compensated,
        total_pixels=total_pixels,
        valid_pixels=valid_pixels,
        in_range_pixels=in_range_count,
        extrapolated_pixels=extrapolate_count,
        compensated_pixels=compensate_count,
        out_of_range_pixels=valid_pixels - compensate_count,
        invalid_pixels=total_pixels - valid_pixels,
        compensation_rate=compensate_count / total_pixels * 100 if total_pixels > 0 else 0.0,
        extrapolation_enabled=extrapolate_config.enabled,
        normalize_offset=normalize_offset
    )


def _create_empty_result(depth_array: np.ndarray,
                          invalid_value: int,
                          extrapolation_enabled: bool,
                          normalize_offset: float) -> CompensationResult:
    """创建空结果（无有效像素时）"""
    total_pixels = depth_array.size
    invalid_pixels = int(np.sum(depth_array == invalid_value))
    
    return CompensationResult(
        compensated_array=depth_array.copy(),
        total_pixels=total_pixels,
        valid_pixels=0,
        in_range_pixels=0,
        extrapolated_pixels=0,
        compensated_pixels=0,
        out_of_range_pixels=0,
        invalid_pixels=invalid_pixels,
        compensation_rate=0.0,
        extrapolation_enabled=extrapolation_enabled,
        normalize_offset=normalize_offset
    )


def calculate_normalization_offset(model: CompensationModel,
                                    target_center: float = 0.0) -> float:
    """
    计算归一化偏移量
    
    根据模型的输出范围自动计算偏移量，使输出以目标中心点为中心
    
    参数:
        model: 补偿模型
        target_center: 目标中心点（默认0）
    
    返回:
        偏移量（补偿后的值加上此偏移量即为归一化后的值）
    
    公式:
        offset = target_center - (y_min + y_max) / 2
    """
    y_min, y_max = model.y_range
    current_center = (y_min + y_max) / 2
    return target_center - current_center


def get_normalize_config(model: CompensationModel,
                          config: NormalizeConfig) -> float:
    """
    根据归一化配置获取实际偏移量
    
    参数:
        model: 补偿模型
        config: 归一化配置
    
    返回:
        实际偏移量
    """
    if not config.enabled:
        return 0.0
    
    if config.auto_offset:
        return calculate_normalization_offset(model, config.target_center)
    else:
        return config.manual_offset
