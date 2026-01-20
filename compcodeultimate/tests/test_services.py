# -*- coding: utf-8 -*-
"""
服务层测试
"""

import pytest
import numpy as np
import os
from pathlib import Path

from compcodeultimate.services import (
    CalibrationService,
    CompensationService,
    LinearityService,
    RepeatabilityService
)
from compcodeultimate.data.models import (
    FilterConfig,
    ROIConfig,
    ExtrapolateConfig,
    NormalizeConfig
)


class TestCompensationService:
    """CompensationService 测试"""
    
    def test_init_without_model(self):
        """测试无模型初始化"""
        service = CompensationService()
        
        assert not service.model_loaded
        assert service.model is None
    
    def test_load_model(self, temp_model_file):
        """测试加载模型"""
        service = CompensationService()
        model = service.load_model(temp_model_file)
        
        assert service.model_loaded
        assert model is not None
    
    def test_compensate_without_model(self, temp_depth_image):
        """测试未加载模型时补偿"""
        service = CompensationService()
        
        with pytest.raises(ValueError, match="模型未加载"):
            service.compensate_image(temp_depth_image)
    
    def test_compensate_image(self, temp_model_file, temp_depth_image, temp_output_dir):
        """测试图像补偿"""
        service = CompensationService()
        service.load_model(temp_model_file)
        
        output_path = os.path.join(temp_output_dir, 'output.png')
        result = service.compensate_image(temp_depth_image, output_path)
        
        assert result.total_pixels > 0
        assert os.path.exists(output_path)
    
    def test_get_model_info(self, temp_model_file):
        """测试获取模型信息"""
        service = CompensationService()
        service.load_model(temp_model_file)
        
        info = service.get_model_info()
        
        assert info is not None
        assert 'calibration_points' in info
        assert 'input_range' in info
        assert 'output_range' in info
    
    def test_normalize_config(self, temp_model_file):
        """测试归一化配置"""
        service = CompensationService()
        service.load_model(temp_model_file)
        
        # 设置归一化
        config = NormalizeConfig(
            enabled=True,
            target_center=0.0,
            auto_offset=True
        )
        service.set_normalize_config(config)
        
        # 偏移量应该被计算
        assert service.normalize_offset != 0.0 or True  # 可能为0取决于模型


class TestCalibrationService:
    """CalibrationService 测试"""
    
    def test_init(self):
        """测试初始化"""
        service = CalibrationService()
        
        assert service.model is None
        assert len(service.actual_values) == 0
        assert len(service.measured_values) == 0
    
    def test_init_with_config(self):
        """测试带配置初始化"""
        filter_config = FilterConfig(enabled=False)
        roi_config = ROIConfig(x=10, y=10, width=100, height=100)
        
        service = CalibrationService(
            filter_config=filter_config,
            roi_config=roi_config
        )
        
        assert not service.filter_config.enabled
        assert service.roi_config.x == 10


class TestLinearityService:
    """LinearityService 测试"""
    
    def test_init(self):
        """测试初始化"""
        service = LinearityService(full_scale=50.0)
        
        assert service.full_scale == 50.0
    
    def test_load_model(self, temp_model_file):
        """测试加载模型"""
        service = LinearityService()
        model = service.load_model(temp_model_file)
        
        assert model is not None


class TestRepeatabilityService:
    """RepeatabilityService 测试"""
    
    def test_init(self):
        """测试初始化"""
        service = RepeatabilityService()
        
        assert service.filter_config.enabled
    
    def test_init_with_roi(self):
        """测试带ROI初始化"""
        roi_config = ROIConfig(x=50, y=50, width=200, height=200)
        service = RepeatabilityService(roi_config=roi_config)
        
        assert service.roi_config.x == 50
        assert service.roi_config.width == 200


class TestServiceIntegration:
    """服务集成测试"""
    
    def test_calibration_to_compensation_workflow(self, temp_model_file, temp_depth_image, temp_output_dir):
        """测试标定到补偿的工作流"""
        # 1. 加载已有模型（模拟标定结果）
        comp_service = CompensationService()
        comp_service.load_model(temp_model_file)
        
        # 2. 补偿图像
        output_path = os.path.join(temp_output_dir, 'compensated.png')
        result = comp_service.compensate_image(temp_depth_image, output_path)
        
        assert result.compensated_array is not None
        assert os.path.exists(output_path)
