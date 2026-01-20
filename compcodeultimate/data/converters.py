# -*- coding: utf-8 -*-
"""
单位转换模块
提供灰度值与毫米之间的转换功能，支持标量和向量化操作
"""

import numpy as np
from typing import Union, Optional

# 默认配置常量
DEFAULT_OFFSET = 32768
DEFAULT_SCALE_FACTOR = 1.6
DEFAULT_INVALID_VALUE = 65535


# ==================== 标量/兼容函数 ====================

def gray_to_mm(gray_value: Union[int, float, np.ndarray],
               offset: Optional[float] = None,
               scale_factor: Optional[float] = None,
               invalid_value: int = DEFAULT_INVALID_VALUE) -> Union[float, np.ndarray, None]:
    """
    灰度值转换为毫米
    
    公式: y(mm) = (gray_value - offset) * scale_factor / 1000
    
    参数:
        gray_value: 灰度值（标量或数组）
        offset: 偏移量，默认 32768
        scale_factor: 缩放因子，默认 1.6
        invalid_value: 无效值，默认 65535
    
    返回:
        毫米值（与输入类型匹配）
    """
    if offset is None:
        offset = DEFAULT_OFFSET
    if scale_factor is None:
        scale_factor = DEFAULT_SCALE_FACTOR
    
    if isinstance(gray_value, np.ndarray):
        return gray_to_mm_vectorized(gray_value, offset, scale_factor)
    
    if gray_value is None or gray_value == invalid_value:
        return None
    
    return ((gray_value - offset) * scale_factor) / 1000.0


def mm_to_gray(mm_value: Union[float, np.ndarray],
               offset: Optional[float] = None,
               scale_factor: Optional[float] = None,
               invalid_value: int = DEFAULT_INVALID_VALUE) -> Union[int, np.ndarray]:
    """
    毫米转换为灰度值
    
    公式: gray_value = (mm_value * 1000 / scale_factor) + offset
    
    参数:
        mm_value: 毫米值（标量或数组）
        offset: 偏移量，默认 32768
        scale_factor: 缩放因子，默认 1.6
        invalid_value: 无效值，默认 65535
    
    返回:
        灰度值（uint16范围）
    """
    if offset is None:
        offset = DEFAULT_OFFSET
    if scale_factor is None:
        scale_factor = DEFAULT_SCALE_FACTOR
    
    if isinstance(mm_value, np.ndarray):
        return mm_to_gray_vectorized(mm_value, offset, scale_factor)
    
    if mm_value is None:
        return invalid_value
    
    gray_value = (mm_value * 1000.0 / scale_factor) + offset
    return int(np.clip(gray_value, 0, 65535))


# ==================== 向量化函数（性能优化）====================

def gray_to_mm_vectorized(gray_array: np.ndarray,
                          offset: float = DEFAULT_OFFSET,
                          scale_factor: float = DEFAULT_SCALE_FACTOR) -> np.ndarray:
    """
    向量化灰度值转毫米
    
    优化说明:
    - 使用 float32 避免 uint16 下溢
    - 单次向量化运算，无Python循环
    
    参数:
        gray_array: 灰度值数组
        offset: 偏移量
        scale_factor: 缩放因子
    
    返回:
        毫米值数组 (float32)
    """
    # 转换为 float32 避免溢出
    gray_float = gray_array.astype(np.float32)
    return ((gray_float - offset) * scale_factor) / 1000.0


def mm_to_gray_vectorized(mm_array: np.ndarray,
                          offset: float = DEFAULT_OFFSET,
                          scale_factor: float = DEFAULT_SCALE_FACTOR) -> np.ndarray:
    """
    向量化毫米转灰度值
    
    优化说明:
    - 使用 np.clip 进行边界检查
    - 直接返回 uint16 类型
    
    参数:
        mm_array: 毫米值数组
        offset: 偏移量
        scale_factor: 缩放因子
    
    返回:
        灰度值数组 (uint16)
    """
    gray_values = (mm_array * 1000.0 / scale_factor) + offset
    return np.clip(gray_values, 0, 65535).astype(np.uint16)


# ==================== 批量转换工具 ====================

def convert_depth_image_to_mm(depth_array: np.ndarray,
                               offset: float = DEFAULT_OFFSET,
                               scale_factor: float = DEFAULT_SCALE_FACTOR,
                               invalid_value: int = DEFAULT_INVALID_VALUE,
                               preserve_invalid: bool = True) -> np.ndarray:
    """
    将整个深度图转换为毫米值
    
    参数:
        depth_array: 深度图数组 (uint16)
        offset: 偏移量
        scale_factor: 缩放因子
        invalid_value: 无效像素值
        preserve_invalid: 是否保留无效值为 NaN
    
    返回:
        毫米值数组 (float32)，无效像素为 NaN
    """
    mm_array = gray_to_mm_vectorized(depth_array, offset, scale_factor)
    
    if preserve_invalid:
        invalid_mask = (depth_array == invalid_value)
        mm_array[invalid_mask] = np.nan
    
    return mm_array


def convert_mm_image_to_depth(mm_array: np.ndarray,
                               offset: float = DEFAULT_OFFSET,
                               scale_factor: float = DEFAULT_SCALE_FACTOR,
                               invalid_value: int = DEFAULT_INVALID_VALUE) -> np.ndarray:
    """
    将毫米值图像转换为深度图
    
    参数:
        mm_array: 毫米值数组 (float32)，NaN 视为无效
        offset: 偏移量
        scale_factor: 缩放因子
        invalid_value: 无效像素值
    
    返回:
        深度图数组 (uint16)
    """
    # 找出无效像素（NaN）
    invalid_mask = np.isnan(mm_array)
    
    # 转换有效像素
    depth_array = mm_to_gray_vectorized(
        np.nan_to_num(mm_array, nan=0.0), 
        offset, 
        scale_factor
    )
    
    # 恢复无效值
    depth_array[invalid_mask] = invalid_value
    
    return depth_array


# ==================== 配置辅助函数 ====================

def create_converter(offset: float = DEFAULT_OFFSET,
                     scale_factor: float = DEFAULT_SCALE_FACTOR,
                     invalid_value: int = DEFAULT_INVALID_VALUE):
    """
    创建预配置的转换器函数
    
    用法:
        to_mm, to_gray = create_converter(offset=32768, scale_factor=1.6)
        depth_mm = to_mm(depth_array)
        depth_gray = to_gray(depth_mm)
    
    参数:
        offset: 偏移量
        scale_factor: 缩放因子
        invalid_value: 无效值
    
    返回:
        (to_mm_func, to_gray_func) 元组
    """
    def to_mm(gray_value):
        return gray_to_mm(gray_value, offset, scale_factor, invalid_value)
    
    def to_gray(mm_value):
        return mm_to_gray(mm_value, offset, scale_factor, invalid_value)
    
    return to_mm, to_gray
