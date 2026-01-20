# -*- coding: utf-8 -*-
"""
标定服务
提供完整的标定流程编排
"""

import os
import numpy as np
from typing import List, Optional, Callable, Dict, Any

from ..data.models import (
    CompensationModel,
    CalibrationResult,
    FilterConfig,
    ROIConfig,
    DepthConversionConfig
)
from ..data.io import read_depth_image, get_image_files, save_model
from ..data.converters import gray_to_mm
from ..core.calibrator import calibrate_image, get_roi, get_valid_pixels
from ..core.spline_model import build_compensation_model


class CalibrationService:
    """
    标定服务
    
    负责从标定数据建立补偿模型的完整流程
    """
    
    def __init__(self,
                 filter_config: Optional[FilterConfig] = None,
                 roi_config: Optional[ROIConfig] = None,
                 depth_config: Optional[DepthConversionConfig] = None):
        """
        初始化标定服务
        
        参数:
            filter_config: 滤波配置
            roi_config: ROI配置
            depth_config: 深度转换配置
        """
        self.filter_config = filter_config or FilterConfig()
        self.roi_config = roi_config or ROIConfig()
        self.depth_config = depth_config or DepthConversionConfig()
        
        # 处理结果
        self._actual_values: List[float] = []
        self._measured_values: List[float] = []
        self._model: Optional[CompensationModel] = None
    
    def process_calibration_data(self,
                                  calib_dir: str,
                                  progress_callback: Optional[Callable[[int, int, str], None]] = None
                                  ) -> Dict[str, Any]:
        """
        处理标定数据，建立补偿模型
        
        参数:
            calib_dir: 标定数据目录
            progress_callback: 进度回调函数 (current, total, message)
        
        返回:
            {
                'model': CompensationModel,
                'actual_values': List[float],
                'measured_values': List[float],
                'skipped_count': int,
                'total_count': int
            }
        
        抛出:
            FileNotFoundError: 目录不存在或无标定文件
            ValueError: 数据不足
        """
        # 获取标定文件
        calib_files = get_image_files(calib_dir)
        if not calib_files:
            raise FileNotFoundError(f"未找到标定文件: {calib_dir}")
        
        png_paths = calib_files['png_paths']
        csv_data = calib_files['csv_data']
        total_count = len(png_paths)
        
        if progress_callback:
            progress_callback(0, total_count, f"开始处理 {total_count} 张标定图像")
        
        actual_values = []
        measured_values = []
        skipped_count = 0
        
        # 处理每张标定图像
        for i, (png_path, csv_row) in enumerate(zip(png_paths, csv_data)):
            if progress_callback:
                filename = os.path.basename(png_path)
                progress_callback(i + 1, total_count, f"处理: {filename}")
            
            result = self._process_single_image(png_path)
            
            if result is None:
                skipped_count += 1
                continue
            
            actual_values.append(csv_row['实际累计位移(mm)'])
            measured_values.append(result)
        
        if len(actual_values) < 4:
            raise ValueError(f"有效图像不足: {len(actual_values)} < 4")
        
        # 建立补偿模型
        model = build_compensation_model(actual_values, measured_values)
        
        # 保存结果
        self._actual_values = actual_values
        self._measured_values = measured_values
        self._model = model
        
        return {
            'model': model,
            'actual_values': actual_values,
            'measured_values': measured_values,
            'skipped_count': skipped_count,
            'total_count': total_count
        }
    
    def _process_single_image(self, image_path: str) -> Optional[float]:
        """
        处理单张标定图像
        
        返回:
            测量值(mm)，如果处理失败返回None
        """
        try:
            depth_array = read_depth_image(image_path)
            
            # 提取ROI
            roi = get_roi(
                depth_array,
                x=self.roi_config.x,
                y=self.roi_config.y,
                width=self.roi_config.width,
                height=self.roi_config.height
            )
            
            # 平面校准
            result = calibrate_image(
                roi,
                apply_filter=self.filter_config.enabled,
                filter_config=self.filter_config,
                invalid_value=self.depth_config.invalid_value
            )
            
            if not result.success:
                return None
            
            # 计算ROI平均深度
            valid_pixels, _ = get_valid_pixels(
                result.calibrated_roi,
                self.depth_config.invalid_value
            )
            
            if valid_pixels.size == 0:
                return None
            
            avg_gray = float(valid_pixels.mean())
            avg_mm = gray_to_mm(
                avg_gray,
                self.depth_config.offset,
                self.depth_config.scale_factor
            )
            
            return avg_mm
            
        except Exception:
            return None
    
    def save_model(self, output_path: str, minimal: bool = True) -> str:
        """
        保存补偿模型
        
        参数:
            output_path: 输出路径
            minimal: 是否使用精简格式
        
        返回:
            实际保存路径
        
        抛出:
            ValueError: 模型未建立
        """
        if self._model is None:
            raise ValueError("模型未建立，请先调用 process_calibration_data")
        
        return save_model(self._model, output_path, minimal)
    
    @property
    def model(self) -> Optional[CompensationModel]:
        """获取已建立的模型"""
        return self._model
    
    @property
    def actual_values(self) -> List[float]:
        """获取实际值列表"""
        return self._actual_values.copy()
    
    @property
    def measured_values(self) -> List[float]:
        """获取测量值列表"""
        return self._measured_values.copy()
