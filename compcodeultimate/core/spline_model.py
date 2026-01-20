# -*- coding: utf-8 -*-
"""
样条模型模块
提供三次样条补偿模型的构建功能
"""

import numpy as np
from scipy.interpolate import splrep
from typing import List, Tuple, Optional

from ..data.models import CompensationModel


def build_compensation_model(actual_values: List[float], 
                             measured_values: List[float],
                             spline_order: int = 3) -> CompensationModel:
    """
    建立补偿模型
    
    使用三次样条插值建立测量值到实际值的映射关系
    
    参数:
        actual_values: 实际值列表 (mm) - 使用绝对值
        measured_values: 测量值列表 (mm) - 使用绝对值
        spline_order: 样条阶数（默认3=三次样条）
    
    返回:
        CompensationModel 对象
    
    抛出:
        ValueError: 数据不足或数据无效
    """
    actual_arr = np.array(actual_values, dtype=np.float64)
    measured_arr = np.array(measured_values, dtype=np.float64)
    
    # 动态调整样条阶数（在验证之前）
    k = min(spline_order, len(actual_arr) - 1)
    
    # 数据验证（使用调整后的阶数）
    _validate_calibration_data(actual_arr, measured_arr, k)
    
    # 确保数据有序（splrep要求x值递增）
    sort_idx_actual = np.argsort(actual_arr)
    actual_sorted = actual_arr[sort_idx_actual]
    measured_sorted_by_actual = measured_arr[sort_idx_actual]
    
    sort_idx_measured = np.argsort(measured_arr)
    measured_sorted = measured_arr[sort_idx_measured]
    actual_sorted_by_measured = actual_arr[sort_idx_measured]
    
    try:
        # 正向模型: 实际值 -> 测量值
        forward_model = splrep(actual_sorted, measured_sorted_by_actual, k=k)
        
        # 逆向模型: 测量值 -> 实际值（用于补偿）
        inverse_model = splrep(measured_sorted, actual_sorted_by_measured, k=k)
    except Exception as e:
        raise ValueError(f"样条拟合失败: {str(e)}。请检查数据是否单调且无重复。")
    
    return CompensationModel(
        knots=inverse_model[0],
        coefficients=inverse_model[1],
        k=inverse_model[2],
        x_range=(measured_arr.min(), measured_arr.max()),
        y_range=(actual_arr.min(), actual_arr.max()),
        calibration_points=len(actual_arr),
        actual_values=actual_arr.tolist(),
        measured_values=measured_arr.tolist(),
        forward_knots=forward_model[0],
        forward_coefficients=forward_model[1]
    )


def _validate_calibration_data(actual_arr: np.ndarray, 
                                measured_arr: np.ndarray,
                                actual_spline_order: int) -> None:
    """
    验证标定数据
    
    参数:
        actual_arr: 实际值数组
        measured_arr: 测量值数组
        actual_spline_order: 实际使用的样条阶数（已动态调整）
    
    抛出:
        ValueError: 数据验证失败
    """
    min_points = actual_spline_order + 1
    
    if len(actual_arr) < min_points:
        raise ValueError(
            f"数据点不足：需要至少{min_points}个点，当前只有{len(actual_arr)}个。"
            f"样条拟合(k={actual_spline_order})要求数据点数量 > 阶数。"
        )
    
    if len(actual_arr) != len(measured_arr):
        raise ValueError(
            f"数据长度不匹配：实际值{len(actual_arr)}个，测量值{len(measured_arr)}个"
        )
    
    # 检查NaN/Inf
    if np.any(np.isnan(actual_arr)) or np.any(np.isinf(actual_arr)):
        raise ValueError("实际值包含NaN或Inf，请检查标定数据")
    
    if np.any(np.isnan(measured_arr)) or np.any(np.isinf(measured_arr)):
        raise ValueError("测量值包含NaN或Inf，请检查图像处理结果")
    
    # 检查重复值（splrep要求x值唯一）
    if len(np.unique(actual_arr)) != len(actual_arr):
        raise ValueError("实际值存在重复，样条拟合要求x值唯一")
    
    if len(np.unique(measured_arr)) != len(measured_arr):
        raise ValueError("测量值存在重复，样条拟合要求x值唯一")


def get_model_range(model: CompensationModel) -> Tuple[float, float]:
    """
    获取模型的有效输入范围
    
    参数:
        model: 补偿模型
    
    返回:
        (min_val, max_val) 元组
    """
    return model.x_range


def get_model_output_range(model: CompensationModel) -> Tuple[float, float]:
    """
    获取模型的输出范围
    
    参数:
        model: 补偿模型
    
    返回:
        (min_val, max_val) 元组
    """
    return model.y_range


def is_in_model_range(value: float, model: CompensationModel) -> bool:
    """
    检查值是否在模型有效范围内
    
    参数:
        value: 测量值
        model: 补偿模型
    
    返回:
        是否在范围内
    """
    x_min, x_max = model.x_range
    return x_min <= value <= x_max
