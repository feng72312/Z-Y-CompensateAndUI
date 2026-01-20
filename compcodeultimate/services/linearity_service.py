# -*- coding: utf-8 -*-
"""
线性度计算服务
提供批量线性度计算功能
"""

import os
import numpy as np
from typing import List, Optional, Callable, Dict, Any

from ..data.models import (
    CompensationModel,
    LinearityResult,
    CompensationEffectResult,
    FilterConfig,
    ROIConfig,
    DepthConversionConfig
)
from ..data.io import read_depth_image, get_image_files, load_model, save_linearity_report
from ..data.converters import gray_to_mm
from ..core.calibrator import calibrate_image, get_roi, get_valid_pixels
from ..core.compensator import apply_compensation
from ..core.linearity import calculate_linearity, calculate_compensation_effect


# 默认满量程
DEFAULT_FULL_SCALE = 41.0


class LinearityService:
    """
    线性度计算服务
    
    提供批量线性度计算和补偿效果评估
    """
    
    def __init__(self,
                 filter_config: Optional[FilterConfig] = None,
                 roi_config: Optional[ROIConfig] = None,
                 depth_config: Optional[DepthConversionConfig] = None,
                 full_scale: float = DEFAULT_FULL_SCALE):
        """
        初始化线性度计算服务
        
        参数:
            filter_config: 滤波配置
            roi_config: ROI配置
            depth_config: 深度转换配置
            full_scale: 满量程 (mm)
        """
        self.filter_config = filter_config or FilterConfig()
        self.roi_config = roi_config or ROIConfig()
        self.depth_config = depth_config or DepthConversionConfig()
        self.full_scale = full_scale
        
        self._model: Optional[CompensationModel] = None
    
    def load_model(self, model_path: str) -> CompensationModel:
        """加载补偿模型"""
        self._model = load_model(model_path)
        return self._model
    
    def set_model(self, model: CompensationModel) -> None:
        """设置补偿模型"""
        self._model = model
    
    def calculate_batch_linearity(self,
                                   test_dir: str,
                                   output_path: Optional[str] = None,
                                   progress_callback: Optional[Callable[[int, int, str], None]] = None
                                   ) -> Dict[str, Any]:
        """
        批量计算线性度
        
        参数:
            test_dir: 测试数据目录
            output_path: 结果输出路径（可选）
            progress_callback: 进度回调函数
        
        返回:
            {
                'before': LinearityResult,
                'after': LinearityResult (如果有模型),
                'improvement': float,
                'num_images': int,
                'image_results': List[dict],
                'actual_abs': List[float],
                'measured_abs': List[float],
                ...
            }
        """
        # 获取测试文件
        test_files = get_image_files(test_dir)
        if not test_files:
            raise FileNotFoundError(f"未找到测试文件: {test_dir}")
        
        png_paths = test_files['png_paths']
        csv_data = test_files['csv_data']
        total_count = len(png_paths)
        
        if progress_callback:
            progress_callback(0, total_count, f"开始处理 {total_count} 张图像")
        
        actual_abs = []
        measured_abs = []
        image_results = []
        
        # 处理每张图像
        for i, (png_path, csv_row) in enumerate(zip(png_paths, csv_data)):
            filename = os.path.basename(png_path)
            
            if progress_callback:
                progress_callback(i + 1, total_count, f"处理: {filename}")
            
            result = self._process_single_image(png_path)
            
            if result is None:
                continue
            
            actual_mm = csv_row['实际累计位移(mm)']
            actual_abs.append(actual_mm)
            measured_abs.append(result)
            
            image_results.append({
                'filename': filename,
                'actual': actual_mm,
                'measured': result
            })
        
        if len(actual_abs) < 2:
            raise ValueError("有效图像数量不足")
        
        # 转换为numpy数组
        actual_abs = np.array(actual_abs)
        measured_abs = np.array(measured_abs)
        
        # 零点归一化
        actual_rel = actual_abs - actual_abs[0]
        measured_rel = measured_abs - measured_abs[0]
        
        # 计算补偿前线性度
        linearity_before = calculate_linearity(actual_rel, measured_rel, self.full_scale)
        
        result = {
            'test_dir': test_dir,
            'num_images': len(actual_abs),
            'full_scale': self.full_scale,
            'roi_config': self.roi_config,
            'before': linearity_before.to_dict(),
            'image_results': image_results,
            'actual_abs': actual_abs.tolist(),
            'measured_abs': measured_abs.tolist(),
            'actual_rel': actual_rel.tolist(),
            'measured_rel': measured_rel.tolist()
        }
        
        # 如果有模型，计算补偿后线性度
        if self._model is not None:
            compensated_abs = apply_compensation(measured_abs, self._model)
            compensated_rel = compensated_abs - compensated_abs[0]
            
            linearity_after = calculate_linearity(actual_rel, compensated_rel, self.full_scale)
            
            improvement = 0.0
            if linearity_before.linearity != 0:
                improvement = ((linearity_before.linearity - linearity_after.linearity) 
                               / linearity_before.linearity * 100.0)
            
            result['after'] = linearity_after.to_dict()
            result['improvement'] = improvement
            result['compensated_abs'] = compensated_abs.tolist()
            result['compensated_rel'] = compensated_rel.tolist()
            
            # 更新图像结果
            for i, r in enumerate(image_results):
                r['compensated'] = float(compensated_abs[i])
        
        # 保存结果
        if output_path:
            save_linearity_report(result, output_path, self._model is not None)
        
        return result
    
    def _process_single_image(self, image_path: str) -> Optional[float]:
        """处理单张图像，返回测量值(mm)"""
        try:
            depth_array = read_depth_image(image_path)
            
            roi = get_roi(
                depth_array,
                x=self.roi_config.x,
                y=self.roi_config.y,
                width=self.roi_config.width,
                height=self.roi_config.height
            )
            
            result = calibrate_image(
                roi,
                apply_filter=self.filter_config.enabled,
                filter_config=self.filter_config,
                invalid_value=self.depth_config.invalid_value
            )
            
            if not result.success:
                return None
            
            valid_pixels, _ = get_valid_pixels(
                result.calibrated_roi,
                self.depth_config.invalid_value
            )
            
            if valid_pixels.size == 0:
                return None
            
            avg_gray = float(valid_pixels.mean())
            return gray_to_mm(
                avg_gray,
                self.depth_config.offset,
                self.depth_config.scale_factor
            )
            
        except Exception:
            return None
