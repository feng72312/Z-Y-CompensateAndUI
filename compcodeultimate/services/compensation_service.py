# -*- coding: utf-8 -*-
"""
补偿服务
提供图像补偿的完整流程
"""

import os
import numpy as np
from typing import List, Optional, Callable, Union
from pathlib import Path

from ..data.models import (
    CompensationModel,
    CompensationResult,
    ExtrapolateConfig,
    NormalizeConfig,
    BatchProcessResult,
    DepthConversionConfig
)
from ..data.io import read_depth_image, save_depth_image, load_model, list_image_files
from ..core.compensator import (
    compensate_image_pixels,
    calculate_normalization_offset,
    get_normalize_config
)


class CompensationService:
    """
    补偿服务
    
    提供单张图像补偿和批量补偿功能
    """
    
    def __init__(self,
                 model: Optional[CompensationModel] = None,
                 extrapolate_config: Optional[ExtrapolateConfig] = None,
                 normalize_config: Optional[NormalizeConfig] = None,
                 depth_config: Optional[DepthConversionConfig] = None):
        """
        初始化补偿服务
        
        参数:
            model: 补偿模型
            extrapolate_config: 外推配置
            normalize_config: 归一化配置
            depth_config: 深度转换配置
        """
        self._model = model
        self.extrapolate_config = extrapolate_config or ExtrapolateConfig()
        self.normalize_config = normalize_config or NormalizeConfig()
        self.depth_config = depth_config or DepthConversionConfig()
        
        self._normalize_offset: float = 0.0
        self._update_normalize_offset()
    
    def load_model(self, model_path: str) -> CompensationModel:
        """
        加载补偿模型
        
        参数:
            model_path: 模型文件路径
        
        返回:
            加载的模型
        """
        self._model = load_model(model_path)
        self._update_normalize_offset()
        return self._model
    
    def set_model(self, model: CompensationModel) -> None:
        """
        设置补偿模型
        
        参数:
            model: 补偿模型
        """
        self._model = model
        self._update_normalize_offset()
    
    def _update_normalize_offset(self) -> None:
        """更新归一化偏移量"""
        if self._model is not None and self.normalize_config.enabled:
            self._normalize_offset = get_normalize_config(self._model, self.normalize_config)
        else:
            self._normalize_offset = 0.0
    
    def set_normalize_config(self, config: NormalizeConfig) -> None:
        """设置归一化配置"""
        self.normalize_config = config
        self._update_normalize_offset()
    
    def set_extrapolate_config(self, config: ExtrapolateConfig) -> None:
        """设置外推配置"""
        self.extrapolate_config = config
    
    @property
    def model(self) -> Optional[CompensationModel]:
        """获取当前模型"""
        return self._model
    
    @property
    def model_loaded(self) -> bool:
        """模型是否已加载"""
        return self._model is not None
    
    @property
    def normalize_offset(self) -> float:
        """获取当前归一化偏移量"""
        return self._normalize_offset
    
    def compensate_image(self, 
                          image_path: str,
                          output_path: Optional[str] = None) -> CompensationResult:
        """
        补偿单张图像
        
        参数:
            image_path: 输入图像路径
            output_path: 输出图像路径（可选）
        
        返回:
            CompensationResult 对象
        
        抛出:
            ValueError: 模型未加载
        """
        if self._model is None:
            raise ValueError("模型未加载")
        
        # 读取图像
        depth_array = read_depth_image(image_path)
        
        # 执行补偿
        result = compensate_image_pixels(
            depth_array,
            self._model,
            invalid_value=self.depth_config.invalid_value,
            extrapolate_config=self.extrapolate_config,
            normalize_offset=self._normalize_offset,
            depth_offset=self.depth_config.offset,
            depth_scale_factor=self.depth_config.scale_factor
        )
        
        # 保存结果
        if output_path:
            save_depth_image(result.compensated_array, output_path)
        
        return result
    
    def compensate_array(self, depth_array: np.ndarray) -> CompensationResult:
        """
        补偿深度数组
        
        参数:
            depth_array: 深度图数组
        
        返回:
            CompensationResult 对象
        
        抛出:
            ValueError: 模型未加载
        """
        if self._model is None:
            raise ValueError("模型未加载")
        
        return compensate_image_pixels(
            depth_array,
            self._model,
            invalid_value=self.depth_config.invalid_value,
            extrapolate_config=self.extrapolate_config,
            normalize_offset=self._normalize_offset,
            depth_offset=self.depth_config.offset,
            depth_scale_factor=self.depth_config.scale_factor
        )
    
    def compensate_batch(self,
                          input_dir: str,
                          output_dir: str,
                          progress_callback: Optional[Callable[[int, int, str], None]] = None
                          ) -> BatchProcessResult:
        """
        批量补偿图像
        
        参数:
            input_dir: 输入目录
            output_dir: 输出目录
            progress_callback: 进度回调函数 (current, total, message)
        
        返回:
            BatchProcessResult 对象
        
        抛出:
            ValueError: 模型未加载
            FileNotFoundError: 输入目录不存在
        """
        if self._model is None:
            raise ValueError("模型未加载")
        
        # 获取图像文件列表
        image_files = list_image_files(input_dir)
        if not image_files:
            raise FileNotFoundError(f"未找到图像文件: {input_dir}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        total_count = len(image_files)
        results: List[CompensationResult] = []
        errors: List[tuple] = []
        total_pixels = 0
        compensated_pixels = 0
        
        for i, image_path in enumerate(image_files):
            filename = os.path.basename(image_path)
            
            if progress_callback:
                progress_callback(i + 1, total_count, f"处理: {filename}")
            
            try:
                output_path = os.path.join(output_dir, filename)
                result = self.compensate_image(image_path, output_path)
                
                results.append(result)
                total_pixels += result.total_pixels
                compensated_pixels += result.compensated_pixels
                
            except Exception as e:
                errors.append((filename, str(e)))
        
        avg_rate = (compensated_pixels / total_pixels * 100) if total_pixels > 0 else 0.0
        
        return BatchProcessResult(
            total_images=total_count,
            processed_images=len(results),
            failed_images=len(errors),
            total_pixels=total_pixels,
            compensated_pixels=compensated_pixels,
            avg_compensation_rate=avg_rate,
            results=results,
            errors=errors
        )
    
    def get_model_info(self) -> Optional[dict]:
        """
        获取模型信息
        
        返回:
            模型信息字典，如果模型未加载返回None
        """
        if self._model is None:
            return None
        
        return {
            'calibration_points': self._model.calibration_points,
            'input_range': self._model.x_range,
            'output_range': self._model.y_range,
            'version': self._model.version,
            'normalize_offset': self._normalize_offset
        }
