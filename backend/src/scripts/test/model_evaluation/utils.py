#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型评估工具模块
包含数据加载、模型加载、评估指标计算等功能
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import mysql.connector
from keras.models import load_model
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import time
import logging
from tqdm import tqdm
import matplotlib

# 导入配置
from config import (
    MODELS_DIR, SCALERS_DIR, CITY_MAP_PATH, INDICATOR_DB_MAPPING,
    DB_CONFIG, PROCESSED_DATA_DIR, CHARTS_DIR, RESULTS_DIR, 
    LOOK_BACK, TEST_START_DATE, TEST_END_DATE, CITY_IDS, INDICATORS
)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('model_evaluation')

# 在文件顶部导入部分添加以下代码
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 12

def load_city_map():
    """加载城市ID到城市名称的映射"""
    try:
        if not os.path.exists(CITY_MAP_PATH):
            logger.error(f"城市映射文件不存在: {CITY_MAP_PATH}")
            return {}
        
        with open(CITY_MAP_PATH, 'r', encoding='utf-8-sig') as f:
            city_map = json.load(f)
        logger.info(f"成功加载城市映射，共{len(city_map)}个城市")
        return city_map
    except Exception as e:
        logger.error(f"加载城市映射出错: {str(e)}")
        return {}

def get_city_name_from_id(city_id):
    """根据城市ID获取城市名称"""
    city_map = load_city_map()
    return city_map.get(city_id)

def load_all_city_ids():
    """加载所有可用的城市ID"""
    city_map = load_city_map()
    return list(city_map.keys())

def get_db_connection():
    """连接到MySQL数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

def load_model_and_scaler(city_id, indicator):
    """加载指定城市和指标的模型和scaler"""
    try:
        model_filename = f"{city_id}_{indicator}"
        model_path = os.path.join(MODELS_DIR, model_filename)
        scaler_path = os.path.join(SCALERS_DIR, f"{model_filename}.npy")
        
        # 检查文件是否存在
        if not os.path.exists(model_path):
            logger.error(f"模型文件不存在: {model_path}")
            return None, None
        
        if not os.path.exists(scaler_path):
            logger.error(f"Scaler文件不存在: {scaler_path}")
            return None, None
        
        # 加载模型
        model = load_model(model_path)
        
        # 加载scaler (与forecast_routes.py中方式一致)
        scaler = np.load(scaler_path, allow_pickle=True).item()
        
        logger.info(f"成功加载 {city_id} 的 {indicator} 模型和scaler")
        return model, scaler
    except Exception as e:
        logger.error(f"加载模型和scaler失败: {e}")
        return None, None

def get_historical_data_for_period(city_name, indicator, start_date, end_date):
    """从数据库获取特定时间段的历史数据"""
    try:
        conn = get_db_connection()
        if not conn:
            return pd.Series(dtype=float)
        
        cursor = conn.cursor()
        db_column = INDICATOR_DB_MAPPING.get(indicator.lower())
        
        if not db_column:
            logger.error(f"未找到指标 {indicator} 对应的数据库列名")
            conn.close()
            return pd.Series(dtype=float)
        
        # 使用UNION合并两个表的查询结果，避免重复
        query = f"""
        (SELECT record_date, {db_column} 
        FROM air_quality_data 
        WHERE city = %s AND record_date BETWEEN %s AND %s)
        UNION
        (SELECT record_date, {db_column} 
        FROM air_quality_newdata 
        WHERE city = %s AND record_date BETWEEN %s AND %s)
        ORDER BY record_date ASC
        """
        
        # 格式化日期为字符串
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # 执行查询
        cursor.execute(query, (city_name, start_date_str, end_date_str, city_name, start_date_str, end_date_str))
        rows = cursor.fetchall()
        
        # 处理查询结果
        data_dict = {}
        for row in rows:
            record_date = row[0]
            value = row[1]
            
            # 处理日期格式
            if isinstance(record_date, str):
                record_date = datetime.strptime(record_date, '%Y-%m-%d').date()
            elif isinstance(record_date, datetime):
                record_date = record_date.date()
            
            # 确保值是有效的浮点数
            if value is not None:
                try:
                    data_dict[record_date] = float(value)
                except (ValueError, TypeError):
                    continue
        
        cursor.close()
        conn.close()
        
        if not data_dict:
            logger.warning(f"未找到城市 {city_name} 的 {indicator} 在 {start_date_str} 至 {end_date_str} 期间的数据")
            return pd.Series(dtype=float)
        
        # 转换为Series
        series = pd.Series(data_dict)
        series.index = pd.to_datetime(series.index)
        series = series.sort_index()
        
        logger.info(f"获取到 {len(series)} 条 {city_name} 的 {indicator} 历史数据 ({start_date_str} 至 {end_date_str})")
        return series
    
    except Exception as e:
        logger.error(f"从数据库获取历史数据失败: {e}")
        return pd.Series(dtype=float)

def generate_predictions(model, scaler, initial_data, prediction_length):
    """使用滚动预测生成指定长度的预测序列"""
    try:
        # 确保初始数据有正确的长度
        if len(initial_data) < LOOK_BACK:
            logger.error(f"初始数据长度不足: {len(initial_data)}/{LOOK_BACK}")
            return None
        
        # 提取最后LOOK_BACK天的数据作为初始输入序列
        input_sequence = initial_data[-LOOK_BACK:].values.reshape(-1, 1)
        
        # 对初始序列进行归一化
        input_sequence_scaled = scaler.transform(input_sequence)
        
        # 准备模型输入形状
        current_input = input_sequence_scaled.reshape(1, LOOK_BACK, 1)
        
        # 存储预测结果
        predictions = []
        
        # 进行滚动预测
        for _ in range(prediction_length):
            # 预测下一个值
            next_pred = model.predict(current_input, verbose=0)[0, 0]
            
            # 将预测值（归一化的）加入预测列表
            predictions.append(next_pred)
            
            # 更新输入序列，移除最早的一天，加入新预测
            next_pred_reshaped = np.array([[next_pred]])
            current_input = np.append(current_input[:, 1:, :], next_pred_reshaped.reshape(1, 1, 1), axis=1)
        
        # 反归一化预测结果
        predictions_array = np.array(predictions).reshape(-1, 1)
        predictions_rescaled = scaler.inverse_transform(predictions_array)
        
        # 转换为一维数组
        predictions_rescaled = predictions_rescaled.flatten()
        
        return predictions_rescaled
        
    except Exception as e:
        logger.error(f"生成预测失败: {e}")
        return None

def calculate_mape(actual, predicted):
    """
    计算平均绝对百分比误差(MAPE)
    
    参数:
    actual - 实际值数组
    predicted - 预测值数组
    
    返回:
    mape - 平均绝对百分比误差, 百分比形式
    """
    # 避免除以零
    mask = actual != 0
    actual_filtered = actual[mask]
    predicted_filtered = predicted[mask]
    
    if len(actual_filtered) == 0:
        return np.nan
    
    # 计算MAPE
    mape = np.mean(np.abs((actual_filtered - predicted_filtered) / actual_filtered)) * 100
    return mape

def evaluate_model(city_id, indicator):
    """评估单个城市和指标的模型性能"""
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
        
        # 获取测试集数据 (4月3日至5月13日)
        actual_values = get_historical_data_for_period(
            city_name, indicator, TEST_START_DATE, TEST_END_DATE
        )
        
        if actual_values.empty:
            logger.error(f"获取不到 {city_name} 的 {indicator} 测试数据，跳过评估")
            return None
        
        # 获取预测所需的初始输入序列 (测试开始前30天)
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
        # 添加MAPE计算
        mape = calculate_mape(actual_values.values, predictions_series.values)
        
        # 绘制图表 - 使用中文字体
        plt.figure(figsize=(12, 6))
        plt.plot(actual_values.index, actual_values.values, label='真实值', marker='.', markersize=8)
        plt.plot(predictions_series.index, predictions_series.values, label='预测值', marker='x', linestyle='--', markersize=6)
        plt.title(f'{city_name} - {indicator.upper()} 模型性能评估\nRMSE: {rmse:.2f}, MAE: {mae:.2f}, R^2: {r2:.4f}')
        plt.xlabel('日期')
        plt.ylabel(f'{indicator.upper()} 值')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 创建图表文件名
        chart_filename = f"{city_id}_{indicator}_evaluation.png"
        chart_path = os.path.join(CHARTS_DIR, chart_filename)
        
        # 保存图表
        plt.savefig(chart_path)
        plt.close()
        
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
            'mape': mape,  # 添加MAPE到结果中
            'data_points': len(actual_values),
            'evaluation_time': elapsed_time,
            'chart_path': chart_path
        }
        
        logger.info(f"完成 {city_name} 的 {indicator} 模型评估, RMSE={rmse:.2f}, MAE={mae:.2f}, R^2={r2:.4f}, MAPE={mape:.2f}%, 用时={elapsed_time:.2f}秒")
        return result
        
    except Exception as e:
        logger.error(f"评估 {city_id} 的 {indicator} 模型时出错: {e}")
        return None

def save_evaluation_results(results):
    """保存评估结果到摘要文件（不生成CSV）"""
    try:
        if not results:
            logger.warning("没有评估结果可保存")
            return False
        
        # 生成文件名，包含时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 创建摘要文件
        summary_filename = f"evaluation_summary_{timestamp}.txt"
        summary_path = os.path.join(RESULTS_DIR, summary_filename)
        
        # 创建JSON结果文件
        json_filename = f"evaluation_results_{timestamp}.json"
        json_path = os.path.join(RESULTS_DIR, json_filename)
        
        # 保存JSON格式结果
        with open(json_path, 'w', encoding='utf-8-sig') as f:
            # 将datetime对象转换为字符串
            serializable_results = []
            for result in results:
                result_copy = dict(result)
                if 'chart_path' in result_copy:
                    result_copy['chart_path'] = str(result_copy['chart_path'])
                serializable_results.append(result_copy)
            
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        # 创建DataFrame（仅用于计算聚合统计，不保存）
        results_df = pd.DataFrame(results)
        
        # 使用带BOM的UTF-8编码，确保Windows中文显示正常
        with open(summary_path, 'w', encoding='utf-8-sig') as f:
            f.write(f"模型评估摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"评估时间范围: {TEST_START_DATE.strftime('%Y-%m-%d')} 至 {TEST_END_DATE.strftime('%Y-%m-%d')}\n")
            f.write(f"评估城市数量: {results_df['city_id'].nunique()}\n")
            f.write(f"评估指标数量: {results_df['indicator'].nunique()}\n")
            f.write(f"总评估次数: {len(results_df)}\n\n")
            
            f.write("整体性能指标:\n")
            f.write(f"平均RMSE: {results_df['rmse'].mean():.4f}\n")
            f.write(f"平均MAE: {results_df['mae'].mean():.4f}\n")
            f.write(f"平均R^2: {results_df['r2'].mean():.4f}\n")
            f.write(f"平均MAPE: {results_df['mape'].mean():.4f}%\n\n")
            
            f.write("各指标平均性能:\n")
            for indicator in results_df['indicator'].unique():
                indicator_df = results_df[results_df['indicator'] == indicator]
                f.write(f"{indicator.upper()}: RMSE={indicator_df['rmse'].mean():.4f}, ")
                f.write(f"MAE={indicator_df['mae'].mean():.4f}, ")
                f.write(f"R^2={indicator_df['r2'].mean():.4f}, ")
                f.write(f"MAPE={indicator_df['mape'].mean():.4f}%\n")
            
            f.write("\n性能最好的前5个模型:\n")
            top_models = results_df.sort_values('rmse').head(5)
            for _, row in top_models.iterrows():
                f.write(f"{row['city_name']} - {row['indicator'].upper()}: ")
                f.write(f"RMSE={row['rmse']:.4f}, MAE={row['mae']:.4f}, R^2={row['r2']:.4f}, MAPE={row['mape']:.4f}%\n")
            
            f.write("\n性能最差的前5个模型:\n")
            worst_models = results_df.sort_values('rmse', ascending=False).head(5)
            for _, row in worst_models.iterrows():
                f.write(f"{row['city_name']} - {row['indicator'].upper()}: ")
                f.write(f"RMSE={row['rmse']:.4f}, MAE={row['mae']:.4f}, R^2={row['r2']:.4f}, MAPE={row['mape']:.4f}%\n")
        
        logger.info(f"评估摘要已保存到 {summary_path}")
        logger.info(f"评估结果JSON已保存到 {json_path}")
        return True
        
    except Exception as e:
        logger.error(f"保存评估结果失败: {e}")
        return False 