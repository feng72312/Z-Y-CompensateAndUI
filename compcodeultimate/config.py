# -*- coding: utf-8 -*-
"""
配置文件 - 所有参数集中管理
"""

# ========================
# 深度转换配置
# ========================
OFFSET = 32768          # 深度转换偏移量
SCALE_FACTOR = 1.6      # 深度转换缩放因子
INVALID_VALUE = 65535   # 无效像素的灰度值

# ========================
# ROI配置
# ========================
ROI_X = 0               # ROI左上角X坐标
ROI_Y = 0               # ROI左上角Y坐标
ROI_WIDTH = -1          # ROI宽度（-1表示使用整个图像）
ROI_HEIGHT = -1         # ROI高度（-1表示使用整个图像）

# ========================
# 平面校准配置
# ========================
MIN_VALID_PIXELS = 100  # 最小有效像素数量
MIN_VALID_RATIO = 0.10  # 最小有效像素比例（10%）

# ========================
# 滤波配置
# ========================
FILTER_ENABLED = True           # 是否启用滤波
OUTLIER_STD_FACTOR = 3.0       # 异常值去除的标准差倍数
MEDIAN_FILTER_SIZE = 3         # 中值滤波窗口大小
GAUSSIAN_FILTER_SIGMA = 1.0    # 高斯滤波标准差

# ========================
# 补偿模型配置
# ========================
SPLINE_ORDER = 3               # 样条阶数（3=三次样条）

# ========================
# 线性度配置
# ========================
FULL_SCALE = 41.0              # 满量程范围 (mm)

# ========================
# 线性外推配置
# ========================
EXTRAPOLATE_ENABLED = True             # 是否启用线性外推
EXTRAPOLATE_MAX_LOW = 2.0              # 低端最大外推距离 (mm)
EXTRAPOLATE_MAX_HIGH = 2.0             # 高端最大外推距离 (mm)
EXTRAPOLATE_OUTPUT_MIN = 0.0           # 输出最小值限制 (mm)
EXTRAPOLATE_OUTPUT_MAX = 43.0          # 输出最大值限制 (mm)
EXTRAPOLATE_CLAMP_OUTPUT = True        # 是否限制输出范围

# ========================
# 输出归一化配置
# ========================
NORMALIZE_ENABLED = False             # 是否启用输出归一化
NORMALIZE_TARGET_CENTER = 0.0         # 归一化目标中心点 (mm)
NORMALIZE_AUTO_OFFSET = True          # 是否自动计算偏移量（基于模型y_range）

# ========================
# 数据质量检测配置
# ========================
ANOMALY_DETECTION_ENABLED = True   # 是否启用异常点检测
ANOMALY_THRESHOLD = 0.15           # 异常点阈值（测量增量与实际增量偏差超过实际增量的15%）
PLANE_STD_WARNING_ENABLED = True   # 是否启用平面标准差警告
PLANE_STD_THRESHOLD = 0.01         # 平面标准差警告阈值 (mm)

# ========================
# 数据目录配置
# ========================
CALIB_DIR = '../AW0350000R7J0004/calib_20251216_161030'
TEST_DIR = '../AW0350000R7J0004/test_20251216_143213'
OUTPUT_DIR = 'output'

