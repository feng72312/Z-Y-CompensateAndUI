# -*- coding: utf-8 -*-
"""
校准模块
提供平面拟合、滤波、校准功能
"""

import numpy as np
from scipy.ndimage import median_filter, gaussian_filter
from typing import Optional, Tuple

from ..data.models import CalibrationResult, FilterConfig

# 默认配置
DEFAULT_INVALID_VALUE = 65535
DEFAULT_MIN_VALID_PIXELS = 100
DEFAULT_MIN_VALID_RATIO = 0.10


# ==================== 滤波功能 ====================

def filter_outliers(roi_region: np.ndarray, 
                    std_factor: float = 3.0,
                    invalid_value: int = DEFAULT_INVALID_VALUE) -> np.ndarray:
    """
    异常值去除（3σ准则）
    
    参数:
        roi_region: ROI区域数组
        std_factor: 标准差倍数
        invalid_value: 无效值
    
    返回:
        滤波后的数组
    """
    filtered = roi_region.copy()
    valid_mask = (filtered != invalid_value)
    valid_pixels = filtered[valid_mask]
    
    if valid_pixels.size == 0:
        return filtered
    
    mean_val = np.mean(valid_pixels)
    std_val = np.std(valid_pixels)
    lower = mean_val - std_factor * std_val
    upper = mean_val + std_factor * std_val
    
    outlier_mask = valid_mask & ((filtered < lower) | (filtered > upper))
    filtered[outlier_mask] = invalid_value
    
    return filtered


def apply_median_filter(roi_region: np.ndarray, 
                        size: int = 3,
                        invalid_value: int = DEFAULT_INVALID_VALUE) -> np.ndarray:
    """
    中值滤波
    
    关键：用有效像素的平均值填充无效区域，避免边界效应
    
    参数:
        roi_region: ROI区域数组
        size: 滤波窗口大小
        invalid_value: 无效值
    
    返回:
        滤波后的数组
    """
    valid_mask = (roi_region != invalid_value)
    
    if not np.any(valid_mask):
        return roi_region
    
    # 用有效像素均值填充无效区域
    temp = roi_region.copy().astype(np.float64)
    valid_mean = temp[valid_mask].mean()
    temp[~valid_mask] = valid_mean
    
    # 应用中值滤波
    filtered = median_filter(temp, size=size)
    
    # 恢复无效值
    filtered[~valid_mask] = invalid_value
    return filtered.astype(np.uint16)


def apply_gaussian_filter(roi_region: np.ndarray, 
                          sigma: float = 1.0,
                          invalid_value: int = DEFAULT_INVALID_VALUE) -> np.ndarray:
    """
    高斯滤波
    
    参数:
        roi_region: ROI区域数组
        sigma: 高斯滤波标准差
        invalid_value: 无效值
    
    返回:
        滤波后的数组
    """
    valid_mask = (roi_region != invalid_value)
    
    if not np.any(valid_mask):
        return roi_region
    
    # 用有效像素均值填充无效区域
    temp = roi_region.copy().astype(np.float32)
    valid_mean = temp[valid_mask].mean()
    temp[~valid_mask] = valid_mean
    
    # 应用高斯滤波
    filtered = gaussian_filter(temp, sigma=sigma)
    
    # 恢复无效值
    filtered[~valid_mask] = invalid_value
    return np.round(filtered).astype(np.uint16)


def apply_filters(roi_region: np.ndarray, 
                  config: Optional[FilterConfig] = None,
                  invalid_value: int = DEFAULT_INVALID_VALUE) -> np.ndarray:
    """
    应用组合滤波
    
    顺序：异常值去除 -> 中值滤波 -> 高斯滤波
    
    参数:
        roi_region: ROI区域数组
        config: 滤波配置
        invalid_value: 无效值
    
    返回:
        滤波后的数组
    """
    if config is None:
        config = FilterConfig()
    
    if not config.enabled:
        return roi_region.copy()
    
    filtered = roi_region.copy()
    
    # 异常值去除
    filtered = filter_outliers(filtered, config.outlier_std_factor, invalid_value)
    
    # 中值滤波
    filtered = apply_median_filter(filtered, config.median_filter_size, invalid_value)
    
    # 高斯滤波
    filtered = apply_gaussian_filter(filtered, config.gaussian_filter_sigma, invalid_value)
    
    return filtered


# ==================== 平面拟合 ====================

def fit_plane(roi_region: np.ndarray,
              invalid_value: int = DEFAULT_INVALID_VALUE,
              min_valid_pixels: int = DEFAULT_MIN_VALID_PIXELS) -> Tuple[float, float, float]:
    """
    拟合平面: z = ax + by + c
    
    参数:
        roi_region: ROI区域数组
        invalid_value: 无效值
        min_valid_pixels: 最小有效像素数
    
    返回:
        (a, b, c) 平面参数
    
    抛出:
        ValueError: 有效像素不足
    """
    valid_mask = (roi_region != invalid_value)
    valid_pixels = roi_region[valid_mask]
    
    if valid_pixels.size < min_valid_pixels:
        raise ValueError(f"有效像素不足: {valid_pixels.size} < {min_valid_pixels}")
    
    # 获取有效像素的坐标
    y_indices, x_indices = np.where(valid_mask)
    z_values = roi_region[valid_mask].astype(np.float64)
    
    # 构建矩阵 A: [x, y, 1]
    A = np.column_stack([x_indices, y_indices, np.ones(len(x_indices))])
    
    # 最小二乘法求解
    params, _, _, _ = np.linalg.lstsq(A, z_values, rcond=None)
    
    return (float(params[0]), float(params[1]), float(params[2]))


def calculate_deviation(roi_region: np.ndarray, 
                        plane_params: Tuple[float, float, float]) -> np.ndarray:
    """
    计算每个像素相对平面的偏差
    
    参数:
        roi_region: ROI区域数组
        plane_params: 平面参数 (a, b, c)
    
    返回:
        偏差数组
    """
    a, b, c = plane_params
    height, width = roi_region.shape
    y_indices, x_indices = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
    
    # 计算拟合平面的z值
    plane_z = a * x_indices + b * y_indices + c
    
    # 计算偏差
    deviation = roi_region.astype(np.float32) - plane_z
    
    return deviation


def calibrate_plane(roi_region: np.ndarray, 
                    plane_params: Tuple[float, float, float],
                    invalid_value: int = DEFAULT_INVALID_VALUE) -> np.ndarray:
    """
    平面校准：去除倾斜，保留偏差
    
    参数:
        roi_region: ROI区域数组
        plane_params: 平面参数
        invalid_value: 无效值
    
    返回:
        校准后的数组 (float32)
    """
    deviation = calculate_deviation(roi_region, plane_params)
    
    # 校准后 = 偏差 + 平面常数项
    calibrated = deviation + plane_params[2]
    
    # 保留无效值
    calibrated[roi_region == invalid_value] = invalid_value
    
    return calibrated.astype(np.float32)


def calculate_flatness(roi_region: np.ndarray, 
                       plane_params: Tuple[float, float, float],
                       invalid_value: int = DEFAULT_INVALID_VALUE) -> Optional[float]:
    """
    计算平面度（最大偏差 - 最小偏差）
    
    参数:
        roi_region: ROI区域数组
        plane_params: 平面参数
        invalid_value: 无效值
    
    返回:
        平面度，如果无有效像素返回None
    """
    deviation = calculate_deviation(roi_region, plane_params)
    valid_deviation = deviation[roi_region != invalid_value]
    
    if valid_deviation.size == 0:
        return None
    
    return float(valid_deviation.max() - valid_deviation.min())


# ==================== 完整校准流程 ====================

def calibrate_image(roi_region: np.ndarray, 
                    apply_filter: bool = True,
                    filter_config: Optional[FilterConfig] = None,
                    invalid_value: int = DEFAULT_INVALID_VALUE,
                    min_valid_pixels: int = DEFAULT_MIN_VALID_PIXELS,
                    min_valid_ratio: float = DEFAULT_MIN_VALID_RATIO) -> CalibrationResult:
    """
    完整的图像校准流程
    
    步骤：
    1. 应用滤波（可选）
    2. 检查有效像素
    3. 平面拟合
    4. 计算平面度
    5. 平面校准
    
    参数:
        roi_region: ROI区域数组
        apply_filter: 是否应用滤波
        filter_config: 滤波配置
        invalid_value: 无效值
        min_valid_pixels: 最小有效像素数
        min_valid_ratio: 最小有效像素比例
    
    返回:
        CalibrationResult 对象
    """
    # 1. 应用滤波（可选）
    if apply_filter:
        if filter_config is None:
            filter_config = FilterConfig()
        processed_roi = apply_filters(roi_region, filter_config, invalid_value)
    else:
        processed_roi = roi_region.copy()
    
    # 2. 检查有效像素
    valid_mask = (processed_roi != invalid_value)
    valid_count = np.sum(valid_mask)
    valid_ratio = valid_count / roi_region.size
    
    if valid_count < min_valid_pixels or valid_ratio < min_valid_ratio:
        return CalibrationResult.failure(
            f'有效像素不足: {valid_count} ({valid_ratio*100:.2f}%)'
        )
    
    # 3. 平面拟合
    try:
        plane_params = fit_plane(processed_roi, invalid_value, min_valid_pixels)
    except ValueError as e:
        return CalibrationResult.failure(str(e))
    
    # 4. 计算平面度
    flatness = calculate_flatness(processed_roi, plane_params, invalid_value)
    
    # 5. 平面校准
    calibrated_roi = calibrate_plane(processed_roi, plane_params, invalid_value)
    deviation = calculate_deviation(processed_roi, plane_params)
    
    return CalibrationResult(
        success=True,
        plane_params=plane_params,
        calibrated_roi=calibrated_roi,
        flatness=flatness,
        filtered_roi=processed_roi if apply_filter else None,
        deviation=deviation
    )


# ==================== ROI工具函数 ====================

def get_roi(depth_array: np.ndarray,
            x: int = 0,
            y: int = 0,
            width: int = -1,
            height: int = -1) -> np.ndarray:
    """
    提取ROI区域
    
    参数:
        depth_array: 深度图数组
        x: ROI左上角X坐标
        y: ROI左上角Y坐标
        width: ROI宽度（-1表示使用整个图像）
        height: ROI高度（-1表示使用整个图像）
    
    返回:
        ROI区域数组
    """
    if width == -1 and height == -1:
        return depth_array
    
    img_height, img_width = depth_array.shape
    x_start = max(0, x)
    y_start = max(0, y)
    x_end = img_width if width == -1 else min(img_width, x + width)
    y_end = img_height if height == -1 else min(img_height, y + height)
    
    return depth_array[y_start:y_end, x_start:x_end]


def get_valid_pixels(array: np.ndarray,
                     invalid_value: int = DEFAULT_INVALID_VALUE) -> Tuple[np.ndarray, np.ndarray]:
    """
    获取有效像素
    
    参数:
        array: 数组
        invalid_value: 无效值
    
    返回:
        (valid_pixels, valid_mask) 元组
    """
    valid_mask = (array != invalid_value)
    valid_pixels = array[valid_mask]
    return valid_pixels, valid_mask
