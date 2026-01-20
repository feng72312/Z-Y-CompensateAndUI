# -*- coding: utf-8 -*-
"""
工具模块 - 整合数据读取、单位转换、ROI处理等基础功能
支持中文路径
"""

import os
import sys
import csv
import numpy as np
from PIL import Image
from pathlib import Path
from config import OFFSET, SCALE_FACTOR, INVALID_VALUE, ROI_X, ROI_Y, ROI_WIDTH, ROI_HEIGHT

# Windows系统中文路径支持
if sys.platform == 'win32':
    import locale
    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass


# ==================== 单位转换 ====================

def gray_to_mm(gray_value, offset=None, scale_factor=None):
    """
    灰度值转换为毫米（支持单个值和numpy数组）
    修复：先转换为float32避免uint16下溢
    
    参数:
        gray_value: 灰度值（单个值或numpy数组）
        offset: 偏移量，默认使用config.OFFSET (32768)
        scale_factor: 缩放因子，默认使用config.SCALE_FACTOR (1.6)
    """
    # 使用默认值
    if offset is None:
        offset = OFFSET
    if scale_factor is None:
        scale_factor = SCALE_FACTOR
    
    if isinstance(gray_value, np.ndarray):
        gray_float = gray_value.astype(np.float32)
        return ((gray_float - offset) * scale_factor) / 1000.0
    
    if gray_value is None or gray_value == INVALID_VALUE:
        return None
    return ((gray_value - offset) * scale_factor) / 1000.0


def mm_to_gray(mm_value, offset=None, scale_factor=None):
    """
    毫米转换为灰度值（支持单个值和numpy数组）
    
    参数:
        mm_value: 毫米值（单个值或numpy数组）
        offset: 偏移量，默认使用config.OFFSET (32768)
        scale_factor: 缩放因子，默认使用config.SCALE_FACTOR (1.6)
    """
    # 使用默认值
    if offset is None:
        offset = OFFSET
    if scale_factor is None:
        scale_factor = SCALE_FACTOR
    
    if isinstance(mm_value, np.ndarray):
        gray_values = (mm_value * 1000.0 / scale_factor) + offset
        return np.clip(gray_values, 0, 65535).astype(np.uint16)
    
    if mm_value is None:
        return INVALID_VALUE
    gray_value = (mm_value * 1000.0 / scale_factor) + offset
    return int(np.clip(gray_value, 0, 65535))


# ==================== 数据读取 ====================

def read_depth_image(image_path):
    """
    读取16位深度图像（支持中文路径）
    """
    # 使用 Path 处理中文路径
    image_path = str(Path(image_path))
    image = Image.open(image_path)
    return np.array(image, dtype=np.uint16)


def save_depth_image(image_array, output_path):
    """
    保存16位深度图像（支持中文路径）
    """
    output_path = str(Path(output_path))
    # 确保目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    Image.fromarray(image_array.astype(np.uint16)).save(output_path)


def parse_csv(csv_path):
    """
    解析CSV文件，返回数据列表
    自动识别列名
    """
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        data = []
        for row in reader:
            # 尝试不同的列名
            displacement = None
            for key in ['实际累计位移(mm)', '实际累计位移', '位移(mm)', '位移']:
                if key in row:
                    displacement = float(row[key])
                    break
            
            if displacement is not None:
                data.append({'实际累计位移(mm)': displacement})
        
        return data


def get_image_files(directory):
    """
    获取目录中的图像文件和对应的CSV（支持中文路径）
    支持PNG和TIF格式的深度图
    返回: {'csv_path': str, 'png_paths': list, 'csv_data': list}
    """
    # 使用 Path 处理中文路径
    directory = Path(directory)
    
    if not directory.exists():
        return None
    
    # 查找CSV文件（使用set去重，Windows不区分大小写）
    csv_files = set()
    for pattern in ['*.csv', '*.CSV']:
        for f in directory.glob(pattern):
            csv_files.add(f.resolve())  # 使用绝对路径确保唯一性
    
    if not csv_files:
        return None
    
    csv_path = str(list(csv_files)[0])
    csv_data = parse_csv(csv_path)
    
    # 查找图像文件（支持PNG和TIF格式，使用set去重）
    image_files = set()
    for pattern in ['*.png', '*.PNG', '*.tif', '*.TIF', '*.tiff', '*.TIFF']:
        for f in directory.glob(pattern):
            image_files.add(f.resolve())  # 使用绝对路径确保唯一性
    
    # 按文件名排序（提取数字部分进行自然排序）
    def extract_number(path):
        """从文件名提取数字用于排序"""
        import re
        name = Path(path).stem
        numbers = re.findall(r'\d+', name)
        return int(numbers[-1]) if numbers else 0
    
    image_paths = sorted([str(f) for f in image_files], key=extract_number)
    
    return {
        'csv_path': csv_path,
        'png_paths': image_paths,  # 保持键名兼容性
        'csv_data': csv_data
    }


# ==================== ROI处理 ====================

def get_roi(depth_array, x=None, y=None, width=None, height=None):
    """
    提取ROI区域，如果参数为None则使用config中的配置
    如果width或height为-1，则返回整个图像
    """
    x = x if x is not None else ROI_X
    y = y if y is not None else ROI_Y
    width = width if width is not None else ROI_WIDTH
    height = height if height is not None else ROI_HEIGHT
    
    # 使用整个图像
    if width == -1 and height == -1:
        return depth_array
    
    img_height, img_width = depth_array.shape
    x_start = max(0, x)
    y_start = max(0, y)
    x_end = img_width if width == -1 else min(img_width, x + width)
    y_end = img_height if height == -1 else min(img_height, y + height)
    
    return depth_array[y_start:y_end, x_start:x_end]


def get_valid_pixels(array):
    """
    获取有效像素（排除无效值）
    返回: valid_pixels, valid_mask
    """
    valid_mask = (array != INVALID_VALUE)
    valid_pixels = array[valid_mask]
    return valid_pixels, valid_mask


def calculate_stats(array):
    """
    计算数组的统计信息
    返回: dict with min, max, mean, std, count
    """
    valid_pixels, _ = get_valid_pixels(array)
    
    if valid_pixels.size == 0:
        return {
            'min': None, 'max': None, 'mean': None, 
            'std': None, 'count': 0, 'total': array.size
        }
    
    return {
        'min': valid_pixels.min(),
        'max': valid_pixels.max(),
        'mean': valid_pixels.mean(),
        'std': valid_pixels.std(),
        'count': valid_pixels.size,
        'total': array.size
    }


# ==================== 批量处理 ====================

def batch_process_images(image_paths, process_func, **kwargs):
    """
    批量处理图像
    process_func: 处理函数，接收depth_array和kwargs
    """
    results = []
    for img_path in image_paths:
        depth_array = read_depth_image(img_path)
        result = process_func(depth_array, **kwargs)
        results.append(result)
    return results


# ==================== 数据质量检测 ====================

def detect_anomalies(actual_values, measured_values, threshold=0.15):
    """
    检测数据中的异常点（基于增量绝对偏差分析）
    
    当测量增量与实际增量的差值超过实际增量的指定百分比时，
    标记为异常点，提示可能存在硬件抖动或数据采集问题。
    
    判定公式: |测量增量 - 实际增量| > 实际增量 × threshold
    
    参数:
        actual_values: 实际值数组 (mm)
        measured_values: 测量值数组 (mm)
        threshold: 偏离阈值（默认0.15，即实际增量的15%）
    
    返回:
        dict: {
            'has_anomaly': bool,           # 是否存在异常
            'anomaly_points': list,        # 异常点列表 [(点索引, 实际增量, 测量增量, 偏差百分比), ...]
            'warning_message': str         # 警告消息
        }
    """
    actual_arr = np.array(actual_values, dtype=np.float64)
    measured_arr = np.array(measured_values, dtype=np.float64)
    
    # 至少需要2个点才能计算增量
    if len(actual_arr) < 2:
        return {
            'has_anomaly': False,
            'anomaly_points': [],
            'warning_message': ''
        }
    
    # 计算相邻点的增量
    actual_inc = np.diff(actual_arr)
    measured_inc = np.diff(measured_arr)
    
    # 检测异常点
    anomaly_points = []
    for i in range(len(actual_inc)):
        act_inc = actual_inc[i]
        mea_inc = measured_inc[i]
        
        # 跳过实际增量为0或接近0的点
        if abs(act_inc) < 1e-9:
            continue
        
        # 计算绝对偏差
        diff = abs(mea_inc - act_inc)
        # 计算相对于实际增量的偏差百分比
        deviation_pct = diff / abs(act_inc)
        
        if deviation_pct > threshold:
            # 点索引从1开始（用户友好），记录的是起始点
            anomaly_points.append((i + 1, act_inc, mea_inc, deviation_pct * 100))
    
    # 生成警告消息
    has_anomaly = len(anomaly_points) > 0
    warning_message = ''
    if has_anomaly:
        warning_lines = [
            "=" * 60,
            "[警告] 检测到数据异常点，可能存在硬件抖动或采集问题！",
            "=" * 60,
            f"异常阈值: 实际增量的 {threshold*100:.0f}%",
            "",
            "异常点详情:"
        ]
        for idx, act_inc, mea_inc, dev_pct in anomaly_points:
            warning_lines.append(f"  点{idx}->点{idx+1}: 实际增量={act_inc:.4f}mm, 测量增量={mea_inc:.4f}mm, 偏差={dev_pct:.1f}%")
        warning_lines.extend([
            "",
            "[建议] 请检查以下问题并考虑重新采集数据:",
            "  1. 硬件移动平台是否发生抖动/抽搐",
            "  2. 标定过程中是否有外部干扰",
            "  3. 对应图像的深度数据是否异常",
            "=" * 60
        ])
        warning_message = '\n'.join(warning_lines)
    
    return {
        'has_anomaly': has_anomaly,
        'anomaly_points': anomaly_points,
        'warning_message': warning_message
    }

