# -*- coding: utf-8 -*-
"""
深度图补偿系统 - 图形用户界面
版本: v2.2 UI Edition
新增: 模型加载、批量补偿、单个补偿功能
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# 添加父目录到路径，以便导入compcodeultimate模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'compcodeultimate'))

from config import (OFFSET, SCALE_FACTOR, INVALID_VALUE, FILTER_ENABLED,
                    OUTLIER_STD_FACTOR, MEDIAN_FILTER_SIZE, GAUSSIAN_FILTER_SIGMA,
                    FULL_SCALE, SPLINE_ORDER,
                    EXTRAPOLATE_ENABLED, EXTRAPOLATE_MAX_LOW, EXTRAPOLATE_MAX_HIGH,
                    EXTRAPOLATE_OUTPUT_MIN, EXTRAPOLATE_OUTPUT_MAX, EXTRAPOLATE_CLAMP_OUTPUT,
                    NORMALIZE_ENABLED, NORMALIZE_TARGET_CENTER, NORMALIZE_AUTO_OFFSET,
                    ANOMALY_DETECTION_ENABLED, ANOMALY_THRESHOLD,
                    PLANE_STD_WARNING_ENABLED, PLANE_STD_THRESHOLD)


class DepthCompensationApp:
    """深度图补偿系统主界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("深度图补偿系统 v2.2")
        self.root.geometry("1100x800")
        self.root.minsize(1000, 700)
        
        # 设置样式
        self.setup_styles()
        
        # 变量
        self.calib_dir = tk.StringVar()
        self.test_dir = tk.StringVar()
        self.output_dir = tk.StringVar(value="output")
        self.model_path = tk.StringVar()
        self.single_image_path = tk.StringVar()
        self.single_output_path = tk.StringVar()
        self.filter_enabled = tk.BooleanVar(value=True)
        self.full_scale = tk.DoubleVar(value=FULL_SCALE)  # 满量程设置
        self.outlier_std = tk.DoubleVar(value=OUTLIER_STD_FACTOR)  # 异常值阈值
        self.median_size = tk.IntVar(value=MEDIAN_FILTER_SIZE)  # 中值滤波窗口
        
        # 外推参数
        self.extrapolate_enabled = tk.BooleanVar(value=EXTRAPOLATE_ENABLED)
        self.extrapolate_max_low = tk.DoubleVar(value=EXTRAPOLATE_MAX_LOW)
        self.extrapolate_max_high = tk.DoubleVar(value=EXTRAPOLATE_MAX_HIGH)
        self.extrapolate_output_min = tk.DoubleVar(value=EXTRAPOLATE_OUTPUT_MIN)
        self.extrapolate_output_max = tk.DoubleVar(value=EXTRAPOLATE_OUTPUT_MAX)
        
        # 归一化参数
        self.normalize_enabled = tk.BooleanVar(value=NORMALIZE_ENABLED)
        self.normalize_target_center = tk.DoubleVar(value=NORMALIZE_TARGET_CENTER)
        self.normalize_auto_offset = tk.BooleanVar(value=NORMALIZE_AUTO_OFFSET)
        self.normalize_manual_offset = tk.DoubleVar(value=0.0)
        self.normalize_calculated_offset = tk.StringVar(value="--")
        
        # 深度转换系数
        self.depth_offset = tk.DoubleVar(value=OFFSET)  # 偏移量 (默认32768)
        self.depth_scale_factor = tk.DoubleVar(value=SCALE_FACTOR)  # 缩放因子 (默认1.6)
        
        # 完整流程ROI参数
        self.full_roi_mode = tk.StringVar(value="full")  # full, x_only, y_only, custom
        self.full_roi_x_start = tk.IntVar(value=0)
        self.full_roi_x_end = tk.IntVar(value=-1)
        self.full_roi_y_start = tk.IntVar(value=0)
        self.full_roi_y_end = tk.IntVar(value=-1)
        
        # 线性度计算深度转换系数
        self.linearity_depth_offset = tk.DoubleVar(value=OFFSET)
        self.linearity_depth_scale_factor = tk.DoubleVar(value=SCALE_FACTOR)
        
        # 重复精度计算深度转换系数
        self.repeat_depth_offset = tk.DoubleVar(value=OFFSET)
        self.repeat_depth_scale_factor = tk.DoubleVar(value=SCALE_FACTOR)
        
        # X位置重复精度参数
        self.x_repeat_depth_offset = tk.DoubleVar(value=OFFSET)
        self.x_repeat_depth_scale = tk.DoubleVar(value=1.6)  # μm/count
        self.x_repeat_spatial_res = tk.DoubleVar(value=0.0125)  # mm/pixel
        self.x_repeat_fit_type = tk.StringVar(value="ellipse")  # circle or ellipse
        self.x_repeat_fixed_diameter = tk.DoubleVar(value=0.0)  # mm, 0=auto
        self.x_repeat_use_dynamic_roi = tk.BooleanVar(value=True)
        
        self.is_running = False
        self.model = None
        self.model_loaded = False
        
        # 创建界面
        self.create_ui()
        
        # 居中窗口
        self.center_window()
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'vista' in available_themes:
            style.theme_use('vista')
        
        # 自定义样式
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 16, 'bold'), foreground='#1a73e8')
        style.configure('Subtitle.TLabel', font=('Microsoft YaHei UI', 10), foreground='#5f6368')
        style.configure('Header.TLabel', font=('Microsoft YaHei UI', 11, 'bold'), foreground='#202124')
        style.configure('Status.TLabel', font=('Microsoft YaHei UI', 9), foreground='#5f6368')
        style.configure('ModelLoaded.TLabel', font=('Microsoft YaHei UI', 10, 'bold'), foreground='#0d904f')
        style.configure('ModelNotLoaded.TLabel', font=('Microsoft YaHei UI', 10), foreground='#ea4335')
        
        style.configure('Primary.TButton', font=('Microsoft YaHei UI', 10, 'bold'), padding=(20, 10))
        style.configure('Secondary.TButton', font=('Microsoft YaHei UI', 9), padding=(10, 5))
        style.configure('Success.TButton', font=('Microsoft YaHei UI', 10, 'bold'), padding=(15, 8))
        
        style.configure('Card.TLabelframe', background='#ffffff')
        style.configure('Card.TLabelframe.Label', font=('Microsoft YaHei UI', 10, 'bold'), foreground='#1a73e8')
        
        style.configure('Good.TLabel', font=('Microsoft YaHei UI', 11, 'bold'), foreground='#0d904f')
        style.configure('Value.TLabel', font=('Consolas', 11), foreground='#202124')
    
    def center_window(self):
        """居中窗口"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_ui(self):
        """创建主界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题区域
        self.create_header(main_frame)
        
        # 分隔线
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=8)
        
        # 使用Notebook创建标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 标签页1: 完整流程（标定+补偿）
        self.tab_full = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_full, text="📊 完整流程（标定+补偿）")
        self.create_full_mode_tab(self.tab_full)
        
        # 标签页2: 补偿模式（加载模型）
        self.tab_compensate = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_compensate, text="🔧 补偿模式（使用模型）")
        self.create_compensate_mode_tab(self.tab_compensate)
        
        # 标签页3: 线性度计算
        self.tab_linearity = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_linearity, text="📈 线性度计算")
        self.create_linearity_tab(self.tab_linearity)
        
        # 标签页4: 重复精度测量
        self.tab_repeatability = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_repeatability, text="🎯 重复精度测量")
        self.create_repeatability_tab(self.tab_repeatability)
        
        # 标签页5: X位置重复精度
        self.tab_x_repeatability = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.tab_x_repeatability, text="📍 X位置重复精度")
        self.create_x_repeatability_tab(self.tab_x_repeatability)
        
        # 状态栏
        self.create_statusbar(main_frame)
    
    def create_header(self, parent):
        """创建标题区域"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(header_frame, text="🎯 深度图补偿系统", style='Title.TLabel')
        title_label.pack(side=tk.LEFT)
        
        version_label = ttk.Label(header_frame, text="v2.2 Ultimate Edition", style='Subtitle.TLabel')
        version_label.pack(side=tk.LEFT, padx=(10, 0))
        
        help_btn = ttk.Button(header_frame, text="❓ 帮助", command=self.show_help, style='Secondary.TButton')
        help_btn.pack(side=tk.RIGHT)
    
    # ==================== 标签页1: 完整流程 ====================
    
    def create_full_mode_tab(self, parent):
        """创建完整流程标签页"""
        # 左右分栏
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 左侧：配置
        self.create_full_config_panel(left_frame)
        
        # 右侧：日志和结果
        self.create_log_panel(right_frame, 'full')
        self.create_result_panel(right_frame)
    
    def create_full_config_panel(self, parent):
        """创建完整模式配置面板"""
        # 目录配置
        dir_frame = ttk.LabelFrame(parent, text="📁 数据目录", padding="10", style='Card.TLabelframe')
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 标定目录
        calib_frame = ttk.Frame(dir_frame)
        calib_frame.pack(fill=tk.X, pady=3)
        ttk.Label(calib_frame, text="标定目录:", width=10).pack(side=tk.LEFT)
        ttk.Entry(calib_frame, textvariable=self.calib_dir, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(calib_frame, text="浏览", command=lambda: self.browse_directory(self.calib_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 测试目录
        test_frame = ttk.Frame(dir_frame)
        test_frame.pack(fill=tk.X, pady=3)
        ttk.Label(test_frame, text="测试目录:", width=10).pack(side=tk.LEFT)
        ttk.Entry(test_frame, textvariable=self.test_dir, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(test_frame, text="浏览", command=lambda: self.browse_directory(self.test_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 输出目录
        output_frame = ttk.Frame(dir_frame)
        output_frame.pack(fill=tk.X, pady=3)
        ttk.Label(output_frame, text="输出目录:", width=10).pack(side=tk.LEFT)
        ttk.Entry(output_frame, textvariable=self.output_dir, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="浏览", command=lambda: self.browse_directory(self.output_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 设置
        settings_frame = ttk.LabelFrame(parent, text="⚙️ 参数设置", padding="10", style='Card.TLabelframe')
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(settings_frame, text="启用滤波处理（推荐）", 
                        variable=self.filter_enabled).pack(anchor=tk.W)
        
        # 滤波参数行
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.pack(fill=tk.X, pady=(8, 0))
        
        ttk.Label(filter_frame, text="异常值阈值:").pack(side=tk.LEFT)
        ttk.Entry(filter_frame, textvariable=self.outlier_std, width=6).pack(side=tk.LEFT, padx=3)
        ttk.Label(filter_frame, text="σ", style='Status.TLabel').pack(side=tk.LEFT)
        
        ttk.Label(filter_frame, text="    中值滤波窗口:").pack(side=tk.LEFT)
        ttk.Entry(filter_frame, textvariable=self.median_size, width=4).pack(side=tk.LEFT, padx=3)
        ttk.Label(filter_frame, text="×N", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 满量程设置
        fs_frame = ttk.Frame(settings_frame)
        fs_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(fs_frame, text="满量程:").pack(side=tk.LEFT)
        fs_entry = ttk.Entry(fs_frame, textvariable=self.full_scale, width=10)
        fs_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(fs_frame, text="mm（用于线性度计算）", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 深度转换系数设置
        depth_frame = ttk.Frame(settings_frame)
        depth_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(depth_frame, text="深度转换:").pack(side=tk.LEFT)
        ttk.Label(depth_frame, text="偏移量=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_frame, textvariable=self.depth_offset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(depth_frame, text="缩放因子=").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Entry(depth_frame, textvariable=self.depth_scale_factor, width=6).pack(side=tk.LEFT, padx=2)
        
        # 公式说明
        formula_frame = ttk.Frame(settings_frame)
        formula_frame.pack(fill=tk.X, pady=(3, 0))
        ttk.Label(formula_frame, text="公式: y(mm) = (灰度值 - 偏移量) × 缩放因子 / 1000", 
                  style='Status.TLabel').pack(side=tk.LEFT, padx=(55, 0))
        
        # ROI设置
        roi_frame = ttk.LabelFrame(parent, text="📐 ROI设置", padding="10", style='Card.TLabelframe')
        roi_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ROI模式选择
        mode_frame = ttk.Frame(roi_frame)
        mode_frame.pack(fill=tk.X, pady=3)
        
        ttk.Radiobutton(mode_frame, text="全部图像", variable=self.full_roi_mode, 
                        value="full", command=self._on_full_roi_mode_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="X方向ROI", variable=self.full_roi_mode, 
                        value="x_only", command=self._on_full_roi_mode_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Y方向ROI", variable=self.full_roi_mode, 
                        value="y_only", command=self._on_full_roi_mode_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="自定义ROI", variable=self.full_roi_mode, 
                        value="custom", command=self._on_full_roi_mode_change).pack(side=tk.LEFT)
        
        # X方向ROI设置
        self.full_roi_x_frame = ttk.Frame(roi_frame)
        self.full_roi_x_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.full_roi_x_frame, text="X方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(self.full_roi_x_frame, text="起始").pack(side=tk.LEFT)
        self.full_roi_x_start_entry = ttk.Entry(self.full_roi_x_frame, textvariable=self.full_roi_x_start, width=6)
        self.full_roi_x_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.full_roi_x_frame, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.full_roi_x_end_entry = ttk.Entry(self.full_roi_x_frame, textvariable=self.full_roi_x_end, width=6)
        self.full_roi_x_end_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.full_roi_x_frame, text="(-1=图像边缘)", style='Status.TLabel').pack(side=tk.LEFT, padx=5)
        
        # Y方向ROI设置
        self.full_roi_y_frame = ttk.Frame(roi_frame)
        self.full_roi_y_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(self.full_roi_y_frame, text="Y方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(self.full_roi_y_frame, text="起始").pack(side=tk.LEFT)
        self.full_roi_y_start_entry = ttk.Entry(self.full_roi_y_frame, textvariable=self.full_roi_y_start, width=6)
        self.full_roi_y_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.full_roi_y_frame, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.full_roi_y_end_entry = ttk.Entry(self.full_roi_y_frame, textvariable=self.full_roi_y_end, width=6)
        self.full_roi_y_end_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.full_roi_y_frame, text="(-1=图像边缘)", style='Status.TLabel').pack(side=tk.LEFT, padx=5)
        
        # ROI预览信息
        self.full_roi_info_label = ttk.Label(roi_frame, text="当前: 使用全部图像", style='Status.TLabel')
        self.full_roi_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 初始化ROI输入框状态
        self._on_full_roi_mode_change()
        
        # 操作按钮
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=10)
        
        self.full_run_btn = ttk.Button(action_frame, text="▶️ 开始标定", 
                                        command=self.run_full_compensation, style='Primary.TButton')
        self.full_run_btn.pack(fill=tk.X, pady=5)
        
        self.full_progress = ttk.Progressbar(action_frame, mode='indeterminate')
        self.full_progress.pack(fill=tk.X, pady=5)
        
        # 快捷操作
        quick_frame = ttk.Frame(action_frame)
        quick_frame.pack(fill=tk.X, pady=5)
        ttk.Button(quick_frame, text="📂 打开输出", command=self.open_output_dir,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="🔄 清空日志", command=lambda: self.clear_log('full'),
                   style='Secondary.TButton').pack(side=tk.LEFT)
    
    # ==================== 标签页2: 补偿模式 ====================
    
    def create_compensate_mode_tab(self, parent):
        """创建补偿模式标签页"""
        # 上下分栏
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上部：模型加载
        self.create_model_load_panel(top_frame)
        
        # 下部：左右分栏（批量补偿 | 单个补偿）
        left_frame = ttk.Frame(bottom_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = ttk.Frame(bottom_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.create_batch_compensate_panel(left_frame)
        self.create_single_compensate_panel(right_frame)
    
    def create_model_load_panel(self, parent):
        """创建模型加载面板"""
        model_frame = ttk.LabelFrame(parent, text="📦 补偿模型", padding="10", style='Card.TLabelframe')
        model_frame.pack(fill=tk.X)
        
        # 模型路径
        path_frame = ttk.Frame(model_frame)
        path_frame.pack(fill=tk.X, pady=3)
        
        ttk.Label(path_frame, text="模型文件:", width=10).pack(side=tk.LEFT)
        ttk.Entry(path_frame, textvariable=self.model_path, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self.browse_model_file,
                   style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(path_frame, text="📥 加载模型", command=self.load_model,
                   style='Success.TButton').pack(side=tk.LEFT)
        
        # 模型状态和满量程设置
        status_frame = ttk.Frame(model_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(status_frame, text="状态:", width=10).pack(side=tk.LEFT)
        self.model_status_label = ttk.Label(status_frame, text="❌ 未加载模型", style='ModelNotLoaded.TLabel')
        self.model_status_label.pack(side=tk.LEFT)
        
        # 模型信息
        self.model_info_label = ttk.Label(status_frame, text="", style='Status.TLabel')
        self.model_info_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 满量程设置（补偿模式）
        ttk.Label(status_frame, text="    满量程:").pack(side=tk.LEFT, padx=(20, 0))
        fs_entry2 = ttk.Entry(status_frame, textvariable=self.full_scale, width=8)
        fs_entry2.pack(side=tk.LEFT, padx=3)
        ttk.Label(status_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 外推设置
        extrapolate_frame = ttk.Frame(model_frame)
        extrapolate_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Checkbutton(extrapolate_frame, text="启用线性外推", 
                        variable=self.extrapolate_enabled).pack(side=tk.LEFT)
        
        ttk.Label(extrapolate_frame, text="    低端外推:").pack(side=tk.LEFT)
        ttk.Entry(extrapolate_frame, textvariable=self.extrapolate_max_low, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(extrapolate_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        ttk.Label(extrapolate_frame, text="    高端外推:").pack(side=tk.LEFT)
        ttk.Entry(extrapolate_frame, textvariable=self.extrapolate_max_high, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(extrapolate_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 输出范围限制
        output_limit_frame = ttk.Frame(model_frame)
        output_limit_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(output_limit_frame, text="输出范围限制:", style='Status.TLabel').pack(side=tk.LEFT)
        ttk.Entry(output_limit_frame, textvariable=self.extrapolate_output_min, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(output_limit_frame, text="~", style='Status.TLabel').pack(side=tk.LEFT)
        ttk.Entry(output_limit_frame, textvariable=self.extrapolate_output_max, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(output_limit_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 归一化设置
        normalize_frame = ttk.Frame(model_frame)
        normalize_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Checkbutton(normalize_frame, text="启用输出归一化", 
                        variable=self.normalize_enabled,
                        command=self._on_normalize_toggle).pack(side=tk.LEFT)
        
        ttk.Label(normalize_frame, text="    目标中心:").pack(side=tk.LEFT)
        self.normalize_center_entry = ttk.Entry(normalize_frame, textvariable=self.normalize_target_center, width=6)
        self.normalize_center_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(normalize_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 归一化详细设置
        normalize_detail_frame = ttk.Frame(model_frame)
        normalize_detail_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.normalize_auto_cb = ttk.Checkbutton(normalize_detail_frame, text="自动计算偏移量", 
                                                  variable=self.normalize_auto_offset,
                                                  command=self._on_normalize_auto_toggle)
        self.normalize_auto_cb.pack(side=tk.LEFT)
        
        ttk.Label(normalize_detail_frame, text="    手动偏移:").pack(side=tk.LEFT)
        self.normalize_manual_entry = ttk.Entry(normalize_detail_frame, textvariable=self.normalize_manual_offset, width=8)
        self.normalize_manual_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(normalize_detail_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 计算结果显示
        normalize_result_frame = ttk.Frame(model_frame)
        normalize_result_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(normalize_result_frame, text="计算偏移量:", style='Status.TLabel').pack(side=tk.LEFT)
        self.normalize_offset_label = ttk.Label(normalize_result_frame, textvariable=self.normalize_calculated_offset, 
                                                 style='Value.TLabel')
        self.normalize_offset_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(normalize_result_frame, text="    归一化范围:", style='Status.TLabel').pack(side=tk.LEFT)
        self.normalize_range_label = ttk.Label(normalize_result_frame, text="--", style='Value.TLabel')
        self.normalize_range_label.pack(side=tk.LEFT, padx=5)
        
        # 初始化归一化控件状态
        self._on_normalize_toggle()
        self._on_normalize_auto_toggle()
    
    def create_batch_compensate_panel(self, parent):
        """创建批量补偿面板"""
        batch_frame = ttk.LabelFrame(parent, text="📁 批量补偿", padding="10", style='Card.TLabelframe')
        batch_frame.pack(fill=tk.BOTH, expand=True)
        
        # 输入目录
        input_frame = ttk.Frame(batch_frame)
        input_frame.pack(fill=tk.X, pady=3)
        ttk.Label(input_frame, text="输入目录:").pack(side=tk.LEFT)
        self.batch_input_dir = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.batch_input_dir, width=25).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="浏览", command=lambda: self.browse_directory(self.batch_input_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 输出目录
        output_frame = ttk.Frame(batch_frame)
        output_frame.pack(fill=tk.X, pady=3)
        ttk.Label(output_frame, text="输出目录:").pack(side=tk.LEFT)
        self.batch_output_dir = tk.StringVar(value="output_batch")
        ttk.Entry(output_frame, textvariable=self.batch_output_dir, width=25).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="浏览", command=lambda: self.browse_directory(self.batch_output_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 操作按钮
        self.batch_run_btn = ttk.Button(batch_frame, text="▶️ 开始批量补偿", 
                                         command=self.run_batch_compensate, style='Primary.TButton')
        self.batch_run_btn.pack(fill=tk.X, pady=10)
        
        self.batch_progress = ttk.Progressbar(batch_frame, mode='determinate')
        self.batch_progress.pack(fill=tk.X)
        
        # 日志
        log_label = ttk.Label(batch_frame, text="处理日志:", style='Status.TLabel')
        log_label.pack(anchor=tk.W, pady=(10, 3))
        
        self.batch_log = tk.Text(batch_frame, height=8, font=('Consolas', 9),
                                  bg='#1e1e1e', fg='#d4d4d4', wrap=tk.WORD)
        self.batch_log.pack(fill=tk.BOTH, expand=True)
        
        self.batch_log.tag_configure('info', foreground='#4fc3f7')
        self.batch_log.tag_configure('success', foreground='#81c784')
        self.batch_log.tag_configure('error', foreground='#e57373')
    
    def create_single_compensate_panel(self, parent):
        """创建单个补偿面板"""
        single_frame = ttk.LabelFrame(parent, text="🖼️ 单个图像补偿", padding="10", style='Card.TLabelframe')
        single_frame.pack(fill=tk.BOTH, expand=True)
        
        # 输入图像
        input_frame = ttk.Frame(single_frame)
        input_frame.pack(fill=tk.X, pady=3)
        ttk.Label(input_frame, text="输入图像:").pack(side=tk.LEFT)
        ttk.Entry(input_frame, textvariable=self.single_image_path, width=25).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="浏览", command=self.browse_single_image,
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 输出图像
        output_frame = ttk.Frame(single_frame)
        output_frame.pack(fill=tk.X, pady=3)
        ttk.Label(output_frame, text="输出图像:").pack(side=tk.LEFT)
        ttk.Entry(output_frame, textvariable=self.single_output_path, width=25).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="浏览", command=self.browse_single_output,
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 操作按钮
        self.single_run_btn = ttk.Button(single_frame, text="▶️ 补偿此图像", 
                                          command=self.run_single_compensate, style='Primary.TButton')
        self.single_run_btn.pack(fill=tk.X, pady=10)
        
        # 结果显示
        result_label = ttk.Label(single_frame, text="补偿结果:", style='Status.TLabel')
        result_label.pack(anchor=tk.W, pady=(10, 3))
        
        self.single_result_frame = ttk.Frame(single_frame)
        self.single_result_frame.pack(fill=tk.X)
        
        # 结果标签
        self.single_result_labels = {}
        metrics = [('total', '总像素'), ('valid', '有效像素'), ('compensated', '补偿像素'), 
                   ('extrapolated', '外推像素'), ('rate', '补偿率')]
        
        for i, (key, label) in enumerate(metrics):
            row_frame = ttk.Frame(self.single_result_frame)
            row_frame.pack(fill=tk.X, pady=2)
            ttk.Label(row_frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
            value_label = ttk.Label(row_frame, text="--", style='Value.TLabel')
            value_label.pack(side=tk.LEFT)
            self.single_result_labels[key] = value_label
    
    # ==================== 通用面板 ====================
    
    def create_log_panel(self, parent, mode='full'):
        """创建日志面板"""
        log_frame = ttk.LabelFrame(parent, text="📋 运行日志", padding="5", style='Card.TLabelframe')
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        log_text = tk.Text(log_frame, height=10, font=('Consolas', 9), 
                           bg='#1e1e1e', fg='#d4d4d4', wrap=tk.WORD, padx=10, pady=10)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.config(yscrollcommand=scrollbar.set)
        
        log_text.tag_configure('info', foreground='#4fc3f7')
        log_text.tag_configure('success', foreground='#81c784')
        log_text.tag_configure('warning', foreground='#ffb74d')
        log_text.tag_configure('error', foreground='#e57373')
        log_text.tag_configure('header', foreground='#ce93d8', font=('Consolas', 9, 'bold'))
        
        if mode == 'full':
            self.full_log_text = log_text
    
    def create_result_panel(self, parent):
        """创建结果面板"""
        result_frame = ttk.LabelFrame(parent, text="📊 补偿结果", padding="10", style='Card.TLabelframe')
        result_frame.pack(fill=tk.X)
        
        self.result_labels = {}
        
        # 分组显示：补偿前 | 补偿后
        metrics = [
            # (key, label, row, col)
            ('linearity_before', '补偿前线性度', 0, 0),
            ('linearity_after', '补偿后线性度', 0, 2),
            # 最大偏差
            ('max_dev_before', '补偿前最大偏差', 1, 0),
            ('max_dev_after', '补偿后最大偏差', 1, 2),
            # 平面标准差均值
            ('plane_std_before', '补偿前平面标准差均值', 2, 0),
            ('plane_std_after', '补偿后平面标准差均值', 2, 2),
            # 改善幅度和R²
            ('improvement', '改善幅度', 3, 0),
            ('r_squared', 'R²决定系数', 3, 2),
        ]
        
        for key, label, row, col in metrics:
            ttk.Label(result_frame, text=f"{label}:", style='Header.TLabel').grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=3)
            
            value_label = ttk.Label(result_frame, text="--", style='Value.TLabel')
            value_label.grid(row=row, column=col+1, sticky=tk.W, padx=10, pady=3)
            self.result_labels[key] = value_label
        
        result_frame.columnconfigure(1, weight=1)
        result_frame.columnconfigure(3, weight=1)
        
        # 警告显示区域
        self.warning_frame = ttk.Frame(result_frame)
        self.warning_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW, pady=(10, 0))
        
        self.warning_label = ttk.Label(self.warning_frame, text="", foreground='red', 
                                        font=('微软雅黑', 9, 'bold'), wraplength=500)
        self.warning_label.pack(fill=tk.X)
    
    def create_statusbar(self, parent):
        """创建状态栏"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="就绪", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        ttk.Label(status_frame, text="© 2025 深度图补偿系统 v2.2", style='Status.TLabel').pack(side=tk.RIGHT)
    
    # ==================== 辅助函数 ====================
    
    def browse_directory(self, var):
        """浏览目录"""
        directory = filedialog.askdirectory(title="选择目录")
        if directory:
            var.set(directory)
    
    def browse_model_file(self):
        """浏览模型文件"""
        filepath = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filepath:
            self.model_path.set(filepath)
    
    def browse_single_image(self):
        """浏览单个图像"""
        filepath = filedialog.askopenfilename(
            title="选择深度图像",
            filetypes=[("深度图", "*.png;*.tif;*.tiff"), ("PNG文件", "*.png"), ("TIF文件", "*.tif;*.tiff"), ("所有文件", "*.*")]
        )
        if filepath:
            self.single_image_path.set(filepath)
            # 自动设置输出路径
            dir_name = os.path.dirname(filepath)
            base_name = os.path.basename(filepath)
            name, ext = os.path.splitext(base_name)
            self.single_output_path.set(os.path.join(dir_name, f"{name}_compensated{ext}"))
    
    def browse_single_output(self):
        """浏览输出图像路径"""
        filepath = filedialog.asksaveasfilename(
            title="保存补偿后图像",
            defaultextension=".png",
            filetypes=[("PNG文件", "*.png"), ("TIF文件", "*.tif")]
        )
        if filepath:
            self.single_output_path.set(filepath)
    
    def log(self, message, level='info', target='full'):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if target == 'full' and hasattr(self, 'full_log_text'):
            self.full_log_text.insert(tk.END, f"[{timestamp}] ", 'info')
            self.full_log_text.insert(tk.END, f"{message}\n", level)
            self.full_log_text.see(tk.END)
        elif target == 'batch' and hasattr(self, 'batch_log'):
            self.batch_log.insert(tk.END, f"[{timestamp}] {message}\n", level)
            self.batch_log.see(tk.END)
        
        self.root.update_idletasks()
    
    def clear_log(self, target='full'):
        """清空日志"""
        if target == 'full' and hasattr(self, 'full_log_text'):
            self.full_log_text.delete(1.0, tk.END)
        elif target == 'batch' and hasattr(self, 'batch_log'):
            self.batch_log.delete(1.0, tk.END)
    
    def open_output_dir(self):
        """打开输出目录"""
        output_path = self.output_dir.get()
        if os.path.exists(output_path):
            os.startfile(output_path)
        else:
            messagebox.showwarning("提示", "输出目录不存在")
    
    def update_status(self, text):
        """更新状态栏"""
        self.status_label.config(text=text)
        self.root.update_idletasks()
    
    def update_results(self, effect, warnings=None):
        """更新结果面板"""
        before = effect['before']
        after = effect['after']
        
        # 线性度
        self.result_labels['linearity_before'].config(text=f"{before['linearity']:.4f}%")
        self.result_labels['linearity_after'].config(text=f"{after['linearity']:.4f}%", style='Good.TLabel')
        
        # 最大偏差
        self.result_labels['max_dev_before'].config(text=f"{before['abs_max_deviation']:.6f} mm")
        self.result_labels['max_dev_after'].config(text=f"{after['abs_max_deviation']:.6f} mm", style='Good.TLabel')
        
        # 平面标准差均值
        avg_plane_std_before = effect.get('avg_plane_std_before', 0)
        avg_plane_std_after = effect.get('avg_plane_std_after', 0)
        self.result_labels['plane_std_before'].config(text=f"{avg_plane_std_before:.6f} mm")
        self.result_labels['plane_std_after'].config(text=f"{avg_plane_std_after:.6f} mm", style='Good.TLabel')
        
        # 改善幅度和R²
        self.result_labels['improvement'].config(text=f"↑ {effect['improvement']:.2f}%", style='Good.TLabel')
        self.result_labels['r_squared'].config(text=f"{after['r_squared']:.8f}")
        
        # 显示警告
        if warnings:
            self.warning_label.config(text=warnings)
        else:
            self.warning_label.config(text="")
    
    # ==================== 标签页3: 线性度计算 ====================
    
    def create_linearity_tab(self, parent):
        """创建线性度计算标签页"""
        # 左右分栏
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=False)
        
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 左侧：配置
        # 数据目录
        dir_frame = ttk.LabelFrame(left_frame, text="📁 测试数据", padding="10", style='Card.TLabelframe')
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.linearity_test_dir = tk.StringVar()
        
        test_frame = ttk.Frame(dir_frame)
        test_frame.pack(fill=tk.X, pady=3)
        ttk.Label(test_frame, text="测试目录:").pack(side=tk.LEFT)
        ttk.Entry(test_frame, textvariable=self.linearity_test_dir, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(test_frame, text="浏览", command=lambda: self.browse_directory(self.linearity_test_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 模型（可选）
        model_frame = ttk.Frame(dir_frame)
        model_frame.pack(fill=tk.X, pady=3)
        
        self.linearity_model_path = tk.StringVar()
        self.linearity_use_model = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(model_frame, text="使用补偿模型:", variable=self.linearity_use_model).pack(side=tk.LEFT)
        ttk.Entry(model_frame, textvariable=self.linearity_model_path, width=25).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(model_frame, text="浏览", command=lambda: self.browse_model_for_linearity(),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 输出文件
        output_frame = ttk.Frame(dir_frame)
        output_frame.pack(fill=tk.X, pady=3)
        
        self.linearity_output_path = tk.StringVar(value="output/线性度报告.txt")
        
        ttk.Label(output_frame, text="输出文件:").pack(side=tk.LEFT)
        ttk.Entry(output_frame, textvariable=self.linearity_output_path, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="浏览", command=self.browse_linearity_output,
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 设置
        settings_frame = ttk.LabelFrame(left_frame, text="⚙️ 参数设置", padding="10", style='Card.TLabelframe')
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 满量程
        fs_frame = ttk.Frame(settings_frame)
        fs_frame.pack(fill=tk.X, pady=3)
        ttk.Label(fs_frame, text="满量程:").pack(side=tk.LEFT)
        ttk.Entry(fs_frame, textvariable=self.full_scale, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(fs_frame, text="mm", style='Status.TLabel').pack(side=tk.LEFT)
        
        # 深度转换系数设置
        depth_frame = ttk.Frame(settings_frame)
        depth_frame.pack(fill=tk.X, pady=3)
        ttk.Label(depth_frame, text="深度转换:").pack(side=tk.LEFT)
        ttk.Label(depth_frame, text="偏移量=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_frame, textvariable=self.linearity_depth_offset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(depth_frame, text="缩放因子=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_frame, textvariable=self.linearity_depth_scale_factor, width=6).pack(side=tk.LEFT, padx=2)
        
        # 公式说明
        formula_frame = ttk.Frame(settings_frame)
        formula_frame.pack(fill=tk.X, pady=(0, 3))
        ttk.Label(formula_frame, text="公式: y(mm) = (灰度值 - 偏移量) × 缩放因子 / 1000", 
                  style='Status.TLabel').pack(side=tk.LEFT, padx=(60, 0))
        
        ttk.Checkbutton(settings_frame, text="启用滤波处理", 
                        variable=self.filter_enabled).pack(anchor=tk.W, pady=3)
        
        # ROI设置
        roi_frame = ttk.LabelFrame(left_frame, text="📐 ROI设置", padding="10", style='Card.TLabelframe')
        roi_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ROI模式选择
        self.roi_mode = tk.StringVar(value="full")  # full, x_only, y_only, custom
        
        mode_frame = ttk.Frame(roi_frame)
        mode_frame.pack(fill=tk.X, pady=3)
        
        ttk.Radiobutton(mode_frame, text="全部图像", variable=self.roi_mode, 
                        value="full", command=self._on_roi_mode_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="X方向ROI", variable=self.roi_mode, 
                        value="x_only", command=self._on_roi_mode_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Y方向ROI", variable=self.roi_mode, 
                        value="y_only", command=self._on_roi_mode_change).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="自定义ROI", variable=self.roi_mode, 
                        value="custom", command=self._on_roi_mode_change).pack(side=tk.LEFT)
        
        # X方向ROI设置
        self.roi_x_frame = ttk.Frame(roi_frame)
        self.roi_x_frame.pack(fill=tk.X, pady=3)
        
        self.roi_x_start = tk.IntVar(value=0)
        self.roi_x_end = tk.IntVar(value=-1)
        
        ttk.Label(self.roi_x_frame, text="X方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(self.roi_x_frame, text="起始").pack(side=tk.LEFT)
        self.roi_x_start_entry = ttk.Entry(self.roi_x_frame, textvariable=self.roi_x_start, width=6)
        self.roi_x_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.roi_x_frame, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.roi_x_end_entry = ttk.Entry(self.roi_x_frame, textvariable=self.roi_x_end, width=6)
        self.roi_x_end_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.roi_x_frame, text="(-1=图像边缘)", style='Status.TLabel').pack(side=tk.LEFT, padx=5)
        
        # Y方向ROI设置
        self.roi_y_frame = ttk.Frame(roi_frame)
        self.roi_y_frame.pack(fill=tk.X, pady=3)
        
        self.roi_y_start = tk.IntVar(value=0)
        self.roi_y_end = tk.IntVar(value=-1)
        
        ttk.Label(self.roi_y_frame, text="Y方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(self.roi_y_frame, text="起始").pack(side=tk.LEFT)
        self.roi_y_start_entry = ttk.Entry(self.roi_y_frame, textvariable=self.roi_y_start, width=6)
        self.roi_y_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.roi_y_frame, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.roi_y_end_entry = ttk.Entry(self.roi_y_frame, textvariable=self.roi_y_end, width=6)
        self.roi_y_end_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.roi_y_frame, text="(-1=图像边缘)", style='Status.TLabel').pack(side=tk.LEFT, padx=5)
        
        # ROI预览信息
        self.roi_info_label = ttk.Label(roi_frame, text="当前: 使用全部图像", style='Status.TLabel')
        self.roi_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 初始化ROI输入框状态
        self._on_roi_mode_change()
        
        # 操作按钮
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        self.linearity_run_btn = ttk.Button(action_frame, text="▶️ 计算线性度", 
                                             command=self.run_linearity_calc, style='Primary.TButton')
        self.linearity_run_btn.pack(fill=tk.X, pady=5)
        
        self.linearity_progress = ttk.Progressbar(action_frame, mode='indeterminate')
        self.linearity_progress.pack(fill=tk.X, pady=5)
        
        # 右侧：结果
        result_frame = ttk.LabelFrame(right_frame, text="📊 计算结果", padding="10", style='Card.TLabelframe')
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果显示
        self.linearity_result_labels = {}
        
        metrics = [
            ('before_linearity', '补偿前线性度'),
            ('before_max_dev', '补偿前最大偏差'),
            ('before_rms', '补偿前RMS误差'),
            ('before_r2', '补偿前R²'),
            ('after_linearity', '补偿后线性度'),
            ('after_max_dev', '补偿后最大偏差'),
            ('improvement', '改善幅度'),
            ('num_images', '有效图像数'),
        ]
        
        for i, (key, label) in enumerate(metrics):
            row_frame = ttk.Frame(result_frame)
            row_frame.pack(fill=tk.X, pady=3)
            ttk.Label(row_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            value_label = ttk.Label(row_frame, text="--", style='Value.TLabel')
            value_label.pack(side=tk.LEFT)
            self.linearity_result_labels[key] = value_label
        
        # 日志
        log_label = ttk.Label(result_frame, text="详细日志:", style='Status.TLabel')
        log_label.pack(anchor=tk.W, pady=(15, 3))
        
        self.linearity_log = tk.Text(result_frame, height=10, font=('Consolas', 9),
                                      bg='#1e1e1e', fg='#d4d4d4', wrap=tk.WORD)
        self.linearity_log.pack(fill=tk.BOTH, expand=True)
        
        self.linearity_log.tag_configure('info', foreground='#4fc3f7')
        self.linearity_log.tag_configure('success', foreground='#81c784')
        self.linearity_log.tag_configure('header', foreground='#ce93d8')
    
    def browse_model_for_linearity(self):
        """浏览线性度计算的模型文件"""
        filepath = filedialog.askopenfilename(
            title="选择模型文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filepath:
            self.linearity_model_path.set(filepath)
            self.linearity_use_model.set(True)
    
    def _on_full_roi_mode_change(self):
        """完整流程ROI模式变化时的回调"""
        mode = self.full_roi_mode.get()
        
        # 启用/禁用X方向输入
        x_state = 'normal' if mode in ('x_only', 'custom') else 'disabled'
        self.full_roi_x_start_entry.config(state=x_state)
        self.full_roi_x_end_entry.config(state=x_state)
        
        # 启用/禁用Y方向输入
        y_state = 'normal' if mode in ('y_only', 'custom') else 'disabled'
        self.full_roi_y_start_entry.config(state=y_state)
        self.full_roi_y_end_entry.config(state=y_state)
        
        # 更新提示信息
        if mode == 'full':
            self.full_roi_info_label.config(text="当前: 使用全部图像")
        elif mode == 'x_only':
            self.full_roi_info_label.config(text="当前: 仅限制X方向范围，Y方向使用全部")
        elif mode == 'y_only':
            self.full_roi_info_label.config(text="当前: 仅限制Y方向范围，X方向使用全部")
        else:
            self.full_roi_info_label.config(text="当前: 自定义X和Y方向范围")
    
    def _get_full_roi_config(self):
        """获取完整流程的ROI配置"""
        mode = self.full_roi_mode.get()
        
        if mode == 'full':
            return {'x': 0, 'y': 0, 'width': -1, 'height': -1}
        elif mode == 'x_only':
            x_start = self.full_roi_x_start.get()
            x_end = self.full_roi_x_end.get()
            width = -1 if x_end == -1 else (x_end - x_start)
            return {'x': x_start, 'y': 0, 'width': width, 'height': -1}
        elif mode == 'y_only':
            y_start = self.full_roi_y_start.get()
            y_end = self.full_roi_y_end.get()
            height = -1 if y_end == -1 else (y_end - y_start)
            return {'x': 0, 'y': y_start, 'width': -1, 'height': height}
        else:
            x_start = self.full_roi_x_start.get()
            x_end = self.full_roi_x_end.get()
            y_start = self.full_roi_y_start.get()
            y_end = self.full_roi_y_end.get()
            width = -1 if x_end == -1 else (x_end - x_start)
            height = -1 if y_end == -1 else (y_end - y_start)
            return {'x': x_start, 'y': y_start, 'width': width, 'height': height}
    
    def _on_roi_mode_change(self):
        """ROI模式变化时的回调（线性度计算）"""
        mode = self.roi_mode.get()
        
        # 启用/禁用X方向输入
        x_state = 'normal' if mode in ('x_only', 'custom') else 'disabled'
        self.roi_x_start_entry.config(state=x_state)
        self.roi_x_end_entry.config(state=x_state)
        
        # 启用/禁用Y方向输入
        y_state = 'normal' if mode in ('y_only', 'custom') else 'disabled'
        self.roi_y_start_entry.config(state=y_state)
        self.roi_y_end_entry.config(state=y_state)
        
        # 更新提示信息
        if mode == 'full':
            self.roi_info_label.config(text="当前: 使用全部图像")
        elif mode == 'x_only':
            self.roi_info_label.config(text="当前: 仅限制X方向范围，Y方向使用全部")
        elif mode == 'y_only':
            self.roi_info_label.config(text="当前: 仅限制Y方向范围，X方向使用全部")
        else:
            self.roi_info_label.config(text="当前: 自定义X和Y方向范围")
    
    def _get_roi_config(self):
        """获取当前ROI配置"""
        mode = self.roi_mode.get()
        
        if mode == 'full':
            # 使用全部图像
            return {'x': 0, 'y': 0, 'width': -1, 'height': -1}
        elif mode == 'x_only':
            # 仅X方向ROI
            x_start = self.roi_x_start.get()
            x_end = self.roi_x_end.get()
            width = -1 if x_end == -1 else (x_end - x_start)
            return {'x': x_start, 'y': 0, 'width': width, 'height': -1}
        elif mode == 'y_only':
            # 仅Y方向ROI
            y_start = self.roi_y_start.get()
            y_end = self.roi_y_end.get()
            height = -1 if y_end == -1 else (y_end - y_start)
            return {'x': 0, 'y': y_start, 'width': -1, 'height': height}
        else:
            # 自定义ROI
            x_start = self.roi_x_start.get()
            x_end = self.roi_x_end.get()
            y_start = self.roi_y_start.get()
            y_end = self.roi_y_end.get()
            width = -1 if x_end == -1 else (x_end - x_start)
            height = -1 if y_end == -1 else (y_end - y_start)
            return {'x': x_start, 'y': y_start, 'width': width, 'height': height}
    
    def browse_linearity_output(self):
        """浏览线性度输出文件"""
        filepath = filedialog.asksaveasfilename(
            title="保存线性度报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            self.linearity_output_path.set(filepath)
    
    def run_linearity_calc(self):
        """运行线性度计算"""
        test_dir = self.linearity_test_dir.get()
        
        if not test_dir:
            messagebox.showerror("错误", "请选择测试目录")
            return
        if not os.path.exists(test_dir):
            messagebox.showerror("错误", "测试目录不存在")
            return
        
        self.linearity_run_btn.config(state='disabled')
        self.linearity_progress.start(10)
        self.linearity_log.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._run_linearity_thread, daemon=True)
        thread.start()
    
    def _run_linearity_thread(self):
        """线性度计算线程"""
        try:
            from linearity_calc import calculate_batch_linearity
            
            test_dir = self.linearity_test_dir.get()
            model_path = self.linearity_model_path.get() if self.linearity_use_model.get() else None
            output_path = self.linearity_output_path.get()
            full_scale = self.full_scale.get()
            use_filter = self.filter_enabled.get()
            roi_config = self._get_roi_config()
            
            # 获取深度转换系数（线性度计算专用）
            depth_offset = self.linearity_depth_offset.get()
            depth_scale_factor = self.linearity_depth_scale_factor.get()
            
            self.root.after(0, lambda: self._log_linearity("开始计算线性度...", 'header'))
            self.root.after(0, lambda: self._log_linearity(f"测试目录: {test_dir}"))
            self.root.after(0, lambda fs=full_scale: self._log_linearity(f"满量程: {fs} mm"))
            self.root.after(0, lambda: self._log_linearity(f"深度转换: 偏移量={depth_offset}, 缩放因子={depth_scale_factor}"))
            
            # 显示ROI信息
            roi_mode = self.roi_mode.get()
            if roi_mode == 'full':
                self.root.after(0, lambda: self._log_linearity("ROI: 使用全部图像"))
            else:
                roi_str = f"ROI: X=[{roi_config['x']}, {roi_config['x']+roi_config['width'] if roi_config['width']!=-1 else '边缘'}], " \
                          f"Y=[{roi_config['y']}, {roi_config['y']+roi_config['height'] if roi_config['height']!=-1 else '边缘'}]"
                self.root.after(0, lambda s=roi_str: self._log_linearity(s))
            
            result = calculate_batch_linearity(
                test_dir=test_dir,
                model_path=model_path,
                output_path=output_path,
                use_filter=use_filter,
                full_scale=full_scale,
                roi_config=roi_config,
                depth_offset=depth_offset,
                depth_scale_factor=depth_scale_factor
            )
            
            # 更新结果
            before = result['before']
            self.root.after(0, lambda: self.linearity_result_labels['before_linearity'].config(
                text=f"{before['linearity']:.4f}%"))
            self.root.after(0, lambda: self.linearity_result_labels['before_max_dev'].config(
                text=f"{before['abs_max_deviation']:.6f} mm"))
            self.root.after(0, lambda: self.linearity_result_labels['before_rms'].config(
                text=f"{before['rms_error']:.6f} mm"))
            self.root.after(0, lambda: self.linearity_result_labels['before_r2'].config(
                text=f"{before['r_squared']:.8f}"))
            self.root.after(0, lambda: self.linearity_result_labels['num_images'].config(
                text=f"{result['num_images']}"))
            
            if 'after' in result:
                after = result['after']
                self.root.after(0, lambda: self.linearity_result_labels['after_linearity'].config(
                    text=f"{after['linearity']:.4f}%", style='Good.TLabel'))
                self.root.after(0, lambda: self.linearity_result_labels['after_max_dev'].config(
                    text=f"{after['abs_max_deviation']:.6f} mm"))
                self.root.after(0, lambda: self.linearity_result_labels['improvement'].config(
                    text=f"↑ {result['improvement']:.2f}%", style='Good.TLabel'))
            else:
                self.root.after(0, lambda: self.linearity_result_labels['after_linearity'].config(text="--"))
                self.root.after(0, lambda: self.linearity_result_labels['after_max_dev'].config(text="--"))
                self.root.after(0, lambda: self.linearity_result_labels['improvement'].config(text="--"))
            
            self.root.after(0, lambda: self._log_linearity("计算完成！", 'success'))
            self.root.after(0, lambda: self.update_status("线性度计算完成"))
            
            if output_path:
                self.root.after(0, lambda: self._log_linearity(f"结果已保存: {output_path}", 'success'))
            
        except Exception as e:
            import traceback
            self.root.after(0, lambda: self._log_linearity(f"错误: {str(e)}", 'error'))
            self.root.after(0, lambda: self.update_status("计算出错"))
        
        finally:
            self.root.after(0, lambda: self.linearity_run_btn.config(state='normal'))
            self.root.after(0, lambda: self.linearity_progress.stop())
    
    def _log_linearity(self, message, level='info'):
        """添加线性度计算日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.linearity_log.insert(tk.END, f"[{timestamp}] {message}\n", level)
        self.linearity_log.see(tk.END)
    
    # ==================== 标签页4: 重复精度测量 ====================
    
    def create_repeatability_tab(self, parent):
        """创建重复精度测量标签页"""
        # 左右分栏
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=False)
        
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ===== 左侧：配置 =====
        # 数据目录
        dir_frame = ttk.LabelFrame(left_frame, text="📁 测试数据", padding="10", style='Card.TLabelframe')
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.repeat_image_dir = tk.StringVar()
        
        dir_row = ttk.Frame(dir_frame)
        dir_row.pack(fill=tk.X, pady=3)
        ttk.Label(dir_row, text="图像目录:").pack(side=tk.LEFT)
        ttk.Entry(dir_row, textvariable=self.repeat_image_dir, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(dir_row, text="浏览", command=lambda: self.browse_directory(self.repeat_image_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 输出文件
        output_row = ttk.Frame(dir_frame)
        output_row.pack(fill=tk.X, pady=3)
        
        self.repeat_output_path = tk.StringVar(value="output/重复精度报告.txt")
        
        ttk.Label(output_row, text="输出文件:").pack(side=tk.LEFT)
        ttk.Entry(output_row, textvariable=self.repeat_output_path, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_row, text="浏览", command=self.browse_repeat_output,
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 参数设置
        settings_frame = ttk.LabelFrame(left_frame, text="⚙️ 参数设置", padding="10", style='Card.TLabelframe')
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.repeat_use_filter = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="启用滤波处理", 
                        variable=self.repeat_use_filter).pack(anchor=tk.W, pady=3)
        
        # 计算模式
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, pady=3)
        
        self.repeat_calc_mode = tk.StringVar(value="mean")
        ttk.Label(mode_frame, text="计算模式:").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="区域平均值", variable=self.repeat_calc_mode, 
                        value="mean").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="逐像素分析", variable=self.repeat_calc_mode, 
                        value="pixel").pack(side=tk.LEFT)
        
        # 深度转换系数设置
        depth_frame = ttk.Frame(settings_frame)
        depth_frame.pack(fill=tk.X, pady=3)
        ttk.Label(depth_frame, text="深度转换:").pack(side=tk.LEFT)
        ttk.Label(depth_frame, text="偏移量=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_frame, textvariable=self.repeat_depth_offset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(depth_frame, text="缩放因子=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_frame, textvariable=self.repeat_depth_scale_factor, width=6).pack(side=tk.LEFT, padx=2)
        
        # 公式说明
        formula_label = ttk.Label(settings_frame, 
                                   text="公式: y(mm) = (灰度值 - 偏移量) × 缩放因子 / 1000", 
                                   style='Status.TLabel')
        formula_label.pack(anchor=tk.W, pady=(3, 0))
        
        # ROI设置
        roi_frame = ttk.LabelFrame(left_frame, text="📐 ROI设置", padding="10", style='Card.TLabelframe')
        roi_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ROI模式选择
        self.repeat_roi_mode = tk.StringVar(value="full")
        
        mode_row = ttk.Frame(roi_frame)
        mode_row.pack(fill=tk.X, pady=3)
        
        ttk.Radiobutton(mode_row, text="全部图像", variable=self.repeat_roi_mode, 
                        value="full", command=self._on_repeat_roi_mode_change).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(mode_row, text="X方向ROI", variable=self.repeat_roi_mode, 
                        value="x_only", command=self._on_repeat_roi_mode_change).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(mode_row, text="Y方向ROI", variable=self.repeat_roi_mode, 
                        value="y_only", command=self._on_repeat_roi_mode_change).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(mode_row, text="自定义", variable=self.repeat_roi_mode, 
                        value="custom", command=self._on_repeat_roi_mode_change).pack(side=tk.LEFT)
        
        # X方向ROI
        self.repeat_roi_x_frame = ttk.Frame(roi_frame)
        self.repeat_roi_x_frame.pack(fill=tk.X, pady=3)
        
        self.repeat_roi_x_start = tk.IntVar(value=0)
        self.repeat_roi_x_end = tk.IntVar(value=-1)
        
        ttk.Label(self.repeat_roi_x_frame, text="X方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(self.repeat_roi_x_frame, text="起始").pack(side=tk.LEFT)
        self.repeat_roi_x_start_entry = ttk.Entry(self.repeat_roi_x_frame, textvariable=self.repeat_roi_x_start, width=6)
        self.repeat_roi_x_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.repeat_roi_x_frame, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.repeat_roi_x_end_entry = ttk.Entry(self.repeat_roi_x_frame, textvariable=self.repeat_roi_x_end, width=6)
        self.repeat_roi_x_end_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.repeat_roi_x_frame, text="(-1=边缘)", style='Status.TLabel').pack(side=tk.LEFT, padx=3)
        
        # Y方向ROI
        self.repeat_roi_y_frame = ttk.Frame(roi_frame)
        self.repeat_roi_y_frame.pack(fill=tk.X, pady=3)
        
        self.repeat_roi_y_start = tk.IntVar(value=0)
        self.repeat_roi_y_end = tk.IntVar(value=-1)
        
        ttk.Label(self.repeat_roi_y_frame, text="Y方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(self.repeat_roi_y_frame, text="起始").pack(side=tk.LEFT)
        self.repeat_roi_y_start_entry = ttk.Entry(self.repeat_roi_y_frame, textvariable=self.repeat_roi_y_start, width=6)
        self.repeat_roi_y_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.repeat_roi_y_frame, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.repeat_roi_y_end_entry = ttk.Entry(self.repeat_roi_y_frame, textvariable=self.repeat_roi_y_end, width=6)
        self.repeat_roi_y_end_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(self.repeat_roi_y_frame, text="(-1=边缘)", style='Status.TLabel').pack(side=tk.LEFT, padx=3)
        
        # ROI提示
        self.repeat_roi_info_label = ttk.Label(roi_frame, text="当前: 使用全部图像", style='Status.TLabel')
        self.repeat_roi_info_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 初始化ROI输入框状态
        self._on_repeat_roi_mode_change()
        
        # 操作按钮
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        self.repeat_run_btn = ttk.Button(action_frame, text="▶️ 计算重复精度", 
                                          command=self.run_repeatability_calc, style='Primary.TButton')
        self.repeat_run_btn.pack(fill=tk.X, pady=5)
        
        self.repeat_progress = ttk.Progressbar(action_frame, mode='indeterminate')
        self.repeat_progress.pack(fill=tk.X, pady=5)
        
        # ===== 右侧：结果 =====
        result_frame = ttk.LabelFrame(right_frame, text="📊 计算结果", padding="10", style='Card.TLabelframe')
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果显示
        self.repeat_result_labels = {}
        
        metrics = [
            ('num_images', '图像数量'),
            ('mean_depth', '平均深度'),
            ('std_1sigma', '标准差(1σ)'),
            ('repeat_3sigma', '重复精度(±3σ)'),
            ('repeat_6sigma', '重复精度(6σ)'),
            ('peak_to_peak', '极差(P-P)'),
            ('intra_std', '图像内标准差'),
        ]
        
        for i, (key, label) in enumerate(metrics):
            row_frame = ttk.Frame(result_frame)
            row_frame.pack(fill=tk.X, pady=3)
            ttk.Label(row_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            value_label = ttk.Label(row_frame, text="--", style='Value.TLabel')
            value_label.pack(side=tk.LEFT)
            self.repeat_result_labels[key] = value_label
        
        # 分隔线
        ttk.Separator(result_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 日志
        log_label = ttk.Label(result_frame, text="详细日志:", style='Status.TLabel')
        log_label.pack(anchor=tk.W, pady=(5, 3))
        
        self.repeat_log = tk.Text(result_frame, height=12, font=('Consolas', 9),
                                   bg='#1e1e1e', fg='#d4d4d4', wrap=tk.WORD)
        self.repeat_log.pack(fill=tk.BOTH, expand=True)
        
        self.repeat_log.tag_configure('info', foreground='#4fc3f7')
        self.repeat_log.tag_configure('success', foreground='#81c784')
        self.repeat_log.tag_configure('header', foreground='#ce93d8')
        self.repeat_log.tag_configure('error', foreground='#e57373')
    
    def _on_repeat_roi_mode_change(self):
        """重复精度ROI模式变化时的回调"""
        mode = self.repeat_roi_mode.get()
        
        # 启用/禁用X方向输入
        x_state = 'normal' if mode in ('x_only', 'custom') else 'disabled'
        self.repeat_roi_x_start_entry.config(state=x_state)
        self.repeat_roi_x_end_entry.config(state=x_state)
        
        # 启用/禁用Y方向输入
        y_state = 'normal' if mode in ('y_only', 'custom') else 'disabled'
        self.repeat_roi_y_start_entry.config(state=y_state)
        self.repeat_roi_y_end_entry.config(state=y_state)
        
        # 更新提示信息
        if mode == 'full':
            self.repeat_roi_info_label.config(text="当前: 使用全部图像")
        elif mode == 'x_only':
            self.repeat_roi_info_label.config(text="当前: 仅限制X方向范围")
        elif mode == 'y_only':
            self.repeat_roi_info_label.config(text="当前: 仅限制Y方向范围")
        else:
            self.repeat_roi_info_label.config(text="当前: 自定义X和Y方向范围")
    
    def _get_repeat_roi_config(self):
        """获取重复精度测量的ROI配置"""
        mode = self.repeat_roi_mode.get()
        
        if mode == 'full':
            return {'x': 0, 'y': 0, 'width': -1, 'height': -1}
        elif mode == 'x_only':
            x_start = self.repeat_roi_x_start.get()
            x_end = self.repeat_roi_x_end.get()
            width = -1 if x_end == -1 else (x_end - x_start)
            return {'x': x_start, 'y': 0, 'width': width, 'height': -1}
        elif mode == 'y_only':
            y_start = self.repeat_roi_y_start.get()
            y_end = self.repeat_roi_y_end.get()
            height = -1 if y_end == -1 else (y_end - y_start)
            return {'x': 0, 'y': y_start, 'width': -1, 'height': height}
        else:
            x_start = self.repeat_roi_x_start.get()
            x_end = self.repeat_roi_x_end.get()
            y_start = self.repeat_roi_y_start.get()
            y_end = self.repeat_roi_y_end.get()
            width = -1 if x_end == -1 else (x_end - x_start)
            height = -1 if y_end == -1 else (y_end - y_start)
            return {'x': x_start, 'y': y_start, 'width': width, 'height': height}
    
    def browse_repeat_output(self):
        """浏览重复精度输出文件"""
        filepath = filedialog.asksaveasfilename(
            title="保存重复精度报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            self.repeat_output_path.set(filepath)
    
    def run_repeatability_calc(self):
        """运行重复精度计算"""
        image_dir = self.repeat_image_dir.get()
        
        if not image_dir:
            messagebox.showerror("错误", "请选择图像目录")
            return
        if not os.path.exists(image_dir):
            messagebox.showerror("错误", "图像目录不存在")
            return
        
        self.repeat_run_btn.config(state='disabled')
        self.repeat_progress.start(10)
        self.repeat_log.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._run_repeatability_thread, daemon=True)
        thread.start()
    
    def _run_repeatability_thread(self):
        """重复精度计算线程"""
        try:
            from repeatability_calc import calculate_repeatability
            
            image_dir = self.repeat_image_dir.get()
            output_path = self.repeat_output_path.get()
            use_filter = self.repeat_use_filter.get()
            calc_mode = self.repeat_calc_mode.get()
            roi_config = self._get_repeat_roi_config()
            
            # 获取深度转换系数（重复精度计算专用）
            depth_offset = self.repeat_depth_offset.get()
            depth_scale_factor = self.repeat_depth_scale_factor.get()
            
            self.root.after(0, lambda: self._log_repeat("开始计算重复精度...", 'header'))
            self.root.after(0, lambda: self._log_repeat(f"图像目录: {image_dir}"))
            self.root.after(0, lambda: self._log_repeat(f"深度转换: 偏移量={depth_offset}, 缩放因子={depth_scale_factor}"))
            
            # 显示ROI信息
            roi_mode = self.repeat_roi_mode.get()
            if roi_mode == 'full':
                self.root.after(0, lambda: self._log_repeat("ROI: 使用全部图像"))
            else:
                roi_str = f"ROI: X=[{roi_config['x']}, {roi_config['x']+roi_config['width'] if roi_config['width']!=-1 else '边缘'}], " \
                          f"Y=[{roi_config['y']}, {roi_config['y']+roi_config['height'] if roi_config['height']!=-1 else '边缘'}]"
                self.root.after(0, lambda s=roi_str: self._log_repeat(s))
            
            result = calculate_repeatability(
                image_dir=image_dir,
                output_path=output_path,
                use_filter=use_filter,
                roi_config=roi_config,
                calc_mode=calc_mode,
                depth_offset=depth_offset,
                depth_scale_factor=depth_scale_factor
            )
            
            # 更新结果
            self.root.after(0, lambda: self.repeat_result_labels['num_images'].config(
                text=f"{result['num_images']}"))
            self.root.after(0, lambda: self.repeat_result_labels['mean_depth'].config(
                text=f"{result['mean_depth']:.6f} mm"))
            self.root.after(0, lambda: self.repeat_result_labels['std_1sigma'].config(
                text=f"{result['std_1sigma']:.6f} mm ({result['std_1sigma']*1000:.3f} μm)"))
            self.root.after(0, lambda: self.repeat_result_labels['repeat_3sigma'].config(
                text=f"±{result['repeatability_3sigma']:.6f} mm (±{result['repeatability_3sigma']*1000:.3f} μm)", 
                style='Good.TLabel'))
            self.root.after(0, lambda: self.repeat_result_labels['repeat_6sigma'].config(
                text=f"{result['repeatability_6sigma']:.6f} mm ({result['repeatability_6sigma']*1000:.3f} μm)"))
            self.root.after(0, lambda: self.repeat_result_labels['peak_to_peak'].config(
                text=f"{result['peak_to_peak']:.6f} mm ({result['peak_to_peak']*1000:.3f} μm)"))
            self.root.after(0, lambda: self.repeat_result_labels['intra_std'].config(
                text=f"{result['avg_intra_image_std']:.6f} mm ({result['avg_intra_image_std']*1000:.3f} μm)"))
            
            self.root.after(0, lambda: self._log_repeat("计算完成！", 'success'))
            self.root.after(0, lambda: self._log_repeat(f"重复精度(±3σ): ±{result['repeatability_3sigma']*1000:.3f} μm", 'success'))
            self.root.after(0, lambda: self.update_status("重复精度计算完成"))
            
            if output_path:
                self.root.after(0, lambda: self._log_repeat(f"报告已保存: {output_path}", 'success'))
            
        except Exception as e:
            import traceback
            self.root.after(0, lambda: self._log_repeat(f"错误: {str(e)}", 'error'))
            self.root.after(0, lambda: self.update_status("计算出错"))
            traceback.print_exc()
        
        finally:
            self.root.after(0, lambda: self.repeat_run_btn.config(state='normal'))
            self.root.after(0, lambda: self.repeat_progress.stop())
    
    def _log_repeat(self, message, level='info'):
        """添加重复精度计算日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.repeat_log.insert(tk.END, f"[{timestamp}] {message}\n", level)
        self.repeat_log.see(tk.END)
    
    # ==================== 标签页5: X位置重复精度 ====================
    
    def create_x_repeatability_tab(self, parent):
        """创建X位置重复精度标签页"""
        # 左右分栏
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10), expand=False)
        
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ===== 左侧：配置 =====
        # 数据目录
        dir_frame = ttk.LabelFrame(left_frame, text="📁 测试数据", padding="10", style='Card.TLabelframe')
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.x_repeat_image_dir = tk.StringVar()
        
        dir_row = ttk.Frame(dir_frame)
        dir_row.pack(fill=tk.X, pady=3)
        ttk.Label(dir_row, text="图像目录:").pack(side=tk.LEFT)
        ttk.Entry(dir_row, textvariable=self.x_repeat_image_dir, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(dir_row, text="浏览", command=lambda: self.browse_directory(self.x_repeat_image_dir),
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 输出文件
        output_row = ttk.Frame(dir_frame)
        output_row.pack(fill=tk.X, pady=3)
        
        self.x_repeat_output_path = tk.StringVar(value="output/X位置重复精度报告.txt")
        
        ttk.Label(output_row, text="输出文件:").pack(side=tk.LEFT)
        ttk.Entry(output_row, textvariable=self.x_repeat_output_path, width=30).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_row, text="浏览", command=self.browse_x_repeat_output,
                   style='Secondary.TButton').pack(side=tk.LEFT)
        
        # 参数设置
        settings_frame = ttk.LabelFrame(left_frame, text="⚙️ 参数设置", padding="10", style='Card.TLabelframe')
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 空间分辨率
        res_row = ttk.Frame(settings_frame)
        res_row.pack(fill=tk.X, pady=3)
        ttk.Label(res_row, text="空间分辨率:").pack(side=tk.LEFT)
        ttk.Entry(res_row, textvariable=self.x_repeat_spatial_res, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(res_row, text="mm/pixel").pack(side=tk.LEFT)
        
        # 深度转换
        depth_row = ttk.Frame(settings_frame)
        depth_row.pack(fill=tk.X, pady=3)
        ttk.Label(depth_row, text="深度转换:").pack(side=tk.LEFT)
        ttk.Label(depth_row, text="偏移=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_row, textvariable=self.x_repeat_depth_offset, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(depth_row, text="缩放=").pack(side=tk.LEFT, padx=(5, 0))
        ttk.Entry(depth_row, textvariable=self.x_repeat_depth_scale, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(depth_row, text="μm/count").pack(side=tk.LEFT)
        
        # 拟合类型
        fit_row = ttk.Frame(settings_frame)
        fit_row.pack(fill=tk.X, pady=3)
        ttk.Label(fit_row, text="拟合类型:").pack(side=tk.LEFT)
        ttk.Radiobutton(fit_row, text="椭圆拟合", variable=self.x_repeat_fit_type, 
                        value="ellipse", command=self._on_x_repeat_fit_type_change).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(fit_row, text="圆拟合", variable=self.x_repeat_fit_type, 
                        value="circle", command=self._on_x_repeat_fit_type_change).pack(side=tk.LEFT)
        
        # 固定直径（仅圆拟合）
        diameter_row = ttk.Frame(settings_frame)
        diameter_row.pack(fill=tk.X, pady=3)
        ttk.Label(diameter_row, text="固定直径:").pack(side=tk.LEFT)
        self.x_repeat_diameter_entry = ttk.Entry(diameter_row, textvariable=self.x_repeat_fixed_diameter, width=10)
        self.x_repeat_diameter_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(diameter_row, text="mm (0=自动拟合)").pack(side=tk.LEFT)
        self.x_repeat_diameter_entry.config(state='disabled')
        
        # ROI设置
        roi_frame = ttk.LabelFrame(left_frame, text="📐 ROI设置", padding="10", style='Card.TLabelframe')
        roi_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(roi_frame, text="使用动态ROI（自动检测有效区域）", 
                        variable=self.x_repeat_use_dynamic_roi,
                        command=self._on_x_repeat_roi_mode_change).pack(anchor=tk.W, pady=3)
        
        # 手动ROI设置
        self.x_repeat_roi_manual_frame = ttk.Frame(roi_frame)
        self.x_repeat_roi_manual_frame.pack(fill=tk.X, pady=3)
        
        self.x_repeat_roi_x_start = tk.IntVar(value=0)
        self.x_repeat_roi_x_end = tk.IntVar(value=-1)
        self.x_repeat_roi_y_start = tk.IntVar(value=0)
        self.x_repeat_roi_y_end = tk.IntVar(value=-1)
        
        # X方向
        x_row = ttk.Frame(self.x_repeat_roi_manual_frame)
        x_row.pack(fill=tk.X, pady=2)
        ttk.Label(x_row, text="X方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(x_row, text="起始").pack(side=tk.LEFT)
        self.x_repeat_roi_x_start_entry = ttk.Entry(x_row, textvariable=self.x_repeat_roi_x_start, width=6)
        self.x_repeat_roi_x_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(x_row, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.x_repeat_roi_x_end_entry = ttk.Entry(x_row, textvariable=self.x_repeat_roi_x_end, width=6)
        self.x_repeat_roi_x_end_entry.pack(side=tk.LEFT, padx=2)
        
        # Y方向
        y_row = ttk.Frame(self.x_repeat_roi_manual_frame)
        y_row.pack(fill=tk.X, pady=2)
        ttk.Label(y_row, text="Y方向:", width=8).pack(side=tk.LEFT)
        ttk.Label(y_row, text="起始").pack(side=tk.LEFT)
        self.x_repeat_roi_y_start_entry = ttk.Entry(y_row, textvariable=self.x_repeat_roi_y_start, width=6)
        self.x_repeat_roi_y_start_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(y_row, text="结束").pack(side=tk.LEFT, padx=(10, 0))
        self.x_repeat_roi_y_end_entry = ttk.Entry(y_row, textvariable=self.x_repeat_roi_y_end, width=6)
        self.x_repeat_roi_y_end_entry.pack(side=tk.LEFT, padx=2)
        
        # 初始化ROI状态
        self._on_x_repeat_roi_mode_change()
        
        # 操作按钮
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        self.x_repeat_run_btn = ttk.Button(action_frame, text="▶️ 计算X位置重复精度", 
                                           command=self.run_x_repeatability_calc, style='Primary.TButton')
        self.x_repeat_run_btn.pack(fill=tk.X, pady=5)
        
        self.x_repeat_progress = ttk.Progressbar(action_frame, mode='indeterminate')
        self.x_repeat_progress.pack(fill=tk.X, pady=5)
        
        # ===== 右侧：结果 =====
        result_frame = ttk.LabelFrame(right_frame, text="📊 计算结果", padding="10", style='Card.TLabelframe')
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 结果显示 - X方向
        x_result_frame = ttk.LabelFrame(result_frame, text="X方向位置重复精度", padding="5")
        x_result_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.x_repeat_result_labels = {}
        
        x_metrics = [
            ('x_mean', '平均位置'),
            ('x_1sigma', '标准差(1σ)'),
            ('x_3sigma', '重复精度(±3σ)'),
            ('x_6sigma', '重复精度(6σ)'),
            ('x_pv', '极差(P-V)'),
        ]
        
        for key, label in x_metrics:
            row_frame = ttk.Frame(x_result_frame)
            row_frame.pack(fill=tk.X, pady=2)
            ttk.Label(row_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            value_label = ttk.Label(row_frame, text="--", style='Value.TLabel')
            value_label.pack(side=tk.LEFT)
            self.x_repeat_result_labels[key] = value_label
        
        # 结果显示 - Z方向
        z_result_frame = ttk.LabelFrame(result_frame, text="Z方向（深度）重复精度", padding="5")
        z_result_frame.pack(fill=tk.X, pady=(0, 10))
        
        z_metrics = [
            ('z_mean', '平均深度'),
            ('z_1sigma', '标准差(1σ)'),
            ('z_3sigma', '重复精度(±3σ)'),
            ('z_6sigma', '重复精度(6σ)'),
            ('z_pv', '极差(P-V)'),
        ]
        
        for key, label in z_metrics:
            row_frame = ttk.Frame(z_result_frame)
            row_frame.pack(fill=tk.X, pady=2)
            ttk.Label(row_frame, text=f"{label}:", width=15).pack(side=tk.LEFT)
            value_label = ttk.Label(row_frame, text="--", style='Value.TLabel')
            value_label.pack(side=tk.LEFT)
            self.x_repeat_result_labels[key] = value_label
        
        # 统计信息
        stats_row = ttk.Frame(result_frame)
        stats_row.pack(fill=tk.X, pady=5)
        ttk.Label(stats_row, text="图像统计:", width=15).pack(side=tk.LEFT)
        self.x_repeat_result_labels['stats'] = ttk.Label(stats_row, text="--", style='Value.TLabel')
        self.x_repeat_result_labels['stats'].pack(side=tk.LEFT)
        
        # 分隔线
        ttk.Separator(result_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 日志
        log_label = ttk.Label(result_frame, text="详细日志:", style='Status.TLabel')
        log_label.pack(anchor=tk.W, pady=(5, 3))
        
        self.x_repeat_log = tk.Text(result_frame, height=10, font=('Consolas', 9),
                                    bg='#1e1e1e', fg='#d4d4d4', wrap=tk.WORD)
        self.x_repeat_log.pack(fill=tk.BOTH, expand=True)
        
        self.x_repeat_log.tag_configure('info', foreground='#4fc3f7')
        self.x_repeat_log.tag_configure('success', foreground='#81c784')
        self.x_repeat_log.tag_configure('header', foreground='#ce93d8')
        self.x_repeat_log.tag_configure('error', foreground='#e57373')
        self.x_repeat_log.tag_configure('warning', foreground='#ffb74d')
    
    def _on_x_repeat_fit_type_change(self):
        """X位置重复精度拟合类型变化回调"""
        fit_type = self.x_repeat_fit_type.get()
        if fit_type == 'circle':
            self.x_repeat_diameter_entry.config(state='normal')
        else:
            self.x_repeat_diameter_entry.config(state='disabled')
    
    def _on_x_repeat_roi_mode_change(self):
        """X位置重复精度ROI模式变化回调"""
        use_dynamic = self.x_repeat_use_dynamic_roi.get()
        state = 'disabled' if use_dynamic else 'normal'
        
        self.x_repeat_roi_x_start_entry.config(state=state)
        self.x_repeat_roi_x_end_entry.config(state=state)
        self.x_repeat_roi_y_start_entry.config(state=state)
        self.x_repeat_roi_y_end_entry.config(state=state)
    
    def browse_x_repeat_output(self):
        """浏览X位置重复精度输出文件"""
        filepath = filedialog.asksaveasfilename(
            title="保存X位置重复精度报告",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            self.x_repeat_output_path.set(filepath)
    
    def run_x_repeatability_calc(self):
        """运行X位置重复精度计算"""
        image_dir = self.x_repeat_image_dir.get()
        
        if not image_dir or not os.path.isdir(image_dir):
            messagebox.showerror("错误", "请选择有效的图像目录")
            return
        
        self.x_repeat_run_btn.config(state='disabled')
        self.x_repeat_progress.start()
        self.x_repeat_log.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self._run_x_repeatability_thread, daemon=True)
        thread.start()
    
    def _run_x_repeatability_thread(self):
        """X位置重复精度计算线程"""
        try:
            from x_repeatability import (get_image_files, calculate_x_repeatability_by_shape,
                                          save_x_repeatability_report)
            
            image_dir = self.x_repeat_image_dir.get()
            output_path = self.x_repeat_output_path.get()
            
            # 获取参数
            spatial_res = self.x_repeat_spatial_res.get()
            depth_offset = self.x_repeat_depth_offset.get()
            depth_scale = self.x_repeat_depth_scale.get()
            fit_type = self.x_repeat_fit_type.get()
            fixed_diameter = self.x_repeat_fixed_diameter.get() if fit_type == 'circle' else 0.0
            use_dynamic_roi = self.x_repeat_use_dynamic_roi.get()
            
            self.root.after(0, lambda: self._log_x_repeat("开始计算X位置重复精度...", 'header'))
            self.root.after(0, lambda: self._log_x_repeat(f"图像目录: {image_dir}"))
            self.root.after(0, lambda: self._log_x_repeat(f"拟合类型: {fit_type}"))
            self.root.after(0, lambda: self._log_x_repeat(f"空间分辨率: {spatial_res} mm/pixel"))
            self.root.after(0, lambda: self._log_x_repeat(f"深度转换: 偏移={depth_offset}, 缩放={depth_scale} μm/count"))
            
            # 获取图像文件
            image_files = get_image_files(image_dir)
            if not image_files:
                raise FileNotFoundError(f"未找到图像文件: {image_dir}")
            
            self.root.after(0, lambda: self._log_x_repeat(f"找到 {len(image_files)} 张图像"))
            
            # 配置ROI
            roi = None
            if not use_dynamic_roi:
                x_start = self.x_repeat_roi_x_start.get()
                x_end = self.x_repeat_roi_x_end.get()
                y_start = self.x_repeat_roi_y_start.get()
                y_end = self.x_repeat_roi_y_end.get()
                roi = (x_start, x_end, y_start, y_end)
                self.root.after(0, lambda: self._log_x_repeat(f"使用手动ROI: X=[{x_start},{x_end}], Y=[{y_start},{y_end}]"))
            else:
                self.root.after(0, lambda: self._log_x_repeat("使用动态ROI（自动检测有效区域）"))
            
            # 执行计算
            self.root.after(0, lambda: self._log_x_repeat("正在拟合...", 'info'))
            
            results, statistics = calculate_x_repeatability_by_shape(
                image_files=image_files,
                roi=roi,
                spatial_resolution=spatial_res,
                fit_type=fit_type,
                depth_offset=depth_offset,
                depth_scale=depth_scale,
                fixed_diameter_mm=fixed_diameter
            )
            
            if statistics is None:
                raise ValueError("没有成功拟合的图像")
            
            # 更新结果显示
            self.root.after(0, lambda: self.x_repeat_result_labels['x_mean'].config(
                text=f"{statistics['x_mean_mm']:.6f} mm"))
            self.root.after(0, lambda: self.x_repeat_result_labels['x_1sigma'].config(
                text=f"{statistics['x_1sigma_um']:.3f} μm"))
            self.root.after(0, lambda: self.x_repeat_result_labels['x_3sigma'].config(
                text=f"±{statistics['x_3sigma_um']:.3f} μm", style='Good.TLabel'))
            self.root.after(0, lambda: self.x_repeat_result_labels['x_6sigma'].config(
                text=f"{statistics['x_6sigma_um']:.3f} μm"))
            self.root.after(0, lambda: self.x_repeat_result_labels['x_pv'].config(
                text=f"{statistics['x_pv_um']:.3f} μm"))
            
            self.root.after(0, lambda: self.x_repeat_result_labels['z_mean'].config(
                text=f"{statistics['z_mean_mm']:.6f} mm"))
            self.root.after(0, lambda: self.x_repeat_result_labels['z_1sigma'].config(
                text=f"{statistics['z_1sigma_um']:.3f} μm"))
            self.root.after(0, lambda: self.x_repeat_result_labels['z_3sigma'].config(
                text=f"±{statistics['z_3sigma_um']:.3f} μm", style='Good.TLabel'))
            self.root.after(0, lambda: self.x_repeat_result_labels['z_6sigma'].config(
                text=f"{statistics['z_6sigma_um']:.3f} μm"))
            self.root.after(0, lambda: self.x_repeat_result_labels['z_pv'].config(
                text=f"{statistics['z_pv_um']:.3f} μm"))
            
            self.root.after(0, lambda: self.x_repeat_result_labels['stats'].config(
                text=f"成功: {statistics['n_success']}/{statistics['n_total']}"))
            
            # 日志输出
            self.root.after(0, lambda: self._log_x_repeat("=" * 40, 'header'))
            self.root.after(0, lambda: self._log_x_repeat("计算完成！", 'success'))
            self.root.after(0, lambda: self._log_x_repeat(f"X方向重复精度(±3σ): ±{statistics['x_3sigma_um']:.3f} μm", 'success'))
            self.root.after(0, lambda: self._log_x_repeat(f"Z方向重复精度(±3σ): ±{statistics['z_3sigma_um']:.3f} μm", 'success'))
            
            # 保存报告
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True) if os.path.dirname(output_path) else None
                save_x_repeatability_report(output_path, results, statistics)
                self.root.after(0, lambda: self._log_x_repeat(f"报告已保存: {output_path}", 'success'))
            
            self.root.after(0, lambda: self.update_status("X位置重复精度计算完成"))
            
        except Exception as e:
            import traceback
            self.root.after(0, lambda: self._log_x_repeat(f"错误: {str(e)}", 'error'))
            self.root.after(0, lambda: self.update_status("计算出错"))
            traceback.print_exc()
        
        finally:
            self.root.after(0, lambda: self.x_repeat_run_btn.config(state='normal'))
            self.root.after(0, lambda: self.x_repeat_progress.stop())
    
    def _log_x_repeat(self, message, level='info'):
        """添加X位置重复精度计算日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.x_repeat_log.insert(tk.END, f"[{timestamp}] {message}\n", level)
        self.x_repeat_log.see(tk.END)
    
    def _on_normalize_toggle(self):
        """归一化开关切换时的回调"""
        enabled = self.normalize_enabled.get()
        state = 'normal' if enabled else 'disabled'
        
        self.normalize_center_entry.config(state=state)
        self.normalize_auto_cb.config(state=state)
        
        if enabled:
            self._on_normalize_auto_toggle()
        else:
            self.normalize_manual_entry.config(state='disabled')
    
    def _on_normalize_auto_toggle(self):
        """自动计算偏移量开关切换时的回调"""
        if not self.normalize_enabled.get():
            return
        
        auto = self.normalize_auto_offset.get()
        self.normalize_manual_entry.config(state='disabled' if auto else 'normal')
        
        # 如果模型已加载且启用自动计算，更新计算结果
        if auto and self.model_loaded:
            self._update_normalize_info()
    
    def _update_normalize_info(self):
        """更新归一化信息显示"""
        if not self.model_loaded:
            self.normalize_calculated_offset.set("--")
            self.normalize_range_label.config(text="--")
            return
        
        try:
            from compensator import calculate_normalization_offset
            
            target_center = self.normalize_target_center.get()
            offset = calculate_normalization_offset(self.model, target_center)
            
            self.normalize_calculated_offset.set(f"{offset:.4f} mm")
            
            y_min, y_max = self.model['actual_range']
            norm_min = y_min + offset
            norm_max = y_max + offset
            self.normalize_range_label.config(text=f"[{norm_min:.2f}, {norm_max:.2f}] mm")
            
        except Exception as e:
            self.normalize_calculated_offset.set("计算失败")
            self.normalize_range_label.config(text="--")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """深度图补偿系统 v2.2 使用说明

【完整流程标签页】
用于从标定数据建立补偿模型，并补偿测试数据。
1. 选择标定目录（包含标定图像和CSV）
2. 选择测试目录
3. 点击"开始标定"
→ 模型自动保存为 compensation_model.json

【补偿模式标签页】
用于加载已有模型进行补偿。
• 加载模型：选择 .json 模型文件后点击"加载模型"
• 批量补偿：选择输入目录，补偿目录中所有PNG图像
• 单个补偿：选择单张图像进行补偿
• 输出归一化：将补偿输出范围平移到以目标中心为中心

【线性度计算标签页】
计算深度图的线性度指标。
• 支持ROI区域设置（X方向/Y方向/自定义）
• 可选择是否使用补偿模型

【重复精度测量标签页】
测量Z方向（深度）的重复精度。
• 选择包含多张同一位置深度图的目录
• 支持ROI区域设置
• 深度公式: y(mm) = (灰度值-偏移量)×缩放因子/1000
• 输出：标准差、±3σ重复精度、极差等

【X位置重复精度标签页】
通过圆/椭圆拟合测量X方向位置重复精度。
• 支持圆拟合和椭圆拟合两种方式
• 可设置固定圆直径约束（仅圆拟合）
• 支持动态ROI（自动检测有效区域）或手动ROI
• 输出：X方向和Z方向的1σ/3σ/6σ/PV值

【输出归一化】
• 自动计算偏移量：根据模型输出范围自动计算
• 公式：offset = target_center - (y_min + y_max) / 2
• 归一化后：compensated_value + offset

【数据格式】
• 图像：16位PNG深度图
• 模型：.json 格式（自动生成）
"""
        messagebox.showinfo("帮助", help_text)
    
    # ==================== 模型加载 ====================
    
    def load_model(self):
        """加载补偿模型"""
        model_path = self.model_path.get()
        
        if not model_path:
            messagebox.showerror("错误", "请选择模型文件")
            return
        
        if not os.path.exists(model_path):
            messagebox.showerror("错误", f"模型文件不存在：{model_path}")
            return
        
        try:
            from compensator import load_model
            
            self.model = load_model(model_path)
            self.model_loaded = True
            
            # 更新状态
            num_points = len(self.model['actual_values'])
            actual_range = self.model['actual_range']
            measured_range = self.model['measured_range']
            
            self.model_status_label.config(text="✅ 模型已加载", style='ModelLoaded.TLabel')
            self.model_info_label.config(
                text=f"标定点: {num_points} | 范围: [{actual_range[0]:.1f}, {actual_range[1]:.1f}] mm"
            )
            
            # 更新归一化信息
            self._update_normalize_info()
            
            self.update_status(f"模型加载成功: {os.path.basename(model_path)}")
            messagebox.showinfo("成功", f"模型加载成功！\n标定点数: {num_points}\n实际值范围: [{actual_range[0]:.2f}, {actual_range[1]:.2f}] mm")
            
        except Exception as e:
            self.model_loaded = False
            self.model = None
            self.model_status_label.config(text="❌ 加载失败", style='ModelNotLoaded.TLabel')
            self.model_info_label.config(text="")
            self.normalize_calculated_offset.set("--")
            self.normalize_range_label.config(text="--")
            messagebox.showerror("错误", f"模型加载失败：{str(e)}")
    
    # ==================== 完整流程运行 ====================
    
    def run_full_compensation(self):
        """运行完整补偿流程"""
        if self.is_running:
            return
        
        # 验证输入
        if not self.calib_dir.get():
            messagebox.showerror("错误", "请选择标定目录")
            return
        if not self.test_dir.get():
            messagebox.showerror("错误", "请选择测试目录")
            return
        if not os.path.exists(self.calib_dir.get()):
            messagebox.showerror("错误", "标定目录不存在")
            return
        if not os.path.exists(self.test_dir.get()):
            messagebox.showerror("错误", "测试目录不存在")
            return
        
        self.is_running = True
        self.full_run_btn.config(state='disabled')
        self.full_progress.start(10)
        self.clear_log('full')
        
        thread = threading.Thread(target=self._run_full_thread, daemon=True)
        thread.start()
    
    def _run_full_thread(self):
        """完整流程线程"""
        try:
            from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm, detect_anomalies
            from calibrator import calibrate_image
            from compensator import (build_compensation_model, apply_compensation,
                                    calculate_compensation_effect, save_model)
            import numpy as np
            
            calib_dir = self.calib_dir.get()
            test_dir = self.test_dir.get()
            output_dir = self.output_dir.get()
            use_filter = self.filter_enabled.get()
            outlier_std = self.outlier_std.get()
            median_size = self.median_size.get()
            
            # 获取深度转换系数
            depth_offset = self.depth_offset.get()
            depth_scale_factor = self.depth_scale_factor.get()
            
            # 获取ROI配置
            roi_config = self._get_full_roi_config()
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 步骤1: 处理标定数据
            self.root.after(0, lambda: self.log("=" * 50, 'header', 'full'))
            self.root.after(0, lambda: self.log("步骤1: 处理标定数据", 'header', 'full'))
            self.root.after(0, lambda: self.update_status("正在处理标定数据..."))
            
            # 显示深度转换系数
            self.root.after(0, lambda: self.log(f"深度转换: 偏移量={depth_offset}, 缩放因子={depth_scale_factor}", 'info', 'full'))
            
            # 显示ROI信息
            if roi_config['width'] == -1 and roi_config['height'] == -1 and roi_config['x'] == 0 and roi_config['y'] == 0:
                self.root.after(0, lambda: self.log("ROI: 使用全部图像", 'info', 'full'))
            else:
                roi_str = f"ROI: X=[{roi_config['x']}, {'边缘' if roi_config['width']==-1 else roi_config['x']+roi_config['width']}], "
                roi_str += f"Y=[{roi_config['y']}, {'边缘' if roi_config['height']==-1 else roi_config['y']+roi_config['height']}]"
                self.root.after(0, lambda s=roi_str: self.log(s, 'info', 'full'))
            
            if use_filter:
                self.root.after(0, lambda: self.log(f"滤波参数: 异常值阈值={outlier_std}σ, 中值窗口={median_size}×{median_size}", 'info', 'full'))
            
            calib_files = get_image_files(calib_dir)
            if not calib_files:
                raise FileNotFoundError(f"未找到标定文件: {calib_dir}")
            
            self.root.after(0, lambda: self.log(f"PNG文件: {len(calib_files['png_paths'])}张", 'info', 'full'))
            
            actual_values = []
            measured_values = []
            calib_plane_stds = []  # 标定图像平面标准差
            
            for png_path, csv_row in zip(calib_files['png_paths'], calib_files['csv_data']):
                depth_array = read_depth_image(png_path)
                roi = get_roi(depth_array, 
                              x=roi_config['x'], y=roi_config['y'],
                              width=roi_config['width'], height=roi_config['height'])
                result = calibrate_image(roi, apply_filter=use_filter, 
                                        std_factor=outlier_std, median_size=median_size)
                
                if not result['success']:
                    continue
                
                calibrated_roi = result['calibrated_roi']
                valid_pixels, _ = get_valid_pixels(calibrated_roi)
                
                if valid_pixels.size == 0:
                    continue
                
                avg_gray = valid_pixels.mean()
                avg_mm = gray_to_mm(avg_gray, offset=depth_offset, scale_factor=depth_scale_factor)
                
                # 计算平面标准差
                valid_pixels_mm = gray_to_mm(valid_pixels, offset=depth_offset, scale_factor=depth_scale_factor)
                plane_std = np.std(valid_pixels_mm)
                calib_plane_stds.append(plane_std)
                
                actual_values.append(csv_row['实际累计位移(mm)'])
                measured_values.append(avg_mm)
            
            self.root.after(0, lambda: self.log(f"有效图像: {len(actual_values)}张", 'success', 'full'))
            
            # 收集警告信息
            warning_messages = []
            
            # 数据质量检测 - 标定数据
            if ANOMALY_DETECTION_ENABLED and len(actual_values) >= 2:
                calib_anomaly_result = detect_anomalies(actual_values, measured_values, ANOMALY_THRESHOLD)
                if calib_anomaly_result['has_anomaly']:
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    self.root.after(0, lambda: self.log("[警告] 标定数据检测到异常点！", 'warning', 'full'))
                    anomaly_details = []
                    for idx, act_inc, mea_inc, dev in calib_anomaly_result['anomaly_points']:
                        msg = f"  点{idx}->点{idx+1}: 实际增量={act_inc:.4f}mm, 测量增量={mea_inc:.4f}mm, 偏差={dev:.1f}%"
                        anomaly_details.append(f"点{idx}->点{idx+1}(偏差{dev:.1f}%)")
                        self.root.after(0, lambda m=msg: self.log(m, 'warning', 'full'))
                    self.root.after(0, lambda: self.log("[建议] 可能存在硬件抖动，建议重新采集标定数据", 'warning', 'full'))
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    warning_messages.append(f"[标定异常] {', '.join(anomaly_details)}")
            
            # 平面标准差检测 - 标定数据
            if PLANE_STD_WARNING_ENABLED and calib_plane_stds:
                avg_calib_std = np.mean(calib_plane_stds)
                if avg_calib_std > PLANE_STD_THRESHOLD:
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    self.root.after(0, lambda s=avg_calib_std: self.log(f"[警告] 标定数据平面标准差均值 ({s:.6f} mm) 超过阈值!", 'warning', 'full'))
                    self.root.after(0, lambda: self.log("[建议] 平面度较差，建议重新采集或调整ROI", 'warning', 'full'))
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    warning_messages.append(f"[标定平面度] 标准差{avg_calib_std:.4f}mm > 阈值{PLANE_STD_THRESHOLD}mm")
            
            # 步骤2: 建立并保存模型
            self.root.after(0, lambda: self.log("步骤2: 建立补偿模型", 'header', 'full'))
            
            model = build_compensation_model(actual_values, measured_values)
            
            model_path = os.path.join(output_dir, 'compensation_model.json')
            save_model(model, model_path)
            self.root.after(0, lambda: self.log(f"模型已保存: {model_path}", 'success', 'full'))
            
            # 步骤3: 处理测试数据
            self.root.after(0, lambda: self.log("步骤3: 处理测试数据", 'header', 'full'))
            self.root.after(0, lambda: self.update_status("正在处理测试数据..."))
            
            test_files = get_image_files(test_dir)
            if not test_files:
                raise FileNotFoundError(f"未找到测试文件: {test_dir}")
            
            actual_abs = []
            measured_abs = []
            image_stds_before = []  # 每张图像的平面标准差（补偿前）
            image_valid_pixels_list = []  # 保存每张图像的有效像素（用于计算补偿后标准差）
            
            for png_path, csv_row in zip(test_files['png_paths'], test_files['csv_data']):
                depth_array = read_depth_image(png_path)
                roi = get_roi(depth_array,
                              x=roi_config['x'], y=roi_config['y'],
                              width=roi_config['width'], height=roi_config['height'])
                result = calibrate_image(roi, apply_filter=use_filter,
                                        std_factor=outlier_std, median_size=median_size)
                
                if not result['success']:
                    continue
                
                calibrated_roi = result['calibrated_roi']
                valid_pixels, _ = get_valid_pixels(calibrated_roi)
                
                if valid_pixels.size == 0:
                    continue
                
                # 转换所有有效像素为毫米
                valid_pixels_mm = gray_to_mm(valid_pixels, offset=depth_offset, scale_factor=depth_scale_factor)
                
                avg_gray = valid_pixels.mean()
                measured_mm = gray_to_mm(avg_gray, offset=depth_offset, scale_factor=depth_scale_factor)
                
                # 计算该图像平面内的标准差（补偿前）
                std_mm = np.std(valid_pixels_mm)
                image_stds_before.append(std_mm)
                image_valid_pixels_list.append(valid_pixels_mm)
                
                actual_abs.append(csv_row['实际累计位移(mm)'])
                measured_abs.append(measured_mm)
            
            actual_abs = np.array(actual_abs)
            measured_abs = np.array(measured_abs)
            
            # 数据质量检测 - 测试数据
            if ANOMALY_DETECTION_ENABLED and len(actual_abs) >= 2:
                test_anomaly_result = detect_anomalies(actual_abs, measured_abs, ANOMALY_THRESHOLD)
                if test_anomaly_result['has_anomaly']:
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    self.root.after(0, lambda: self.log("[警告] 测试数据检测到异常点！", 'warning', 'full'))
                    anomaly_details = []
                    for idx, act_inc, mea_inc, dev in test_anomaly_result['anomaly_points']:
                        msg = f"  点{idx}->点{idx+1}: 实际增量={act_inc:.4f}mm, 测量增量={mea_inc:.4f}mm, 偏差={dev:.1f}%"
                        anomaly_details.append(f"点{idx}->点{idx+1}(偏差{dev:.1f}%)")
                        self.root.after(0, lambda m=msg: self.log(m, 'warning', 'full'))
                    self.root.after(0, lambda: self.log("[建议] 可能存在硬件抖动，建议重新采集测试数据", 'warning', 'full'))
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    warning_messages.append(f"[测试异常] {', '.join(anomaly_details)}")
            
            # 平面标准差警告 - 测试数据
            if PLANE_STD_WARNING_ENABLED and image_stds_before:
                avg_test_std = np.mean(image_stds_before)
                if avg_test_std > PLANE_STD_THRESHOLD:
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    self.root.after(0, lambda s=avg_test_std: self.log(f"[警告] 测试数据平面标准差均值 ({s:.6f} mm) 超过阈值!", 'warning', 'full'))
                    self.root.after(0, lambda: self.log("[建议] 平面度较差，建议重新采集或调整ROI", 'warning', 'full'))
                    self.root.after(0, lambda: self.log("=" * 50, 'warning', 'full'))
                    warning_messages.append(f"[测试平面度] 标准差{avg_test_std:.4f}mm > 阈值{PLANE_STD_THRESHOLD}mm")
            
            compensated_abs = apply_compensation(measured_abs, model['inverse_model'])
            
            # 计算每张图像补偿后的平面标准差
            image_stds_after = []
            for i, valid_pixels_mm in enumerate(image_valid_pixels_list):
                # 计算每个像素的补偿量（基于平均值的偏移）
                compensation_offset = compensated_abs[i] - measured_abs[i]
                # 补偿后的像素值
                compensated_pixels_mm = valid_pixels_mm + compensation_offset
                std_after = np.std(compensated_pixels_mm)
                image_stds_after.append(std_after)
            
            # 计算所有图像平面标准差的平均值
            avg_plane_std_before = np.mean(image_stds_before) if image_stds_before else 0
            avg_plane_std_after = np.mean(image_stds_after) if image_stds_after else 0
            
            actual_rel = actual_abs - actual_abs[0]
            measured_rel = measured_abs - measured_abs[0]
            compensated_rel = compensated_abs - compensated_abs[0]
            
            # 步骤4: 计算线性度
            self.root.after(0, lambda: self.log("步骤4: 计算线性度", 'header', 'full'))
            
            # 使用用户设置的满量程
            full_scale = self.full_scale.get()
            effect = calculate_compensation_effect(actual_rel, measured_rel, compensated_rel, full_scale=full_scale)
            
            # 添加图像平面标准差平均值到effect
            effect['avg_plane_std_before'] = avg_plane_std_before
            effect['avg_plane_std_after'] = avg_plane_std_after
            
            self.root.after(0, lambda fs=full_scale: self.log(f"满量程: {fs} mm", 'info', 'full'))
            
            before = effect['before']
            after = effect['after']
            self.root.after(0, lambda: self.log(f"补偿前线性度: {before['linearity']:.4f}%", 'info', 'full'))
            self.root.after(0, lambda: self.log(f"补偿后线性度: {after['linearity']:.4f}%", 'success', 'full'))
            self.root.after(0, lambda: self.log(f"改善幅度: {effect['improvement']:.2f}%", 'success', 'full'))
            self.root.after(0, lambda: self.log(f"补偿前平面标准差均值: {avg_plane_std_before:.6f} mm", 'info', 'full'))
            self.root.after(0, lambda: self.log(f"补偿后平面标准差均值: {avg_plane_std_after:.6f} mm", 'info', 'full'))
            
            # 构建警告文本
            warning_text = " | ".join(warning_messages) if warning_messages else None
            self.root.after(0, lambda w=warning_text: self.update_results(effect, w))
            
            # 完成
            self.root.after(0, lambda: self.log("=" * 50, 'header', 'full'))
            self.root.after(0, lambda: self.log("✅ 完成！", 'success', 'full'))
            self.root.after(0, lambda: self.update_status("完成"))
            
        except Exception as e:
            import traceback
            self.root.after(0, lambda: self.log(f"错误: {str(e)}", 'error', 'full'))
            self.root.after(0, lambda: self.update_status("运行出错"))
        
        finally:
            self.root.after(0, self._finish_full_run)
    
    def _finish_full_run(self):
        """完成完整流程"""
        self.is_running = False
        self.full_run_btn.config(state='normal')
        self.full_progress.stop()
    
    # ==================== 批量补偿 ====================
    
    def run_batch_compensate(self):
        """运行批量补偿"""
        if not self.model_loaded:
            messagebox.showerror("错误", "请先加载补偿模型")
            return
        
        input_dir = self.batch_input_dir.get()
        output_dir = self.batch_output_dir.get()
        
        if not input_dir:
            messagebox.showerror("错误", "请选择输入目录")
            return
        if not os.path.exists(input_dir):
            messagebox.showerror("错误", "输入目录不存在")
            return
        
        self.batch_run_btn.config(state='disabled')
        self.clear_log('batch')
        
        thread = threading.Thread(target=self._run_batch_thread, args=(input_dir, output_dir), daemon=True)
        thread.start()
    
    def _get_extrapolate_config(self):
        """获取外推配置"""
        return {
            'enabled': self.extrapolate_enabled.get(),
            'max_low': self.extrapolate_max_low.get(),
            'max_high': self.extrapolate_max_high.get(),
            'output_min': self.extrapolate_output_min.get(),
            'output_max': self.extrapolate_output_max.get(),
            'clamp_output': True
        }
    
    def _get_normalize_config(self):
        """获取归一化配置"""
        return {
            'enabled': self.normalize_enabled.get(),
            'target_center': self.normalize_target_center.get(),
            'auto_offset': self.normalize_auto_offset.get(),
            'manual_offset': self.normalize_manual_offset.get()
        }
    
    def _run_batch_thread(self, input_dir, output_dir):
        """批量补偿线程"""
        try:
            from utils import read_depth_image
            from compensator import compensate_image_pixels, calculate_normalization_offset
            from PIL import Image
            import glob
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取外推配置
            extrapolate_config = self._get_extrapolate_config()
            
            # 获取归一化配置
            normalize_config = self._get_normalize_config()
            normalize_offset = 0.0
            if normalize_config['enabled']:
                if normalize_config['auto_offset']:
                    normalize_offset = calculate_normalization_offset(
                        self.model, normalize_config['target_center'])
                else:
                    normalize_offset = normalize_config['manual_offset']
                
                # 关键修复：启用归一化时，调整钳位范围以适应补偿后的值
                # 补偿后的值范围约 [0, 43] mm，需要确保不被截断
                y_min, y_max = self.model['actual_range']
                extrapolate_config['output_min'] = min(extrapolate_config['output_min'], y_min - 5.0)
                extrapolate_config['output_max'] = max(extrapolate_config['output_max'], y_max + 5.0)
            
            # 获取所有图像文件（支持PNG和TIF格式）
            import re
            image_files = []
            for pattern in ["*.png", "*.PNG", "*.tif", "*.TIF", "*.tiff", "*.TIFF"]:
                image_files.extend(glob.glob(os.path.join(input_dir, pattern)))
            image_files = list(set(image_files))  # 去重
            
            # 自然排序
            def extract_number(path):
                name = os.path.splitext(os.path.basename(path))[0]
                numbers = re.findall(r'\d+', name)
                return int(numbers[-1]) if numbers else 0
            png_files = sorted(image_files, key=extract_number)
            
            if not png_files:
                self.root.after(0, lambda: self.log("未找到图像文件(PNG/TIF)", 'error', 'batch'))
                return
            
            self.root.after(0, lambda: self.log(f"找到 {len(png_files)} 个图像文件", 'info', 'batch'))
            if extrapolate_config['enabled']:
                self.root.after(0, lambda: self.log(
                    f"外推已启用: 低端{extrapolate_config['max_low']}mm, 高端{extrapolate_config['max_high']}mm", 
                    'info', 'batch'))
            if normalize_config['enabled']:
                self.root.after(0, lambda off=normalize_offset: self.log(
                    f"归一化已启用: 偏移量={off:.4f}mm", 'info', 'batch'))
            self.root.after(0, lambda: self.batch_progress.config(maximum=len(png_files), value=0))
            
            total_compensated = 0
            total_pixels = 0
            total_extrapolated = 0
            
            for i, png_path in enumerate(png_files, 1):
                filename = os.path.basename(png_path)
                
                depth_array = read_depth_image(png_path)
                result = compensate_image_pixels(depth_array, self.model['inverse_model'],
                                                  extrapolate_config=extrapolate_config,
                                                  normalize_offset=normalize_offset)
                
                output_path = os.path.join(output_dir, filename)
                Image.fromarray(result['compensated_array']).save(output_path)
                
                stats = result['stats']
                total_compensated += stats['compensated_pixels']
                total_pixels += stats['total_pixels']
                total_extrapolated += stats.get('extrapolated_pixels', 0)
                
                self.root.after(0, lambda f=filename, r=stats['compensation_rate']: 
                               self.log(f"{f} - 补偿率: {r:.1f}%", 'success', 'batch'))
                self.root.after(0, lambda v=i: self.batch_progress.config(value=v))
            
            avg_rate = total_compensated / total_pixels * 100 if total_pixels > 0 else 0
            summary = f"完成！平均补偿率: {avg_rate:.1f}%"
            if total_extrapolated > 0:
                summary += f" (外推像素: {total_extrapolated:,})"
            if normalize_config['enabled']:
                summary += f" (归一化偏移: {normalize_offset:.2f}mm)"
            self.root.after(0, lambda s=summary: self.log(s, 'success', 'batch'))
            self.root.after(0, lambda: self.update_status(f"批量补偿完成: {len(png_files)}张"))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"错误: {str(e)}", 'error', 'batch'))
        
        finally:
            self.root.after(0, lambda: self.batch_run_btn.config(state='normal'))
    
    # ==================== 单个补偿 ====================
    
    def run_single_compensate(self):
        """运行单个图像补偿"""
        if not self.model_loaded:
            messagebox.showerror("错误", "请先加载补偿模型")
            return
        
        input_path = self.single_image_path.get()
        output_path = self.single_output_path.get()
        
        if not input_path:
            messagebox.showerror("错误", "请选择输入图像")
            return
        if not os.path.exists(input_path):
            messagebox.showerror("错误", "输入图像不存在")
            return
        if not output_path:
            messagebox.showerror("错误", "请指定输出路径")
            return
        
        try:
            from utils import read_depth_image
            from compensator import compensate_image_pixels, calculate_normalization_offset
            from PIL import Image
            
            self.update_status("正在补偿...")
            
            # 获取外推配置
            extrapolate_config = self._get_extrapolate_config()
            
            # 获取归一化配置
            normalize_config = self._get_normalize_config()
            normalize_offset = 0.0
            if normalize_config['enabled']:
                if normalize_config['auto_offset']:
                    normalize_offset = calculate_normalization_offset(
                        self.model, normalize_config['target_center'])
                else:
                    normalize_offset = normalize_config['manual_offset']
                
                # 关键修复：启用归一化时，调整钳位范围以适应补偿后的值
                y_min, y_max = self.model['actual_range']
                extrapolate_config['output_min'] = min(extrapolate_config['output_min'], y_min - 5.0)
                extrapolate_config['output_max'] = max(extrapolate_config['output_max'], y_max + 5.0)
            
            depth_array = read_depth_image(input_path)
            result = compensate_image_pixels(depth_array, self.model['inverse_model'],
                                              extrapolate_config=extrapolate_config,
                                              normalize_offset=normalize_offset)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            Image.fromarray(result['compensated_array']).save(output_path)
            
            stats = result['stats']
            
            # 更新结果
            self.single_result_labels['total'].config(text=f"{stats['total_pixels']:,}")
            self.single_result_labels['valid'].config(text=f"{stats['valid_pixels']:,}")
            self.single_result_labels['compensated'].config(text=f"{stats['compensated_pixels']:,}")
            self.single_result_labels['extrapolated'].config(text=f"{stats.get('extrapolated_pixels', 0):,}")
            self.single_result_labels['rate'].config(text=f"{stats['compensation_rate']:.2f}%", style='Good.TLabel')
            
            self.update_status("补偿完成")
            
            extra_info = ""
            if stats.get('extrapolated_pixels', 0) > 0:
                extra_info = f"\n外推像素: {stats['extrapolated_pixels']:,}"
            if normalize_config['enabled']:
                extra_info += f"\n归一化偏移: {normalize_offset:.4f} mm"
            
            messagebox.showinfo("成功", f"图像补偿完成！\n补偿率: {stats['compensation_rate']:.2f}%{extra_info}\n保存至: {output_path}")
            
        except Exception as e:
            messagebox.showerror("错误", f"补偿失败：{str(e)}")
            self.update_status("补偿失败")


def main():
    """主函数"""
    root = tk.Tk()
    
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    app = DepthCompensationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
