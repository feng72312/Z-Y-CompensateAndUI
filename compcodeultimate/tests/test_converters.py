# -*- coding: utf-8 -*-
"""
单位转换模块测试
"""

import pytest
import numpy as np

from compcodeultimate.data.converters import (
    gray_to_mm,
    mm_to_gray,
    gray_to_mm_vectorized,
    mm_to_gray_vectorized,
    convert_depth_image_to_mm,
    convert_mm_image_to_depth,
    create_converter
)


class TestGrayToMm:
    """gray_to_mm 测试"""
    
    def test_zero_point(self):
        """测试零点转换"""
        # 32768 应该对应 0mm
        result = gray_to_mm(32768, offset=32768, scale_factor=1.6)
        assert result == pytest.approx(0.0, abs=1e-6)
    
    def test_positive_depth(self):
        """测试正深度"""
        # (33768 - 32768) * 1.6 / 1000 = 1.6mm
        result = gray_to_mm(33768, offset=32768, scale_factor=1.6)
        assert result == pytest.approx(1.6, abs=1e-6)
    
    def test_negative_depth(self):
        """测试负深度"""
        # (31768 - 32768) * 1.6 / 1000 = -1.6mm
        result = gray_to_mm(31768, offset=32768, scale_factor=1.6)
        assert result == pytest.approx(-1.6, abs=1e-6)
    
    def test_invalid_value(self):
        """测试无效值"""
        result = gray_to_mm(65535, invalid_value=65535)
        assert result is None
    
    def test_array_input(self):
        """测试数组输入"""
        gray_array = np.array([32768, 33768, 31768], dtype=np.uint16)
        result = gray_to_mm(gray_array, offset=32768, scale_factor=1.6)
        expected = np.array([0.0, 1.6, -1.6])
        np.testing.assert_array_almost_equal(result, expected, decimal=6)


class TestMmToGray:
    """mm_to_gray 测试"""
    
    def test_zero_mm(self):
        """测试0mm转换"""
        result = mm_to_gray(0.0, offset=32768, scale_factor=1.6)
        assert result == 32768
    
    def test_positive_mm(self):
        """测试正毫米值"""
        result = mm_to_gray(1.6, offset=32768, scale_factor=1.6)
        assert result == 33768
    
    def test_clipping(self):
        """测试边界裁剪"""
        # 超大值应该被裁剪到65535
        result = mm_to_gray(100.0, offset=32768, scale_factor=1.6)
        assert result <= 65535
    
    def test_array_input(self):
        """测试数组输入"""
        mm_array = np.array([0.0, 1.6, -1.6])
        result = mm_to_gray(mm_array, offset=32768, scale_factor=1.6)
        expected = np.array([32768, 33768, 31768], dtype=np.uint16)
        np.testing.assert_array_equal(result, expected)


class TestVectorizedFunctions:
    """向量化函数测试"""
    
    def test_vectorized_roundtrip(self):
        """测试向量化往返转换"""
        original = np.array([30000, 32768, 35000], dtype=np.uint16)
        mm = gray_to_mm_vectorized(original, 32768, 1.6)
        back = mm_to_gray_vectorized(mm, 32768, 1.6)
        np.testing.assert_array_equal(original, back)
    
    def test_large_array_performance(self):
        """测试大数组性能"""
        # 创建1000x1000数组
        large_array = np.random.randint(20000, 45000, size=(1000, 1000), dtype=np.uint16)
        
        # 应该能快速完成
        mm_result = gray_to_mm_vectorized(large_array, 32768, 1.6)
        assert mm_result.shape == large_array.shape


class TestImageConversion:
    """图像转换测试"""
    
    def test_image_to_mm_with_invalid(self, sample_depth_array_with_invalid):
        """测试带无效值的图像转换"""
        mm_image = convert_depth_image_to_mm(
            sample_depth_array_with_invalid,
            invalid_value=65535,
            preserve_invalid=True
        )
        
        # 无效区域应该是NaN
        assert np.isnan(mm_image[0, 0])
        # 有效区域应该有值
        assert not np.isnan(mm_image[50, 50])
    
    def test_mm_image_to_depth(self):
        """测试毫米图转深度图"""
        mm_image = np.array([[0.0, 1.0], [np.nan, 2.0]])
        depth_image = convert_mm_image_to_depth(mm_image, invalid_value=65535)
        
        assert depth_image[0, 0] != 65535  # 有效值
        assert depth_image[1, 0] == 65535  # NaN转为无效


class TestCreateConverter:
    """转换器工厂测试"""
    
    def test_create_converter(self):
        """测试创建转换器"""
        to_mm, to_gray = create_converter(offset=32768, scale_factor=1.6)
        
        # 测试转换
        mm = to_mm(33768)
        assert mm == pytest.approx(1.6, abs=1e-6)
        
        gray = to_gray(1.6)
        assert gray == 33768
