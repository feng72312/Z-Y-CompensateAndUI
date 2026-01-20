# -*- coding: utf-8 -*-
"""
线性度计算模块
使用最佳直线法(BFSL)计算线性度
"""

import numpy as np
from typing import Optional, Union, List

from ..data.models import LinearityResult, CompensationEffectResult


# 默认满量程
DEFAULT_FULL_SCALE = 41.0


def calculate_linearity(actual_values: Union[List[float], np.ndarray],
                        measured_values: Union[List[float], np.ndarray],
                        full_scale: Optional[float] = None) -> LinearityResult:
    """
    使用最佳直线法(BFSL)计算线性度
    
    注意：输入值应为相对值（零点归一化后）
    
    参数:
        actual_values: 实际值数组
        measured_values: 测量值数组
        full_scale: 满量程（mm），默认41.0
    
    返回:
        LinearityResult 对象
    
    抛出:
        ValueError: 数据不足或数据无效
    """
    full_scale = full_scale or DEFAULT_FULL_SCALE
    
    actual_arr = np.array(actual_values, dtype=np.float64)
    measured_arr = np.array(measured_values, dtype=np.float64)
    
    # 数据验证
    _validate_linearity_data(actual_arr, measured_arr)
    
    # 零点归一化（如果输入不是已归一化的相对值）
    actual_relative = actual_arr - actual_arr[0]
    measured_relative = measured_arr - measured_arr[0]
    
    # 线性回归
    try:
        coeffs = np.polyfit(actual_relative, measured_relative, 1)
    except np.linalg.LinAlgError as e:
        raise ValueError(
            f"线性回归失败(SVD不收敛): {str(e)}。"
            f"请检查数据是否有效，实际值范围: {actual_arr.min():.4f}~{actual_arr.max():.4f}"
        )
    
    slope, intercept = coeffs[0], coeffs[1]
    
    # 预测值
    predicted = slope * actual_relative + intercept
    
    # 计算偏差
    deviations = measured_relative - predicted
    max_deviation = float(deviations.max())
    min_deviation = float(deviations.min())
    abs_max_deviation = max(abs(max_deviation), abs(min_deviation))
    
    # 线性度 = 最大偏差 / 满量程 * 100%
    linearity = (abs_max_deviation / full_scale) * 100.0
    
    # 其他统计指标
    rms_error = float(np.sqrt(np.mean(deviations ** 2)))
    mae = float(np.mean(np.abs(deviations)))
    
    # R²
    ss_res = np.sum(deviations ** 2)
    ss_tot = np.sum((measured_relative - measured_relative.mean()) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    
    return LinearityResult(
        linearity=linearity,
        max_deviation=max_deviation,
        min_deviation=min_deviation,
        abs_max_deviation=abs_max_deviation,
        rms_error=rms_error,
        mae=mae,
        r_squared=float(r_squared),
        slope=float(slope),
        intercept=float(intercept)
    )


def _validate_linearity_data(actual_arr: np.ndarray, 
                              measured_arr: np.ndarray) -> None:
    """验证线性度计算数据"""
    if len(actual_arr) < 2:
        raise ValueError(f"数据点不足：线性回归需要至少2个点，当前只有{len(actual_arr)}个")
    
    if len(actual_arr) != len(measured_arr):
        raise ValueError(f"数据长度不匹配：实际值{len(actual_arr)}个，测量值{len(measured_arr)}个")
    
    if np.any(np.isnan(actual_arr)) or np.any(np.isinf(actual_arr)):
        raise ValueError("实际值包含NaN或Inf")
    
    if np.any(np.isnan(measured_arr)) or np.any(np.isinf(measured_arr)):
        raise ValueError("测量值包含NaN或Inf")
    
    # 检查实际值是否有变化
    if np.all(actual_arr == actual_arr[0]):
        raise ValueError("所有实际值相同，无法进行线性回归")


def calculate_compensation_effect(actual_values: Union[List[float], np.ndarray],
                                   measured_values: Union[List[float], np.ndarray],
                                   compensated_values: Union[List[float], np.ndarray],
                                   full_scale: Optional[float] = None) -> CompensationEffectResult:
    """
    计算补偿前后的效果对比
    
    注意：所有输入值应该已经是相对值（零点归一化）
    
    参数:
        actual_values: 实际相对值数组
        measured_values: 测量相对值数组
        compensated_values: 补偿后相对值数组
        full_scale: 满量程（mm）
    
    返回:
        CompensationEffectResult 对象
    """
    before = calculate_linearity(actual_values, measured_values, full_scale)
    after = calculate_linearity(actual_values, compensated_values, full_scale)
    
    # 计算改善幅度
    improvement = 0.0
    if before.linearity != 0:
        improvement = ((before.linearity - after.linearity) / before.linearity) * 100.0
    
    return CompensationEffectResult(
        before=before,
        after=after,
        improvement=improvement,
        actual_values_mm=np.array(actual_values),
        measured_values_mm=np.array(measured_values),
        compensated_values_mm=np.array(compensated_values)
    )


def normalize_to_relative(values: np.ndarray) -> np.ndarray:
    """
    零点归一化：将绝对值转换为相对值
    
    参数:
        values: 绝对值数组
    
    返回:
        相对值数组（第一个元素为0）
    """
    return values - values[0]
