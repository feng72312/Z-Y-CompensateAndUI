# -*- coding: utf-8 -*-
"""
校准模块 - 整合平面拟合、滤波、校准功能
"""

import numpy as np
from scipy.ndimage import median_filter, gaussian_filter
from config import (INVALID_VALUE, MIN_VALID_PIXELS, MIN_VALID_RATIO,
                    OUTLIER_STD_FACTOR, MEDIAN_FILTER_SIZE, GAUSSIAN_FILTER_SIGMA)
from utils import get_valid_pixels


# ==================== 滤波功能 ====================

def filter_outliers(roi_region, std_factor=None):
    """异常值去除（3σ准则）"""
    std_factor = std_factor or OUTLIER_STD_FACTOR
    filtered = roi_region.copy()
    valid_pixels, _ = get_valid_pixels(filtered)
    
    if valid_pixels.size == 0:
        return filtered
    
    mean_val = np.mean(valid_pixels)
    std_val = np.std(valid_pixels)
    lower = mean_val - std_factor * std_val
    upper = mean_val + std_factor * std_val
    
    outlier_mask = (filtered != INVALID_VALUE) & ((filtered < lower) | (filtered > upper))
    filtered[outlier_mask] = INVALID_VALUE
    
    return filtered


def apply_median_filter(roi_region, size=None):
    """中值滤波"""
    size = size or MEDIAN_FILTER_SIZE
    valid_mask = (roi_region != INVALID_VALUE)
    
    if not np.any(valid_mask):
        return roi_region
    
    # 🔥 关键修复：用有效像素的平均值填充，而不是0
    temp = roi_region.copy()
    valid_mean = temp[valid_mask].mean()
    temp[~valid_mask] = valid_mean
    
    # 应用中值滤波
    filtered = median_filter(temp, size=size)
    
    # 恢复无效值
    filtered[~valid_mask] = INVALID_VALUE
    return filtered.astype(np.uint16)


def apply_gaussian_filter(roi_region, sigma=None):
    """高斯滤波"""
    sigma = sigma or GAUSSIAN_FILTER_SIGMA
    valid_mask = (roi_region != INVALID_VALUE)
    
    if not np.any(valid_mask):
        return roi_region
    
    # 🔥 关键修复：用有效像素的平均值填充，而不是0
    temp = roi_region.copy().astype(np.float32)
    valid_mean = temp[valid_mask].mean()
    temp[~valid_mask] = valid_mean
    
    # 应用高斯滤波
    filtered = gaussian_filter(temp, sigma=sigma)
    
    # 恢复无效值
    filtered[~valid_mask] = INVALID_VALUE
    return np.round(filtered).astype(np.uint16)


def apply_filters(roi_region, use_outlier=True, use_median=True, use_gaussian=True,
                  std_factor=None, median_size=None, gaussian_sigma=None):
    """
    应用组合滤波
    
    参数:
        roi_region: ROI区域数组
        use_outlier: 是否使用异常值去除
        use_median: 是否使用中值滤波
        use_gaussian: 是否使用高斯滤波
        std_factor: 异常值阈值（σ倍数），None则使用config默认值
        median_size: 中值滤波窗口大小，None则使用config默认值
        gaussian_sigma: 高斯滤波σ，None则使用config默认值
    """
    filtered = roi_region.copy()
    
    if use_outlier:
        filtered = filter_outliers(filtered, std_factor=std_factor)
    if use_median:
        filtered = apply_median_filter(filtered, size=median_size)
    if use_gaussian:
        filtered = apply_gaussian_filter(filtered, sigma=gaussian_sigma)
    
    return filtered


# ==================== 平面拟合 ====================

def fit_plane(roi_region):
    """
    拟合平面: z = ax + by + c
    返回: (a, b, c)
    """
    valid_pixels, valid_mask = get_valid_pixels(roi_region)
    
    if valid_pixels.size < MIN_VALID_PIXELS:
        raise ValueError(f"有效像素不足: {valid_pixels.size} < {MIN_VALID_PIXELS}")
    
    # 获取有效像素的坐标
    height, width = roi_region.shape
    y_indices, x_indices = np.where(valid_mask)
    z_values = roi_region[valid_mask].astype(np.float64)
    
    # 构建矩阵 A: [x, y, 1]
    A = np.column_stack([x_indices, y_indices, np.ones(len(x_indices))])
    
    # 最小二乘法求解
    params, _, _, _ = np.linalg.lstsq(A, z_values, rcond=None)
    
    return tuple(params)


def calculate_deviation(roi_region, plane_params):
    """
    计算每个像素相对平面的偏差
    """
    a, b, c = plane_params
    height, width = roi_region.shape
    y_indices, x_indices = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
    
    # 计算拟合平面的z值
    plane_z = a * x_indices + b * y_indices + c
    
    # 计算偏差
    deviation = roi_region.astype(np.float32) - plane_z
    
    return deviation


def calibrate(roi_region, plane_params):
    """
    平面校准：去除倾斜，保留偏差
    """
    deviation = calculate_deviation(roi_region, plane_params)
    
    # 校准后 = 偏差 + 平面常数项
    calibrated = deviation + plane_params[2]
    
    # 保留无效值（使用原始ROI判断）
    calibrated[roi_region == INVALID_VALUE] = INVALID_VALUE
    
    # 🔥 关键：返回float32类型，保留负值
    return calibrated.astype(np.float32)


def calculate_flatness(roi_region, plane_params):
    """
    计算平面度（最大偏差 - 最小偏差）
    """
    deviation = calculate_deviation(roi_region, plane_params)
    valid_deviation = deviation[roi_region != INVALID_VALUE]
    
    if valid_deviation.size == 0:
        return None
    
    return valid_deviation.max() - valid_deviation.min()


# ==================== 完整校准流程 ====================

def calibrate_image(roi_region, apply_filter=True, **filter_kwargs):
    """
    完整的图像校准流程
    
    参数:
        roi_region: ROI区域数组
        apply_filter: 是否应用滤波
        filter_kwargs: 滤波参数
    
    返回:
        dict: {
            'success': bool,
            'plane_params': tuple,
            'flatness': float,
            'calibrated_roi': ndarray,
            'deviation': ndarray,
            'filtered_roi': ndarray  # 如果应用了滤波
        }
    """
    # 1. 应用滤波（可选）
    processed_roi = apply_filters(roi_region, **filter_kwargs) if apply_filter else roi_region.copy()
    
    # 2. 检查有效像素
    valid_pixels, _ = get_valid_pixels(processed_roi)
    valid_ratio = valid_pixels.size / roi_region.size
    
    if valid_pixels.size < MIN_VALID_PIXELS or valid_ratio < MIN_VALID_RATIO:
        return {
            'success': False,
            'reason': f'有效像素不足: {valid_pixels.size} ({valid_ratio*100:.2f}%)'
        }
    
    # 3. 平面拟合
    try:
        plane_params = fit_plane(processed_roi)
    except ValueError as e:
        return {'success': False, 'reason': str(e)}
    
    # 4. 计算平面度
    flatness = calculate_flatness(processed_roi, plane_params)
    
    # 5. 平面校准
    calibrated_roi = calibrate(processed_roi, plane_params)
    deviation = calculate_deviation(processed_roi, plane_params)
    
    result = {
        'success': True,
        'plane_params': plane_params,
        'flatness': flatness,
        'calibrated_roi': calibrated_roi,
        'deviation': deviation
    }
    
    if apply_filter:
        result['filtered_roi'] = processed_roi
    
    return result

