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
                    EXTRAPOLATE_OUTPUT_MIN, EXTRAPOLATE_OUTPUT_MAX, EXTRAPOLATE_CLAMP_OUTPUT)


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
            # RMS误差
            ('rms_before', '补偿前RMS误差', 2, 0),
            ('rms_after', '补偿后RMS误差', 2, 2),
            # 标准差
            ('std_before', '补偿前标准差', 3, 0),
            ('std_after', '补偿后标准差', 3, 2),
            # 改善幅度和R²
            ('improvement', '改善幅度', 4, 0),
            ('r_squared', 'R²决定系数', 4, 2),
        ]
        
        for key, label, row, col in metrics:
            ttk.Label(result_frame, text=f"{label}:", style='Header.TLabel').grid(
                row=row, column=col, sticky=tk.W, padx=5, pady=3)
            
            value_label = ttk.Label(result_frame, text="--", style='Value.TLabel')
            value_label.grid(row=row, column=col+1, sticky=tk.W, padx=10, pady=3)
            self.result_labels[key] = value_label
        
        result_frame.columnconfigure(1, weight=1)
        result_frame.columnconfigure(3, weight=1)
    
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
            filetypes=[("PNG文件", "*.png"), ("所有文件", "*.*")]
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
            filetypes=[("PNG文件", "*.png")]
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
    
    def update_results(self, effect):
        """更新结果面板"""
        before = effect['before']
        after = effect['after']
        
        # 线性度
        self.result_labels['linearity_before'].config(text=f"{before['linearity']:.4f}%")
        self.result_labels['linearity_after'].config(text=f"{after['linearity']:.4f}%", style='Good.TLabel')
        
        # 最大偏差
        self.result_labels['max_dev_before'].config(text=f"{before['abs_max_deviation']:.6f} mm")
        self.result_labels['max_dev_after'].config(text=f"{after['abs_max_deviation']:.6f} mm", style='Good.TLabel')
        
        # RMS误差
        self.result_labels['rms_before'].config(text=f"{before['rms_error']:.6f} mm")
        self.result_labels['rms_after'].config(text=f"{after['rms_error']:.6f} mm", style='Good.TLabel')
        
        # 标准差
        if 'std' in before:
            self.result_labels['std_before'].config(text=f"{before['std']:.6f} mm")
        else:
            self.result_labels['std_before'].config(text=f"{before['rms_error']:.6f} mm")
        
        if 'std' in after:
            self.result_labels['std_after'].config(text=f"{after['std']:.6f} mm", style='Good.TLabel')
        else:
            self.result_labels['std_after'].config(text=f"{after['rms_error']:.6f} mm", style='Good.TLabel')
        
        # 改善幅度和R²
        self.result_labels['improvement'].config(text=f"↑ {effect['improvement']:.2f}%", style='Good.TLabel')
        self.result_labels['r_squared'].config(text=f"{after['r_squared']:.8f}")
    
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
        
        ttk.Checkbutton(settings_frame, text="启用滤波处理", 
                        variable=self.filter_enabled).pack(anchor=tk.W, pady=3)
        
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
            
            self.root.after(0, lambda: self._log_linearity("开始计算线性度...", 'header'))
            self.root.after(0, lambda: self._log_linearity(f"测试目录: {test_dir}"))
            
            result = calculate_batch_linearity(
                test_dir=test_dir,
                model_path=model_path,
                output_path=output_path,
                use_filter=use_filter,
                full_scale=full_scale
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
            
            self.update_status(f"模型加载成功: {os.path.basename(model_path)}")
            messagebox.showinfo("成功", f"模型加载成功！\n标定点数: {num_points}\n实际值范围: [{actual_range[0]:.2f}, {actual_range[1]:.2f}] mm")
            
        except Exception as e:
            self.model_loaded = False
            self.model = None
            self.model_status_label.config(text="❌ 加载失败", style='ModelNotLoaded.TLabel')
            self.model_info_label.config(text="")
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
            from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm
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
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 步骤1: 处理标定数据
            self.root.after(0, lambda: self.log("=" * 50, 'header', 'full'))
            self.root.after(0, lambda: self.log("步骤1: 处理标定数据", 'header', 'full'))
            self.root.after(0, lambda: self.update_status("正在处理标定数据..."))
            
            if use_filter:
                self.root.after(0, lambda: self.log(f"滤波参数: 异常值阈值={outlier_std}σ, 中值窗口={median_size}×{median_size}", 'info', 'full'))
            
            calib_files = get_image_files(calib_dir)
            if not calib_files:
                raise FileNotFoundError(f"未找到标定文件: {calib_dir}")
            
            self.root.after(0, lambda: self.log(f"PNG文件: {len(calib_files['png_paths'])}张", 'info', 'full'))
            
            actual_values = []
            measured_values = []
            
            for png_path, csv_row in zip(calib_files['png_paths'], calib_files['csv_data']):
                depth_array = read_depth_image(png_path)
                roi = get_roi(depth_array)
                result = calibrate_image(roi, apply_filter=use_filter, 
                                        std_factor=outlier_std, median_size=median_size)
                
                if not result['success']:
                    continue
                
                calibrated_roi = result['calibrated_roi']
                valid_pixels, _ = get_valid_pixels(calibrated_roi)
                
                if valid_pixels.size == 0:
                    continue
                
                avg_gray = valid_pixels.mean()
                avg_mm = gray_to_mm(avg_gray)
                
                actual_values.append(csv_row['实际累计位移(mm)'])
                measured_values.append(avg_mm)
            
            self.root.after(0, lambda: self.log(f"有效图像: {len(actual_values)}张", 'success', 'full'))
            
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
            
            for png_path, csv_row in zip(test_files['png_paths'], test_files['csv_data']):
                depth_array = read_depth_image(png_path)
                roi = get_roi(depth_array)
                result = calibrate_image(roi, apply_filter=use_filter,
                                        std_factor=outlier_std, median_size=median_size)
                
                if not result['success']:
                    continue
                
                calibrated_roi = result['calibrated_roi']
                valid_pixels, _ = get_valid_pixels(calibrated_roi)
                
                if valid_pixels.size == 0:
                    continue
                
                avg_gray = valid_pixels.mean()
                measured_mm = gray_to_mm(avg_gray)
                
                actual_abs.append(csv_row['实际累计位移(mm)'])
                measured_abs.append(measured_mm)
            
            actual_abs = np.array(actual_abs)
            measured_abs = np.array(measured_abs)
            compensated_abs = apply_compensation(measured_abs, model['inverse_model'])
            
            actual_rel = actual_abs - actual_abs[0]
            measured_rel = measured_abs - measured_abs[0]
            compensated_rel = compensated_abs - compensated_abs[0]
            
            # 步骤4: 计算线性度
            self.root.after(0, lambda: self.log("步骤4: 计算线性度", 'header', 'full'))
            
            # 使用用户设置的满量程
            full_scale = self.full_scale.get()
            effect = calculate_compensation_effect(actual_rel, measured_rel, compensated_rel, full_scale=full_scale)
            self.root.after(0, lambda fs=full_scale: self.log(f"满量程: {fs} mm", 'info', 'full'))
            
            before = effect['before']
            after = effect['after']
            self.root.after(0, lambda: self.log(f"补偿前线性度: {before['linearity']:.4f}%", 'info', 'full'))
            self.root.after(0, lambda: self.log(f"补偿后线性度: {after['linearity']:.4f}%", 'success', 'full'))
            self.root.after(0, lambda: self.log(f"改善幅度: {effect['improvement']:.2f}%", 'success', 'full'))
            
            self.root.after(0, lambda: self.update_results(effect))
            
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
    
    def _run_batch_thread(self, input_dir, output_dir):
        """批量补偿线程"""
        try:
            from utils import read_depth_image
            from compensator import compensate_image_pixels
            from PIL import Image
            import glob
            
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取外推配置
            extrapolate_config = self._get_extrapolate_config()
            
            # 获取所有PNG文件
            png_files = sorted(glob.glob(os.path.join(input_dir, "*.png")))
            
            if not png_files:
                self.root.after(0, lambda: self.log("未找到PNG文件", 'error', 'batch'))
                return
            
            self.root.after(0, lambda: self.log(f"找到 {len(png_files)} 个PNG文件", 'info', 'batch'))
            if extrapolate_config['enabled']:
                self.root.after(0, lambda: self.log(
                    f"外推已启用: 低端{extrapolate_config['max_low']}mm, 高端{extrapolate_config['max_high']}mm", 
                    'info', 'batch'))
            self.root.after(0, lambda: self.batch_progress.config(maximum=len(png_files), value=0))
            
            total_compensated = 0
            total_pixels = 0
            total_extrapolated = 0
            
            for i, png_path in enumerate(png_files, 1):
                filename = os.path.basename(png_path)
                
                depth_array = read_depth_image(png_path)
                result = compensate_image_pixels(depth_array, self.model['inverse_model'],
                                                  extrapolate_config=extrapolate_config)
                
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
            from compensator import compensate_image_pixels
            from PIL import Image
            
            self.update_status("正在补偿...")
            
            # 获取外推配置
            extrapolate_config = self._get_extrapolate_config()
            
            depth_array = read_depth_image(input_path)
            result = compensate_image_pixels(depth_array, self.model['inverse_model'],
                                              extrapolate_config=extrapolate_config)
            
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
