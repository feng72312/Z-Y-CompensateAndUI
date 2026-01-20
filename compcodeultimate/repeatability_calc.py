# -*- coding: utf-8 -*-
"""
重复精度计算模块
计算深度图的Y-Z重复精度
支持ROI区域设置
"""

import os
import sys
import numpy as np
from pathlib import Path
from datetime import datetime

# 确保支持中文路径
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, '')

from config import OFFSET, SCALE_FACTOR, INVALID_VALUE, FILTER_ENABLED
from utils import read_depth_image, get_roi, get_valid_pixels
from calibrator import calibrate_image


def gray_to_mm(gray_value, offset=None, scale_factor=None):
    """
    灰度值转换为毫米
    公式: y(mm) = (x - offset) * scale_factor / 1000
    
    参数:
        gray_value: 灰度值（标量或数组）
        offset: 偏移量（默认使用config中的OFFSET）
        scale_factor: 缩放因子（默认使用config中的SCALE_FACTOR）
    """
    if offset is None:
        offset = OFFSET
    if scale_factor is None:
        scale_factor = SCALE_FACTOR
        
    if isinstance(gray_value, np.ndarray):
        gray_float = gray_value.astype(np.float64)
        return ((gray_float - offset) * scale_factor) / 1000.0
    
    if gray_value is None or gray_value == INVALID_VALUE:
        return None
    return ((gray_value - offset) * scale_factor) / 1000.0


def calculate_repeatability(image_dir, output_path=None, use_filter=True, 
                            roi_config=None, calc_mode='mean',
                            depth_offset=None, depth_scale_factor=None):
    """
    计算重复精度
    
    参数:
        image_dir: 图像目录（包含多张同一位置的深度图）
        output_path: 结果输出路径（可选）
        use_filter: 是否使用滤波
        roi_config: ROI配置字典
            - x: ROI起始X坐标
            - y: ROI起始Y坐标
            - width: ROI宽度（-1表示到图像边缘）
            - height: ROI高度（-1表示到图像边缘）
        calc_mode: 计算模式
            - 'mean': 使用ROI区域平均值计算重复精度
            - 'pixel': 逐像素计算重复精度后取平均
        depth_offset: 深度转换偏移量（默认使用config中的OFFSET）
        depth_scale_factor: 深度转换缩放因子（默认使用config中的SCALE_FACTOR）
    
    返回:
        dict: 重复精度计算结果
    """
    # 默认ROI配置
    if roi_config is None:
        roi_config = {'x': 0, 'y': 0, 'width': -1, 'height': -1}
    
    # 默认深度转换系数
    if depth_offset is None:
        depth_offset = OFFSET
    if depth_scale_factor is None:
        depth_scale_factor = SCALE_FACTOR
    
    print("=" * 60)
    print("Y-Z重复精度计算工具")
    print("=" * 60)
    
    # 使用 Path 处理中文路径
    image_dir = str(Path(image_dir))
    
    print(f"\n图像目录: {image_dir}")
    print(f"滤波: {'启用' if use_filter else '禁用'}")
    print(f"计算模式: {'区域平均值' if calc_mode == 'mean' else '逐像素'}")
    print(f"深度转换: 偏移量={depth_offset}, 缩放因子={depth_scale_factor}")
    
    # 显示ROI信息
    if roi_config['width'] == -1 and roi_config['height'] == -1 and roi_config['x'] == 0 and roi_config['y'] == 0:
        print(f"ROI: 使用全部图像")
    else:
        roi_desc = f"ROI: X=[{roi_config['x']}, {'边缘' if roi_config['width']==-1 else roi_config['x']+roi_config['width']}], "
        roi_desc += f"Y=[{roi_config['y']}, {'边缘' if roi_config['height']==-1 else roi_config['y']+roi_config['height']}]"
        print(roi_desc)
    
    # 获取所有图像文件（支持PNG和TIF格式）
    image_dir_path = Path(image_dir)
    image_files = []
    for pattern in ['*.png', '*.PNG', '*.tif', '*.TIF', '*.tiff', '*.TIFF']:
        image_files.extend(image_dir_path.glob(pattern))
    image_files = list(set([str(f.resolve()) for f in image_files]))  # 去重
    
    # 自然排序（按文件名中的数字）
    import re
    def extract_number(path):
        name = Path(path).stem
        numbers = re.findall(r'\d+', name)
        return int(numbers[-1]) if numbers else 0
    png_files = sorted(image_files, key=extract_number)
    
    if not png_files:
        raise FileNotFoundError(f"未找到图像文件(PNG/TIF): {image_dir}")
    
    print(f"\n找到 {len(png_files)} 张图像")
    
    if len(png_files) < 2:
        raise ValueError("至少需要2张图像才能计算重复精度")
    
    # 处理每张图像
    image_values = []  # 每张图像的平均深度值(mm)
    image_stats = []   # 每张图像的统计信息
    all_valid_pixels_mm = []  # 所有图像的有效像素（用于逐像素计算）
    
    print("\n处理图像:")
    print("-" * 60)
    
    first_roi_shape = None
    
    for i, png_path in enumerate(png_files, 1):
        filename = os.path.basename(png_path)
        
        depth_array = read_depth_image(png_path)
        
        # 提取ROI
        roi = get_roi(depth_array, 
                      x=roi_config['x'], 
                      y=roi_config['y'], 
                      width=roi_config['width'], 
                      height=roi_config['height'])
        
        # 记录ROI尺寸
        if first_roi_shape is None:
            first_roi_shape = roi.shape
            print(f"ROI尺寸: {roi.shape[1]} x {roi.shape[0]} 像素")
        
        # 滤波处理
        if use_filter:
            result = calibrate_image(roi, apply_filter=True)
            if result['success']:
                roi = result['calibrated_roi']
        
        # 获取有效像素
        valid_pixels, valid_mask = get_valid_pixels(roi)
        
        if valid_pixels.size == 0:
            print(f"[{i}] {filename} - 跳过（无有效像素）")
            continue
        
        # 转换为毫米
        valid_pixels_mm = gray_to_mm(valid_pixels, offset=depth_offset, scale_factor=depth_scale_factor)
        
        # 计算统计信息
        mean_mm = np.mean(valid_pixels_mm)
        std_mm = np.std(valid_pixels_mm)
        min_mm = np.min(valid_pixels_mm)
        max_mm = np.max(valid_pixels_mm)
        valid_count = valid_pixels.size
        valid_ratio = valid_count / roi.size * 100
        
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
        
        # 保存所有有效像素（用于逐像素分析）
        all_valid_pixels_mm.append(valid_pixels_mm)
        
        print(f"[{i}] {filename}: 平均={mean_mm:.6f}mm, 标准差={std_mm:.6f}mm, 有效像素={valid_ratio:.1f}%")
    
    print("-" * 60)
    print(f"有效图像: {len(image_values)} / {len(png_files)}")
    
    if len(image_values) < 2:
        raise ValueError("有效图像数量不足，无法计算重复精度")
    
    # 转换为numpy数组
    image_values_arr = np.array(image_values)
    
    # ==================== 计算重复精度 ====================
    print("\n" + "=" * 60)
    print("重复精度计算结果")
    print("=" * 60)
    
    # 基于图像平均值的重复精度
    overall_mean = np.mean(image_values_arr)
    overall_std = np.std(image_values_arr, ddof=1)  # 使用样本标准差
    
    # 重复精度指标
    repeatability_1sigma = overall_std
    repeatability_3sigma = 3 * overall_std
    repeatability_6sigma = 6 * overall_std
    
    # 极差（最大值-最小值）
    peak_to_peak = np.max(image_values_arr) - np.min(image_values_arr)
    
    print(f"\n【基于区域平均值的重复精度】")
    print(f"  图像数量: {len(image_values)}")
    print(f"  平均深度: {overall_mean:.6f} mm")
    print(f"  标准差(1σ): {repeatability_1sigma:.6f} mm ({repeatability_1sigma*1000:.3f} μm)")
    print(f"  重复精度(±3σ): ±{repeatability_3sigma:.6f} mm (±{repeatability_3sigma*1000:.3f} μm)")
    print(f"  重复精度(6σ): {repeatability_6sigma:.6f} mm ({repeatability_6sigma*1000:.3f} μm)")
    print(f"  极差(Peak-to-Peak): {peak_to_peak:.6f} mm ({peak_to_peak*1000:.3f} μm)")
    
    # 计算逐像素的统计（如果所有图像有效像素数相同）
    pixel_repeatability = None
    if calc_mode == 'pixel' and len(set(len(p) for p in all_valid_pixels_mm)) == 1:
        # 将所有图像的像素值堆叠成矩阵 (num_images, num_pixels)
        pixel_matrix = np.vstack(all_valid_pixels_mm)
        
        # 计算每个像素位置的标准差
        pixel_stds = np.std(pixel_matrix, axis=0, ddof=1)
        
        pixel_repeatability = {
            'mean_std': np.mean(pixel_stds),
            'max_std': np.max(pixel_stds),
            'min_std': np.min(pixel_stds),
            'median_std': np.median(pixel_stds)
        }
        
        print(f"\n【逐像素重复精度分析】")
        print(f"  像素数量: {pixel_matrix.shape[1]}")
        print(f"  平均标准差: {pixel_repeatability['mean_std']:.6f} mm ({pixel_repeatability['mean_std']*1000:.3f} μm)")
        print(f"  最大标准差: {pixel_repeatability['max_std']:.6f} mm ({pixel_repeatability['max_std']*1000:.3f} μm)")
        print(f"  最小标准差: {pixel_repeatability['min_std']:.6f} mm ({pixel_repeatability['min_std']*1000:.3f} μm)")
        print(f"  中位数标准差: {pixel_repeatability['median_std']:.6f} mm ({pixel_repeatability['median_std']*1000:.3f} μm)")
    
    # 计算图像间的噪声指标
    avg_intra_image_std = np.mean([s['std'] for s in image_stats])
    
    print(f"\n【图像内部噪声】")
    print(f"  平均图像内标准差: {avg_intra_image_std:.6f} mm ({avg_intra_image_std*1000:.3f} μm)")
    
    # 构建结果
    result = {
        'image_dir': image_dir,
        'num_images': len(image_values),
        'roi_config': roi_config,
        'roi_shape': first_roi_shape,
        'use_filter': use_filter,
        'calc_mode': calc_mode,
        'depth_offset': depth_offset,
        'depth_scale_factor': depth_scale_factor,
        
        # 主要指标
        'mean_depth': overall_mean,
        'std_1sigma': repeatability_1sigma,
        'repeatability_3sigma': repeatability_3sigma,
        'repeatability_6sigma': repeatability_6sigma,
        'peak_to_peak': peak_to_peak,
        
        # 图像内噪声
        'avg_intra_image_std': avg_intra_image_std,
        
        # 逐像素分析
        'pixel_repeatability': pixel_repeatability,
        
        # 详细数据
        'image_values': image_values,
        'image_stats': image_stats
    }
    
    # 保存结果
    if output_path:
        output_path = str(Path(output_path))
        save_repeatability_result(result, output_path)
        print(f"\n结果已保存: {output_path}")
    
    print("\n" + "=" * 60)
    print("计算完成！")
    print("=" * 60)
    
    return result


def save_repeatability_result(result, output_path):
    """保存重复精度计算结果"""
    # 确保目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("Y-Z重复精度测量报告\n")
        f.write("=" * 70 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("【测试参数】\n")
        f.write("-" * 70 + "\n")
        f.write(f"图像目录: {result['image_dir']}\n")
        f.write(f"图像数量: {result['num_images']}\n")
        f.write(f"滤波处理: {'启用' if result['use_filter'] else '禁用'}\n")
        
        # ROI信息
        roi = result['roi_config']
        if roi['width'] == -1 and roi['height'] == -1 and roi['x'] == 0 and roi['y'] == 0:
            f.write(f"ROI设置: 使用全部图像\n")
        else:
            x_end = '边缘' if roi['width'] == -1 else roi['x'] + roi['width']
            y_end = '边缘' if roi['height'] == -1 else roi['y'] + roi['height']
            f.write(f"ROI设置: X=[{roi['x']}, {x_end}], Y=[{roi['y']}, {y_end}]\n")
        
        if result['roi_shape']:
            f.write(f"ROI尺寸: {result['roi_shape'][1]} x {result['roi_shape'][0]} 像素\n")
        f.write("\n")
        
        f.write("【重复精度结果】\n")
        f.write("-" * 70 + "\n")
        f.write(f"平均深度值: {result['mean_depth']:.6f} mm\n")
        f.write(f"标准差(1σ): {result['std_1sigma']:.6f} mm ({result['std_1sigma']*1000:.3f} μm)\n")
        f.write(f"重复精度(±3σ): ±{result['repeatability_3sigma']:.6f} mm (±{result['repeatability_3sigma']*1000:.3f} μm)\n")
        f.write(f"重复精度(6σ): {result['repeatability_6sigma']:.6f} mm ({result['repeatability_6sigma']*1000:.3f} μm)\n")
        f.write(f"极差(Peak-to-Peak): {result['peak_to_peak']:.6f} mm ({result['peak_to_peak']*1000:.3f} μm)\n")
        f.write(f"图像内平均标准差: {result['avg_intra_image_std']:.6f} mm ({result['avg_intra_image_std']*1000:.3f} μm)\n")
        f.write("\n")
        
        # 逐像素分析结果
        if result['pixel_repeatability']:
            pr = result['pixel_repeatability']
            f.write("【逐像素重复精度分析】\n")
            f.write("-" * 70 + "\n")
            f.write(f"平均标准差: {pr['mean_std']:.6f} mm ({pr['mean_std']*1000:.3f} μm)\n")
            f.write(f"最大标准差: {pr['max_std']:.6f} mm ({pr['max_std']*1000:.3f} μm)\n")
            f.write(f"最小标准差: {pr['min_std']:.6f} mm ({pr['min_std']*1000:.3f} μm)\n")
            f.write(f"中位数标准差: {pr['median_std']:.6f} mm ({pr['median_std']*1000:.3f} μm)\n")
            f.write("\n")
        
        f.write("【逐图像详细数据】\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'序号':<6} {'文件名':<40} {'平均值(mm)':<14} {'标准差(mm)':<14} {'有效率':<8}\n")
        f.write("-" * 70 + "\n")
        
        for i, stat in enumerate(result['image_stats'], 1):
            f.write(f"{i:<6} {stat['filename']:<40} {stat['mean']:<14.6f} {stat['std']:<14.6f} {stat['valid_ratio']:<8.1f}%\n")
        
        f.write("-" * 70 + "\n")
        f.write("\n")
        
        f.write("【计算公式说明】\n")
        f.write("-" * 70 + "\n")
        depth_offset = result.get('depth_offset', OFFSET)
        depth_scale_factor = result.get('depth_scale_factor', SCALE_FACTOR)
        f.write(f"深度转换公式: y(mm) = (灰度值 - {depth_offset}) × {depth_scale_factor} / 1000\n")
        f.write("重复精度(±3σ): 基于多次测量的平均值计算的3倍标准差\n")
        f.write("极差: 所有测量值中最大值与最小值之差\n")
        f.write("=" * 70 + "\n")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Y-Z重复精度计算工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 计算重复精度
  python repeatability_calc.py -d ../测试数据/repeatability_test
  
  # 指定ROI区域
  python repeatability_calc.py -d test_data --roi 100,100,500,400
  
  # 禁用滤波
  python repeatability_calc.py -d test_data --no-filter
        '''
    )
    
    parser.add_argument('-d', '--dir', required=True,
                        help='图像目录（包含多张PNG图像）')
    parser.add_argument('-o', '--output', default=None,
                        help='结果输出文件路径（可选）')
    parser.add_argument('--roi', default=None,
                        help='ROI区域: x,y,width,height（-1表示到边缘）')
    parser.add_argument('--no-filter', action='store_true',
                        help='禁用滤波处理')
    parser.add_argument('--pixel-mode', action='store_true',
                        help='使用逐像素分析模式')
    
    args = parser.parse_args()
    
    # 解析ROI参数
    roi_config = None
    if args.roi:
        parts = [int(x) for x in args.roi.split(',')]
        if len(parts) == 4:
            roi_config = {'x': parts[0], 'y': parts[1], 'width': parts[2], 'height': parts[3]}
    
    try:
        calculate_repeatability(
            image_dir=args.dir,
            output_path=args.output,
            use_filter=not args.no_filter,
            roi_config=roi_config,
            calc_mode='pixel' if args.pixel_mode else 'mean'
        )
        return 0
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

