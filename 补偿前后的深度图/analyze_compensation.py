# -*- coding: utf-8 -*-
"""
深度图补偿前后对比分析脚本
分析补偿后出现"多余点"的原因
"""

import sys
import os
import numpy as np
from pathlib import Path
from PIL import Image
import cv2

# 添加compcodeultimate目录到路径
compcodeultimate_dir = Path(__file__).resolve().parent.parent / 'compcodeultimate'
sys.path.insert(0, str(compcodeultimate_dir))

from utils import gray_to_mm, mm_to_gray
from compensator import load_model, get_model_range

def analyze_depth_images(before_path, after_path, model_path):
    """分析补偿前后的深度图差异"""
    
    print("=" * 60)
    print("深度图补偿分析报告")
    print("=" * 60)
    
    # 1. 读取图像（使用PIL支持中文路径）
    print("\n[1] 读取图像...")
    try:
        before_img = np.array(Image.open(before_path))
        after_img = np.array(Image.open(after_path))
    except Exception as e:
        print(f"错误：无法读取图像 - {e}")
        return
    
    print(f"  补偿前图像尺寸: {before_img.shape}, 类型: {before_img.dtype}")
    print(f"  补偿后图像尺寸: {after_img.shape}, 类型: {after_img.dtype}")
    
    # 2. 加载模型
    print("\n[2] 加载补偿模型...")
    model = load_model(model_path)
    inverse_model = model['inverse_model']
    model_min, model_max = get_model_range(inverse_model)
    print(f"  模型有效范围: {model_min:.4f} mm ~ {model_max:.4f} mm")
    
    # 3. 基本统计
    print("\n[3] 像素值基本统计...")
    
    # 无效值（16位深度图通常用65535表示无效）
    invalid_value = 65535
    
    # 补偿前统计
    before_valid_mask = (before_img != invalid_value) & (before_img != 0)
    before_valid = before_img[before_valid_mask]
    before_invalid_65535 = np.sum(before_img == invalid_value)
    before_zero = np.sum(before_img == 0)
    
    print(f"\n  补偿前图像:")
    print(f"    总像素数: {before_img.size:,}")
    print(f"    有效像素: {len(before_valid):,} ({len(before_valid)/before_img.size*100:.2f}%)")
    print(f"    值为0的像素: {before_zero:,}")
    print(f"    值为65535的像素: {before_invalid_65535:,}")
    print(f"    有效像素灰度范围: {before_valid.min()} ~ {before_valid.max()}")
    print(f"    有效像素灰度均值: {before_valid.mean():.2f}")
    
    # 补偿后统计
    after_valid_mask = (after_img != invalid_value) & (after_img != 0)
    after_valid = after_img[after_valid_mask]
    after_invalid_65535 = np.sum(after_img == invalid_value)
    after_zero = np.sum(after_img == 0)
    
    print(f"\n  补偿后图像:")
    print(f"    总像素数: {after_img.size:,}")
    print(f"    有效像素: {len(after_valid):,} ({len(after_valid)/after_img.size*100:.2f}%)")
    print(f"    值为0的像素: {after_zero:,}")
    print(f"    值为65535的像素: {after_invalid_65535:,}")
    if len(after_valid) > 0:
        print(f"    有效像素灰度范围: {after_valid.min()} ~ {after_valid.max()}")
        print(f"    有效像素灰度均值: {after_valid.mean():.2f}")
    
    # 4. 分析范围外像素
    print("\n[4] 分析超出模型范围的像素...")
    
    # 将灰度值转换为毫米
    before_mm = gray_to_mm(before_img.astype(np.float64))
    
    # 找出在模型范围外的有效像素
    valid_mask = (before_img != invalid_value)
    below_range_mask = valid_mask & (before_mm < model_min)
    above_range_mask = valid_mask & (before_mm > model_max)
    in_range_mask = valid_mask & (before_mm >= model_min) & (before_mm <= model_max)
    
    below_count = np.sum(below_range_mask)
    above_count = np.sum(above_range_mask)
    in_range_count = np.sum(in_range_mask)
    
    print(f"  模型范围: [{model_min:.4f}, {model_max:.4f}] mm")
    print(f"  有效像素总数: {np.sum(valid_mask):,}")
    print(f"  在范围内的像素: {in_range_count:,} ({in_range_count/np.sum(valid_mask)*100:.2f}%)")
    print(f"  低于范围的像素: {below_count:,} ({below_count/np.sum(valid_mask)*100:.2f}%)")
    print(f"  高于范围的像素: {above_count:,} ({above_count/np.sum(valid_mask)*100:.2f}%)")
    
    if below_count > 0:
        below_mm = before_mm[below_range_mask]
        print(f"    低于范围的像素mm范围: {below_mm.min():.4f} ~ {below_mm.max():.4f}")
    
    if above_count > 0:
        above_mm = before_mm[above_range_mask]
        print(f"    高于范围的像素mm范围: {above_mm.min():.4f} ~ {above_mm.max():.4f}")
    
    # 5. 分析补偿后变为0的像素
    print("\n[5] 分析'多余点'产生的原因...")
    
    # 补偿前有效但补偿后变为0的像素
    became_zero = (before_img != invalid_value) & (before_img != 0) & (after_img == 0)
    became_zero_count = np.sum(became_zero)
    
    print(f"  补偿后新增的0值像素: {became_zero_count:,}")
    
    if became_zero_count > 0:
        # 这些像素在补偿前的值
        became_zero_before_gray = before_img[became_zero]
        became_zero_before_mm = gray_to_mm(became_zero_before_gray.astype(np.float64))
        
        print(f"  这些像素补偿前的灰度范围: {became_zero_before_gray.min()} ~ {became_zero_before_gray.max()}")
        print(f"  这些像素补偿前的mm范围: {became_zero_before_mm.min():.4f} ~ {became_zero_before_mm.max():.4f}")
        
        # 检查这些是否都在范围外
        out_of_range_became_zero = np.sum((became_zero_before_mm < model_min) | (became_zero_before_mm > model_max))
        print(f"  其中超出模型范围的像素: {out_of_range_became_zero:,}")
    
    # 6. 问题诊断
    print("\n[6] 问题诊断...")
    print("=" * 60)
    
    # 分析65535变成0的情况
    was_65535 = (before_img == invalid_value)
    now_zero = (after_img == 0)
    invalid_to_zero = was_65535 & now_zero
    invalid_to_zero_count = np.sum(invalid_to_zero)
    
    print(f"\n  补偿前65535像素数: {np.sum(was_65535):,}")
    print(f"  补偿后0像素数: {np.sum(now_zero):,}")
    print(f"  65535变成0的像素数: {invalid_to_zero_count:,}")
    
    if invalid_to_zero_count > 0:
        print("\n★ 问题原因确认：")
        print("  补偿后出现的'多余点'（黑色散点）是因为：")
        print("  原图中的无效像素（灰度值65535，显示为白色）")
        print("  在补偿处理后被设置为0（黑色）！")
        print("\n  这是 compensate_image_pixels 函数的一个BUG：")
        print("  函数用 np.zeros_like() 初始化输出数组，")
        print("  然后只更新有效像素，导致无效像素变成了0。")
        print("\n★ 解决方案：")
        print("  修改 compensator.py 中的 compensate_image_pixels 函数，")
        print("  对于无效像素应该保持原值（65535）而不是变成0。")
    
    if became_zero_count > 0 and below_count + above_count > 0:
        print("\n★ 额外问题：")
        print("  部分像素的测量值超出了补偿模型的有效范围。")
        print("  当像素值超出模型范围 [{:.4f}, {:.4f}] mm 时，".format(model_min, model_max))
        print("  补偿函数将它们的输出设为0（黑色），导致图像中出现散点。")
    
    # 7. 可视化差异
    print("\n[7] 生成可视化图像...")
    
    # 创建差异图
    diff_img = np.zeros((before_img.shape[0], before_img.shape[1], 3), dtype=np.uint8)
    
    # 标记不同类型的像素
    # 蓝色：补偿后变为0的像素
    diff_img[became_zero] = [255, 0, 0]  # BGR - 蓝色
    
    # 红色：超出范围的像素（补偿前）
    diff_img[below_range_mask | above_range_mask] = [0, 0, 255]  # BGR - 红色
    
    # 绿色：正常补偿的像素
    diff_img[in_range_mask] = [0, 255, 0]  # BGR - 绿色
    
    # 灰色：无效像素
    diff_img[~valid_mask] = [128, 128, 128]
    
    output_dir = Path(before_path).parent
    diff_path = output_dir / 'analysis_result.png'
    # 使用PIL保存图像（支持中文路径）
    Image.fromarray(diff_img[:, :, ::-1]).save(str(diff_path))  # BGR to RGB
    print(f"  差异可视化已保存: {diff_path}")
    print("    绿色 = 正常补偿的像素")
    print("    红色 = 超出模型范围的像素")
    print("    蓝色 = 补偿后变为0的像素")
    print("    灰色 = 无效像素")
    
    # 保存分析报告
    report_path = output_dir / 'analysis_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("深度图补偿分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"模型有效范围: {model_min:.4f} ~ {model_max:.4f} mm\n")
        f.write(f"补偿前有效像素: {np.sum(valid_mask):,}\n")
        f.write(f"在范围内像素: {in_range_count:,} ({in_range_count/np.sum(valid_mask)*100:.2f}%)\n")
        f.write(f"超出范围像素: {below_count + above_count:,} ({(below_count + above_count)/np.sum(valid_mask)*100:.2f}%)\n")
        f.write(f"补偿前65535像素: {np.sum(was_65535):,}\n")
        f.write(f"补偿后0像素: {np.sum(now_zero):,}\n")
        f.write(f"65535变成0的像素: {invalid_to_zero_count:,}\n\n")
        f.write("问题原因:\n")
        f.write("  compensate_image_pixels函数中，输出数组用zeros初始化，\n")
        f.write("  无效像素（65535）没有被更新，所以变成了0（黑色）。\n\n")
        f.write("解决方案:\n")
        f.write("  修改compensator.py，使用depth_array.copy()初始化输出数组，\n")
        f.write("  保持无效像素和超范围像素的原始值。\n")
    
    print(f"  分析报告已保存: {report_path}")
    print("\n" + "=" * 60)
    print("分析完成！")


if __name__ == "__main__":
    # 默认路径
    script_dir = Path(__file__).resolve().parent
    before_path = str(script_dir / 'before.png')
    after_path = str(script_dir / 'after.png')
    model_path = str(script_dir.parent / 'compcodeultimate' / 'output' / 'compensation_model.json')
    
    analyze_depth_images(before_path, after_path, model_path)

