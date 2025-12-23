# -*- coding: utf-8 -*-
"""
单独补偿脚本 - 加载已保存的模型，对新的测试数据进行补偿
无需重新标定，直接使用已有模型
"""

import os
import sys
import argparse
import numpy as np
from PIL import Image

from config import OUTPUT_DIR, FILTER_ENABLED
from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm
from calibrator import calibrate_image
from compensator import (load_model, apply_compensation, 
                        calculate_compensation_effect, compensate_image_pixels)


def compensate_with_model(test_dir, model_path, output_dir, use_filter=True):
    """
    使用已保存的模型补偿测试数据
    
    参数:
        test_dir: 测试数据目录
        model_path: 模型文件路径 (.npz)
        output_dir: 输出目录
        use_filter: 是否启用滤波
    """
    print("="*60)
    print("深度图补偿系统 - 单独补偿模式")
    print("="*60)
    
    # 1. 加载模型
    print(f"\n步骤1: 加载补偿模型")
    print(f"  模型文件: {model_path}")
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    
    model = load_model(model_path)
    print(f"  模型类型: 三次样条")
    print(f"  标定点数: {len(model['actual_values'])}")
    print(f"  实际值范围: [{model['actual_range'][0]:.2f}, {model['actual_range'][1]:.2f}] mm")
    print(f"  测量值范围: [{model['measured_range'][0]:.2f}, {model['measured_range'][1]:.2f}] mm")
    
    # 2. 处理测试数据
    print(f"\n步骤2: 处理测试数据")
    print(f"  目录: {test_dir}")
    print(f"  滤波: {'启用' if use_filter else '禁用'}")
    
    test_files = get_image_files(test_dir)
    if not test_files:
        raise FileNotFoundError(f"未找到测试文件: {test_dir}")
    
    print(f"  PNG文件: {len(test_files['png_paths'])}张")
    
    actual_values_abs = []
    measured_values_abs = []
    skipped_count = 0
    
    for png_path, csv_row in zip(test_files['png_paths'], test_files['csv_data']):
        depth_array = read_depth_image(png_path)
        roi = get_roi(depth_array)
        result = calibrate_image(roi, apply_filter=use_filter)
        
        if not result['success']:
            skipped_count += 1
            continue
        
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
    
    # 应用补偿
    compensated_values_abs = apply_compensation(measured_values_abs, model['inverse_model'])
    
    # 转换为相对值
    actual_values = actual_values_abs - actual_values_abs[0]
    measured_values = measured_values_abs - measured_values_abs[0]
    compensated_values = compensated_values_abs - compensated_values_abs[0]
    
    print(f"\n零点归一化:")
    print(f"  实际值零点: {actual_values_abs[0]:.2f} mm")
    print(f"  测量值零点: {measured_values_abs[0]:.2f} mm")
    print(f"  补偿后零点: {compensated_values_abs[0]:.2f} mm")
    
    # 3. 计算线性度
    print(f"\n步骤3: 计算线性度")
    effect = calculate_compensation_effect(actual_values, measured_values, compensated_values)
    
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
    
    # 4. 逐像素补偿
    print(f"\n步骤4: 逐像素图像补偿")
    output_subdir = os.path.join(output_dir, 'compensated_images')
    os.makedirs(output_subdir, exist_ok=True)
    print(f"  输出目录: {output_subdir}")
    
    total_compensated = 0
    total_pixels = 0
    
    for i, png_path in enumerate(test_files['png_paths'], 1):
        filename = os.path.basename(png_path)
        print(f"\n[{i}/{len(test_files['png_paths'])}] {filename}")
        
        depth_array = read_depth_image(png_path)
        result = compensate_image_pixels(depth_array, model['inverse_model'])
        
        output_path = os.path.join(output_subdir, filename)
        Image.fromarray(result['compensated_array']).save(output_path)
        
        stats = result['stats']
        total_compensated += stats['in_range_pixels']
        total_pixels += stats['total_pixels']
        
        print(f"  补偿率: {stats['compensation_rate']:.2f}%")
        print(f"  有效像素: {stats['in_range_pixels']:,} / {stats['valid_pixels']:,}")
    
    # 5. 保存结果
    print(f"\n步骤5: 保存结果")
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存CSV
    csv_path = os.path.join(output_dir, 'compensation_result.csv')
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("相对实际值(mm),相对测量值(mm),相对补偿后值(mm)\n")
        for a, m, c in zip(actual_values, measured_values, compensated_values):
            f.write(f"{a},{m},{c}\n")
    
    # 保存报告
    report_path = os.path.join(output_dir, 'compensation_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("深度图补偿报告（单独补偿模式）\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"使用模型: {model_path}\n")
        f.write(f"测试目录: {test_dir}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"补偿前线性度: {before['linearity']:.4f}%\n")
        f.write(f"补偿后线性度: {after['linearity']:.4f}%\n")
        f.write(f"改善幅度: {effect['improvement']:.2f}%\n\n")
        f.write(f"补偿前R²: {before['r_squared']:.8f}\n")
        f.write(f"补偿后R²: {after['r_squared']:.8f}\n\n")
        f.write(f"图像补偿统计\n")
        f.write("=" * 60 + "\n")
        f.write(f"总像素数: {total_pixels:,}\n")
        f.write(f"补偿像素: {total_compensated:,} ({total_compensated/total_pixels*100:.2f}%)\n")
    
    print(f"\n结果已保存:")
    print(f"  CSV: {csv_path}")
    print(f"  报告: {report_path}")
    
    print(f"\n{'='*60}")
    print("补偿完成！")
    print(f"{'='*60}")
    
    return effect


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='使用已保存的模型补偿测试数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python compensate_only.py -m output/compensation_model.json -t ../AW0350000R7J0004/test_20251216_143213
  python compensate_only.py -m output/compensation_model.json -t test_data -o result --no-filter
        '''
    )
    
    parser.add_argument('-m', '--model', required=True,
                        help='模型文件路径 (.json)')
    parser.add_argument('-t', '--test-dir', required=True,
                        help='测试数据目录')
    parser.add_argument('-o', '--output-dir', default='output',
                        help='输出目录 (默认: output)')
    parser.add_argument('--no-filter', action='store_true',
                        help='禁用滤波处理')
    
    args = parser.parse_args()
    
    try:
        compensate_with_model(
            test_dir=args.test_dir,
            model_path=args.model,
            output_dir=args.output_dir,
            use_filter=not args.no_filter
        )
        return 0
    except Exception as e:
        print(f"\n程序执行出错：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

