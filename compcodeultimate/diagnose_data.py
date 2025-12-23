# -*- coding: utf-8 -*-
"""
数据诊断脚本
用于检查标定数据是否存在问题，导致 "SVD did not converge" 错误
"""

import sys
import os
import numpy as np
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import INVALID_VALUE, MIN_VALID_PIXELS
from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm


def diagnose_directory(directory):
    """诊断标定/测试目录的数据问题"""
    
    print("=" * 60)
    print(f"数据诊断报告")
    print(f"目录: {directory}")
    print("=" * 60)
    
    # 1. 检查目录是否存在
    if not os.path.exists(directory):
        print(f"\n❌ 错误: 目录不存在!")
        return
    
    # 2. 获取文件
    try:
        files = get_image_files(directory)
    except Exception as e:
        print(f"\n❌ 获取文件错误: {e}")
        return
    
    if not files:
        print(f"\n❌ 未找到PNG或CSV文件!")
        return
    
    print(f"\n[1] 文件统计")
    print(f"  PNG文件: {len(files['png_paths'])}张")
    print(f"  CSV数据: {len(files['csv_data'])}行")
    
    if len(files['png_paths']) < 4:
        print(f"\n⚠️ 警告: PNG文件太少 ({len(files['png_paths'])}张)，建议至少4张用于样条拟合!")
    
    # 3. 检查CSV数据
    print(f"\n[2] CSV数据检查")
    actual_values = []
    for i, row in enumerate(files['csv_data']):
        val = row.get('实际累计位移(mm)', None)
        if val is None:
            print(f"  ❌ 第{i+1}行: 缺少 '实际累计位移(mm)' 列")
        else:
            actual_values.append(val)
            print(f"  第{i+1}行: 实际值 = {val:.4f} mm")
    
    # 检查数据问题
    if len(actual_values) > 0:
        actual_arr = np.array(actual_values)
        print(f"\n  数值范围: {actual_arr.min():.4f} ~ {actual_arr.max():.4f} mm")
        
        # 检查NaN/Inf
        if np.any(np.isnan(actual_arr)):
            print(f"  ❌ 存在NaN值!")
        if np.any(np.isinf(actual_arr)):
            print(f"  ❌ 存在Inf值!")
        
        # 检查重复值
        unique_vals = np.unique(actual_arr)
        if len(unique_vals) < len(actual_arr):
            print(f"  ⚠️ 存在重复值: {len(actual_arr) - len(unique_vals)}个重复")
        
        # 检查是否单调
        if len(actual_arr) > 1:
            diffs = np.diff(actual_arr)
            if np.all(diffs > 0):
                print(f"  ✅ 数据单调递增")
            elif np.all(diffs < 0):
                print(f"  ✅ 数据单调递减")
            else:
                print(f"  ⚠️ 数据非单调！这可能导致样条拟合失败")
    
    # 4. 检查图像数据
    print(f"\n[3] 图像数据检查")
    measured_values = []
    problem_images = []
    
    for i, png_path in enumerate(files['png_paths']):
        filename = os.path.basename(png_path)
        try:
            depth_array = read_depth_image(png_path)
            roi = get_roi(depth_array)
            valid_pixels, valid_mask = get_valid_pixels(roi)
            
            if valid_pixels.size < MIN_VALID_PIXELS:
                print(f"  ⚠️ {filename}: 有效像素不足 ({valid_pixels.size})")
                problem_images.append(filename)
                continue
            
            avg_gray = valid_pixels.mean()
            avg_mm = gray_to_mm(avg_gray)
            measured_values.append(avg_mm)
            
            print(f"  ✓ {filename}: 灰度={avg_gray:.2f}, mm={avg_mm:.4f}")
            
        except Exception as e:
            print(f"  ❌ {filename}: 处理失败 - {e}")
            problem_images.append(filename)
    
    # 5. 检查测量值
    if len(measured_values) > 0:
        measured_arr = np.array(measured_values)
        print(f"\n[4] 测量值分析")
        print(f"  有效图像: {len(measured_values)}张")
        print(f"  测量值范围: {measured_arr.min():.4f} ~ {measured_arr.max():.4f} mm")
        
        # 检查NaN/Inf
        if np.any(np.isnan(measured_arr)):
            print(f"  ❌ 存在NaN值!")
        if np.any(np.isinf(measured_arr)):
            print(f"  ❌ 存在Inf值!")
        
        # 检查重复值
        unique_vals = np.unique(measured_arr)
        if len(unique_vals) < len(measured_arr):
            duplicates = len(measured_arr) - len(unique_vals)
            print(f"  ⚠️ 存在重复测量值: {duplicates}个重复")
        
        # 检查是否有足够数据建模
        if len(measured_values) < 4:
            print(f"\n❌ 错误: 有效数据点太少 ({len(measured_values)}个)")
            print(f"   三次样条需要至少4个数据点！")
    
    # 6. 综合诊断
    print(f"\n[5] 诊断结论")
    print("=" * 60)
    
    issues = []
    
    if len(files['png_paths']) < 4:
        issues.append("PNG文件太少，需要至少4张")
    
    if len(measured_values) < 4:
        issues.append(f"有效数据点太少 ({len(measured_values)}个)")
    
    if problem_images:
        issues.append(f"{len(problem_images)}张图像处理失败")
    
    if len(actual_values) > 1:
        diffs = np.diff(np.array(actual_values))
        if not (np.all(diffs > 0) or np.all(diffs < 0)):
            issues.append("实际值不单调，可能导致样条拟合失败")
    
    if len(measured_values) > 1:
        measured_arr = np.array(measured_values)
        if len(np.unique(measured_arr)) != len(measured_arr):
            issues.append("测量值有重复，可能导致样条拟合失败")
    
    if issues:
        print("\n⚠️ 发现以下问题：")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print("\n这些问题可能导致 'SVD did not converge' 错误。")
        print("\n建议解决方案：")
        print("  1. 确保有至少4张有效的标定图像")
        print("  2. 检查CSV文件的实际值是否单调递增/递减")
        print("  3. 确保每张图像有足够的有效像素")
        print("  4. 检查是否有重复的测量点")
    else:
        print("\n✅ 数据看起来正常，可以进行标定。")


if __name__ == "__main__":
    # 默认检查标定目录
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        # 使用config中的默认目录
        from config import CALIB_DIR
        directory = CALIB_DIR
    
    diagnose_directory(directory)

