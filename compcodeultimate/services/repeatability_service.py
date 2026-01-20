# -*- coding: utf-8 -*-
"""
重复精度计算服务
提供Y-Z重复精度计算功能
"""

import os
import numpy as np
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime
from pathlib import Path

from ..data.models import (
    RepeatabilityResult,
    FilterConfig,
    ROIConfig,
    DepthConversionConfig
)
from ..data.io import read_depth_image, list_image_files
from ..data.converters import gray_to_mm_vectorized
from ..core.calibrator import calibrate_image, get_roi, get_valid_pixels


class RepeatabilityService:
    """
    重复精度计算服务
    
    提供Y-Z方向重复精度计算
    """
    
    def __init__(self,
                 filter_config: Optional[FilterConfig] = None,
                 roi_config: Optional[ROIConfig] = None,
                 depth_config: Optional[DepthConversionConfig] = None):
        """
        初始化重复精度计算服务
        
        参数:
            filter_config: 滤波配置
            roi_config: ROI配置
            depth_config: 深度转换配置
        """
        self.filter_config = filter_config or FilterConfig()
        self.roi_config = roi_config or ROIConfig()
        self.depth_config = depth_config or DepthConversionConfig()
    
    def calculate_repeatability(self,
                                 image_dir: str,
                                 output_path: Optional[str] = None,
                                 calc_mode: str = 'mean',
                                 progress_callback: Optional[Callable[[int, int, str], None]] = None
                                 ) -> RepeatabilityResult:
        """
        计算重复精度
        
        参数:
            image_dir: 图像目录（包含多张同一位置的深度图）
            output_path: 结果输出路径（可选）
            calc_mode: 计算模式 ('mean' 或 'pixel')
            progress_callback: 进度回调函数
        
        返回:
            RepeatabilityResult 对象
        """
        # 获取图像文件
        image_files = list_image_files(image_dir)
        if not image_files:
            raise FileNotFoundError(f"未找到图像文件: {image_dir}")
        
        if len(image_files) < 2:
            raise ValueError("至少需要2张图像才能计算重复精度")
        
        total_count = len(image_files)
        
        if progress_callback:
            progress_callback(0, total_count, f"开始处理 {total_count} 张图像")
        
        image_values = []
        image_stats = []
        all_valid_pixels_mm = []
        first_roi_shape = None
        
        # 处理每张图像
        for i, image_path in enumerate(image_files):
            filename = os.path.basename(image_path)
            
            if progress_callback:
                progress_callback(i + 1, total_count, f"处理: {filename}")
            
            result = self._process_single_image(image_path)
            
            if result is None:
                continue
            
            mean_mm, std_mm, min_mm, max_mm, valid_count, valid_ratio, valid_pixels_mm, roi_shape = result
            
            if first_roi_shape is None:
                first_roi_shape = roi_shape
            
            image_values.append(mean_mm)
            image_stats.append({
                'filename': filename,
                'mean': mean_mm,
                'std': std_mm,
                'min': min_mm,
                'max': max_mm,
                'valid_count': valid_count,
                'valid_ratio': valid_ratio
            })
            all_valid_pixels_mm.append(valid_pixels_mm)
        
        if len(image_values) < 2:
            raise ValueError("有效图像数量不足")
        
        # 计算重复精度
        image_values_arr = np.array(image_values)
        
        overall_mean = float(np.mean(image_values_arr))
        overall_std = float(np.std(image_values_arr, ddof=1))
        
        repeatability_1sigma = overall_std
        repeatability_3sigma = 3 * overall_std
        repeatability_6sigma = 6 * overall_std
        peak_to_peak = float(np.max(image_values_arr) - np.min(image_values_arr))
        
        # 计算逐像素重复精度（如果所有图像有效像素数相同）
        pixel_repeatability = None
        if calc_mode == 'pixel' and len(set(len(p) for p in all_valid_pixels_mm)) == 1:
            pixel_matrix = np.vstack(all_valid_pixels_mm)
            pixel_stds = np.std(pixel_matrix, axis=0, ddof=1)
            
            pixel_repeatability = {
                'mean_std': float(np.mean(pixel_stds)),
                'max_std': float(np.max(pixel_stds)),
                'min_std': float(np.min(pixel_stds)),
                'median_std': float(np.median(pixel_stds))
            }
        
        # 图像内平均标准差
        avg_intra_image_std = float(np.mean([s['std'] for s in image_stats]))
        
        result = RepeatabilityResult(
            num_images=len(image_values),
            mean_depth=overall_mean,
            std_1sigma=repeatability_1sigma,
            repeatability_3sigma=repeatability_3sigma,
            repeatability_6sigma=repeatability_6sigma,
            peak_to_peak=peak_to_peak,
            avg_intra_image_std=avg_intra_image_std,
            image_values=image_values,
            image_stats=image_stats,
            pixel_repeatability=pixel_repeatability,
            roi_config=self.roi_config,
            roi_shape=first_roi_shape
        )
        
        # 保存结果
        if output_path:
            self._save_report(result, output_path, image_dir)
        
        return result
    
    def _process_single_image(self, image_path: str):
        """
        处理单张图像
        
        返回:
            (mean_mm, std_mm, min_mm, max_mm, valid_count, valid_ratio, valid_pixels_mm, roi_shape)
            或 None（处理失败）
        """
        try:
            depth_array = read_depth_image(image_path)
            
            roi = get_roi(
                depth_array,
                x=self.roi_config.x,
                y=self.roi_config.y,
                width=self.roi_config.width,
                height=self.roi_config.height
            )
            
            roi_shape = roi.shape
            
            # 滤波处理
            if self.filter_config.enabled:
                result = calibrate_image(roi, apply_filter=True, filter_config=self.filter_config)
                if result.success:
                    roi = result.calibrated_roi
            
            valid_pixels, _ = get_valid_pixels(roi, self.depth_config.invalid_value)
            
            if valid_pixels.size == 0:
                return None
            
            valid_pixels_mm = gray_to_mm_vectorized(
                valid_pixels,
                self.depth_config.offset,
                self.depth_config.scale_factor
            )
            
            mean_mm = float(np.mean(valid_pixels_mm))
            std_mm = float(np.std(valid_pixels_mm))
            min_mm = float(np.min(valid_pixels_mm))
            max_mm = float(np.max(valid_pixels_mm))
            valid_count = valid_pixels.size
            valid_ratio = valid_count / roi.size * 100
            
            return (mean_mm, std_mm, min_mm, max_mm, valid_count, valid_ratio, valid_pixels_mm, roi_shape)
            
        except Exception:
            return None
    
    def _save_report(self, result: RepeatabilityResult, output_path: str, image_dir: str) -> None:
        """保存重复精度报告"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Y-Z重复精度测量报告\n")
            f.write("=" * 70 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("【测试参数】\n")
            f.write("-" * 70 + "\n")
            f.write(f"图像目录: {image_dir}\n")
            f.write(f"图像数量: {result.num_images}\n")
            f.write(f"滤波处理: {'启用' if self.filter_config.enabled else '禁用'}\n")
            
            # ROI信息
            roi = result.roi_config
            if roi.is_full_image():
                f.write("ROI设置: 使用全部图像\n")
            else:
                x_end = '边缘' if roi.width == -1 else roi.x + roi.width
                y_end = '边缘' if roi.height == -1 else roi.y + roi.height
                f.write(f"ROI设置: X=[{roi.x}, {x_end}], Y=[{roi.y}, {y_end}]\n")
            
            if result.roi_shape:
                f.write(f"ROI尺寸: {result.roi_shape[1]} x {result.roi_shape[0]} 像素\n")
            f.write("\n")
            
            f.write("【重复精度结果】\n")
            f.write("-" * 70 + "\n")
            f.write(f"平均深度值: {result.mean_depth:.6f} mm\n")
            f.write(f"标准差(1σ): {result.std_1sigma:.6f} mm ({result.std_1sigma*1000:.3f} μm)\n")
            f.write(f"重复精度(±3σ): ±{result.repeatability_3sigma:.6f} mm (±{result.repeatability_3sigma*1000:.3f} μm)\n")
            f.write(f"重复精度(6σ): {result.repeatability_6sigma:.6f} mm ({result.repeatability_6sigma*1000:.3f} μm)\n")
            f.write(f"极差(P-P): {result.peak_to_peak:.6f} mm ({result.peak_to_peak*1000:.3f} μm)\n")
            f.write(f"图像内平均标准差: {result.avg_intra_image_std:.6f} mm ({result.avg_intra_image_std*1000:.3f} μm)\n")
            f.write("\n")
            
            if result.pixel_repeatability:
                pr = result.pixel_repeatability
                f.write("【逐像素重复精度分析】\n")
                f.write("-" * 70 + "\n")
                f.write(f"平均标准差: {pr['mean_std']:.6f} mm ({pr['mean_std']*1000:.3f} μm)\n")
                f.write(f"最大标准差: {pr['max_std']:.6f} mm ({pr['max_std']*1000:.3f} μm)\n")
                f.write(f"最小标准差: {pr['min_std']:.6f} mm ({pr['min_std']*1000:.3f} μm)\n")
                f.write(f"中位数标准差: {pr['median_std']:.6f} mm ({pr['median_std']*1000:.3f} μm)\n")
                f.write("\n")
            
            f.write("【逐图像详细数据】\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'序号':<6} {'文件名':<40} {'平均值(mm)':<14} {'标准差(mm)':<14}\n")
            f.write("-" * 70 + "\n")
            
            for i, stat in enumerate(result.image_stats, 1):
                f.write(f"{i:<6} {stat['filename']:<40} {stat['mean']:<14.6f} {stat['std']:<14.6f}\n")
            
            f.write("=" * 70 + "\n")
