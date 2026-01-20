# -*- coding: utf-8 -*-
"""
补偿模块测试
"""

import pytest
import numpy as np

from compcodeultimate.core.compensator import (
    apply_compensation,
    compensate_image_pixels,
    calculate_normalization_offset
)
from compcodeultimate.core.spline_model import build_compensation_model
from compcodeultimate.data.models import ExtrapolateConfig


class TestApplyCompensation:
    """apply_compensation 测试"""
    
    def test_compensation_in_range(self, sample_compensation_model):
        """测试范围内补偿"""
        # 测量值20mm应该返回接近20的实际值
        result = apply_compensation(20.0, sample_compensation_model)
        assert 15 < result < 25
    
    def test_compensation_array(self, sample_compensation_model):
        """测试数组补偿"""
        measured = np.array([5.0, 10.0, 15.0, 20.0])
        result = apply_compensation(measured, sample_compensation_model)
        
        assert len(result) == 4
        assert np.all(result > 0)
    
    def test_compensation_with_extrapolation(self, sample_compensation_model):
        """测试带外推的补偿"""
        config = ExtrapolateConfig(
            enabled=True,
            max_low=5.0,
            max_high=5.0
        )
        
        # 超出范围的值
        result = apply_compensation(-2.0, sample_compensation_model, config)
        
        # 应该返回有效值（外推结果）
        assert result is not None
    
    def test_scalar_returns_float_without_extrapolation(self, sample_compensation_model):
        """测试标量输入在不启用外推时返回float"""
        result = apply_compensation(5.0, sample_compensation_model, extrapolate_config=None)
        assert isinstance(result, float), f"期望返回float，实际返回{type(result)}"
        assert not isinstance(result, np.ndarray), "标量输入不应返回numpy数组"
    
    def test_array_returns_ndarray_without_extrapolation(self, sample_compensation_model):
        """测试数组输入在不启用外推时返回np.ndarray"""
        result = apply_compensation(np.array([5.0, 10.0]), sample_compensation_model, extrapolate_config=None)
        assert isinstance(result, np.ndarray), f"期望返回np.ndarray，实际返回{type(result)}"
        assert result.shape == (2,), "数组形状应该保持"
    
    def test_scalar_returns_float_with_disabled_extrapolation(self, sample_compensation_model):
        """测试标量输入在显式禁用外推时返回float"""
        config = ExtrapolateConfig(enabled=False)
        result = apply_compensation(5.0, sample_compensation_model, extrapolate_config=config)
        assert isinstance(result, float), f"期望返回float，实际返回{type(result)}"


class TestCompensateImagePixels:
    """compensate_image_pixels 测试"""
    
    def test_compensate_image_basic(self, sample_depth_array, sample_compensation_model):
        """测试基本图像补偿"""
        result = compensate_image_pixels(
            sample_depth_array,
            sample_compensation_model,
            invalid_value=65535
        )
        
        assert result.compensated_array.shape == sample_depth_array.shape
        assert result.total_pixels == sample_depth_array.size
        assert result.valid_pixels > 0
    
    def test_compensate_preserves_invalid(self, sample_depth_array_with_invalid, sample_compensation_model):
        """测试补偿保留无效像素"""
        result = compensate_image_pixels(
            sample_depth_array_with_invalid,
            sample_compensation_model,
            invalid_value=65535
        )
        
        # 检查无效像素是否保持
        original_invalid = np.sum(sample_depth_array_with_invalid == 65535)
        result_invalid = np.sum(result.compensated_array == 65535)
        
        # 无效像素数量应该相同或更多（超范围像素也可能保持原值）
        assert result_invalid >= original_invalid
    
    def test_compensation_stats(self, sample_depth_array, sample_compensation_model):
        """测试补偿统计信息"""
        result = compensate_image_pixels(
            sample_depth_array,
            sample_compensation_model
        )
        
        stats = result.stats
        
        assert 'total_pixels' in stats
        assert 'valid_pixels' in stats
        assert 'compensation_rate' in stats
        assert stats['compensation_rate'] >= 0
        assert stats['compensation_rate'] <= 100


class TestNormalization:
    """归一化测试"""
    
    def test_calculate_normalization_offset(self, sample_compensation_model):
        """测试归一化偏移量计算"""
        # 目标中心为0
        offset = calculate_normalization_offset(sample_compensation_model, target_center=0.0)
        
        # 偏移量应该使输出范围居中于0
        y_min, y_max = sample_compensation_model.y_range
        center = (y_min + y_max) / 2
        expected_offset = 0.0 - center
        
        assert offset == pytest.approx(expected_offset, abs=0.01)
    
    def test_compensate_with_normalization(self, sample_depth_array, sample_compensation_model):
        """测试带归一化的补偿"""
        offset = calculate_normalization_offset(sample_compensation_model, target_center=0.0)
        
        result = compensate_image_pixels(
            sample_depth_array,
            sample_compensation_model,
            normalize_offset=offset
        )
        
        assert result.normalize_offset == offset


class TestSplineModel:
    """样条模型测试"""
    
    def test_build_model(self, sample_calibration_data):
        """测试模型构建"""
        actual_values, measured_values = sample_calibration_data
        model = build_compensation_model(actual_values, measured_values)
        
        assert model.calibration_points == len(actual_values)
        assert model.k == 3  # 三次样条
    
    def test_build_model_insufficient_points(self):
        """测试数据点不足"""
        actual = [0.0, 1.0, 2.0]  # 只有3个点，不够三次样条
        measured = [0.0, 1.0, 2.0]
        
        # 应该降级到二次样条
        model = build_compensation_model(actual, measured)
        assert model.k <= 2
    
    def test_build_model_invalid_data(self):
        """测试无效数据"""
        actual = [0.0, 0.0, 0.0, 0.0]  # 全相同
        measured = [0.0, 1.0, 2.0, 3.0]
        
        with pytest.raises(ValueError, match="重复"):
            build_compensation_model(actual, measured)
    
    def test_model_ranges(self, sample_compensation_model):
        """测试模型范围"""
        assert sample_compensation_model.x_range[0] < sample_compensation_model.x_range[1]
        assert sample_compensation_model.y_range[0] < sample_compensation_model.y_range[1]
