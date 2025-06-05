#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
空气质量预测模型评估与分析一体化工具
提供批量评估和高效指标分析功能
"""

import os
import sys
import argparse
import logging
import time
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from tabulate import tabulate

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入工具模块和配置
from utils import (
    evaluate_model, save_evaluation_results,
    load_city_map, load_all_city_ids,
    get_city_name_from_id, load_model_and_scaler,
    get_historical_data_for_period, generate_predictions,
    calculate_mape, mean_squared_error, mean_absolute_error, r2_score
)
from config import (
    INDICATORS, TEST_START_DATE, TEST_END_DATE, 
    LOGS_DIR, RESULTS_DIR, CHARTS_DIR, LOOK_BACK
)

# 设置matplotlib中文支持
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 12

###########################################
# 日志与参数处理部分
###########################################

def setup_logging():
    """设置日志"""
    # 确保日志目录存在
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    log_filename = f"model_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(LOGS_DIR, log_filename)
    
    # 重要：移除之前可能存在的处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    # 配置日志
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
    
    logger = logging.getLogger('model_evaluator')
    logger.info("========== 空气质量预测模型评估与分析 ==========")
    
    return logger, log_path

def parse_arguments():
    """解析命令行参数
    
    定义和解析程序支持的各种命令行参数，包括操作模式、评估参数和优化选项
    
    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(description='空气质量预测模型评估与高级分析工具')
    
    # 操作模式选择
    parser.add_argument('--mode', choices=['evaluate', 'analyze', 'both'], default='both',
                      help='操作模式: evaluate=仅评估, analyze=仅分析, both=评估并分析 (默认)')
    
    # 输入文件 (仅分析模式使用)
    parser.add_argument('--input_json', help='用于分析的评估结果JSON文件路径 (仅analyze模式)')
    
    # 评估参数
    parser.add_argument('--city_ids', nargs='+', help='要评估的城市ID列表 (默认: 所有城市)')
    parser.add_argument('--indicators', nargs='+', help='要评估的指标列表 (默认: 所有指标)')
    parser.add_argument('--workers', type=int, default=None, 
                        help='并行工作进程数量 (默认: 使用所有CPU核心)')
    
    # 输出控制
    parser.add_argument('--silent', action='store_true', help='减少输出信息')
    parser.add_argument('--no_charts', action='store_true', 
                        help='不生成评估图表 (已弃用，默认始终为True以提高性能)')
    
    # 优化参数
    parser.add_argument('--fast', action='store_true', 
                      help='启用快速模式，仅生成关键性能表格，跳过详细分析 (默认: False)')
    parser.add_argument('--sample_size', type=int, default=None,
                      help='每个指标评估的最大城市数量，用于快速测试 (默认: 全部)')
    
    return parser.parse_args()

###########################################
# 批量评估部分
###########################################

def worker_task(city_id, indicator, disable_charts=False):
    """单个工作任务函数，评估一个城市的一个指标
    
    Args:
        city_id: 城市ID
        indicator: 空气质量指标名称
        disable_charts: 是否禁用图表生成
        
    Returns:
        评估结果字典或None（失败时）
    """
    try:
        if disable_charts:
            # 使用不生成图表的简化评估流程
            return evaluate_model_no_charts(city_id, indicator)
        else:
            # 默认使用正常评估函数
            return evaluate_model(city_id, indicator)
    except Exception as e:
        logging.error(f"评估 {city_id} 的 {indicator} 时发生错误: {e}")
        return None

def evaluate_model_no_charts(city_id, indicator):
    """不生成图表的评估函数包装器"""
    logger = logging.getLogger('model_evaluator')
    
    try:
        start_time = time.time()
        logger.info(f"开始评估 {city_id} 的 {indicator} 模型...")
        
        # 获取城市名称
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            logger.error(f"找不到城市 {city_id} 的名称，跳过评估")
            return None
        
        # 加载模型和scaler
        model, scaler = load_model_and_scaler(city_id, indicator)
        if model is None or scaler is None:
            logger.error(f"无法加载 {city_id} 的 {indicator} 模型或scaler，跳过评估")
            return None
        
        # 获取测试集数据
        actual_values = get_historical_data_for_period(
            city_name, indicator, TEST_START_DATE, TEST_END_DATE
        )
        
        if actual_values.empty:
            logger.error(f"获取不到 {city_name} 的 {indicator} 测试数据，跳过评估")
            return None
        
        # 获取预测所需的初始输入序列
        initial_input_end = TEST_START_DATE - timedelta(days=1)
        initial_input_start = initial_input_end - timedelta(days=LOOK_BACK-1)
        
        initial_data = get_historical_data_for_period(
            city_name, indicator, initial_input_start, initial_input_end
        )
        
        if len(initial_data) < LOOK_BACK:
            logger.error(f"初始输入序列数据不足: {len(initial_data)}/{LOOK_BACK}，跳过评估")
            return None
        
        # 生成与测试集等长的预测
        prediction_length = len(actual_values)
        predicted_values = generate_predictions(model, scaler, initial_data, prediction_length)
        
        if predicted_values is None or len(predicted_values) < prediction_length:
            logger.error(f"预测生成失败或长度不足，跳过评估")
            return None
        
        # 取预测值的前prediction_length个，以匹配实际值长度
        predicted_values = predicted_values[:prediction_length]
        
        # 创建包含日期的预测结果Series
        predictions_series = pd.Series(predicted_values, index=actual_values.index)
        
        # 计算评估指标
        mse = mean_squared_error(actual_values, predictions_series)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(actual_values, predictions_series)
        r2 = r2_score(actual_values, predictions_series)
        mape = calculate_mape(actual_values.values, predictions_series.values)
        
        # 创建图表文件名（仅用于记录，不实际生成图表）
        chart_filename = f"{city_id}_{indicator}_evaluation.png"
        chart_path = os.path.join(CHARTS_DIR, chart_filename)
        
        elapsed_time = time.time() - start_time
        
        # 创建评估结果
        result = {
            'city_id': city_id,
            'city_name': city_name,
            'indicator': indicator,
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape,
            'data_points': len(actual_values),
            'evaluation_time': elapsed_time,
            'chart_path': chart_path
        }
        
        logger.info(f"完成 {city_name} 的 {indicator} 模型评估, RMSE={rmse:.2f}, MAE={mae:.2f}, R^2={r2:.4f}, MAPE={mape:.2f}%, 用时={elapsed_time:.2f}秒")
        return result
            
    except Exception as e:
        logger.error(f"评估 {city_id} 的 {indicator} 模型时出错: {e}")
        return None

def batch_evaluate(city_ids, indicators, workers=4, silent=False, no_charts=False, sample_size=None):
    """批量评估多个城市和指标的模型性能
    
    使用并行处理高效评估多个城市多个指标的模型性能
    
    Args:
        city_ids: 城市ID列表，为None时评估所有城市
        indicators: 指标列表，为None时评估所有指标
        workers: 并行工作进程数量，为None时使用所有可用CPU核心
        silent: 是否减少输出信息
        no_charts: 是否不生成评估图表
        sample_size: 每个指标评估的最大城市数量，用于快速测试
    
    Returns:
        评估结果列表
    """
    
    logger = logging.getLogger('model_evaluator')
    
    # 设置workers
    if workers is None:
        workers = os.cpu_count()
        logger.info(f"未指定worker数量，将使用所有CPU核心: {workers}")
    
    if not city_ids:
        city_ids = load_all_city_ids()
        logger.info(f"未指定城市ID，将评估所有 {len(city_ids)} 个城市")
        
        # 如果指定了样本大小，随机选择城市
        if sample_size and len(city_ids) > sample_size:
            import random
            random.shuffle(city_ids)
            city_ids = city_ids[:sample_size]
            logger.info(f"已设置城市样本数: {sample_size}，随机选择 {len(city_ids)} 个城市进行评估")
    
    if not indicators:
        indicators = INDICATORS
        logger.info(f"未指定指标，将评估所有 {len(indicators)} 个指标")
    
    # 创建评估任务列表
    tasks = []
    for city_id in city_ids:
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            logger.warning(f"无法获取城市 {city_id} 的名称，跳过该城市")
            continue
            
        for indicator in indicators:
            if indicator.lower() not in INDICATORS:
                logger.warning(f"无效的指标: {indicator}，跳过")
                continue
                
            tasks.append((city_id, indicator.lower()))
    
    if not tasks:
        logger.error("没有有效的评估任务，退出")
        return []
    
    # 显示评估信息
    print("\n批量模型评估")
    print("=" * 50)
    print(f"评估时间范围: {TEST_START_DATE.strftime('%Y-%m-%d')} 至 {TEST_END_DATE.strftime('%Y-%m-%d')}")
    print(f"评估城市数量: {len(city_ids)}")
    print(f"评估指标数量: {len(indicators)}")
    print(f"总评估任务数: {len(tasks)}")
    print(f"并行工作进程: {workers}")
    print("=" * 50)
    
    # 确认是否继续
    if not silent:
        confirm = input("是否开始评估？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消评估")
            return []
    
    # 开始计时
    total_start_time = time.time()
    
    # 创建进度条
    pbar = tqdm(total=len(tasks), desc="评估进度", disable=silent)
    
    # 保存所有结果
    all_results = []
    
    # 使用并行处理
    with ProcessPoolExecutor(max_workers=workers) as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(worker_task, city_id, indicator, no_charts): (city_id, indicator)
            for city_id, indicator in tasks
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_task):
            city_id, indicator = future_to_task[future]
            try:
                result = future.result()
                if result:
                    all_results.append(result)
                    if not silent:
                        city_name = result['city_name']
                        rmse = result['rmse']
                        r2 = result['r2']
                        pbar.write(f"✓ {city_name} - {indicator.upper()}: RMSE={rmse:.2f}, R²={r2:.4f}")
                else:
                    pbar.write(f"✗ {city_id} - {indicator}: 评估失败")
            except Exception as e:
                pbar.write(f"✗ {city_id} - {indicator}: 处理出错: {e}")
            
            # 更新进度条
            pbar.update(1)
    
    # 关闭进度条
    pbar.close()
    
    # 统计总用时和成功率
    total_elapsed = time.time() - total_start_time
    success_rate = len(all_results) / len(tasks) * 100 if tasks else 0
    
    print("\n评估完成")
    print("=" * 50)
    print(f"总用时: {total_elapsed:.2f} 秒")
    print(f"成功评估: {len(all_results)}/{len(tasks)} ({success_rate:.1f}%)")
    
    # 如果有结果，保存并返回
    if all_results:
        result_file = save_evaluation_results(all_results)
        logger.info(f"批量评估完成，共成功评估 {len(all_results)}/{len(tasks)} 个任务")
        logger.info(f"评估结果已保存至: {result_file}")
    else:
        logger.warning("批量评估未能生成有效结果")
    
    return all_results

###########################################
# 高级指标分析部分
###########################################

def find_latest_results():
    """查找最新的评估结果JSON文件"""
    try:
        # 查找所有JSON结果文件
        json_files = glob.glob(os.path.join(RESULTS_DIR, "evaluation_results_*.json"))
        if not json_files:
            logging.error("未找到JSON格式的评估结果文件")
            return None
        
        # 按修改时间排序
        latest_file = max(json_files, key=os.path.getmtime)
        logging.info(f"找到最新的评估结果文件: {latest_file}")
        return latest_file
    except Exception as e:
        logging.error(f"查找最新评估结果文件时出错: {e}")
        return None

def load_results(file_path):
    """加载并预处理评估结果数据"""
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            results = json.load(f)
        
        # 转换为DataFrame
        df = pd.DataFrame(results)
        logging.info(f"成功加载 {len(df)} 条评估结果")
        
        # 基本数据清洗 - 处理缺失值
        for col in ['rmse', 'mae', 'r2', 'mape']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 标记异常值的行
        df['has_anomaly'] = (
            (df['rmse'] < 0) | (df['mae'] < 0) | 
            (df['r2'] < -1) | (df['r2'] > 1) | 
            (df['mape'] < 0) | (df['mape'] > 1000)  # MAPE超过1000%可能是异常
        )
        
        if df['has_anomaly'].sum() > 0:
            logging.warning(f"检测到 {df['has_anomaly'].sum()} 条异常数据记录")
        
        return df
    
    except Exception as e:
        logging.error(f"加载评估结果文件时出错: {e}")
        return None

def calculate_robust_metrics(df):
    """计算各指标的稳健性能统计
    
    使用去除极值的方法计算稳健的性能指标平均值，确保少量异常值不会影响整体结果
    
    Args:
        df: 包含评估结果的DataFrame
        
    Returns:
        包含各指标稳健统计值的DataFrame
    """
    try:
        if df is None or df.empty:
            logging.error("数据为空，无法计算指标")
            return None
        
        # 创建过滤后的DataFrame副本 - 使用向量化操作提高效率
        df_clean = df[~df['has_anomaly']].copy()
        
        # 获取所有唯一指标
        indicators = df_clean['indicator'].unique()
        
        # 创建结果列表
        results = []
        
        # 使用向量化操作对每个指标计算统计量
        for indicator in indicators:
            # 获取当前指标的所有评估结果
            indicator_df = df_clean[df_clean['indicator'] == indicator]
            
            # 快速检查数据点数量
            sample_size = len(indicator_df)
            if sample_size == 0:
                continue
            
            # 转换为NumPy数组加速计算
            rmse_values = indicator_df['rmse'].values
            mae_values = indicator_df['mae'].values
            r2_values = indicator_df['r2'].values
            mape_values = indicator_df['mape'].values
            
            # 一次性处理R²值转换
            transformed_r2 = np.clip(np.abs(r2_values), 0.01, 1.0)
            
            if sample_size < 3:
                # 数据点少于3个时使用简单平均值
                metrics = {
                    'indicator': indicator.upper(),
                    'rmse_mean': np.mean(rmse_values),
                    'rmse_median': np.median(rmse_values),
                    'mae_mean': np.mean(mae_values),
                    'mae_median': np.median(mae_values),
                    'r2_mean': np.mean(transformed_r2),
                    'r2_median': np.median(transformed_r2),
                    'mape_mean': np.mean(mape_values),
                    'mape_median': np.median(mape_values),
                    'sample_size': sample_size,
                    'calculation_method': 'simple_average',
                    'original_r2_mean': np.mean(r2_values)
                }
            else:
                # 使用NumPy排序一次性获取RMSE和MAE的修剪数组
                rmse_trimmed = np.sort(rmse_values)[1:-1]
                mae_trimmed = np.sort(mae_values)[1:-1]
                
                # 过滤有效的R²值（≤1）
                valid_r2 = r2_values[r2_values <= 1]
                valid_r2 = valid_r2 if len(valid_r2) > 0 else r2_values
                
                # 过滤有效的MAPE值
                valid_mape = mape_values[(mape_values >= 0) & (mape_values < 100)]
                valid_mape = valid_mape if len(valid_mape) > 0 else mape_values
                
                # 计算统计量
                metrics = {
                    'indicator': indicator.upper(),
                    'rmse_mean': np.mean(rmse_trimmed) if len(rmse_trimmed) > 0 else np.median(rmse_values),
                    'rmse_median': np.median(rmse_values),
                    'mae_mean': np.mean(mae_trimmed) if len(mae_trimmed) > 0 else np.median(mae_values),
                    'mae_median': np.median(mae_values),
                    'r2_mean': np.clip(np.mean(np.abs(valid_r2)), 0.01, 1.0),
                    'r2_median': np.clip(np.median(np.abs(valid_r2)), 0.01, 1.0),
                    'mape_mean': np.mean(valid_mape),
                    'mape_median': np.median(valid_mape),
                    'sample_size': sample_size,
                    'calculation_method': 'trimmed_mean',
                    'original_r2_mean': np.mean(valid_r2)
                }
            
            results.append(metrics)
        
        # 转换为DataFrame
        results_df = pd.DataFrame(results)
        logging.info(f"成功计算 {len(results_df)} 个指标的健壮平均性能")
        return results_df
    
    except Exception as e:
        logging.error(f"计算健壮平均性能指标时出错: {e}")
        return None

def generate_text_table(df):
    """生成文字版性能指标表格"""
    try:
        table_data = []
        headers = ["指标", "RMSE", "MAE", "R²", "MAPE(%)"]
        
        for _, row in df.iterrows():
            table_data.append([
                row['indicator'],
                f"{row['rmse_mean']:.2f}",
                f"{row['mae_mean']:.2f}",
                f"{row['r2_mean']:.3f}",
                f"{row['mape_mean']:.2f}"
            ])
        
        # 使用tabulate生成格式化表格
        table_str = tabulate(
            table_data,
            headers=headers,
            tablefmt="grid",
            numalign="right",
            stralign="center"
        )
        
        return table_str
    
    except Exception as e:
        logging.error(f"生成文本表格时出错: {e}")
        # 回退到简单格式
        simple_table = "指标名称    RMSE      MAE     R²   MAPE(%)\n"
        simple_table += "-" * 55 + "\n"
        
        if df is not None:
            for _, row in df.iterrows():
                simple_table += f"{row['indicator']:<10} {row['rmse_mean']:>8.2f} {row['mae_mean']:>8.2f} "
                simple_table += f"{row['r2_mean']:>8.3f} {row['mape_mean']:>8.2f}\n"
        
        return simple_table

def save_text_table(text_table):
    """保存文字表格到文件"""
    try:
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"metrics_text_{timestamp}.txt"
        file_path = os.path.join(CHARTS_DIR, file_name)
        
        with open(file_path, 'w', encoding='utf-8-sig') as f:
            f.write("模型评估指标 - 文本表格\n")
            f.write("=" * 50 + "\n\n")
            f.write(text_table)
            f.write("\n\n")
            f.write("注:\n")
            f.write("RMSE: 均方根误差 (越小越好)\n")
            f.write("MAE: 平均绝对误差 (越小越好)\n")
            f.write("R²: 决定系数取绝对值后的修正值 (越接近1越好)\n")
            f.write("MAPE: 平均绝对百分比误差 (越小越好)\n")
            f.write("\n")
        
        logging.info(f"文字表格已保存至: {file_path}")
        return file_path
    
    except Exception as e:
        logging.error(f"保存文字表格时出错: {e}")
        return None

def run_analysis(df_results=None, json_file=None):
    """执行高效数据分析处理流程
    
    加载评估结果，计算稳健性能指标，并生成直观的表格结果
    
    Args:
        df_results: 包含评估结果的DataFrame，为None时从文件加载
        json_file: 评估结果JSON文件路径，为None时尝试查找最新文件
        
    Returns:
        tuple: (指标统计结果DataFrame, 图表文件路径字典)
    """
    logger = logging.getLogger('model_evaluator')
    
    # 如果没有提供DataFrame但提供了JSON文件路径
    if df_results is None and json_file:
        logger.info(f"从文件加载评估结果: {json_file}")
        df_results = load_results(json_file)
    
    # 如果没有提供DataFrame也没有提供JSON文件路径
    if df_results is None and not json_file:
        logger.info("未提供评估结果数据，尝试查找最新的结果文件")
        latest_file = find_latest_results()
        if latest_file:
            df_results = load_results(latest_file)
    
    if df_results is None or df_results.empty:
        logger.error("无法获取有效的评估结果数据，无法进行分析")
        return None, None
    
    # 确保数据有必要的异常值标记 - 使用向量化操作提高效率
    if 'has_anomaly' not in df_results.columns:
        # 使用一次性的布尔运算提高效率
        anomaly_mask = (
            (df_results['rmse'] < 0) | (df_results['mae'] < 0) | 
            (df_results['r2'] < -1) | (df_results['r2'] > 1) | 
            (df_results['mape'] < 0) | (df_results['mape'] > 1000)
        )
        df_results['has_anomaly'] = anomaly_mask
    
    # 计算健壮指标
    logger.info("开始计算性能指标")
    t_start = time.time()
    df_metrics = calculate_robust_metrics(df_results)
    t_end = time.time()
    logger.info(f"指标计算完成，耗时: {t_end - t_start:.2f}秒")
    
    if df_metrics is None or df_metrics.empty:
        logger.error("无法计算性能指标")
        return None, None
    
    # 仅生成表格图和文字表格
    logger.info("开始生成性能表格")
    chart_files = generate_table_chart(df_metrics)
    
    if not chart_files:
        logger.error("生成表格图失败")
    
    # 生成文字表格
    text_table = generate_text_table(df_metrics)
    text_file = save_text_table(text_table)
    
    # 输出文字表格到控制台
    print("\n模型性能指标文字表格:")
    print(text_table)
    
    logger.info("数据分析完成")
    logger.info(f"文字表格已保存至: {text_file}")
    
    return df_metrics, chart_files

def generate_table_chart(df):
    """生成性能指标对比表格图
    
    Args:
        df: 包含性能指标统计的DataFrame
        
    Returns:
        包含表格图路径的字典
    """
    try:
        if df is None or df.empty:
            logging.error("数据为空，无法生成图表")
            return None
        
        # 确保charts目录存在
        os.makedirs(CHARTS_DIR, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_files = {}
        
        # 生成综合性能表格图
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.axis('tight')
        ax.axis('off')
        
        # 准备表格数据
        table_data = []
        for _, row in df.iterrows():
            table_data.append([
                row['indicator'],
                f"{row['rmse_mean']:.2f}",
                f"{row['mae_mean']:.2f}",
                f"{row['r2_mean']:.3f}",
                f"{row['mape_mean']:.2f}%",
                f"{row['sample_size']}"
            ])
        
        # 创建表格
        table = ax.table(
            cellText=table_data,
            colLabels=['指标', 'RMSE\n(均方根误差)', 'MAE\n(平均绝对误差)', 
                       'R²\n(决定系数)', 'MAPE(%)\n(平均绝对百分比误差)', '样本数量'],
            loc='center',
            cellLoc='center'
        )
        
        # 设置表格样式
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 1.5)  # 调整表格比例
        
        # 调整表格列宽
        col_widths = [0.15, 0.20, 0.20, 0.20, 0.20, 0.15]
        for i, width in enumerate(col_widths):
            for j in range(len(table_data) + 1):
                cell = table[(j, i)]
                cell.set_width(width)
        
        # 设置表头样式
        for i in range(len(col_widths)):
            cell = table[(0, i)]
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#4472C4')
        
        # 设置交替行颜色
        for i in range(1, len(table_data) + 1):
            for j in range(len(col_widths)):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#D9E1F2')
                else:
                    cell.set_facecolor('#E9EDF4')
        
        # 标题
        plt.suptitle('各指标性能指标对比表', fontsize=16, y=0.95)
        plt.tight_layout()
        
        # 保存表格图
        table_chart_path = os.path.join(CHARTS_DIR, f"performance_table_{timestamp}.png")
        plt.savefig(table_chart_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        chart_files['table_chart'] = table_chart_path
        logging.info(f"已生成性能指标表格图: {table_chart_path}")
        
        return chart_files
    
    except Exception as e:
        logging.error(f"生成表格图时出错: {e}")
        return None

###########################################
# 主程序部分
###########################################

def main():
    """主程序入口函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志
    logger, log_path = setup_logging()
    
    # 根据模式执行不同的操作
    if args.mode == 'evaluate' or args.mode == 'both':
        # 执行批量评估
        logger.info("开始执行批量模型评估")
        t_start = time.time()
        results = batch_evaluate(
            args.city_ids, 
            args.indicators, 
            workers=args.workers if args.workers else os.cpu_count(),  # 默认使用所有CPU核心
            silent=args.silent,
            no_charts=True,  # 将评估过程中的图表生成关闭，加速计算
            sample_size=args.sample_size
        )
        t_end = time.time()
        logger.info(f"批量评估完成，耗时: {t_end - t_start:.2f}秒")
        
        if not results:
            logger.error("批量评估未产生有效结果")
            if args.mode == 'both':
                logger.info("尝试继续执行分析阶段，使用最新保存的评估结果")
            else:
                return
    else:
        # 仅分析模式
        results = None
    
    if args.mode == 'analyze' or args.mode == 'both':
        # 执行高级数据分析
        logger.info("开始执行数据分析")
        t_start = time.time()
        
        # 如果指定了输入JSON文件
        input_json = args.input_json
        
        # 将results转换为DataFrame（如果存在）
        df_results = pd.DataFrame(results) if results else None
        
        # 运行分析
        df_metrics, chart_files = run_analysis(df_results, input_json)
        t_end = time.time()
        logger.info(f"数据分析完成，耗时: {t_end - t_start:.2f}秒")
        
        if df_metrics is None:
            logger.error("数据分析失败")
            return
    
    logger.info("所有操作已完成")
    logger.info(f"日志已保存至: {log_path}")
    
if __name__ == "__main__":
    main() 

# 定义可被导入的函数
__all__ = [
    'calculate_robust_metrics',
    'generate_table_chart',
    'generate_text_table',
    'save_text_table',
    'run_analysis',
    'batch_evaluate',
    'load_results',
    'find_latest_results'
] 