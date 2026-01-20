# -*- coding: utf-8 -*-
"""
X位置重复精度测量核心模块
用于通过圆/椭圆拟合计算X方向位置重复精度

功能:
  - 加载深度图（PNG/TIF）
  - 提取深度剖面
  - 圆/椭圆拟合
  - 计算X位置重复精度统计
"""

import os
import re
import numpy as np
from PIL import Image
from scipy.optimize import least_squares


def natural_sort_key(s):
    """
    自然排序的键函数，用于正确排序包含数字的文件名
    例如: 1.tif, 2.tif, ..., 10.tif, 11.tif
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]


def load_depth_image(filepath, roi=None, dynamic_roi=False, depth_offset=32768, depth_scale=1.6):
    """
    加载深度图并转换为物理单位（微米）
    
    Args:
        filepath: 图片路径（PNG或TIF）
        roi: 感兴趣区域 (x_start, x_end, y_start, y_end)，None表示使用全图
        dynamic_roi: 是否使用动态ROI（自动检测有效数据区域）
        depth_offset: 深度转换偏移（默认32768）
        depth_scale: 深度转换缩放因子（默认1.6 μm/count）
    
    Returns:
        - depth_data: 深度数据（μm），无效区域为NaN
        - valid_mask: 有效数据掩码
        - x_offset: X方向偏移（仅当dynamic_roi=True时返回，否则为0）
    """
    img = Image.open(filepath)
    depth_raw = np.array(img, dtype=np.uint16)
    
    # 判断无效值
    file_ext = os.path.splitext(filepath)[1].lower()
    if file_ext in ['.tif', '.tiff']:
        invalid_value = 0
    else:
        invalid_value = 65535
    
    # 转换为物理单位
    valid_mask_full = depth_raw != invalid_value
    depth_data = (depth_raw.astype(np.float64) - depth_offset) * depth_scale
    depth_data[~valid_mask_full] = np.nan
    
    x_offset = 0
    
    # 动态ROI：自动检测有效数据区域
    if dynamic_roi:
        if np.any(valid_mask_full):
            valid_rows = np.where(np.any(valid_mask_full, axis=1))[0]
            valid_cols = np.where(np.any(valid_mask_full, axis=0))[0]
            
            if len(valid_rows) > 0 and len(valid_cols) > 0:
                y_min, y_max = valid_rows[0], valid_rows[-1]
                x_min, x_max = valid_cols[0], valid_cols[-1]
                
                # 裁剪到有效区域
                depth_data = depth_data[y_min:y_max+1, x_min:x_max+1]
                x_offset = x_min  # 记录X偏移
    elif roi:
        x_start, x_end, y_start, y_end = roi
        depth_data = depth_data[y_start:y_end, x_start:x_end]
        x_offset = x_start
    
    valid_mask = ~np.isnan(depth_data)
    
    if dynamic_roi:
        return depth_data, valid_mask, x_offset
    else:
        return depth_data, valid_mask


def extract_depth_profile_for_circle(depth_data, n_rows=50):
    """
    提取深度剖面（用于圆/椭圆拟合）
    取中间n_rows行的平均深度
    
    Args:
        depth_data: 深度数据（μm）
        n_rows: 平均行数
    
    Returns:
        - x_pixels: X方向像素坐标数组
        - z_depths: 对应的深度值数组（μm）
    """
    h, w = depth_data.shape
    valid_rows = np.where(np.any(~np.isnan(depth_data), axis=1))[0]
    
    if len(valid_rows) == 0:
        return None, None
    
    # 取中间n_rows行
    y_center = (valid_rows[0] + valid_rows[-1]) // 2
    y_start = max(0, y_center - n_rows // 2)
    y_end = min(h, y_center + n_rows // 2)
    
    # 计算平均剖面
    profile = np.nanmean(depth_data[y_start:y_end, :], axis=0)
    valid_mask = ~np.isnan(profile)
    
    if np.sum(valid_mask) < 50:
        return None, None
    
    x_pixels = np.arange(w)[valid_mask]
    z_depths = profile[valid_mask]
    
    return x_pixels, z_depths


def fit_circle_from_profile(x_pixels, z_depths, spatial_resolution=0.0125, x_offset=0, fixed_diameter_mm=0.0):
    """
    从深度剖面拟合圆
    
    Args:
        x_pixels: X方向像素坐标（相对于裁剪后的图片）
        z_depths: 深度值（μm）
        spatial_resolution: 空间分辨率（mm/pixel），默认0.0125
        x_offset: X方向偏移（相对于全图的像素偏移）
        fixed_diameter_mm: 固定的圆直径（mm），0表示自动拟合半径
    
    Returns:
        字典，包含拟合结果
    """
    if len(x_pixels) < 20:
        return None
    
    # 转换为mm（使用全局坐标）
    x_mm = (x_pixels + x_offset) * spatial_resolution
    z_mm = z_depths / 1000.0
    
    # 初始估计
    x_m = np.mean(x_mm)
    z_m = (np.max(z_mm) + np.min(z_mm)) / 2
    x_span = np.max(x_mm) - np.min(x_mm)
    z_span = np.max(z_mm) - np.min(z_mm)
    
    # 检查是否使用固定直径约束
    if fixed_diameter_mm > 0:
        # 固定半径模式：只优化圆心位置
        fixed_radius_mm = fixed_diameter_mm / 2.0
        
        def residuals_fixed_r(params):
            cx, cz = params
            return np.sqrt((x_mm - cx)**2 + (z_mm - cz)**2) - fixed_radius_mm
        
        z_center = z_m
        z_tolerance = z_span * 0.5
        
        result = least_squares(residuals_fixed_r, [x_m, z_m], bounds=(
            [np.min(x_mm) - x_span, z_center - z_tolerance],
            [np.max(x_mm) + x_span, z_center + z_tolerance]
        ))
        
        if result.success:
            cx, cz = result.x
            r = fixed_radius_mm
            fit_errors = residuals_fixed_r(result.x)
            rms_error = np.sqrt(np.mean(fit_errors**2))
        else:
            return None
    else:
        # 自动拟合模式：优化圆心和半径
        r_m = max(x_span, z_span) / 2
        
        def residuals(params):
            cx, cz, r = params
            return np.sqrt((x_mm - cx)**2 + (z_mm - cz)**2) - r
        
        z_center = z_m
        z_tolerance = z_span * 0.5
        
        result = least_squares(residuals, [x_m, z_m, r_m], bounds=(
            [np.min(x_mm) - x_span, z_center - z_tolerance, 0],
            [np.max(x_mm) + x_span, z_center + z_tolerance, np.inf]
        ))
        
        if result.success:
            cx, cz, r = result.x
            fit_errors = residuals(result.x)
            rms_error = np.sqrt(np.mean(fit_errors**2))
        else:
            return None
    
    # 转换回原始单位
    cx_pixel = cx / spatial_resolution
    cz_um = cz * 1000.0
    r_um = r * 1000.0
    
    # 异常值检测
    z_mean_um = np.mean(z_depths)
    z_center_deviation = abs(cz_um - z_mean_um)
    z_data_std = np.std(z_depths)
    
    if z_center_deviation > 10 * z_data_std:
        return None
    
    if z_span * 1000 > abs(z_mean_um) * 3:
        return None
    
    return {
        'center_x_mm': cx,
        'center_x_pixel': cx_pixel,
        'center_z_um': cz_um,
        'radius_mm': r,
        'radius_um': r_um,
        'rms_error_mm': rms_error,
        'rms_error_um': rms_error * 1000,
        'n_points': len(x_pixels),
        'fit_type': 'circle',
        'fixed_radius': fixed_diameter_mm > 0,
        'z_mean_um': z_mean_um,
        'z_span_um': z_span * 1000
    }


def fit_ellipse_from_profile(x_pixels, z_depths, spatial_resolution=0.0125, x_offset=0):
    """
    从深度剖面拟合椭圆
    
    Args:
        x_pixels: X方向像素坐标（相对于裁剪后的图片）
        z_depths: 深度值（μm）
        spatial_resolution: 空间分辨率（mm/pixel），默认0.0125
        x_offset: X方向偏移（相对于全图的像素偏移）
    
    Returns:
        字典，包含拟合结果
    """
    if len(x_pixels) < 20:
        return None
    
    # 转换为mm（使用全局坐标）
    x_mm = (x_pixels + x_offset) * spatial_resolution
    z_mm = z_depths / 1000.0
    
    # 初始估计
    x_m = np.mean(x_mm)
    z_m = (np.max(z_mm) + np.min(z_mm)) / 2
    x_span = np.max(x_mm) - np.min(x_mm)
    z_span = np.max(z_mm) - np.min(z_mm)
    a_m = max(x_span, z_span) / 2
    b_m = min(x_span, z_span) / 2
    
    def residuals(params):
        cx, cz, a, b, theta = params
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        xr = (x_mm - cx) * cos_t + (z_mm - cz) * sin_t
        zr = -(x_mm - cx) * sin_t + (z_mm - cz) * cos_t
        return (xr / a)**2 + (zr / b)**2 - 1
    
    z_center = z_m
    z_tolerance = z_span * 0.5
    
    result = least_squares(residuals, [x_m, z_m, a_m, b_m, 0], bounds=(
        [np.min(x_mm) - x_span, z_center - z_tolerance, 0, 0, -np.pi],
        [np.max(x_mm) + x_span, z_center + z_tolerance, np.inf, np.inf, np.pi]
    ))
    
    if not result.success:
        return None
    
    cx, cz, a, b, theta = result.x
    fit_errors = residuals(result.x)
    rms_error = np.sqrt(np.mean(fit_errors**2))
    
    # 转换回原始单位
    cx_pixel = cx / spatial_resolution
    cz_um = cz * 1000.0
    a_um = a * 1000.0
    b_um = b * 1000.0
    
    # 异常值检测
    z_mean_um = np.mean(z_depths)
    z_center_deviation = abs(cz_um - z_mean_um)
    z_data_std = np.std(z_depths)
    
    if z_center_deviation > 10 * z_data_std:
        return None
    
    z_span_check = np.max(z_mm) - np.min(z_mm)
    if z_span_check * 1000 > abs(z_mean_um) * 3:
        return None
    
    return {
        'center_x_mm': cx,
        'center_x_pixel': cx_pixel,
        'center_z_um': cz_um,
        'semi_major_um': a_um,
        'semi_minor_um': b_um,
        'rotation_rad': theta,
        'rotation_deg': np.degrees(theta),
        'rms_error': rms_error,
        'n_points': len(x_pixels),
        'fit_type': 'ellipse'
    }


def fit_shape_from_profile(x_pixels, z_depths, spatial_resolution=0.0125, fit_type='ellipse', 
                           x_offset=0, fixed_diameter_mm=0.0):
    """
    从深度剖面拟合形状（圆或椭圆）
    """
    if fit_type == 'circle':
        return fit_circle_from_profile(x_pixels, z_depths, spatial_resolution, x_offset, fixed_diameter_mm)
    else:
        return fit_ellipse_from_profile(x_pixels, z_depths, spatial_resolution, x_offset)


def calculate_x_repeatability_by_shape(image_files, roi=None, spatial_resolution=0.0125, fit_type='ellipse',
                                       depth_offset=32768, depth_scale=1.6, fixed_diameter_mm=0.0):
    """
    通过拟合圆/椭圆计算X位置重复精度
    
    Args:
        image_files: 图片文件路径列表
        roi: 感兴趣区域 (x_start, x_end, y_start, y_end)，None表示使用动态ROI
        spatial_resolution: 空间分辨率（mm/pixel），默认0.0125
        fit_type: 'circle' 或 'ellipse'
        depth_offset: 深度转换偏移
        depth_scale: 深度转换缩放因子 (μm/count)
        fixed_diameter_mm: 固定的圆直径（mm），仅用于circle拟合
    
    Returns:
        - results: 每张图片的拟合结果列表
        - statistics: 统计信息字典
    """
    results = []
    center_x_list = []
    center_z_list = []
    
    # 判断是否使用动态ROI
    use_dynamic_roi = (roi is None)
    
    for img_path in image_files:
        # 加载深度图像
        if use_dynamic_roi:
            depth_data, valid_mask, x_offset = load_depth_image(img_path, roi=None, dynamic_roi=True,
                                                                 depth_offset=depth_offset, depth_scale=depth_scale)
        else:
            depth_data, valid_mask = load_depth_image(img_path, roi, dynamic_roi=False,
                                                      depth_offset=depth_offset, depth_scale=depth_scale)
            x_offset = roi[0] if roi else 0
        
        # 提取深度剖面
        x_pixels, z_depths = extract_depth_profile_for_circle(depth_data)
        
        if x_pixels is None:
            results.append({
                'filename': os.path.basename(img_path),
                'success': False,
                'error': '深度剖面数据不足'
            })
            continue
        
        # 拟合圆或椭圆
        fit_result = fit_shape_from_profile(x_pixels, z_depths, spatial_resolution, fit_type, 
                                           x_offset, fixed_diameter_mm)
        
        if fit_result is None:
            results.append({
                'filename': os.path.basename(img_path),
                'success': False,
                'error': f'{fit_type}拟合失败'
            })
            continue
        
        center_x_list.append(fit_result['center_x_mm'])
        center_z_list.append(fit_result['center_z_um'] / 1000.0)
        
        # 构建结果字典
        result_dict = {
            'filename': os.path.basename(img_path),
            'success': True,
            'center_x_pixel': fit_result['center_x_pixel'],
            'center_x_mm': fit_result['center_x_mm'],
            'center_z_um': fit_result['center_z_um'],
            'fit_type': fit_type,
            'x_offset': x_offset
        }
        
        # 添加圆或椭圆特定的参数
        if fit_type == 'circle':
            result_dict['radius_um'] = fit_result['radius_um']
            result_dict['rms_error_um'] = fit_result['rms_error_um']
        else:  # ellipse
            result_dict['semi_major_um'] = fit_result['semi_major_um']
            result_dict['semi_minor_um'] = fit_result['semi_minor_um']
            result_dict['rotation_deg'] = fit_result['rotation_deg']
            result_dict['rms_error'] = fit_result['rms_error']
        
        result_dict['n_points'] = fit_result['n_points']
        results.append(result_dict)
    
    # 计算统计信息
    if len(center_x_list) == 0:
        return results, None
    
    center_x_arr = np.array(center_x_list)
    center_z_arr = np.array(center_z_list)
    
    # X方向统计
    x_mean_mm = np.mean(center_x_arr)
    x_std_mm = np.std(center_x_arr, ddof=1) if len(center_x_arr) > 1 else 0
    x_std_um = x_std_mm * 1000
    x_pv_mm = np.ptp(center_x_arr)
    x_pv_um = x_pv_mm * 1000
    
    # Z方向统计
    z_mean_mm = np.mean(center_z_arr)
    z_std_mm = np.std(center_z_arr, ddof=1) if len(center_z_arr) > 1 else 0
    z_std_um = z_std_mm * 1000
    z_pv_mm = np.ptp(center_z_arr)
    z_pv_um = z_pv_mm * 1000
    
    statistics = {
        'fit_type': fit_type,
        'n_total': len(image_files),
        'n_success': len(center_x_list),
        # X方向位置重复精度
        'x_mean_mm': x_mean_mm,
        'x_std_mm': x_std_mm,
        'x_std_um': x_std_um,
        'x_1sigma_um': x_std_um,
        'x_3sigma_um': x_std_um * 3,
        'x_6sigma_um': x_std_um * 6,
        'x_pv_mm': x_pv_mm,
        'x_pv_um': x_pv_um,
        # Z方向（深度）重复精度
        'z_mean_mm': z_mean_mm,
        'z_std_mm': z_std_mm,
        'z_std_um': z_std_um,
        'z_1sigma_um': z_std_um,
        'z_3sigma_um': z_std_um * 3,
        'z_6sigma_um': z_std_um * 6,
        'z_pv_mm': z_pv_mm,
        'z_pv_um': z_pv_um
    }
    
    return results, statistics


def get_image_files(folder):
    """
    获取文件夹中的所有图片文件（PNG/TIF），并按自然顺序排序
    """
    all_files = os.listdir(folder)
    image_files_list = [f for f in all_files if f.lower().endswith(('.png', '.tif', '.tiff'))]
    image_files = [os.path.join(folder, f) for f in sorted(image_files_list, key=natural_sort_key)]
    return image_files


def save_x_repeatability_report(output_path, results, statistics):
    """
    保存X位置重复精度报告
    
    Args:
        output_path: 输出文件路径
        results: 每张图片的拟合结果列表
        statistics: 统计信息字典
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("X位置重复精度测量报告\n")
        f.write("=" * 60 + "\n\n")
        
        if statistics is None:
            f.write("错误: 没有成功拟合的图像\n")
            return
        
        f.write(f"拟合类型: {statistics['fit_type']}\n")
        f.write(f"图像总数: {statistics['n_total']}\n")
        f.write(f"成功拟合: {statistics['n_success']}\n\n")
        
        f.write("【X方向位置重复精度】\n")
        f.write("-" * 40 + "\n")
        f.write(f"  平均位置: {statistics['x_mean_mm']:.6f} mm\n")
        f.write(f"  标准差(1σ): {statistics['x_1sigma_um']:.3f} μm\n")
        f.write(f"  重复精度(±3σ): ±{statistics['x_3sigma_um']:.3f} μm\n")
        f.write(f"  重复精度(6σ): {statistics['x_6sigma_um']:.3f} μm\n")
        f.write(f"  极差(P-V): {statistics['x_pv_um']:.3f} μm\n\n")
        
        f.write("【Z方向（深度）重复精度】\n")
        f.write("-" * 40 + "\n")
        f.write(f"  平均深度: {statistics['z_mean_mm']:.6f} mm\n")
        f.write(f"  标准差(1σ): {statistics['z_1sigma_um']:.3f} μm\n")
        f.write(f"  重复精度(±3σ): ±{statistics['z_3sigma_um']:.3f} μm\n")
        f.write(f"  重复精度(6σ): {statistics['z_6sigma_um']:.3f} μm\n")
        f.write(f"  极差(P-V): {statistics['z_pv_um']:.3f} μm\n\n")
        
        f.write("【逐图像拟合结果】\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'文件名':<40} {'X位置(mm)':<12} {'Z深度(μm)':<12} {'状态':<8}\n")
        f.write("-" * 60 + "\n")
        
        for r in results:
            if r['success']:
                f.write(f"{r['filename']:<40} {r['center_x_mm']:<12.6f} {r['center_z_um']:<12.2f} {'成功':<8}\n")
            else:
                f.write(f"{r['filename']:<40} {'--':<12} {'--':<12} {r.get('error', '失败'):<8}\n")
        
        f.write("\n" + "=" * 60 + "\n")
