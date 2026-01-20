# -*- coding: utf-8 -*-
"""
文件读写模块
提供深度图、补偿模型、CSV数据的读写功能
支持中文路径
"""

import os
import sys
import csv
import json
import re
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from .models import CompensationModel

# Windows系统中文路径支持
if sys.platform == 'win32':
    import locale
    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass


# ==================== 图像读写 ====================

def read_depth_image(image_path: Union[str, Path]) -> np.ndarray:
    """
    读取16位深度图像
    
    支持格式: PNG, TIF/TIFF
    支持中文路径
    
    参数:
        image_path: 图像文件路径
    
    返回:
        深度图数组 (uint16)
    
    抛出:
        FileNotFoundError: 文件不存在
        ValueError: 图像格式不支持
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    image = Image.open(str(image_path))
    return np.array(image, dtype=np.uint16)


def save_depth_image(image_array: np.ndarray, 
                     output_path: Union[str, Path],
                     create_dir: bool = True) -> str:
    """
    保存16位深度图像
    
    参数:
        image_array: 深度图数组
        output_path: 输出路径
        create_dir: 是否自动创建目录
    
    返回:
        实际保存路径
    """
    output_path = Path(output_path)
    
    if create_dir:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    Image.fromarray(image_array.astype(np.uint16)).save(str(output_path))
    return str(output_path)


# ==================== CSV读取 ====================

def parse_csv(csv_path: Union[str, Path], 
              displacement_columns: Optional[List[str]] = None) -> List[Dict[str, float]]:
    """
    解析CSV文件，返回位移数据列表
    
    自动识别列名，支持多种列名格式
    
    参数:
        csv_path: CSV文件路径
        displacement_columns: 自定义位移列名列表
    
    返回:
        包含位移数据的字典列表
    """
    if displacement_columns is None:
        displacement_columns = [
            '实际累计位移(mm)', 
            '实际累计位移', 
            '位移(mm)', 
            '位移',
            'displacement',
            'Displacement'
        ]
    
    csv_path = Path(csv_path)
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        data = []
        
        for row in reader:
            displacement = None
            for key in displacement_columns:
                if key in row:
                    try:
                        displacement = float(row[key])
                        break
                    except ValueError:
                        continue
            
            if displacement is not None:
                data.append({'实际累计位移(mm)': displacement})
        
        return data


def get_image_files(directory: Union[str, Path],
                    image_patterns: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    获取目录中的图像文件和对应的CSV
    
    参数:
        directory: 目录路径
        image_patterns: 图像文件模式列表
    
    返回:
        {
            'csv_path': CSV文件路径,
            'png_paths': 图像文件路径列表（自然排序）,
            'csv_data': CSV数据列表
        }
        如果目录不存在或没有找到文件，返回None
    """
    if image_patterns is None:
        image_patterns = ['*.png', '*.PNG', '*.tif', '*.TIF', '*.tiff', '*.TIFF']
    
    directory = Path(directory)
    
    if not directory.exists():
        return None
    
    # 查找CSV文件（去重）
    csv_files = set()
    for pattern in ['*.csv', '*.CSV']:
        for f in directory.glob(pattern):
            csv_files.add(f.resolve())
    
    if not csv_files:
        return None
    
    csv_path = str(list(csv_files)[0])
    csv_data = parse_csv(csv_path)
    
    # 查找图像文件（去重）
    image_files = set()
    for pattern in image_patterns:
        for f in directory.glob(pattern):
            image_files.add(f.resolve())
    
    # 自然排序（按文件名中的数字）
    def extract_number(path: Path) -> int:
        name = path.stem
        numbers = re.findall(r'\d+', name)
        return int(numbers[-1]) if numbers else 0
    
    image_paths = sorted([str(f) for f in image_files], key=lambda x: extract_number(Path(x)))
    
    return {
        'csv_path': csv_path,
        'png_paths': image_paths,  # 保持键名兼容性
        'csv_data': csv_data
    }


def list_image_files(directory: Union[str, Path],
                     patterns: Optional[List[str]] = None) -> List[str]:
    """
    列出目录中的所有图像文件（不需要CSV）
    
    参数:
        directory: 目录路径
        patterns: 文件模式列表
    
    返回:
        图像文件路径列表（自然排序）
    """
    if patterns is None:
        patterns = ['*.png', '*.PNG', '*.tif', '*.TIF', '*.tiff', '*.TIFF']
    
    directory = Path(directory)
    
    if not directory.exists():
        return []
    
    # 收集文件（去重）
    image_files = set()
    for pattern in patterns:
        for f in directory.glob(pattern):
            image_files.add(f.resolve())
    
    # 自然排序
    def extract_number(path: Path) -> int:
        name = path.stem
        numbers = re.findall(r'\d+', name)
        return int(numbers[-1]) if numbers else 0
    
    return sorted([str(f) for f in image_files], key=lambda x: extract_number(Path(x)))


# ==================== 模型读写 ====================

def save_model(model: CompensationModel, 
               filepath: Union[str, Path],
               minimal: bool = True) -> str:
    """
    保存补偿模型到JSON文件
    
    参数:
        model: CompensationModel对象
        filepath: 保存路径
        minimal: 是否使用精简格式（仅逆向模型）
    
    返回:
        实际保存路径
    """
    filepath = Path(filepath)
    
    # 确保扩展名为 .json
    if filepath.suffix.lower() not in ['.json']:
        filepath = filepath.with_suffix('.json')
    
    # 确保目录存在
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # 精度控制
    def round_list(arr, decimals=6) -> List[float]:
        return [round(float(x), decimals) for x in np.array(arr)]
    
    if minimal:
        # 精简格式：仅保存补偿必需的逆向模型
        model_data = {
            'model_type': 'cubic_spline',
            'version': model.version,
            'knots': round_list(model.knots),
            'coefficients': round_list(model.coefficients),
            'k': model.k,
            'x_range': round_list(model.x_range, 4),
            'y_range': round_list(model.y_range, 4),
            'calibration_points': model.calibration_points
        }
    else:
        # 完整格式：包含所有信息
        model_data = {
            'model_type': 'cubic_spline',
            'version': model.version,
            'description': '深度图补偿三次样条模型（完整格式）',
            'inverse_model': {
                't': round_list(model.knots),
                'c': round_list(model.coefficients),
                'k': model.k
            },
            'actual_range': round_list(model.y_range, 4),
            'measured_range': round_list(model.x_range, 4),
            'calibration_data': {
                'num_points': model.calibration_points,
                'actual_values': round_list(model.actual_values, 4) if model.actual_values else [],
                'measured_values': round_list(model.measured_values, 4) if model.measured_values else []
            }
        }
        
        # 添加正向模型（如果有）
        if model.forward_knots is not None:
            model_data['forward_model'] = {
                't': round_list(model.forward_knots),
                'c': round_list(model.forward_coefficients),
                'k': model.k
            }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(model_data, f, indent=2, ensure_ascii=False)
    
    return str(filepath)


def load_model(filepath: Union[str, Path]) -> CompensationModel:
    """
    从JSON文件加载补偿模型
    
    支持多种格式：
    - 精简格式（v2.2）：knots, coefficients, k
    - 完整格式（v2.1/v2.2）：inverse_model 字典
    - 旧版格式
    
    参数:
        filepath: 模型文件路径
    
    返回:
        CompensationModel对象
    
    抛出:
        FileNotFoundError: 文件不存在
        ValueError: 格式无法识别
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"模型文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return _parse_model_data(data)


def _parse_model_data(data: Dict[str, Any]) -> CompensationModel:
    """
    解析模型数据字典
    
    参数:
        data: JSON加载的字典
    
    返回:
        CompensationModel对象
    """
    if 'knots' in data:
        # 精简格式或旧版格式
        return _parse_minimal_format(data)
    elif 'inverse_model' in data:
        # 完整格式
        return _parse_full_format(data)
    else:
        raise ValueError("无法识别的模型格式")


def _parse_minimal_format(data: Dict[str, Any]) -> CompensationModel:
    """解析精简格式模型"""
    knots = np.array(data['knots'])
    coefficients = np.array(data['coefficients'])
    k = data['k']
    
    # 获取范围信息
    if 'x_range' in data:
        x_range = tuple(data['x_range'])
        y_range = tuple(data['y_range'])
    else:
        # 从 knots 推断范围
        x_range = (knots[k], knots[-k-1])
        y_range = x_range  # 近似
    
    return CompensationModel(
        knots=knots,
        coefficients=coefficients,
        k=k,
        x_range=x_range,
        y_range=y_range,
        calibration_points=data.get('calibration_points', 0),
        version=data.get('version', '2.0')
    )


def _parse_full_format(data: Dict[str, Any]) -> CompensationModel:
    """解析完整格式模型"""
    inv = data['inverse_model']
    
    # 逆向模型
    knots = np.array(inv['t'])
    coefficients = np.array(inv['c'])
    k = inv['k']
    
    # 范围
    y_range = tuple(data['actual_range'])
    x_range = tuple(data['measured_range'])
    
    # 标定数据
    calib = data.get('calibration_data', {})
    actual_values = calib.get('actual_values', None)
    measured_values = calib.get('measured_values', None)
    num_points = calib.get('num_points', len(actual_values) if actual_values else 0)
    
    # 正向模型（可选）
    forward_knots = None
    forward_coefficients = None
    if 'forward_model' in data:
        fwd = data['forward_model']
        forward_knots = np.array(fwd['t'])
        forward_coefficients = np.array(fwd['c'])
    
    return CompensationModel(
        knots=knots,
        coefficients=coefficients,
        k=k,
        x_range=x_range,
        y_range=y_range,
        calibration_points=num_points,
        version=data.get('version', '2.1'),
        actual_values=actual_values,
        measured_values=measured_values,
        forward_knots=forward_knots,
        forward_coefficients=forward_coefficients
    )


# ==================== 结果保存 ====================

def save_linearity_report(result: Dict[str, Any], 
                          output_path: Union[str, Path],
                          has_compensation: bool = False) -> str:
    """
    保存线性度计算报告
    
    参数:
        result: 计算结果字典
        output_path: 输出路径
        has_compensation: 是否包含补偿后结果
    
    返回:
        实际保存路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("批量线性度计算报告\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"测试目录: {result.get('test_dir', 'N/A')}\n")
        f.write(f"图像数量: {result.get('num_images', 0)}\n")
        f.write(f"满量程: {result.get('full_scale', 41.0)} mm\n\n")
        
        before = result.get('before', {})
        f.write("【补偿前线性度】\n")
        f.write(f"  线性度: {before.get('linearity', 0):.4f}%\n")
        f.write(f"  最大偏差: {before.get('abs_max_deviation', 0):.6f} mm\n")
        f.write(f"  RMS误差: {before.get('rms_error', 0):.6f} mm\n")
        f.write(f"  R²: {before.get('r_squared', 0):.8f}\n\n")
        
        if has_compensation and 'after' in result:
            after = result['after']
            f.write("【补偿后线性度】\n")
            f.write(f"  线性度: {after.get('linearity', 0):.4f}%\n")
            f.write(f"  最大偏差: {after.get('abs_max_deviation', 0):.6f} mm\n")
            f.write(f"  改善效果: {result.get('improvement', 0):.2f}%\n\n")
    
    return str(output_path)
