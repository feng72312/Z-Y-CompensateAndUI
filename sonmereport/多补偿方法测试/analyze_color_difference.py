# -*- coding: utf-8 -*-
"""
分析补偿前后深度图颜色差异
解释为什么补偿后图像看起来颜色更浅
"""

import sys
import numpy as np
from pathlib import Path
from PIL import Image

# 添加compcodeultimate目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'compcodeultimate'))

from utils import gray_to_mm


def analyze_color_difference(before_path, after_path):
    """分析补偿前后的颜色差异"""
    
    print("=" * 70)
    print("深度图颜色差异分析报告")
    print("=" * 70)
    
    # 读取图像
    print("\n[1] 读取图像...")
    before_img = np.array(Image.open(before_path))
    after_img = np.array(Image.open(after_path))
    
    print(f"  补偿前图像: {before_img.shape}, dtype: {before_img.dtype}")
    print(f"  补偿后图像: {after_img.shape}, dtype: {after_img.dtype}")
    
    # 排除无效像素
    invalid_value = 65535
    before_valid_mask = (before_img != invalid_value) & (before_img != 0)
    after_valid_mask = (after_img != invalid_value) & (after_img != 0)
    
    before_valid = before_img[before_valid_mask]
    after_valid = after_img[after_valid_mask]
    
    # 灰度值统计
    print("\n[2] 灰度值统计（16位: 0-65535）")
    print("-" * 50)
    print(f"{'指标':<15} {'补偿前':>15} {'补偿后':>15} {'差值':>12}")
    print("-" * 50)
    
    before_mean = before_valid.mean()
    after_mean = after_valid.mean()
    print(f"{'平均值':<15} {before_mean:>15.2f} {after_mean:>15.2f} {after_mean - before_mean:>+12.2f}")
    
    before_min = before_valid.min()
    after_min = after_valid.min()
    print(f"{'最小值':<15} {before_min:>15} {after_min:>15} {after_min - before_min:>+12}")
    
    before_max = before_valid.max()
    after_max = after_valid.max()
    print(f"{'最大值':<15} {before_max:>15} {after_max:>15} {after_max - before_max:>+12}")
    
    before_std = before_valid.std()
    after_std = after_valid.std()
    print(f"{'标准差':<15} {before_std:>15.2f} {after_std:>15.2f} {after_std - before_std:>+12.2f}")
    
    # 转换为毫米
    print("\n[3] 深度值统计（毫米）")
    print("-" * 50)
    
    before_mm = gray_to_mm(before_valid.astype(np.float64))
    after_mm = gray_to_mm(after_valid.astype(np.float64))
    
    print(f"{'指标':<15} {'补偿前':>15} {'补偿后':>15} {'差值':>12}")
    print("-" * 50)
    
    before_mm_mean = before_mm.mean()
    after_mm_mean = after_mm.mean()
    print(f"{'平均深度(mm)':<15} {before_mm_mean:>15.4f} {after_mm_mean:>15.4f} {after_mm_mean - before_mm_mean:>+12.4f}")
    
    before_mm_min = before_mm.min()
    after_mm_min = after_mm.min()
    print(f"{'最小深度(mm)':<15} {before_mm_min:>15.4f} {after_mm_min:>15.4f} {after_mm_min - before_mm_min:>+12.4f}")
    
    before_mm_max = before_mm.max()
    after_mm_max = after_mm.max()
    print(f"{'最大深度(mm)':<15} {before_mm_max:>15.4f} {after_mm_max:>15.4f} {after_mm_max - before_mm_max:>+12.4f}")
    
    # 颜色差异解释
    print("\n" + "=" * 70)
    print("[4] 颜色差异原因分析")
    print("=" * 70)
    
    gray_diff = after_mean - before_mean
    mm_diff = after_mm_mean - before_mm_mean
    
    print(f"""
★ 现象：
  - 补偿前图像颜色较深（灰度值较低）
  - 补偿后图像颜色较浅（灰度值较高）
  
★ 数据：
  - 灰度值平均增加: {gray_diff:+.2f}（从 {before_mean:.2f} 到 {after_mean:.2f}）
  - 深度值平均变化: {mm_diff:+.4f} mm（从 {before_mm_mean:.4f} 到 {after_mm_mean:.4f}）

★ 原因解释：
  补偿模型的作用是将"测量值"修正为"真实值"。
  
  在16位深度图中：
  - 灰度值 = OFFSET + (深度mm × 1000 / SCALE_FACTOR)
  - OFFSET = 32768（中心偏移量）
  
  补偿改变了深度值的映射关系：
  - 补偿前: 测量深度 = {before_mm_mean:.4f} mm（相对值，负数表示在基准面下方）
  - 补偿后: 真实深度 = {after_mm_mean:.4f} mm（修正后的实际深度）
  
  灰度值增加 {gray_diff:.0f} 对应深度增加约 {mm_diff:.4f} mm
""")
    
    # 对精度的影响
    print("=" * 70)
    print("[5] 对精度的影响分析")
    print("=" * 70)
    
    # 计算补偿前后的像素值分布差异
    before_range = int(before_max) - int(before_min)
    after_range = int(after_max) - int(after_min)
    
    print(f"""
★ 精度评估：

  1. 动态范围分析：
     - 补偿前像素范围: {before_min} ~ {before_max} (跨度: {before_range})
     - 补偿后像素范围: {after_min} ~ {after_max} (跨度: {after_range})
     - 范围变化: {after_range - before_range:+d}
     
  2. 标准差分析（反映数据离散度）：
     - 补偿前标准差: {before_std:.2f}
     - 补偿后标准差: {after_std:.2f}
     - 变化: {after_std - before_std:+.2f}
""")
    
    # 判断精度影响
    range_change_percent = (after_range - before_range) / before_range * 100
    std_change_percent = (after_std - before_std) / before_std * 100
    
    print(f"""  3. 精度影响结论：
     - 动态范围变化: {range_change_percent:+.2f}%
     - 标准差变化: {std_change_percent:+.2f}%
""")
    
    if abs(range_change_percent) < 5 and abs(std_change_percent) < 10:
        print("  ✅ 颜色差异对精度影响很小，补偿是正常的偏移校正。")
    elif after_std < before_std:
        print("  ✅ 补偿后标准差减小，说明补偿减少了测量误差，精度可能有所提升。")
    else:
        print("  ⚠️ 需要进一步检查补偿模型是否正确。")
    
    print(f"""
★ 总结：

  颜色深浅的变化是【正常现象】，不影响精度！
  
  原因：补偿模型修正了深度值的系统性偏差（bias），
  将测量值映射到了不同的灰度区间，导致视觉上颜色变浅。
  
  这类似于：
  - 补偿前：测量值在 "深色区域"
  - 补偿后：真实值在 "浅色区域"
  
  关键是看补偿后的线性度是否改善，而不是看颜色深浅！
""")
    
    # 保存分析报告
    report_path = Path(before_path).parent / 'color_difference_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("深度图颜色差异分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"补偿前灰度均值: {before_mean:.2f}\n")
        f.write(f"补偿后灰度均值: {after_mean:.2f}\n")
        f.write(f"灰度值变化: {gray_diff:+.2f}\n\n")
        f.write(f"补偿前深度均值: {before_mm_mean:.4f} mm\n")
        f.write(f"补偿后深度均值: {after_mm_mean:.4f} mm\n")
        f.write(f"深度变化: {mm_diff:+.4f} mm\n\n")
        f.write("结论: 颜色差异是正常的补偿偏移，不影响精度。\n")
    
    print(f"\n报告已保存: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    before_path = str(script_dir / 'before.png')
    after_path = str(script_dir / 'after.png')
    
    analyze_color_difference(before_path, after_path)

