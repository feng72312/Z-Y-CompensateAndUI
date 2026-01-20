# -*- coding: utf-8 -*-
"""
批量线性度计算工具
与完整流程使用完全相同的算法
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

from config import (FULL_SCALE, FILTER_ENABLED,
                    ANOMALY_DETECTION_ENABLED, ANOMALY_THRESHOLD,
                    PLANE_STD_WARNING_ENABLED, PLANE_STD_THRESHOLD)
from utils import get_image_files, read_depth_image, get_roi, get_valid_pixels, gray_to_mm, detect_anomalies
from calibrator import calibrate_image
from compensator import load_model, apply_compensation, calculate_linearity


def calculate_batch_linearity(test_dir, model_path=None, output_path=None, 
                               use_filter=True, full_scale=None, roi_config=None,
                               depth_offset=None, depth_scale_factor=None):
    """
    批量计算线性度 - 与完整流程使用相同算法
    
    参数:
        test_dir: 测试数据目录（包含PNG和CSV）
        model_path: 模型文件路径（可选，如果提供则计算补偿后线性度）
        output_path: 结果输出路径（可选）
        use_filter: 是否使用滤波
        full_scale: 满量程（mm）
        roi_config: ROI配置字典（可选）
        depth_offset: 深度转换偏移量（可选，默认使用config中的值）
        depth_scale_factor: 深度转换缩放因子（可选，默认使用config中的值）
    
    返回:
        dict: 线性度计算结果
    """
    # 满量程处理
    if full_scale is None or full_scale == 0:
        full_scale = FULL_SCALE
    full_scale = float(full_scale)
    
    # 默认ROI配置（使用全部图像）
    if roi_config is None:
        roi_config = {'x': 0, 'y': 0, 'width': -1, 'height': -1}
    
    print("=" * 60)
    print("批量线性度计算工具（与完整流程算法一致）")
    print("=" * 60)
    
    # 使用 Path 处理中文路径
    test_dir = str(Path(test_dir))
    
    print(f"\n测试目录: {test_dir}")
    print(f"滤波: {'启用' if use_filter else '禁用'}")
    print(f"满量程: {full_scale} mm")
    
    # 显示深度转换系数
    if depth_offset is not None or depth_scale_factor is not None:
        from config import OFFSET, SCALE_FACTOR
        actual_offset = depth_offset if depth_offset is not None else OFFSET
        actual_scale = depth_scale_factor if depth_scale_factor is not None else SCALE_FACTOR
        print(f"深度转换: 偏移量={actual_offset}, 缩放因子={actual_scale}")
    
    # 显示ROI信息
    if roi_config['width'] == -1 and roi_config['height'] == -1 and roi_config['x'] == 0 and roi_config['y'] == 0:
        print(f"ROI: 使用全部图像")
    else:
        roi_desc = f"ROI: X=[{roi_config['x']}, {'边缘' if roi_config['width']==-1 else roi_config['x']+roi_config['width']}], "
        roi_desc += f"Y=[{roi_config['y']}, {'边缘' if roi_config['height']==-1 else roi_config['y']+roi_config['height']}]"
        print(roi_desc)
    
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
    
    # ==================== 与完整流程相同的处理逻辑 ====================
    # 处理每张图像，获取绝对值
    actual_abs = []
    measured_abs = []
    image_plane_stds = []  # 每张图像的平面标准差
    image_results = []
    
    print("\n处理图像:")
    print("-" * 60)
    
    for i, (png_path, csv_row) in enumerate(zip(test_files['png_paths'], test_files['csv_data']), 1):
        filename = os.path.basename(png_path)
        
        depth_array = read_depth_image(png_path)
        
        # 提取ROI（与完整流程相同）
        roi = get_roi(depth_array, 
                      x=roi_config['x'], 
                      y=roi_config['y'], 
                      width=roi_config['width'], 
                      height=roi_config['height'])
        
        # 校准（与完整流程相同）
        result = calibrate_image(roi, apply_filter=use_filter)
        
        if not result['success']:
            print(f"[{i}] {filename} - 跳过（{result.get('reason', '校准失败')}）")
            continue
        
        calibrated_roi = result['calibrated_roi']
        valid_pixels, _ = get_valid_pixels(calibrated_roi)
        
        if valid_pixels.size == 0:
            print(f"[{i}] {filename} - 跳过（无有效像素）")
            continue
        
        # 计算平均灰度值并转换为毫米（与完整流程相同）
        avg_gray = valid_pixels.mean()
        measured_mm = gray_to_mm(avg_gray, offset=depth_offset, scale_factor=depth_scale_factor)
        actual_mm = csv_row['实际累计位移(mm)']
        
        # 计算平面标准差
        valid_pixels_mm = gray_to_mm(valid_pixels, offset=depth_offset, scale_factor=depth_scale_factor)
        plane_std = np.std(valid_pixels_mm)
        image_plane_stds.append(plane_std)
        
        actual_abs.append(actual_mm)
        measured_abs.append(measured_mm)
        
        image_results.append({
            'filename': filename,
            'actual': actual_mm,
            'measured': measured_mm,
            'plane_std': plane_std
        })
        
        print(f"[{i}] {filename}: 实际={actual_mm:.4f}mm, 测量={measured_mm:.4f}mm")
    
    print("-" * 60)
    print(f"有效图像: {len(actual_abs)} / {len(test_files['png_paths'])}")
    
    if len(actual_abs) < 2:
        raise ValueError("有效图像数量不足，无法计算线性度")
    
    # 转换为numpy数组
    actual_abs = np.array(actual_abs)
    measured_abs = np.array(measured_abs)
    
    # ==================== 数据质量检测 ====================
    anomaly_result = None
    avg_plane_std = None
    warnings_found = False
    
    # 1. 异常点检测
    if ANOMALY_DETECTION_ENABLED and len(actual_abs) >= 2:
        anomaly_result = detect_anomalies(actual_abs, measured_abs, ANOMALY_THRESHOLD)
        if anomaly_result['has_anomaly']:
            warnings_found = True
            print(anomaly_result['warning_message'])
    
    # 2. 平面标准差检测
    if PLANE_STD_WARNING_ENABLED and image_plane_stds:
        avg_plane_std = np.mean(image_plane_stds)
        print(f"\n平面标准差均值: {avg_plane_std:.6f} mm")
        if avg_plane_std > PLANE_STD_THRESHOLD:
            warnings_found = True
            print("=" * 60)
            print(f"[警告] 平面标准差均值 ({avg_plane_std:.6f} mm) 超过阈值 ({PLANE_STD_THRESHOLD} mm)!")
            print("=" * 60)
            print("[建议] 数据平面度较差，建议:")
            print("  1. 重新采集数据")
            print("  2. 调整ROI区域，避开边缘或异常区域")
            print("  3. 检查测试平面是否平整")
            print("=" * 60)
    
    # ==================== 关键：与完整流程相同的归一化处理 ====================
    # 转换为相对值（零点归一化）
    actual_rel = actual_abs - actual_abs[0]
    measured_rel = measured_abs - measured_abs[0]
    
    print(f"\n零点归一化:")
    print(f"  实际值第一个点: {actual_abs[0]:.4f} mm -> 0")
    print(f"  测量值第一个点: {measured_abs[0]:.4f} mm -> 0")
    
    # ==================== 计算补偿前线性度（使用相对值）====================
    print("\n" + "=" * 60)
    print("线性度计算结果")
    print("=" * 60)
    
    # 直接调用 calculate_linearity，输入已经是相对值
    linearity_before = calculate_linearity(actual_rel, measured_rel, full_scale)
    
    print(f"\n【补偿前】")
    print(f"  线性度: {linearity_before['linearity']:.4f}%")
    print(f"  最大偏差: {linearity_before['abs_max_deviation']:.6f} mm")
    print(f"  RMS误差: {linearity_before['rms_error']:.6f} mm")
    print(f"  R2: {linearity_before['r_squared']:.8f}")
    print(f"  斜率: {linearity_before['slope']:.6f}")
    print(f"  截距: {linearity_before['intercept']:.6f} mm")
    
    result = {
        'test_dir': test_dir,
        'num_images': len(actual_abs),
        'full_scale': full_scale,
        'roi_config': roi_config,
        'before': linearity_before,
        'image_results': image_results,
        # 保存原始数据供调试
        'actual_abs': actual_abs.tolist(),
        'measured_abs': measured_abs.tolist(),
        'actual_rel': actual_rel.tolist(),
        'measured_rel': measured_rel.tolist(),
        # 数据质量检测结果
        'anomaly_result': anomaly_result,
        'avg_plane_std': avg_plane_std,
        'warnings_found': warnings_found
    }
    
    # 如果有模型，计算补偿后线性度
    if model:
        # 补偿（使用绝对值）
        compensated_abs = apply_compensation(measured_abs, model['inverse_model'])
        # 转换为相对值
        compensated_rel = compensated_abs - compensated_abs[0]
        
        # 计算补偿后线性度（使用相对值）
        linearity_after = calculate_linearity(actual_rel, compensated_rel, full_scale)
        
        improvement = ((linearity_before['linearity'] - linearity_after['linearity']) 
                       / linearity_before['linearity'] * 100.0
                       if linearity_before['linearity'] != 0 else 0)
        
        print(f"\n【补偿后】")
        print(f"  线性度: {linearity_after['linearity']:.4f}%")
        print(f"  最大偏差: {linearity_after['abs_max_deviation']:.6f} mm")
        print(f"  RMS误差: {linearity_after['rms_error']:.6f} mm")
        print(f"  R2: {linearity_after['r_squared']:.8f}")
        
        print(f"\n【改善效果】")
        print(f"  线性度改善: {improvement:.2f}%")
        
        result['after'] = linearity_after
        result['improvement'] = improvement
        result['compensated_abs'] = compensated_abs.tolist()
        result['compensated_rel'] = compensated_rel.tolist()
        
        # 更新图像结果
        for i, r in enumerate(image_results):
            r['compensated'] = float(compensated_abs[i])
    
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
        
        f.write(f"图像数量: {result['num_images']}\n")
        f.write(f"满量程: {result['full_scale']} mm\n")
        
        # 输出ROI信息
        if 'roi_config' in result:
            roi = result['roi_config']
            if roi['width'] == -1 and roi['height'] == -1 and roi['x'] == 0 and roi['y'] == 0:
                f.write(f"ROI设置: 使用全部图像\n\n")
            else:
                x_end = '边缘' if roi['width'] == -1 else roi['x'] + roi['width']
                y_end = '边缘' if roi['height'] == -1 else roi['y'] + roi['height']
                f.write(f"ROI设置: X=[{roi['x']}, {x_end}], Y=[{roi['y']}, {y_end}]\n\n")
        else:
            f.write("\n")
        
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
        
        # 数据质量警告
        warnings_written = False
        
        # 异常点警告
        anomaly_result = result.get('anomaly_result')
        if anomaly_result and anomaly_result.get('has_anomaly'):
            if not warnings_written:
                f.write("【数据质量警告】\n")
                f.write("=" * 60 + "\n")
                warnings_written = True
            
            f.write("[异常点检测]\n")
            f.write(f"  检测阈值: 实际增量的 {ANOMALY_THRESHOLD*100:.0f}%\n")
            f.write("  异常点:\n")
            for idx, act_inc, mea_inc, dev in anomaly_result['anomaly_points']:
                f.write(f"    点{idx}->点{idx+1}: 实际增量={act_inc:.4f}mm, 测量增量={mea_inc:.4f}mm, 偏差={dev:.1f}%\n")
            f.write("  [建议] 检测到数据异常，可能存在硬件抖动，建议重新采集数据\n\n")
        
        # 平面标准差警告
        avg_plane_std = result.get('avg_plane_std')
        if avg_plane_std is not None and avg_plane_std > PLANE_STD_THRESHOLD:
            if not warnings_written:
                f.write("【数据质量警告】\n")
                f.write("=" * 60 + "\n")
                warnings_written = True
            
            f.write("[平面标准差警告]\n")
            f.write(f"  平面标准差均值: {avg_plane_std:.6f} mm\n")
            f.write(f"  警告阈值: {PLANE_STD_THRESHOLD} mm\n")
            f.write("  [建议] 平面度较差，建议重新采集数据或调整ROI区域\n\n")
        
        if warnings_written:
            f.write("=" * 60 + "\n\n")
        
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
        description='批量计算图像线性度（与完整流程算法一致）',
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
