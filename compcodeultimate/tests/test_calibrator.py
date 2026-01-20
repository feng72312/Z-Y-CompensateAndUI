# -*- coding: utf-8 -*-
"""
校准模块测试
"""

import pytest
import numpy as np

from compcodeultimate.core.calibrator import (
    filter_outliers,
    apply_median_filter,
    apply_gaussian_filter,
    apply_filters,
    fit_plane,
    calibrate_plane,
    calculate_flatness,
    calibrate_image,
    get_roi,
    get_valid_pixels
)
from compcodeultimate.data.models import FilterConfig


class TestFilterFunctions:
    """滤波函数测试"""
    
    def test_filter_outliers(self):
        """测试异常值过滤"""
        # 创建带异常值的数组
        array = np.array([[100, 100, 100],
                          [100, 500, 100],  # 500是异常值
                          [100, 100, 100]], dtype=np.uint16)
        
        result = filter_outliers(array, std_factor=2.0, invalid_value=65535)
        
        # 异常值应该被标记为无效
        assert result[1, 1] == 65535
        # 正常值应该保持
        assert result[0, 0] == 100
    
    def test_median_filter_preserves_invalid(self):
        """测试中值滤波保留无效值"""
        array = np.array([[100, 100, 100],
                          [100, 65535, 100],  # 中心是无效值
                          [100, 100, 100]], dtype=np.uint16)
        
        result = apply_median_filter(array, size=3, invalid_value=65535)
        
        # 无效值应该保持
        assert result[1, 1] == 65535
    
    def test_gaussian_filter_preserves_invalid(self):
        """测试高斯滤波保留无效值"""
        array = np.array([[100, 100, 100],
                          [100, 65535, 100],
                          [100, 100, 100]], dtype=np.uint16)
        
        result = apply_gaussian_filter(array, sigma=1.0, invalid_value=65535)
        
        assert result[1, 1] == 65535
    
    def test_apply_filters_combined(self):
        """测试组合滤波"""
        array = np.full((10, 10), 100, dtype=np.uint16)
        config = FilterConfig(
            enabled=True,
            outlier_std_factor=3.0,
            median_filter_size=3,
            gaussian_filter_sigma=1.0
        )
        
        result = apply_filters(array, config)
        
        # 均匀数组滤波后应该基本不变
        assert result.shape == array.shape
        assert np.all(result != 65535)


class TestPlaneFitting:
    """平面拟合测试"""
    
    def test_fit_horizontal_plane(self):
        """测试水平平面拟合"""
        # 创建水平平面（所有值相同）
        array = np.full((50, 50), 1000, dtype=np.uint16)
        
        a, b, c = fit_plane(array, invalid_value=65535)
        
        # 水平面的斜率应该接近0
        assert abs(a) < 0.1
        assert abs(b) < 0.1
        assert abs(c - 1000) < 1
    
    def test_fit_tilted_plane(self):
        """测试倾斜平面拟合"""
        # 创建倾斜平面：z = x + y + 1000
        x = np.arange(50)
        y = np.arange(50)
        xx, yy = np.meshgrid(x, y)
        array = (xx + yy + 1000).astype(np.uint16)
        
        a, b, c = fit_plane(array, invalid_value=65535)
        
        # 斜率应该接近1
        assert abs(a - 1) < 0.1
        assert abs(b - 1) < 0.1
    
    def test_fit_plane_insufficient_pixels(self):
        """测试像素不足时抛出异常"""
        # 几乎全是无效值
        array = np.full((10, 10), 65535, dtype=np.uint16)
        array[0, 0] = 100
        
        with pytest.raises(ValueError, match="有效像素不足"):
            fit_plane(array, invalid_value=65535, min_valid_pixels=100)


class TestCalibration:
    """校准测试"""
    
    def test_calibrate_plane(self):
        """测试平面校准"""
        # 创建倾斜平面
        x = np.arange(20)
        y = np.arange(20)
        xx, yy = np.meshgrid(x, y)
        array = (xx + yy + 1000).astype(np.uint16)
        
        plane_params = fit_plane(array)
        calibrated = calibrate_plane(array, plane_params)
        
        # 校准后应该接近常数（平面常数项）
        valid_mask = calibrated != 65535
        valid_values = calibrated[valid_mask]
        assert np.std(valid_values) < 1.0
    
    def test_calculate_flatness(self):
        """测试平面度计算"""
        # 创建有偏差的平面
        array = np.array([[1000, 1001, 1002],
                          [1001, 1005, 1001],  # 中心有凸起
                          [1002, 1001, 1000]], dtype=np.uint16)
        
        plane_params = (0, 0, 1001)  # 水平面
        flatness = calculate_flatness(array, plane_params)
        
        assert flatness > 0
    
    def test_calibrate_image_success(self, sample_depth_array):
        """测试完整校准流程成功"""
        result = calibrate_image(
            sample_depth_array,
            apply_filter=True,
            filter_config=FilterConfig(enabled=True)
        )
        
        assert result.success
        assert result.calibrated_roi is not None
        assert result.plane_params is not None
    
    def test_calibrate_image_failure(self):
        """测试校准失败（无效像素太多）"""
        # 全是无效值
        array = np.full((100, 100), 65535, dtype=np.uint16)
        
        result = calibrate_image(array)
        
        assert not result.success
        assert "有效像素不足" in result.reason


class TestROIFunctions:
    """ROI函数测试"""
    
    def test_get_roi_full_image(self):
        """测试获取整个图像"""
        array = np.zeros((100, 100), dtype=np.uint16)
        roi = get_roi(array, x=0, y=0, width=-1, height=-1)
        
        assert roi.shape == array.shape
    
    def test_get_roi_partial(self):
        """测试获取部分区域"""
        array = np.zeros((100, 100), dtype=np.uint16)
        roi = get_roi(array, x=10, y=20, width=30, height=40)
        
        assert roi.shape == (40, 30)
    
    def test_get_valid_pixels(self):
        """测试获取有效像素"""
        array = np.array([[100, 65535],
                          [200, 300]], dtype=np.uint16)
        
        valid_pixels, valid_mask = get_valid_pixels(array, invalid_value=65535)
        
        assert len(valid_pixels) == 3
        assert not valid_mask[0, 1]
        assert valid_mask[0, 0]
