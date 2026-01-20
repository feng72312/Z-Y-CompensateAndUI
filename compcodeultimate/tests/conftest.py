# -*- coding: utf-8 -*-
"""
pytest 配置和共享 fixtures
"""

import pytest
import numpy as np
import json
import tempfile
import os
from pathlib import Path


@pytest.fixture
def sample_depth_array():
    """创建示例深度数组"""
    # 创建一个100x100的深度图，中心值约32768（对应0mm）
    array = np.full((100, 100), 32768, dtype=np.uint16)
    # 添加一些变化
    array[40:60, 40:60] = 33000  # 中心区域略高
    return array


@pytest.fixture
def sample_depth_array_with_invalid():
    """创建带无效值的深度数组"""
    array = np.full((100, 100), 32768, dtype=np.uint16)
    array[0:10, :] = 65535  # 顶部无效
    array[90:100, :] = 65535  # 底部无效
    return array


@pytest.fixture
def sample_calibration_data():
    """创建示例标定数据"""
    # 模拟标定数据：实际值和测量值
    actual_values = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0]
    # 测量值有轻微误差
    measured_values = [0.05, 5.02, 10.08, 15.01, 19.98, 25.05, 30.02, 34.95, 40.03]
    return actual_values, measured_values


@pytest.fixture
def sample_model_data():
    """创建示例模型数据（JSON格式）"""
    return {
        'model_type': 'cubic_spline',
        'version': '2.2',
        'knots': [0.0, 0.0, 0.0, 0.0, 10.0, 20.0, 30.0, 40.0, 40.0, 40.0, 40.0],
        'coefficients': [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 0.0, 0.0],
        'k': 3,
        'x_range': [0.0, 40.0],
        'y_range': [0.0, 40.0],
        'calibration_points': 9
    }


@pytest.fixture
def temp_model_file(sample_model_data, tmp_path):
    """创建临时模型文件"""
    model_path = tmp_path / 'test_model.json'
    with open(model_path, 'w', encoding='utf-8') as f:
        json.dump(sample_model_data, f)
    return str(model_path)


@pytest.fixture
def temp_depth_image(sample_depth_array, tmp_path):
    """创建临时深度图文件"""
    from PIL import Image
    image_path = tmp_path / 'test_depth.png'
    Image.fromarray(sample_depth_array).save(str(image_path))
    return str(image_path)


@pytest.fixture
def temp_output_dir(tmp_path):
    """创建临时输出目录"""
    output_dir = tmp_path / 'output'
    output_dir.mkdir()
    return str(output_dir)


# 创建测试用的模型 fixture
@pytest.fixture
def sample_compensation_model(sample_calibration_data):
    """创建示例补偿模型对象"""
    from compcodeultimate.core.spline_model import build_compensation_model
    actual_values, measured_values = sample_calibration_data
    return build_compensation_model(actual_values, measured_values)
