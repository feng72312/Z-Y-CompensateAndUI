# -*- coding: utf-8 -*-
"""
批量线性度计算工具
支持对一批图像计算补偿前后的线性度
支持中文路径
"""

import os
import sys
import argparse
import numpy as np
from pathlib import Path

# 确保支持中文路径
if sys.platform == 'win32':
    import locale
    locale.setlocale(locale.LC_ALL, '')

from config import FULL_SCALE, FILTER_ENABLED
from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm
from calibrator import calibrate_image
from compensator import load_model, apply_compensation, calculate_linearity


def calculate_batch_linearity(test_dir, model_path=None, output_path=None, 
                               use_filter=True, full_scale=None):
    """
    批量计算线性度
    
    参数:
        test_dir: 测试数据目录（包含PNG和CSV）
        model_path: 模型文件路径（可选，如果提供则计算补偿后线性度）
        output_path: 结果输出路径（可选）
        use_filter: 是否使用滤波
        full_scale: 满量程（mm）
    
    返回:
        dict: 线性度计算结果
    """
    full_scale = full_scale or FULL_SCALE
    
    print("=" * 60)
    print("批量线性度计算工具")
    print("=" * 60)
    
    # 使用 Path 处理中文路径
    test_dir = str(Path(test_dir))
    
    print(f"\n测试目录: {test_dir}")
    print(f"滤波: {'启用' if use_filter else '禁用'}")
    print(f"满量程: {full_scale} mm")
    
    # 加载模型（如果提供）
    model = None
    if model_path:
        model_path = str(Path(model_path))
        print(f"\n加载补偿模型: {model_path}")
        model = load_model(model_path)
        print(f"  模型范围: [{model['measured_range'][0]:.2f}, {model['measured_range'][1]:.2f}] mm")
    
    # 获取测试文件
    test_files = get_image_files(test_dir)
    if not test_files:
        raise FileNotFoundError(f"未找到测试文件: {test_dir}")
    
    print(f"\n找到 {len(test_files['png_paths'])} 张图像")
    
    # 处理每张图像
    actual_values = []
    measured_values = []
    image_results = []
    
    print("\n处理图像:")
    print("-" * 60)
    
    for i, (png_path, csv_row) in enumerate(zip(test_files['png_paths'], test_files['csv_data']), 1):
        filename = os.path.basename(png_path)
        
        depth_array = read_depth_image(png_path)
        roi = get_roi(depth_array)
        result = calibrate_image(roi, apply_filter=use_filter)
        
        if not result['success']:
            print(f"[{i}] {filename} - 跳过（{result.get('reason', '校准失败')}）")
            continue
        
        calibrated_roi = result['calibrated_roi']
        valid_pixels, _ = get_valid_pixels(calibrated_roi)
        
        if valid_pixels.size == 0:
            print(f"[{i}] {filename} - 跳过（无有效像素）")
            continue
        
        avg_gray = valid_pixels.mean()
        measured_mm = gray_to_mm(avg_gray)
        actual_mm = csv_row['实际累计位移(mm)']
        
        actual_values.append(actual_mm)
        measured_values.append(measured_mm)
        
        image_results.append({
            'filename': filename,
            'actual': actual_mm,
            'measured': measured_mm
        })
        
        print(f"[{i}] {filename}: 实际={actual_mm:.4f}mm, 测量={measured_mm:.4f}mm")
    
    print("-" * 60)
    print(f"有效图像: {len(actual_values)} / {len(test_files['png_paths'])}")
    
    if len(actual_values) < 2:
        raise ValueError("有效图像数量不足，无法计算线性度")
    
    # 转换为numpy数组
    actual_arr = np.array(actual_values)
    measured_arr = np.array(measured_values)
    
    # 计算补偿前线性度
    print("\n" + "=" * 60)
    print("线性度计算结果")
    print("=" * 60)
    
    linearity_before = calculate_linearity(actual_arr, measured_arr, full_scale)
    
    print(f"\n【补偿前】")
    print(f"  线性度: {linearity_before['linearity']:.4f}%")
    print(f"  最大偏差: {linearity_before['abs_max_deviation']:.6f} mm")
    print(f"  RMS误差: {linearity_before['rms_error']:.6f} mm")
    print(f"  R²: {linearity_before['r_squared']:.8f}")
    print(f"  斜率: {linearity_before['slope']:.6f}")
    print(f"  截距: {linearity_before['intercept']:.6f} mm")
    
    result = {
        'test_dir': test_dir,
        'num_images': len(actual_values),
        'full_scale': full_scale,
        'before': linearity_before,
        'image_results': image_results
    }
    
    # 如果有模型，计算补偿后线性度
    if model:
        compensated_arr = apply_compensation(measured_arr, model['inverse_model'])
        
        linearity_after = calculate_linearity(actual_arr, compensated_arr, full_scale)
        
        improvement = ((linearity_before['linearity'] - linearity_after['linearity']) 
                       / linearity_before['linearity'] * 100.0
                       if linearity_before['linearity'] != 0 else 0)
        
        print(f"\n【补偿后】")
        print(f"  线性度: {linearity_after['linearity']:.4f}%")
        print(f"  最大偏差: {linearity_after['abs_max_deviation']:.6f} mm")
        print(f"  RMS误差: {linearity_after['rms_error']:.6f} mm")
        print(f"  R²: {linearity_after['r_squared']:.8f}")
        
        print(f"\n【改善效果】")
        print(f"  线性度改善: {improvement:.2f}%")
        
        result['after'] = linearity_after
        result['improvement'] = improvement
        
        # 更新图像结果
        for i, r in enumerate(image_results):
            r['compensated'] = float(compensated_arr[i])
    
    # 保存结果
    if output_path:
        output_path = str(Path(output_path))
        save_linearity_result(result, output_path, model is not None)
        print(f"\n结果已保存: {output_path}")
    
    print("\n" + "=" * 60)
    print("计算完成！")
    print("=" * 60)
    
    return result


def save_linearity_result(result, output_path, has_compensation=False):
    """保存线性度计算结果"""
    # 确保目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("批量线性度计算报告\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"测试目录: {result['test_dir']}\n")
        f.write(f"图像数量: {result['num_images']}\n")
        f.write(f"满量程: {result['full_scale']} mm\n\n")
        
        before = result['before']
        f.write("【补偿前线性度】\n")
        f.write(f"  线性度: {before['linearity']:.4f}%\n")
        f.write(f"  最大偏差: {before['abs_max_deviation']:.6f} mm\n")
        f.write(f"  RMS误差: {before['rms_error']:.6f} mm\n")
        f.write(f"  R²: {before['r_squared']:.8f}\n")
        f.write(f"  斜率: {before['slope']:.6f}\n")
        f.write(f"  截距: {before['intercept']:.6f} mm\n\n")
        
        if has_compensation and 'after' in result:
            after = result['after']
            f.write("【补偿后线性度】\n")
            f.write(f"  线性度: {after['linearity']:.4f}%\n")
            f.write(f"  最大偏差: {after['abs_max_deviation']:.6f} mm\n")
            f.write(f"  RMS误差: {after['rms_error']:.6f} mm\n")
            f.write(f"  R²: {after['r_squared']:.8f}\n\n")
            f.write(f"【改善效果】: {result['improvement']:.2f}%\n\n")
        
        f.write("【逐图像数据】\n")
        f.write("-" * 60 + "\n")
        
        if has_compensation:
            f.write(f"{'文件名':<40} {'实际值':<12} {'测量值':<12} {'补偿后':<12}\n")
            for r in result['image_results']:
                f.write(f"{r['filename']:<40} {r['actual']:<12.4f} {r['measured']:<12.4f} {r.get('compensated', 0):<12.4f}\n")
        else:
            f.write(f"{'文件名':<40} {'实际值':<12} {'测量值':<12}\n")
            for r in result['image_results']:
                f.write(f"{r['filename']:<40} {r['actual']:<12.4f} {r['measured']:<12.4f}\n")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='批量计算图像线性度（支持中文路径）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 仅计算线性度
  python linearity_calc.py -t ../测试数据/test_001
  
  # 计算补偿前后线性度
  python linearity_calc.py -t ../测试数据/test_001 -m output/compensation_model.json
  
  # 指定满量程和输出文件
  python linearity_calc.py -t test_data -m model.json -o 结果/线性度报告.txt -fs 50.0
        '''
    )
    
    parser.add_argument('-t', '--test-dir', required=True,
                        help='测试数据目录（包含PNG和CSV）')
    parser.add_argument('-m', '--model', default=None,
                        help='补偿模型文件路径（可选，.json格式）')
    parser.add_argument('-o', '--output', default=None,
                        help='结果输出文件路径（可选）')
    parser.add_argument('-fs', '--full-scale', type=float, default=None,
                        help=f'满量程（mm），默认 {FULL_SCALE}')
    parser.add_argument('--no-filter', action='store_true',
                        help='禁用滤波处理')
    
    args = parser.parse_args()
    
    try:
        calculate_batch_linearity(
            test_dir=args.test_dir,
            model_path=args.model,
            output_path=args.output,
            use_filter=not args.no_filter,
            full_scale=args.full_scale
        )
        return 0
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

