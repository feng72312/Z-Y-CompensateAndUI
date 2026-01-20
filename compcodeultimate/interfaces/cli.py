# -*- coding: utf-8 -*-
"""
命令行接口
提供命令行工具入口
"""

import argparse
import sys
import os
from typing import Optional

from ..services import (
    CalibrationService,
    CompensationService,
    LinearityService,
    RepeatabilityService
)
from ..data.models import (
    FilterConfig,
    ROIConfig,
    ExtrapolateConfig,
    DepthConversionConfig
)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog='compcodeultimate',
        description='深度图补偿系统命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 完整标定流程
  python -m compcodeultimate calibrate -c ./calib_data -t ./test_data -o ./output
  
  # 批量补偿
  python -m compcodeultimate compensate -m model.json -i ./input -o ./output
  
  # 计算线性度
  python -m compcodeultimate linearity -t ./test_data -m model.json
  
  # 计算重复精度
  python -m compcodeultimate repeatability -d ./repeat_data
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # calibrate 子命令
    calib_parser = subparsers.add_parser('calibrate', help='执行标定并建立补偿模型')
    calib_parser.add_argument('-c', '--calib-dir', required=True, help='标定数据目录')
    calib_parser.add_argument('-t', '--test-dir', help='测试数据目录（可选）')
    calib_parser.add_argument('-o', '--output', default='output', help='输出目录')
    calib_parser.add_argument('--no-filter', action='store_true', help='禁用滤波')
    calib_parser.add_argument('--full-scale', type=float, default=41.0, help='满量程(mm)')
    
    # compensate 子命令
    comp_parser = subparsers.add_parser('compensate', help='批量补偿图像')
    comp_parser.add_argument('-m', '--model', required=True, help='模型文件路径')
    comp_parser.add_argument('-i', '--input', required=True, help='输入目录')
    comp_parser.add_argument('-o', '--output', required=True, help='输出目录')
    comp_parser.add_argument('--no-extrapolate', action='store_true', help='禁用外推')
    
    # linearity 子命令
    lin_parser = subparsers.add_parser('linearity', help='计算线性度')
    lin_parser.add_argument('-t', '--test-dir', required=True, help='测试数据目录')
    lin_parser.add_argument('-m', '--model', help='补偿模型（可选）')
    lin_parser.add_argument('-o', '--output', help='输出报告路径')
    lin_parser.add_argument('--full-scale', type=float, default=41.0, help='满量程(mm)')
    lin_parser.add_argument('--no-filter', action='store_true', help='禁用滤波')
    
    # repeatability 子命令
    rep_parser = subparsers.add_parser('repeatability', help='计算重复精度')
    rep_parser.add_argument('-d', '--dir', required=True, help='图像目录')
    rep_parser.add_argument('-o', '--output', help='输出报告路径')
    rep_parser.add_argument('--no-filter', action='store_true', help='禁用滤波')
    rep_parser.add_argument('--pixel-mode', action='store_true', help='逐像素分析模式')
    
    return parser


def progress_callback(current: int, total: int, message: str) -> None:
    """命令行进度回调"""
    print(f"[{current}/{total}] {message}")


def run_calibrate(args) -> int:
    """执行标定命令"""
    print("=" * 60)
    print("深度图补偿系统 - 标定模式")
    print("=" * 60)
    
    filter_config = FilterConfig(enabled=not args.no_filter)
    
    service = CalibrationService(filter_config=filter_config)
    
    try:
        # 处理标定数据
        print(f"\n标定目录: {args.calib_dir}")
        result = service.process_calibration_data(
            args.calib_dir,
            progress_callback=progress_callback
        )
        
        print(f"\n有效图像: {len(result['actual_values'])}")
        print(f"跳过图像: {result['skipped_count']}")
        
        # 保存模型
        os.makedirs(args.output, exist_ok=True)
        model_path = os.path.join(args.output, 'compensation_model.json')
        service.save_model(model_path)
        print(f"\n模型已保存: {model_path}")
        
        # 如果有测试数据，计算线性度
        if args.test_dir:
            print("\n" + "=" * 60)
            print("计算线性度")
            print("=" * 60)
            
            lin_service = LinearityService(
                filter_config=filter_config,
                full_scale=args.full_scale
            )
            lin_service.set_model(result['model'])
            
            output_path = os.path.join(args.output, 'linearity_report.txt')
            lin_result = lin_service.calculate_batch_linearity(
                args.test_dir,
                output_path=output_path,
                progress_callback=progress_callback
            )
            
            print(f"\n补偿前线性度: {lin_result['before']['linearity']:.4f}%")
            if 'after' in lin_result:
                print(f"补偿后线性度: {lin_result['after']['linearity']:.4f}%")
                print(f"改善幅度: {lin_result['improvement']:.2f}%")
        
        print("\n标定完成！")
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        return 1


def run_compensate(args) -> int:
    """执行补偿命令"""
    print("=" * 60)
    print("深度图补偿系统 - 批量补偿模式")
    print("=" * 60)
    
    extrapolate_config = ExtrapolateConfig(enabled=not args.no_extrapolate)
    
    service = CompensationService(extrapolate_config=extrapolate_config)
    
    try:
        # 加载模型
        print(f"\n加载模型: {args.model}")
        service.load_model(args.model)
        
        info = service.get_model_info()
        print(f"标定点数: {info['calibration_points']}")
        print(f"输入范围: {info['input_range']}")
        
        # 批量补偿
        print(f"\n输入目录: {args.input}")
        print(f"输出目录: {args.output}")
        
        result = service.compensate_batch(
            args.input,
            args.output,
            progress_callback=progress_callback
        )
        
        print(f"\n处理完成:")
        print(f"  成功: {result.processed_images}")
        print(f"  失败: {result.failed_images}")
        print(f"  平均补偿率: {result.avg_compensation_rate:.2f}%")
        
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        return 1


def run_linearity(args) -> int:
    """执行线性度计算命令"""
    print("=" * 60)
    print("深度图补偿系统 - 线性度计算")
    print("=" * 60)
    
    filter_config = FilterConfig(enabled=not args.no_filter)
    
    service = LinearityService(
        filter_config=filter_config,
        full_scale=args.full_scale
    )
    
    try:
        # 加载模型（如果有）
        if args.model:
            print(f"\n加载模型: {args.model}")
            service.load_model(args.model)
        
        # 计算线性度
        print(f"\n测试目录: {args.test_dir}")
        
        result = service.calculate_batch_linearity(
            args.test_dir,
            output_path=args.output,
            progress_callback=progress_callback
        )
        
        print(f"\n结果:")
        print(f"  有效图像: {result['num_images']}")
        print(f"  满量程: {result['full_scale']} mm")
        print(f"  补偿前线性度: {result['before']['linearity']:.4f}%")
        
        if 'after' in result:
            print(f"  补偿后线性度: {result['after']['linearity']:.4f}%")
            print(f"  改善幅度: {result['improvement']:.2f}%")
        
        if args.output:
            print(f"\n报告已保存: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        return 1


def run_repeatability(args) -> int:
    """执行重复精度计算命令"""
    print("=" * 60)
    print("深度图补偿系统 - 重复精度计算")
    print("=" * 60)
    
    filter_config = FilterConfig(enabled=not args.no_filter)
    
    service = RepeatabilityService(filter_config=filter_config)
    
    try:
        print(f"\n图像目录: {args.dir}")
        
        calc_mode = 'pixel' if args.pixel_mode else 'mean'
        
        result = service.calculate_repeatability(
            args.dir,
            output_path=args.output,
            calc_mode=calc_mode,
            progress_callback=progress_callback
        )
        
        print(f"\n结果:")
        print(f"  图像数量: {result.num_images}")
        print(f"  平均深度: {result.mean_depth:.6f} mm")
        print(f"  标准差(1σ): {result.std_1sigma:.6f} mm ({result.std_1sigma*1000:.3f} μm)")
        print(f"  重复精度(±3σ): ±{result.repeatability_3sigma:.6f} mm (±{result.repeatability_3sigma*1000:.3f} μm)")
        print(f"  极差: {result.peak_to_peak:.6f} mm ({result.peak_to_peak*1000:.3f} μm)")
        
        if args.output:
            print(f"\n报告已保存: {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"\n错误: {e}")
        return 1


def main(args: Optional[list] = None) -> int:
    """主入口"""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    if parsed_args.command is None:
        parser.print_help()
        return 0
    
    commands = {
        'calibrate': run_calibrate,
        'compensate': run_compensate,
        'linearity': run_linearity,
        'repeatability': run_repeatability
    }
    
    handler = commands.get(parsed_args.command)
    if handler:
        return handler(parsed_args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
