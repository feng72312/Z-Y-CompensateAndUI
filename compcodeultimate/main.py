# -*- coding: utf-8 -*-
"""
主程序 - 深度图补偿完整流程
整合标定、测试、补偿、分析功能
"""

import os
import sys
import numpy as np
from PIL import Image

from config import CALIB_DIR, TEST_DIR, OUTPUT_DIR, FILTER_ENABLED
from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm
from calibrator import calibrate_image
from compensator import (build_compensation_model, apply_compensation, 
                        calculate_compensation_effect, compensate_image_pixels,
                        save_model, load_model)


def process_calibration_data(calib_dir, use_filter=True):
    """
    处理标定数据，建立补偿模型
    
    返回:
        dict: {
            'model': 补偿模型,
            'actual_values': 实际值列表,
            'measured_values': 测量值列表
        }
    """
    print(f"\n{'='*60}")
    print("步骤1: 处理标定数据")
    print(f"{'='*60}")
    print(f"目录: {calib_dir}")
    print(f"滤波: {'启用' if use_filter else '禁用'}")
    
    # 获取标定文件
    calib_files = get_image_files(calib_dir)
    if not calib_files:
        raise FileNotFoundError(f"未找到标定文件: {calib_dir}")
    
    print(f"CSV文件: {os.path.basename(calib_files['csv_path'])}")
    print(f"PNG文件: {len(calib_files['png_paths'])}张")
    
    actual_values = []
    measured_values = []
    skipped_count = 0
    
    # 处理每张标定图像
    for i, (png_path, csv_row) in enumerate(zip(calib_files['png_paths'], 
                                                   calib_files['csv_data'])):
        depth_array = read_depth_image(png_path)
        roi = get_roi(depth_array)
        
        # 平面校准
        result = calibrate_image(roi, apply_filter=use_filter)
        
        if not result['success']:
            skipped_count += 1
            continue
        
        # 计算ROI平均深度
        calibrated_roi = result['calibrated_roi']
        valid_pixels, _ = get_valid_pixels(calibrated_roi)
        
        if valid_pixels.size == 0:
            skipped_count += 1
            continue
        
        avg_gray = valid_pixels.mean()
        avg_mm = gray_to_mm(avg_gray)
        
        actual_values.append(csv_row['实际累计位移(mm)'])
        measured_values.append(avg_mm)
    
    print(f"\n处理完成:")
    print(f"  有效图像: {len(actual_values)}")
    print(f"  跳过图像: {skipped_count}")
    
    # 建立补偿模型
    print(f"\n步骤2: 建立补偿模型")
    model = build_compensation_model(actual_values, measured_values)
    
    print(f"  模型类型: 三次样条")
    print(f"  实际值范围: [{model['actual_range'][0]:.2f}, {model['actual_range'][1]:.2f}] mm")
    print(f"  测量值范围: [{model['measured_range'][0]:.2f}, {model['measured_range'][1]:.2f}] mm")
    
    return {
        'model': model,
        'actual_values': actual_values,
        'measured_values': measured_values
    }


def process_test_data(test_dir, model, use_filter=True):
    """
    处理测试数据，计算补偿前后的线性度
    
    返回:
        dict: 线性度对比结果
    """
    print(f"\n{'='*60}")
    print("步骤3: 处理测试数据")
    print(f"{'='*60}")
    print(f"目录: {test_dir}")
    print(f"滤波: {'启用' if use_filter else '禁用'}")
    
    # 获取测试文件
    test_files = get_image_files(test_dir)
    if not test_files:
        raise FileNotFoundError(f"未找到测试文件: {test_dir}")
    
    print(f"PNG文件: {len(test_files['png_paths'])}张")
    
    actual_values_abs = []  # 绝对值
    measured_values_abs = []  # 绝对值
    skipped_count = 0
    
    # 处理每张测试图像
    for i, (png_path, csv_row) in enumerate(zip(test_files['png_paths'], 
                                                   test_files['csv_data'])):
        depth_array = read_depth_image(png_path)
        roi = get_roi(depth_array)
        
        # 平面校准
        result = calibrate_image(roi, apply_filter=use_filter)
        
        if not result['success']:
            skipped_count += 1
            continue
        
        # 计算ROI平均深度
        calibrated_roi = result['calibrated_roi']
        valid_pixels, _ = get_valid_pixels(calibrated_roi)
        
        if valid_pixels.size == 0:
            skipped_count += 1
            continue
        
        avg_gray = valid_pixels.mean()
        measured_mm = gray_to_mm(avg_gray)
        
        actual_values_abs.append(csv_row['实际累计位移(mm)'])
        measured_values_abs.append(measured_mm)
    
    print(f"\n处理完成:")
    print(f"  有效图像: {len(actual_values_abs)}")
    print(f"  跳过图像: {skipped_count}")
    
    # 转换为numpy数组
    actual_values_abs = np.array(actual_values_abs)
    measured_values_abs = np.array(measured_values_abs)
    
    # 🔥 关键：使用绝对值进行补偿
    compensated_values_abs = apply_compensation(measured_values_abs, model['inverse_model'])
    
    # 🔥 关键修复：转换为相对值（零点归一化）计算线性度
    actual_values = actual_values_abs - actual_values_abs[0]
    measured_values = measured_values_abs - measured_values_abs[0]
    compensated_values = compensated_values_abs - compensated_values_abs[0]
    
    print(f"\n零点归一化:")
    print(f"  实际值零点: {actual_values_abs[0]:.2f} mm")
    print(f"  测量值零点: {measured_values_abs[0]:.2f} mm")
    print(f"  补偿后零点: {compensated_values_abs[0]:.2f} mm")
    
    # 计算线性度（使用相对值）
    print(f"\n步骤4: 计算线性度")
    effect = calculate_compensation_effect(actual_values, measured_values, compensated_values)
    
    return {
        'effect': effect,
        'actual_values': actual_values.tolist(),
        'measured_values': measured_values.tolist(),
        'compensated_values': compensated_values.tolist()
    }


def compensate_test_images(test_dir, model, output_dir):
    """
    对测试图像进行逐像素补偿并保存
    
    返回:
        dict: 补偿统计信息
    """
    print(f"\n{'='*60}")
    print("步骤5: 逐像素图像补偿")
    print(f"{'='*60}")
    
    # 获取测试文件
    test_files = get_image_files(test_dir)
    if not test_files:
        raise FileNotFoundError(f"未找到测试文件: {test_dir}")
    
    # 创建输出目录
    output_subdir = os.path.join(output_dir, 'compensated_images')
    os.makedirs(output_subdir, exist_ok=True)
    print(f"输出目录: {output_subdir}")
    
    all_stats = []
    
    for i, png_path in enumerate(test_files['png_paths'], 1):
        filename = os.path.basename(png_path)
        print(f"\n[{i}/{len(test_files['png_paths'])}] {filename}")
        
        # 读取并补偿
        depth_array = read_depth_image(png_path)
        result = compensate_image_pixels(depth_array, model['inverse_model'])
        
        # 保存
        output_path = os.path.join(output_subdir, filename)
        Image.fromarray(result['compensated_array']).save(output_path)
        
        # 打印统计
        stats = result['stats']
        print(f"  补偿率: {stats['compensation_rate']:.2f}%")
        print(f"  有效像素: {stats['in_range_pixels']:,} / {stats['valid_pixels']:,}")
        
        all_stats.append(stats)
    
    # 总计
    total_stats = {
        'total_pixels': sum(s['total_pixels'] for s in all_stats),
        'valid_pixels': sum(s['valid_pixels'] for s in all_stats),
        'in_range_pixels': sum(s['in_range_pixels'] for s in all_stats),
        'out_of_range_pixels': sum(s['out_of_range_pixels'] for s in all_stats),
        'invalid_pixels': sum(s['invalid_pixels'] for s in all_stats)
    }
    
    return total_stats


def print_results(test_result):
    """打印结果"""
    effect = test_result['effect']
    before = effect['before']
    after = effect['after']
    
    print(f"\n{'='*60}")
    print("补偿效果总结")
    print(f"{'='*60}")
    
    print(f"\n{'指标':<20} {'补偿前':<15} {'补偿后':<15} {'改善':<10}")
    print("-" * 60)
    print(f"{'线性度':<20} {before['linearity']:.4f}%{' '*8} {after['linearity']:.4f}%{' '*8} {effect['improvement']:.2f}%")
    print(f"{'最大偏差(mm)':<20} {before['abs_max_deviation']:.6f}{' '*8} {after['abs_max_deviation']:.6f}{' '*8} -")
    print(f"{'RMS误差(mm)':<20} {before['rms_error']:.6f}{' '*8} {after['rms_error']:.6f}{' '*8} -")
    print(f"{'R²':<20} {before['r_squared']:.8f}{' '*6} {after['r_squared']:.8f}{' '*6} -")


def save_results(test_result, output_dir, compensate_stats=None):
    """保存结果到文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存CSV（相对值，用于线性度计算）
    csv_path = os.path.join(output_dir, 'compensation_result.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("相对实际值(mm),相对测量值(mm),相对补偿后值(mm)\n")
        for a, m, c in zip(test_result['actual_values'], 
                          test_result['measured_values'],
                          test_result['compensated_values']):
            f.write(f"{a},{m},{c}\n")
    
    print(f"\n结果已保存: {csv_path}")
    print(f"  说明: CSV中保存的是零点归一化的相对值")
    
    # 保存报告
    report_path = os.path.join(output_dir, 'compensation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        effect = test_result['effect']
        before = effect['before']
        after = effect['after']
        
        f.write("深度图补偿报告（最终版）\n")
        f.write("=" * 60 + "\n\n")
        f.write("说明:\n")
        f.write("  - 补偿模型: 使用绝对值建立\n")
        f.write("  - 线性度计算: 使用相对值（零点归一化）\n")
        f.write("  - 滤波填充: 使用有效像素均值（已修复Bug）\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"补偿前线性度: {before['linearity']:.4f}%\n")
        f.write(f"补偿后线性度: {after['linearity']:.4f}%\n")
        f.write(f"改善幅度: {effect['improvement']:.2f}%\n")
        f.write(f"\n补偿前最大偏差: {before['abs_max_deviation']:.6f} mm\n")
        f.write(f"补偿后最大偏差: {after['abs_max_deviation']:.6f} mm\n")
        f.write(f"\n补偿前RMS误差: {before['rms_error']:.6f} mm\n")
        f.write(f"补偿后RMS误差: {after['rms_error']:.6f} mm\n")
        f.write(f"\n补偿前R²: {before['r_squared']:.8f}\n")
        f.write(f"补偿后R²: {after['r_squared']:.8f}\n")
        
        if compensate_stats:
            f.write(f"\n\n图像补偿统计\n")
            f.write("=" * 60 + "\n")
            f.write(f"总像素数: {compensate_stats['total_pixels']:,}\n")
            f.write(f"有效像素: {compensate_stats['valid_pixels']:,} ({compensate_stats['valid_pixels']/compensate_stats['total_pixels']*100:.2f}%)\n")
            f.write(f"补偿像素: {compensate_stats['in_range_pixels']:,} ({compensate_stats['in_range_pixels']/compensate_stats['total_pixels']*100:.2f}%)\n")
    
    print(f"报告已保存: {report_path}")


def main():
    """主程序入口"""
    print("="*60)
    print("深度图补偿系统 - 最终优化版 v2.1")
    print("="*60)
    
    try:
        # 确保输出目录存在
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # 1. 处理标定数据
        calib_result = process_calibration_data(CALIB_DIR, use_filter=FILTER_ENABLED)
        
        # 2. 保存补偿模型
        model_path = os.path.join(OUTPUT_DIR, 'compensation_model.json')
        saved_path = save_model(calib_result['model'], model_path)
        print(f"\n步骤2.1: 保存补偿模型")
        print(f"  模型文件: {saved_path}")
        
        # 3. 处理测试数据
        test_result = process_test_data(TEST_DIR, calib_result['model'], use_filter=FILTER_ENABLED)
        
        # 4. 打印结果
        print_results(test_result)
        
        # 5. 逐像素补偿
        compensate_stats = compensate_test_images(TEST_DIR, calib_result['model'], OUTPUT_DIR)
        
        print(f"\n{'='*60}")
        print("图像补偿统计")
        print(f"{'='*60}")
        print(f"总像素数: {compensate_stats['total_pixels']:,}")
        print(f"补偿像素: {compensate_stats['in_range_pixels']:,} ({compensate_stats['in_range_pixels']/compensate_stats['total_pixels']*100:.2f}%)")
        
        # 6. 保存结果
        save_results(test_result, OUTPUT_DIR, compensate_stats)
        
        print(f"\n{'='*60}")
        print("程序执行成功！")
        print(f"{'='*60}")
        
        return 0
        
    except Exception as e:
        print(f"\n程序执行出错：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

