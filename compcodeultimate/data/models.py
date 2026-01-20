# -*- coding: utf-8 -*-
"""
数据模型定义
使用 dataclass 定义清晰的数据结构，提升类型安全和代码可读性
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Any
import numpy as np


# ==================== 配置类 ====================

@dataclass
class DepthConversionConfig:
    """深度转换配置"""
    offset: float = 32768.0
    scale_factor: float = 1.6
    invalid_value: int = 65535


@dataclass
class ROIConfig:
    """ROI区域配置"""
    x: int = 0
    y: int = 0
    width: int = -1   # -1 表示使用整个图像宽度
    height: int = -1  # -1 表示使用整个图像高度
    
    def is_full_image(self) -> bool:
        """是否使用整个图像"""
        return self.x == 0 and self.y == 0 and self.width == -1 and self.height == -1


@dataclass
class FilterConfig:
    """滤波配置"""
    enabled: bool = True
    outlier_std_factor: float = 3.0
    median_filter_size: int = 3
    gaussian_filter_sigma: float = 1.0


@dataclass
class ExtrapolateConfig:
    """外推配置"""
    enabled: bool = True
    max_low: float = 2.0    # 低端最大外推距离 (mm)
    max_high: float = 2.0   # 高端最大外推距离 (mm)
    output_min: float = 0.0
    output_max: float = 43.0
    clamp_output: bool = True


@dataclass
class NormalizeConfig:
    """归一化配置"""
    enabled: bool = False
    target_center: float = 0.0
    auto_offset: bool = True
    manual_offset: float = 0.0


# ==================== 模型类 ====================

@dataclass
class CompensationModel:
    """
    补偿模型数据结构
    
    存储三次样条插值模型的参数，支持序列化和反序列化
    """
    knots: np.ndarray              # 样条节点
    coefficients: np.ndarray       # 样条系数
    k: int                         # 样条阶数
    x_range: Tuple[float, float]   # 输入范围（测量值）
    y_range: Tuple[float, float]   # 输出范围（实际值）
    calibration_points: int        # 标定点数量
    version: str = "2.2"
    
    # 可选：完整标定数据（用于分析）
    actual_values: Optional[List[float]] = None
    measured_values: Optional[List[float]] = None
    
    # 可选：正向模型参数（实际值 -> 测量值）
    forward_knots: Optional[np.ndarray] = None
    forward_coefficients: Optional[np.ndarray] = None
    
    def get_inverse_model_tuple(self) -> Tuple[np.ndarray, np.ndarray, int]:
        """获取逆向模型元组，用于 scipy splev"""
        return (self.knots, self.coefficients, self.k)
    
    def get_forward_model_tuple(self) -> Optional[Tuple[np.ndarray, np.ndarray, int]]:
        """获取正向模型元组，用于 scipy splev"""
        if self.forward_knots is not None and self.forward_coefficients is not None:
            return (self.forward_knots, self.forward_coefficients, self.k)
        return None
    
    @property
    def measured_range(self) -> Tuple[float, float]:
        """测量值范围（别名，保持向后兼容）"""
        return self.x_range
    
    @property
    def actual_range(self) -> Tuple[float, float]:
        """实际值范围（别名，保持向后兼容）"""
        return self.y_range


# ==================== 结果类 ====================

@dataclass
class CalibrationResult:
    """
    平面校准结果
    """
    success: bool
    plane_params: Optional[Tuple[float, float, float]] = None  # (a, b, c) for z = ax + by + c
    calibrated_roi: Optional[np.ndarray] = None
    flatness: Optional[float] = None
    filtered_roi: Optional[np.ndarray] = None
    deviation: Optional[np.ndarray] = None
    reason: str = ""
    
    @classmethod
    def failure(cls, reason: str) -> 'CalibrationResult':
        """创建失败结果"""
        return cls(success=False, reason=reason)


@dataclass
class LinearityResult:
    """
    线性度计算结果（BFSL方法）
    """
    linearity: float           # 线性度百分比 (%)
    max_deviation: float       # 最大正偏差 (mm)
    min_deviation: float       # 最大负偏差 (mm)
    abs_max_deviation: float   # 绝对最大偏差 (mm)
    rms_error: float           # 均方根误差 (mm)
    mae: float                 # 平均绝对误差 (mm)
    r_squared: float           # 决定系数 R²
    slope: float               # 拟合直线斜率
    intercept: float           # 拟合直线截距 (mm)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'linearity': self.linearity,
            'max_deviation': self.max_deviation,
            'min_deviation': self.min_deviation,
            'abs_max_deviation': self.abs_max_deviation,
            'rms_error': self.rms_error,
            'mae': self.mae,
            'r_squared': self.r_squared,
            'slope': self.slope,
            'intercept': self.intercept
        }


@dataclass
class CompensationResult:
    """
    补偿结果（单张图像）
    """
    compensated_array: np.ndarray
    total_pixels: int
    valid_pixels: int
    in_range_pixels: int
    extrapolated_pixels: int
    compensated_pixels: int
    out_of_range_pixels: int
    invalid_pixels: int
    compensation_rate: float
    extrapolation_enabled: bool
    normalize_offset: float = 0.0
    
    @property
    def stats(self) -> dict:
        """获取统计信息字典（兼容旧接口）"""
        return {
            'total_pixels': self.total_pixels,
            'valid_pixels': self.valid_pixels,
            'in_range_pixels': self.in_range_pixels,
            'extrapolated_pixels': self.extrapolated_pixels,
            'compensated_pixels': self.compensated_pixels,
            'out_of_range_pixels': self.out_of_range_pixels,
            'invalid_pixels': self.invalid_pixels,
            'compensation_rate': self.compensation_rate,
            'extrapolation_enabled': self.extrapolation_enabled,
            'normalize_offset': self.normalize_offset
        }


@dataclass
class CompensationEffectResult:
    """
    补偿效果对比结果
    """
    before: LinearityResult
    after: LinearityResult
    improvement: float  # 改善百分比 (%)
    
    # 可选：原始数据
    actual_values_mm: Optional[np.ndarray] = None
    measured_values_mm: Optional[np.ndarray] = None
    compensated_values_mm: Optional[np.ndarray] = None
    
    # 可选：平面标准差
    avg_plane_std_before: float = 0.0
    avg_plane_std_after: float = 0.0


@dataclass
class RepeatabilityResult:
    """
    重复精度计算结果
    """
    num_images: int
    mean_depth: float           # 平均深度 (mm)
    std_1sigma: float           # 标准差 1σ (mm)
    repeatability_3sigma: float # 重复精度 ±3σ (mm)
    repeatability_6sigma: float # 重复精度 6σ (mm)
    peak_to_peak: float         # 极差 (mm)
    avg_intra_image_std: float  # 图像内平均标准差 (mm)
    
    # 可选：详细数据
    image_values: Optional[List[float]] = None
    image_stats: Optional[List[dict]] = None
    pixel_repeatability: Optional[dict] = None
    roi_config: Optional[ROIConfig] = None
    roi_shape: Optional[Tuple[int, int]] = None


@dataclass
class BatchProcessResult:
    """
    批量处理结果
    """
    total_images: int
    processed_images: int
    failed_images: int
    total_pixels: int
    compensated_pixels: int
    avg_compensation_rate: float
    results: List[CompensationResult] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)  # (filename, error_message)
