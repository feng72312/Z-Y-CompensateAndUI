# -*- coding: utf-8 -*-
"""
补偿模块 - 整合补偿模型、线性度计算功能
"""

import os
import json
import numpy as np
from scipy.interpolate import splrep, splev
from config import (SPLINE_ORDER, FULL_SCALE, 
                    EXTRAPOLATE_ENABLED, EXTRAPOLATE_MAX_LOW, EXTRAPOLATE_MAX_HIGH,
                    EXTRAPOLATE_OUTPUT_MIN, EXTRAPOLATE_OUTPUT_MAX, EXTRAPOLATE_CLAMP_OUTPUT)


# ==================== 补偿模型 ====================

def build_compensation_model(actual_values, measured_values):
    """
    建立补偿模型
    
    参数:
        actual_values: 实际值列表 (mm) - 使用绝对值
        measured_values: 测量值列表 (mm) - 使用绝对值
    
    返回:
        dict: {
            'forward_model': 正向模型 (实际→测量),
            'inverse_model': 逆向模型 (测量→实际),
            'actual_range': (min, max),
            'measured_range': (min, max)
        }
    
    抛出:
        ValueError: 数据不足或数据无效
    """
    actual_arr = np.array(actual_values, dtype=np.float64)
    measured_arr = np.array(measured_values, dtype=np.float64)
    
    # 数据验证
    if len(actual_arr) < 4:
        raise ValueError(f"数据点不足：需要至少4个点，当前只有{len(actual_arr)}个。"
                        f"三次样条拟合(k=3)要求数据点数量 > 阶数。")
    
    if len(actual_arr) != len(measured_arr):
        raise ValueError(f"数据长度不匹配：实际值{len(actual_arr)}个，测量值{len(measured_arr)}个")
    
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
    
    # 确保数据有序（splrep要求x值递增）
    sort_idx_actual = np.argsort(actual_arr)
    actual_sorted = actual_arr[sort_idx_actual]
    measured_sorted_by_actual = measured_arr[sort_idx_actual]
    
    sort_idx_measured = np.argsort(measured_arr)
    measured_sorted = measured_arr[sort_idx_measured]
    actual_sorted_by_measured = actual_arr[sort_idx_measured]
    
    # 使用绝对值建立模型
    # 移除s=0，让scipy自动选择平滑因子，防止过拟合
    k = min(3, len(actual_arr) - 1)
    
    try:
        # 正向模型: 实际值 -> 测量值
        forward_model = splrep(actual_sorted, measured_sorted_by_actual, k=k)
        
        # 逆向模型: 测量值 -> 实际值
        inverse_model = splrep(measured_sorted, actual_sorted_by_measured, k=k)
    except Exception as e:
        raise ValueError(f"样条拟合失败: {str(e)}。请检查数据是否单调且无重复。")
    
    return {
        'forward_model': forward_model,
        'inverse_model': inverse_model,
        'actual_range': (actual_arr.min(), actual_arr.max()),
        'measured_range': (measured_arr.min(), measured_arr.max()),
        'actual_values': actual_arr.tolist(),
        'measured_values': measured_arr.tolist()
    }


def save_model(model, filepath, minimal=True):
    """
    保存补偿模型到JSON文件
    
    参数:
        model: build_compensation_model返回的模型字典
        filepath: 保存路径（.json格式）
        minimal: 是否使用精简格式（默认True，文件更小）
    
    返回:
        str: 保存的文件路径
    """
    # 确保文件扩展名为 .json
    if not filepath.endswith('.json'):
        filepath = filepath.replace('.npz', '.json')
        if not filepath.endswith('.json'):
            filepath += '.json'
    
    # 提取样条模型参数
    inv_t, inv_c, inv_k = model['inverse_model']
    
    # 精度控制函数（6位小数足够精度，大幅减小文件大小）
    def round_list(arr, decimals=6):
        return [round(float(x), decimals) for x in np.array(arr)]
    
    if minimal:
        # 精简格式：只保存补偿必需的逆向模型
        model_data = {
            'model_type': 'cubic_spline',
            'version': '2.2',
            # 逆向模型（用于补偿：测量值 -> 实际值）
            'knots': round_list(inv_t),
            'coefficients': round_list(inv_c),
            'k': int(inv_k),
            # 范围信息
            'x_range': round_list(model['measured_range'], 4),  # 输入范围（测量值）
            'y_range': round_list(model['actual_range'], 4),    # 输出范围（实际值）
            'calibration_points': len(model['actual_values'])
        }
    else:
        # 完整格式：保存所有信息（用于分析和调试）
        fwd_t, fwd_c, fwd_k = model['forward_model']
        model_data = {
            'model_type': 'cubic_spline',
            'version': '2.2',
            'description': '深度图补偿三次样条模型（完整格式）',
            'forward_model': {
                't': round_list(fwd_t),
                'c': round_list(fwd_c),
                'k': int(fwd_k)
            },
            'inverse_model': {
                't': round_list(inv_t),
                'c': round_list(inv_c),
                'k': int(inv_k)
            },
            'actual_range': round_list(model['actual_range'], 4),
            'measured_range': round_list(model['measured_range'], 4),
            'calibration_data': {
                'num_points': len(model['actual_values']),
                'actual_values': round_list(model['actual_values'], 4),
                'measured_values': round_list(model['measured_values'], 4)
            }
        }
    
    # 保存为JSON文件（使用缩进便于查看）
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(model_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def load_model(filepath):
    """
    从JSON文件加载补偿模型
    
    支持多种格式：
    - 精简格式（v2.2）：只含 knots, coefficients, k
    - 完整格式（v2.1/v2.2）：含 forward_model, inverse_model
    - 旧版格式：用户以前的模型格式
    
    参数:
        filepath: 模型文件路径（.json格式）
    
    返回:
        dict: 与build_compensation_model返回格式相同的模型字典
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 检测格式并解析
    if 'knots' in data:
        # 精简格式或旧版格式：直接包含 knots, coefficients, k
        inverse_model = (
            np.array(data['knots']),
            np.array(data['coefficients']),
            data['k']
        )
        # 精简格式没有正向模型，创建一个占位符
        forward_model = None
        
        # 获取范围信息
        if 'x_range' in data:
            measured_range = tuple(data['x_range'])
            actual_range = tuple(data['y_range'])
        else:
            # 从knots推断范围
            t = data['knots']
            k = data['k']
            measured_range = (t[k], t[-k-1])
            actual_range = measured_range  # 近似
        
        num_points = data.get('calibration_points', 0)
        actual_values = []
        measured_values = []
        
    elif 'inverse_model' in data:
        # 完整格式：含有 inverse_model 字典
        inv = data['inverse_model']
        inverse_model = (np.array(inv['t']), np.array(inv['c']), inv['k'])
        
        # 正向模型（可选）
        if 'forward_model' in data:
            fwd = data['forward_model']
            forward_model = (np.array(fwd['t']), np.array(fwd['c']), fwd['k'])
        else:
            forward_model = None
        
        actual_range = tuple(data['actual_range'])
        measured_range = tuple(data['measured_range'])
        
        # 获取标定数据
        calib = data.get('calibration_data', {})
        actual_values = calib.get('actual_values', [])
        measured_values = calib.get('measured_values', [])
        num_points = calib.get('num_points', len(actual_values))
    
    else:
        raise ValueError("无法识别的模型格式")
    
    return {
        'forward_model': forward_model,
        'inverse_model': inverse_model,
        'actual_range': actual_range,
        'measured_range': measured_range,
        'actual_values': actual_values,
        'measured_values': measured_values,
        'num_points': num_points
    }


def apply_compensation(measured_values, inverse_model, extrapolate_config=None):
    """
    应用补偿模型（支持线性外推）
    
    参数:
        measured_values: 测量值（单个值或数组）
        inverse_model: 逆向补偿模型
        extrapolate_config: 外推配置字典（可选）
            - enabled: 是否启用外推
            - max_low: 低端最大外推距离
            - max_high: 高端最大外推距离
            - output_min: 输出最小值
            - output_max: 输出最大值
            - clamp_output: 是否限制输出范围
    
    返回:
        补偿后的值
    """
    # 默认配置
    if extrapolate_config is None:
        extrapolate_config = {
            'enabled': EXTRAPOLATE_ENABLED,
            'max_low': EXTRAPOLATE_MAX_LOW,
            'max_high': EXTRAPOLATE_MAX_HIGH,
            'output_min': EXTRAPOLATE_OUTPUT_MIN,
            'output_max': EXTRAPOLATE_OUTPUT_MAX,
            'clamp_output': EXTRAPOLATE_CLAMP_OUTPUT
        }
    
    if not extrapolate_config.get('enabled', False):
        # 不使用外推，直接使用样条插值
        return splev(measured_values, inverse_model, ext=0)
    
    # 使用线性外推
    return apply_compensation_with_extrapolation(measured_values, inverse_model, extrapolate_config)


def apply_compensation_with_extrapolation(measured_values, inverse_model, config):
    """
    带线性外推的补偿函数
    
    参数:
        measured_values: 测量值数组
        inverse_model: 逆向补偿模型 (t, c, k)
        config: 外推配置字典
    
    返回:
        补偿后的值数组
    """
    measured_arr = np.atleast_1d(np.array(measured_values, dtype=np.float64))
    is_scalar = np.ndim(measured_values) == 0
    
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
        # 计算低端斜率（样条导数）
        slope_low = splev(x_min, inverse_model, der=1)
        y_min = splev(x_min, inverse_model)
        
        # 计算外推距离
        extrapolate_dist = x_min - measured_arr[below_range]
        max_dist = config.get('max_low', EXTRAPOLATE_MAX_LOW)
        
        # 限制外推距离
        extrapolate_dist_clamped = np.minimum(extrapolate_dist, max_dist)
        
        # 线性外推
        result[below_range] = y_min - slope_low * extrapolate_dist_clamped
    
    # 高端外推
    above_range = measured_arr > x_max
    if np.any(above_range):
        # 计算高端斜率（样条导数）
        slope_high = splev(x_max, inverse_model, der=1)
        y_max = splev(x_max, inverse_model)
        
        # 计算外推距离
        extrapolate_dist = measured_arr[above_range] - x_max
        max_dist = config.get('max_high', EXTRAPOLATE_MAX_HIGH)
        
        # 限制外推距离
        extrapolate_dist_clamped = np.minimum(extrapolate_dist, max_dist)
        
        # 线性外推
        result[above_range] = y_max + slope_high * extrapolate_dist_clamped
    
    # 输出范围限制
    if config.get('clamp_output', True):
        output_min = config.get('output_min', EXTRAPOLATE_OUTPUT_MIN)
        output_max = config.get('output_max', EXTRAPOLATE_OUTPUT_MAX)
        result = np.clip(result, output_min, output_max)
    
    return result[0] if is_scalar else result


def get_extrapolation_stats(measured_values, inverse_model):
    """
    获取外推统计信息
    
    参数:
        measured_values: 测量值数组
        inverse_model: 逆向补偿模型
    
    返回:
        dict: 外推统计信息
    """
    measured_arr = np.atleast_1d(np.array(measured_values, dtype=np.float64))
    
    t, c, k = inverse_model
    x_min, x_max = t[k], t[-k-1]
    
    below_range = measured_arr < x_min
    above_range = measured_arr > x_max
    in_range = (measured_arr >= x_min) & (measured_arr <= x_max)
    
    stats = {
        'total_count': len(measured_arr),
        'in_range_count': np.sum(in_range),
        'below_range_count': np.sum(below_range),
        'above_range_count': np.sum(above_range),
        'model_range': (float(x_min), float(x_max)),
        'data_range': (float(measured_arr.min()), float(measured_arr.max())),
    }
    
    if np.any(below_range):
        stats['below_range_max_dist'] = float(x_min - measured_arr[below_range].min())
    else:
        stats['below_range_max_dist'] = 0.0
    
    if np.any(above_range):
        stats['above_range_max_dist'] = float(measured_arr[above_range].max() - x_max)
    else:
        stats['above_range_max_dist'] = 0.0
    
    return stats


def get_model_range(model):
    """
    获取模型的有效范围
    
    参数:
        model: splrep返回的模型 (t, c, k)
    
    返回:
        (min_val, max_val)
    """
    t, c, k = model
    return t[k], t[-k-1]


# ==================== 线性度计算 ====================

def calculate_linearity(actual_values, measured_values, full_scale=None):
    """
    使用最佳直线法(BFSL)计算线性度
    
    参数:
        actual_values: 实际值数组
        measured_values: 测量值数组
        full_scale: 满量程（如果为None，使用config中的值）
    
    返回:
        dict: {
            'linearity': 线性度百分比,
            'max_deviation': 最大偏差,
            'abs_max_deviation': 绝对最大偏差,
            'rms_error': 均方根误差,
            'mae': 平均绝对误差,
            'r_squared': 决定系数,
            'slope': 斜率,
            'intercept': 截距
        }
    
    抛出:
        ValueError: 数据不足或数据无效
    """
    full_scale = full_scale or FULL_SCALE
    
    actual_arr = np.array(actual_values, dtype=np.float64)
    measured_arr = np.array(measured_values, dtype=np.float64)
    
    # 数据验证
    if len(actual_arr) < 2:
        raise ValueError(f"数据点不足：线性回归需要至少2个点，当前只有{len(actual_arr)}个")
    
    if len(actual_arr) != len(measured_arr):
        raise ValueError(f"数据长度不匹配：实际值{len(actual_arr)}个，测量值{len(measured_arr)}个")
    
    # 检查NaN/Inf
    if np.any(np.isnan(actual_arr)) or np.any(np.isinf(actual_arr)):
        raise ValueError("实际值包含NaN或Inf")
    
    if np.any(np.isnan(measured_arr)) or np.any(np.isinf(measured_arr)):
        raise ValueError("测量值包含NaN或Inf")
    
    # 零点归一化（相对值）
    actual_relative = actual_arr - actual_arr[0]
    measured_relative = measured_arr - measured_arr[0]
    
    # 检查实际值是否有变化（避免全部相同导致SVD不收敛）
    if np.all(actual_relative == 0):
        raise ValueError("所有实际值相同，无法进行线性回归")
    
    # 线性回归
    try:
        coeffs = np.polyfit(actual_relative, measured_relative, 1)
    except np.linalg.LinAlgError as e:
        raise ValueError(f"线性回归失败(SVD不收敛): {str(e)}。"
                        f"请检查数据是否有效，实际值范围: {actual_arr.min():.4f}~{actual_arr.max():.4f}")
    
    slope, intercept = coeffs[0], coeffs[1]
    
    # 预测值
    predicted = slope * actual_relative + intercept
    
    # 计算偏差
    deviations = measured_relative - predicted
    max_deviation = deviations.max()
    min_deviation = deviations.min()
    abs_max_deviation = max(abs(max_deviation), abs(min_deviation))
    
    # 线性度 = 最大偏差 / 满量程 * 100%
    linearity = (abs_max_deviation / full_scale) * 100.0
    
    # 其他统计指标
    rms_error = np.sqrt(np.mean(deviations ** 2))
    mae = np.mean(np.abs(deviations))
    
    # R²
    ss_res = np.sum(deviations ** 2)
    ss_tot = np.sum((measured_relative - measured_relative.mean()) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    return {
        'linearity': linearity,
        'max_deviation': max_deviation,
        'min_deviation': min_deviation,
        'abs_max_deviation': abs_max_deviation,
        'rms_error': rms_error,
        'mae': mae,
        'r_squared': r_squared,
        'slope': slope,
        'intercept': intercept
    }


def calculate_compensation_effect(actual_values, measured_values, compensated_values, full_scale=None):
    """
    计算补偿前后的效果对比
    
    注意：所有输入值应该已经是相对值（零点归一化）
    
    返回:
        dict: {
            'before': 补偿前的线性度指标,
            'after': 补偿后的线性度指标,
            'improvement': 改善百分比,
            'actual_values_mm': 实际相对值,
            'measured_values_mm': 测量相对值,
            'compensated_values_mm': 补偿后相对值
        }
    """
    before = calculate_linearity(actual_values, measured_values, full_scale)
    after = calculate_linearity(actual_values, compensated_values, full_scale)
    
    improvement = ((before['linearity'] - after['linearity']) / before['linearity'] * 100.0
                   if before['linearity'] != 0 else 0)
    
    return {
        'before': before,
        'after': after,
        'improvement': improvement,
        'actual_values_mm': actual_values,
        'measured_values_mm': measured_values,
        'compensated_values_mm': compensated_values
    }


# ==================== 逐像素补偿 ====================

def compensate_image_pixels(depth_array, inverse_model, invalid_value=65535, extrapolate_config=None):
    """
    对深度图进行逐像素补偿（支持线性外推）
    
    参数:
        depth_array: 深度图数组（灰度值）
        inverse_model: 逆向补偿模型
        invalid_value: 无效像素值
        extrapolate_config: 外推配置字典（可选）
    
    返回:
        dict: {
            'compensated_array': 补偿后的数组,
            'stats': 统计信息
        }
    """
    from utils import gray_to_mm, mm_to_gray
    
    # 默认外推配置
    if extrapolate_config is None:
        extrapolate_config = {
            'enabled': EXTRAPOLATE_ENABLED,
            'max_low': EXTRAPOLATE_MAX_LOW,
            'max_high': EXTRAPOLATE_MAX_HIGH,
            'output_min': EXTRAPOLATE_OUTPUT_MIN,
            'output_max': EXTRAPOLATE_OUTPUT_MAX,
            'clamp_output': EXTRAPOLATE_CLAMP_OUTPUT
        }
    
    # 获取模型范围
    model_min, model_max = get_model_range(inverse_model)
    
    # 创建输出数组（复制原数组，保持无效像素和超范围像素的原值）
    compensated = depth_array.copy().astype(np.uint16)
    
    # 标记无效像素
    valid_mask = (depth_array != invalid_value)
    valid_gray = depth_array[valid_mask]
    
    # 转换为毫米
    measured_mm = gray_to_mm(valid_gray)
    
    # 判断在范围内的像素（用于统计）
    in_range_mask = (measured_mm >= model_min) & (measured_mm <= model_max)
    in_range_count = np.sum(in_range_mask)
    
    # 判断外推区域的像素
    extrapolate_enabled = extrapolate_config.get('enabled', False)
    max_low = extrapolate_config.get('max_low', EXTRAPOLATE_MAX_LOW)
    max_high = extrapolate_config.get('max_high', EXTRAPOLATE_MAX_HIGH)
    
    if extrapolate_enabled:
        # 扩展范围到包括外推区域
        extended_min = model_min - max_low
        extended_max = model_max + max_high
        compensate_mask = (measured_mm >= extended_min) & (measured_mm <= extended_max)
    else:
        compensate_mask = in_range_mask
    
    compensate_count = np.sum(compensate_mask)
    extrapolate_count = compensate_count - in_range_count if extrapolate_enabled else 0
    
    # 补偿像素
    if compensate_count > 0:
        compensated_mm = apply_compensation(
            measured_mm[compensate_mask], 
            inverse_model,
            extrapolate_config=extrapolate_config
        )
        compensated_gray = mm_to_gray(compensated_mm)
        
        # 填充结果
        temp = valid_gray.copy()
        temp[compensate_mask] = compensated_gray
        compensated[valid_mask] = temp
    
    stats = {
        'total_pixels': depth_array.size,
        'valid_pixels': np.sum(valid_mask),
        'in_range_pixels': in_range_count,
        'extrapolated_pixels': extrapolate_count,
        'compensated_pixels': compensate_count,
        'out_of_range_pixels': np.sum(valid_mask) - compensate_count,
        'invalid_pixels': depth_array.size - np.sum(valid_mask),
        'compensation_rate': compensate_count / depth_array.size * 100,
        'extrapolation_enabled': extrapolate_enabled
    }
    
    return {
        'compensated_array': compensated,
        'stats': stats
    }

