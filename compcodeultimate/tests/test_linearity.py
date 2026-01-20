# -*- coding: utf-8 -*-
"""
线性度计算模块测试
"""

import pytest
import numpy as np

from compcodeultimate.core.linearity import (
    calculate_linearity,
    calculate_compensation_effect,
    normalize_to_relative
)


class TestCalculateLinearity:
    """calculate_linearity 测试"""
    
    def test_perfect_linearity(self):
        """测试完美线性度"""
        # 完美线性关系
        actual = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        measured = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        
        result = calculate_linearity(actual, measured, full_scale=40.0)
        
        # 完美线性应该接近0%
        assert result.linearity < 0.01
        assert result.r_squared > 0.9999
    
    def test_with_deviation(self):
        """测试有偏差的线性度"""
        actual = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        measured = np.array([0.0, 10.5, 19.5, 30.2, 39.8])  # 有小偏差
        
        result = calculate_linearity(actual, measured, full_scale=40.0)
        
        # 应该有一定线性度误差
        assert result.linearity > 0
        assert result.abs_max_deviation > 0
    
    def test_linearity_metrics(self):
        """测试线性度指标完整性"""
        actual = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        measured = np.array([0.1, 10.1, 20.1, 30.1, 40.1])
        
        result = calculate_linearity(actual, measured, full_scale=40.0)
        
        # 检查所有指标
        assert hasattr(result, 'linearity')
        assert hasattr(result, 'max_deviation')
        assert hasattr(result, 'min_deviation')
        assert hasattr(result, 'abs_max_deviation')
        assert hasattr(result, 'rms_error')
        assert hasattr(result, 'mae')
        assert hasattr(result, 'r_squared')
        assert hasattr(result, 'slope')
        assert hasattr(result, 'intercept')
    
    def test_insufficient_data(self):
        """测试数据不足"""
        actual = np.array([0.0])
        measured = np.array([0.0])
        
        with pytest.raises(ValueError, match="数据点不足"):
            calculate_linearity(actual, measured)
    
    def test_mismatched_length(self):
        """测试数据长度不匹配"""
        actual = np.array([0.0, 10.0, 20.0])
        measured = np.array([0.0, 10.0])
        
        with pytest.raises(ValueError, match="数据长度不匹配"):
            calculate_linearity(actual, measured)


class TestCompensationEffect:
    """calculate_compensation_effect 测试"""
    
    def test_improvement_calculation(self):
        """测试改善计算"""
        actual = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        measured = np.array([0.0, 10.5, 19.5, 30.5, 39.5])  # 补偿前有偏差
        compensated = np.array([0.0, 10.1, 20.1, 30.1, 40.1])  # 补偿后更好
        
        result = calculate_compensation_effect(actual, measured, compensated, full_scale=40.0)
        
        # 补偿后应该更好
        assert result.after.linearity < result.before.linearity
        assert result.improvement > 0
    
    def test_negative_improvement(self):
        """测试负改善（补偿后变差）"""
        actual = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        measured = np.array([0.0, 10.1, 20.1, 30.1, 40.1])  # 本来很好
        compensated = np.array([0.0, 10.5, 19.5, 30.5, 39.5])  # 补偿后变差
        
        result = calculate_compensation_effect(actual, measured, compensated, full_scale=40.0)
        
        # 改善为负
        assert result.improvement < 0


class TestNormalizeToRelative:
    """normalize_to_relative 测试"""
    
    def test_basic_normalization(self):
        """测试基本归一化"""
        values = np.array([10.0, 15.0, 20.0, 25.0])
        result = normalize_to_relative(values)
        
        # 第一个值应该是0
        assert result[0] == 0.0
        # 相对差应该保持
        assert result[1] == 5.0
        assert result[2] == 10.0
    
    def test_negative_start(self):
        """测试负起始值"""
        values = np.array([-5.0, 0.0, 5.0, 10.0])
        result = normalize_to_relative(values)
        
        assert result[0] == 0.0
        assert result[1] == 5.0
