#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据处理工具函数
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def load_data(file_path, start_date=None, end_date=None, region=None):
    """
    加载数据并根据条件筛选
    
    Args:
        file_path: 数据文件路径
        start_date: 开始日期 (可选)
        end_date: 结束日期 (可选)
        region: 地区 (可选)
        
    Returns:
        DataFrame: 筛选后的数据
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.warning(f"数据文件不存在: {file_path}")
            return pd.DataFrame()
            
        # 根据文件类型读取数据
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            logger.error(f"不支持的文件格式: {file_path}")
            return pd.DataFrame()
        
        # 日期列处理
        if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
            
        # 应用筛选条件
        if start_date and 'date' in df.columns:
            start_date = pd.to_datetime(start_date)
            df = df[df['date'] >= start_date]
            
        if end_date and 'date' in df.columns:
            end_date = pd.to_datetime(end_date)
            df = df[df['date'] <= end_date]
            
        if region and region != 'all' and 'region' in df.columns:
            df = df[df['region'] == region]
            
        return df
    
    except Exception as e:
        logger.error(f"加载数据失败: {str(e)}")
        return pd.DataFrame()

def process_data(df, aggregation='mean', group_by='date'):
    """
    处理数据，支持各种聚合和分组操作
    
    Args:
        df: 输入数据DataFrame
        aggregation: 聚合方法 ('mean', 'sum', 'max', 'min', 'median')
        group_by: 分组列 ('date', 'region', 'station', 等)
        
    Returns:
        DataFrame: 处理后的数据
    """
    try:
        if df.empty:
            return df
            
        # 确保分组列存在
        if group_by not in df.columns:
            logger.warning(f"分组列不存在: {group_by}")
            return df
            
        # 选择聚合方法
        agg_func = {
            'mean': 'mean',
            'sum': 'sum',
            'max': 'max',
            'min': 'min',
            'median': 'median'
        }.get(aggregation.lower(), 'mean')
        
        # 确定可以聚合的数值列
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        
        # 创建聚合字典
        agg_dict = {col: agg_func for col in numeric_cols if col != group_by}
        
        # 执行分组聚合
        result = df.groupby(group_by).agg(agg_dict).reset_index()
        
        return result
    
    except Exception as e:
        logger.error(f"处理数据失败: {str(e)}")
        return df

def calculate_aqi(pollutants_df):
    """
    根据污染物浓度计算AQI
    
    Args:
        pollutants_df: 包含污染物数据的DataFrame
        
    Returns:
        DataFrame: 带有AQI值的数据
    """
    try:
        if pollutants_df.empty:
            return pollutants_df
            
        # 这里实现AQI计算逻辑
        # 注意: 这里只是一个示例，实际计算需要根据国标来实现
        
        # 复制原始数据
        result = pollutants_df.copy()
        
        # 检查是否有必要的污染物列
        required_pollutants = ['pm25', 'pm10', 'so2', 'no2', 'o3', 'co']
        missing_pollutants = [p for p in required_pollutants if p not in result.columns]
        
        if missing_pollutants:
            logger.warning(f"缺少计算AQI所需的污染物: {missing_pollutants}")
            
        # 简化的AQI计算示例（仅作示范，实际应使用国标公式）
        if 'pm25' in result.columns:
            result['pm25_aqi'] = result['pm25'] * 1.5  # 简化计算，仅示例
            
        if 'pm10' in result.columns:
            result['pm10_aqi'] = result['pm10'] * 1.0  # 简化计算，仅示例
            
        # 计算综合AQI（取最大值）
        aqi_columns = [col for col in result.columns if col.endswith('_aqi')]
        if aqi_columns:
            result['aqi'] = result[aqi_columns].max(axis=1)
        else:
            # 如果没有AQI列，就简单估算一个（仅作示例）
            if 'pm25' in result.columns:
                result['aqi'] = result['pm25'] * 1.5
            elif 'pm10' in result.columns:
                result['aqi'] = result['pm10'] * 1.0
            else:
                logger.warning("无法计算AQI，缺少必要的污染物数据")
        
        return result
    
    except Exception as e:
        logger.error(f"计算AQI失败: {str(e)}")
        return pollutants_df

def get_aqi_level(aqi_value):
    """
    根据AQI值获取空气质量等级
    
    Args:
        aqi_value: AQI值
        
    Returns:
        dict: 包含等级、颜色和描述的字典
    """
    try:
        aqi = float(aqi_value)
        
        if aqi <= 50:
            return {
                'level': 1,
                'name': '优',
                'color': '#00e400',
                'description': '空气质量令人满意，基本无空气污染'
            }
        elif aqi <= 100:
            return {
                'level': 2,
                'name': '良',
                'color': '#ffff00',
                'description': '空气质量可接受，但某些污染物可能对极少数异常敏感人群健康有较弱影响'
            }
        elif aqi <= 150:
            return {
                'level': 3,
                'name': '轻度污染',
                'color': '#ff7e00',
                'description': '易感人群症状有轻度加剧，健康人群可能出现刺激症状'
            }
        elif aqi <= 200:
            return {
                'level': 4,
                'name': '中度污染',
                'color': '#ff0000',
                'description': '进一步加剧易感人群症状，可能对健康人群心脏、呼吸系统有影响'
            }
        elif aqi <= 300:
            return {
                'level': 5,
                'name': '重度污染',
                'color': '#99004c',
                'description': '心脏病和肺病患者症状显著加剧，运动耐受力降低，健康人群普遍出现症状'
            }
        else:
            return {
                'level': 6,
                'name': '严重污染',
                'color': '#7e0023',
                'description': '健康人群运动耐受力降低，有明显强烈症状，提前出现某些疾病'
            }
    except (ValueError, TypeError):
        return {
            'level': 0,
            'name': '未知',
            'color': '#cccccc',
            'description': '无法获取空气质量信息'
        } 