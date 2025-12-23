# -*- coding: utf-8 -*-
"""
分析工具 - 数据范围分析、质量检查
"""

import os
from config import CALIB_DIR, TEST_DIR, INVALID_VALUE
from utils import get_image_files, read_depth_image, get_valid_pixels, gray_to_mm


def analyze_dataset(directory, name="数据集"):
    """
    分析数据集的灰度和深度范围
    
    返回:
        dict: 统计信息
    """
    print(f"\n{'='*70}")
    print(f"分析: {name}")
    print(f"目录: {directory}")
    print(f"{'='*70}")
    
    files = get_image_files(directory)
    if not files:
        print("错误: 未找到数据文件")
        return None
    
    print(f"找到 {len(files['png_paths'])} 个PNG文件\n")
    
    all_gray_min = []
    all_gray_max = []
    all_depth_min = []
    all_depth_max = []
    
    print(f"{'序号':<6} {'文件名':<45} {'灰度范围':<25} {'深度范围(mm)':<25}")
    print("-" * 120)
    
    for i, png_path in enumerate(files['png_paths'], 1):
        filename = os.path.basename(png_path)
        depth_array = read_depth_image(png_path)
        
        valid_pixels, _ = get_valid_pixels(depth_array)
        
        if valid_pixels.size == 0:
            print(f"{i:<6} {filename:<45} {'无有效像素':<25} {'N/A':<25}")
            continue
        
        gray_min = valid_pixels.min()
        gray_max = valid_pixels.max()
        
        depth_min = gray_to_mm(gray_min)
        depth_max = gray_to_mm(gray_max)
        
        all_gray_min.append(gray_min)
        all_gray_max.append(gray_max)
        all_depth_min.append(depth_min)
        all_depth_max.append(depth_max)
        
        gray_str = f"[{gray_min}, {gray_max}]"
        depth_str = f"[{depth_min:.2f}, {depth_max:.2f}]"
        
        print(f"{i:<6} {filename:<45} {gray_str:<25} {depth_str:<25}")
    
    if not all_gray_min:
        print("\n没有有效数据")
        return None
    
    # 统计
    print(f"\n{'='*70}")
    print("统计总结")
    print(f"{'='*70}")
    
    print(f"\n灰度范围: [{min(all_gray_min)}, {max(all_gray_max)}]")
    print(f"深度范围: [{min(all_depth_min):.2f}, {max(all_depth_max):.2f}] mm")
    print(f"深度跨度: {max(all_depth_max) - min(all_depth_min):.2f} mm")
    
    return {
        'gray_min': min(all_gray_min),
        'gray_max': max(all_gray_max),
        'depth_min': min(all_depth_min),
        'depth_max': max(all_depth_max),
        'depth_span': max(all_depth_max) - min(all_depth_min)
    }


def compare_datasets():
    """对比标定数据和测试数据"""
    calib_stats = analyze_dataset(CALIB_DIR, "标定数据集")
    test_stats = analyze_dataset(TEST_DIR, "测试数据集")
    
    if calib_stats and test_stats:
        print(f"\n{'='*70}")
        print("数据集对比")
        print(f"{'='*70}")
        
        print(f"\n{'数据集':<15} {'灰度范围':<25} {'深度范围(mm)':<30} {'跨度(mm)':<15}")
        print("-" * 85)
        
        calib_gray_str = f"[{calib_stats['gray_min']}, {calib_stats['gray_max']}]"
        calib_depth_str = f"[{calib_stats['depth_min']:.2f}, {calib_stats['depth_max']:.2f}]"
        print(f"{'标定数据':<15} {calib_gray_str:<25} {calib_depth_str:<30} {calib_stats['depth_span']:.2f}")
        
        test_gray_str = f"[{test_stats['gray_min']}, {test_stats['gray_max']}]"
        test_depth_str = f"[{test_stats['depth_min']:.2f}, {test_stats['depth_max']:.2f}]"
        print(f"{'测试数据':<15} {test_gray_str:<25} {test_depth_str:<30} {test_stats['depth_span']:.2f}")
        
        # 重叠分析
        print(f"\n重叠分析:")
        calib_min = calib_stats['depth_min']
        calib_max = calib_stats['depth_max']
        test_min = test_stats['depth_min']
        test_max = test_stats['depth_max']
        
        if test_min >= calib_min and test_max <= calib_max:
            overlap_span = test_max - test_min
            print(f"  ✓ 测试数据完全在标定范围内")
            print(f"  重叠范围: [{test_min:.2f}, {test_max:.2f}] mm")
            print(f"  占标定范围: {overlap_span / calib_stats['depth_span'] * 100:.2f}%")
        else:
            if test_max < calib_min:
                print(f"  ⚠️ 测试数据完全低于标定范围")
            elif test_min > calib_max:
                print(f"  ⚠️ 测试数据完全高于标定范围")
            else:
                overlap_min = max(calib_min, test_min)
                overlap_max = min(calib_max, test_max)
                overlap_span = overlap_max - overlap_min
                print(f"  ⚠️ 部分重叠")
                print(f"  重叠范围: [{overlap_min:.2f}, {overlap_max:.2f}] mm")
                print(f"  重叠跨度: {overlap_span:.2f} mm")


if __name__ == "__main__":
    compare_datasets()

