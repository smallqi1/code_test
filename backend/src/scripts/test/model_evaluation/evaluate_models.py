#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型评估主脚本
用于评估单个城市和指标的模型性能
"""

import os
import argparse
import sys
import logging
from datetime import datetime

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入工具模块和配置
from utils import (
    evaluate_model, save_evaluation_results, 
    load_city_map, load_all_city_ids,
    get_city_name_from_id
)
from config import INDICATORS, CITY_IDS, TEST_START_DATE, TEST_END_DATE, LOGS_DIR

# 添加可选的高级指标分析支持
try:
    # 从新的model_evaluator模块导入分析函数
    from model_evaluator import (
        calculate_robust_metrics, generate_table_chart, 
        generate_text_table, save_text_table
    )
    METRICS_ANALYZER_AVAILABLE = True
except ImportError:
    METRICS_ANALYZER_AVAILABLE = False

def setup_logging(city_id=None, indicator=None):
    """设置日志"""
    # 确保日志目录存在
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    if city_id and indicator:
        log_filename = f"evaluate_{city_id}_{indicator}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    else:
        log_filename = f"evaluate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path = os.path.join(LOGS_DIR, log_filename)
    
    # 重要：移除之前可能存在的处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    # 配置日志 - 使用utf-8-sig编码确保Windows中文显示正常
    file_handler = logging.FileHandler(log_path, encoding='utf-8-sig')
    console_handler = logging.StreamHandler()
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 配置根日志记录器
    logging.root.setLevel(logging.INFO)
    logging.root.addHandler(file_handler)
    logging.root.addHandler(console_handler)
    
    logger = logging.getLogger('model_evaluation')
    logger.info("========== 开始单模型评估 ==========")
    
    return logger, log_path

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='评估空气质量预测模型性能')
    
    # 必选参数：城市ID和指标
    parser.add_argument('--city_id', type=str, help='要评估的城市ID (例如: city_f8696158)')
    parser.add_argument('--indicator', type=str, help='要评估的指标 (例如: pm25, pm10, o3, aqi等)')
    
    # 可选参数
    parser.add_argument('--list_cities', action='store_true', help='列出所有可用的城市ID和名称')
    parser.add_argument('--list_indicators', action='store_true', help='列出所有可用的指标')
    
    # 高级分析参数
    parser.add_argument('--analyze', action='store_true', help='使用高级分析处理评估结果')
    
    return parser.parse_args()

def list_available_cities():
    """列出所有可用的城市ID和名称"""
    city_map = load_city_map()
    print("\n可用的城市列表:")
    print("="*50)
    print(f"{'城市ID':<20} {'城市名称':<20}")
    print("-"*50)
    
    for city_id, city_name in city_map.items():
        print(f"{city_id:<20} {city_name:<20}")
    
    print("="*50)
    print(f"共有 {len(city_map)} 个城市可用于评估")

def list_available_indicators():
    """列出所有可用的指标"""
    print("\n可用的指标列表:")
    print("="*30)
    for indicator in INDICATORS:
        print(f"- {indicator}")
    print("="*30)

def main():
    """主函数"""
    args = parse_arguments()
    
    # 如果请求列出城市或指标，则显示后退出
    if args.list_cities:
        list_available_cities()
        return
    
    if args.list_indicators:
        list_available_indicators()
        return
    
    # 验证必须参数
    if not args.city_id or not args.indicator:
        print("错误: 必须指定城市ID (--city_id) 和指标 (--indicator)")
        print("使用 --list_cities 查看可用的城市列表")
        print("使用 --list_indicators 查看可用的指标列表")
        return
    
    # 设置日志
    logger, log_path = setup_logging(args.city_id, args.indicator)
    
    # 确认城市ID
    city_name = get_city_name_from_id(args.city_id)
    if not city_name:
        logger.error(f"错误: 找不到城市ID '{args.city_id}'，请使用 --list_cities 查看可用的城市ID")
        return
    
    # 确认指标
    if args.indicator.lower() not in INDICATORS:
        logger.error(f"错误: 无效的指标 '{args.indicator}'，请使用 --list_indicators 查看可用的指标")
        return
    
    # 显示评估信息
    logger.info(f"开始评估 {city_name} ({args.city_id}) 的 {args.indicator.upper()} 模型")
    logger.info(f"评估时间范围: {TEST_START_DATE.strftime('%Y-%m-%d')} 至 {TEST_END_DATE.strftime('%Y-%m-%d')}")
    
    # 执行评估
    result = evaluate_model(args.city_id, args.indicator.lower())
    
    if result:
        # 保存结果
        save_evaluation_results([result])
        
        # 显示评估结果摘要
        print("\n评估结果摘要:")
        print("="*50)
        print(f"城市: {result['city_name']} ({result['city_id']})")
        print(f"指标: {result['indicator'].upper()}")
        print(f"数据点数量: {result['data_points']}")
        print(f"均方误差 (MSE): {result['mse']:.4f}")
        print(f"均方根误差 (RMSE): {result['rmse']:.4f}")
        print(f"平均绝对误差 (MAE): {result['mae']:.4f}")
        print(f"决定系数 (R^2): {result['r2']:.4f}")
        print(f"平均绝对百分比误差 (MAPE): {result['mape']:.4f}%")
        print(f"评估用时: {result['evaluation_time']:.2f} 秒")
        print(f"评估图表保存至: {result['chart_path']}")
        print("="*50)
        
        logger.info(f"评估成功完成，评估图表保存至: {result['chart_path']}")
        logger.info(f"日志文件保存在: {log_path}")
        
        # 如果要求进行高级分析且模块可用
        if args.analyze and METRICS_ANALYZER_AVAILABLE:
            logger.info("执行高级指标分析...")
            try:
                # 将结果转换为DataFrame格式
                import pandas as pd
                df_result = pd.DataFrame([result])
                
                # 添加异常标记
                df_result['has_anomaly'] = (
                    (df_result['rmse'] < 0) | (df_result['mae'] < 0) | 
                    (df_result['r2'] < -1) | (df_result['r2'] > 1) | 
                    (df_result['mape'] < 0) | (df_result['mape'] > 1000)
                )
                
                # 计算更健壮的指标
                df_metrics = calculate_robust_metrics(df_result)
                
                if df_metrics is not None:
                    # 生成高级图表
                    chart_files = generate_table_chart(df_metrics)
                    
                    # 生成文字表格
                    text_table = generate_text_table(df_metrics)
                    report_file = save_text_table(text_table)
                    
                    logger.info(f"高级指标分析完成，报告保存至: {report_file}")
                    print(f"\n高级分析报告已保存至: {report_file}")
                else:
                    logger.warning("无法执行高级指标分析，可能是数据点不足")
            except Exception as e:
                logger.error(f"执行高级指标分析时出错: {e}")
                print("\n警告: 执行高级指标分析时出错")
        elif args.analyze and not METRICS_ANALYZER_AVAILABLE:
            logger.warning("请求高级分析，但metrics_analyzer模块不可用")
            print("\n警告: 无法执行高级分析，metrics_analyzer模块不可用")
        
        logger.info("========== 单模型评估结束 ==========")
    else:
        logger.error("评估失败，未能生成结果")
        logger.info("========== 单模型评估结束（失败）==========")

if __name__ == "__main__":
    main() 