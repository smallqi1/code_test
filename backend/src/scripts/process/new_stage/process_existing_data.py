#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
广东省空气质量已下载数据处理脚本
功能：
    1. 读取data/new_data/raw_data目录下的所有已下载数据文件
    2. 检查对应的processed_newdata目录中是否有对应的处理后文件
    3. 处理所有缺失的文件，并同时保存到数据库和处理后的CSV文件
    4. 对于周末或处理结果为0的文件进行特殊处理
注意：这个脚本仅处理已下载但未处理的数据，不会下载新数据
"""

import os
import sys
import time
import logging
import pandas as pd
import numpy as np
import csv
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
from pathlib import Path
import yaml
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from time import perf_counter
from functools import lru_cache

# 导入原始数据处理脚本中的函数
from download_data_process import (
    setup_logging, init_db_pool, get_db_connection, 
    validate_record, determine_quality_level,
    insert_data_to_db, log_import_result, CONFIG, GUANGDONG_CITIES
)

# 初始化logger
logger = logging.getLogger(__name__)

# 加载配置
@lru_cache(maxsize=1)
def load_config():
    try:
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            # 确保save_csv设置为True
            config['save_csv'] = True
            return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        sys.exit(1)

CONFIG = load_config()

def get_raw_files():
    """获取raw_data目录下的所有CSV文件"""
    raw_dir = Path(CONFIG['paths']['download_dir'])
    return sorted(list(raw_dir.glob('*.csv')))

def get_processed_files():
    """获取processed_newdata目录下的所有已处理文件"""
    processed_dir = Path('D:/CODE/data/new_data/processed_newdata')
    processed_dir.mkdir(parents=True, exist_ok=True)
    return [f.stem for f in processed_dir.glob('*.csv')]

def find_missing_files(raw_files, processed_files):
    """找出已下载但尚未处理的文件"""
    missing_files = []
    
    for raw_file in raw_files:
        file_name = raw_file.stem
        # 从文件名提取日期
        date_str = file_name.replace('china_cities_', '')
        
        # 检查是否已有处理后的文件
        if date_str not in processed_files:
            missing_files.append(raw_file)
    
    return missing_files

def read_and_process_file(file_path):
    """直接读取并处理文件，替代原来的process_data_file函数"""
    try:
        start_time = perf_counter()
        logger.info(f"开始处理文件: {file_path}")
        processed_records = 0
        
        # 提取文件中的日期
        file_name = os.path.basename(file_path)
        date_str = file_name.replace('china_cities_', '').replace('.csv', '')
        file_date = datetime.strptime(date_str, '%Y%m%d').date()
        
        # 尝试不同的编码方式读取文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'cp936']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"读取文件时出错: {e}")
                continue
        
        if df is None:
            logger.error(f"无法读取文件: {file_path}")
            # 为0记录的文件创建一个空的CSV文件，防止重复处理
            save_empty_csv(date_str)
            return 0
        
        # 检查必要的列是否存在，兼容可能的不同列名
        required_cols_sets = [
            ['date', 'hour', 'type'],  # 标准格式
            ['日期', '小时', '类型']    # 可能的中文列名
        ]
        
        has_required_cols = False
        for required_cols in required_cols_sets:
            if all(col in df.columns for col in required_cols):
                has_required_cols = True
                # 如果是中文列名，重命名为英文
                if required_cols[0] == '日期':
                    df.rename(columns={
                        '日期': 'date',
                        '小时': 'hour',
                        '类型': 'type'
                    }, inplace=True)
                break
                
        if not has_required_cols:
            logger.error(f"文件缺少必要的列: {file_path}")
            save_empty_csv(date_str)
            return 0
        
        # 标识广东省城市的列
        gd_cities_cols = []
        for col in df.columns:
            for city in GUANGDONG_CITIES:
                city_without_suffix = city.replace('市', '')  # 去掉"市"字进行比较
                if city in col or city_without_suffix in col or col in city:
                    if col not in gd_cities_cols:
                        gd_cities_cols.append(col)
                    break
        
        if not gd_cities_cols:
            logger.error(f"未找到任何广东省城市: {file_path}")
            save_empty_csv(date_str)
            return 0
        
        # 仅保留AQI类型的数据用于检查
        aqi_data = df[df['type'] == 'AQI']
        if len(aqi_data) == 0:
            logger.warning(f"文件中没有AQI类型的数据: {file_path}")
            save_empty_csv(date_str)
            return 0
            
        # 处理周末数据 - 周末也应该有数据，检查特殊处理
        is_weekend = file_date.weekday() >= 5  # 5是周六，6是周日
        if is_weekend:
            logger.info(f"检测到周末数据 ({file_date}), 应用特殊处理逻辑")
        
        # 创建指标数据集
        indicators = {
            'AQI': aqi_data
        }
        for indicator in ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'CO']:
            indicator_data = df[df['type'] == indicator]
            if len(indicator_data) > 0:
                indicators[indicator] = indicator_data
        
        # 收集所有广东省的数据
        all_processed_data = []
        
        # 按日期小时分组
        date_hour_groups = {}
        for _, row in aqi_data.iterrows():
            key = (row['date'], row['hour'])
            if key not in date_hour_groups:
                date_hour_groups[key] = []
            date_hour_groups[key].append(row)
        
        # 处理每个日期和小时的数据
        for (date, hour), group_rows in date_hour_groups.items():
            # 格式化日期
            try:
                date_str = str(date)
                # 如果日期格式是YYYYMMDD，转换为YYYY-MM-DD
                if len(date_str) == 8 and date_str.isdigit():
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    date_str = date_obj.strftime('%Y-%m-%d')
            except Exception as e:
                logger.warning(f"日期格式错误: {date}, {e}")
                continue
            
            # 创建DataFrame用于处理
            group = pd.DataFrame(group_rows)
            
            # 处理每个广东省城市
            city_records = []
            for city_col in gd_cities_cols:
                record = process_city_data_local(city_col, group, date_str, hour, indicators)
                if record:
                    city_records.append(record)
            
            all_processed_data.extend(city_records)
            processed_records += len(city_records)
        
        # 保存数据到数据库和CSV
        if all_processed_data:
            # 使用自己的save_to_csv函数保存CSV
            save_to_csv(all_processed_data, file_date.strftime('%Y-%m-%d'))
            
            # 保存到数据库
            try:
                conn = get_db_connection()
                batch_size = 1000
                for i in range(0, len(all_processed_data), batch_size):
                    batch = all_processed_data[i:i+batch_size]
                    inserted_count = insert_data_to_db(conn, batch)
                    logger.info(f"已插入 {inserted_count} 条记录（批次 {i//batch_size + 1}/{(len(all_processed_data) + batch_size - 1) // batch_size}）")
                
                # 记录导入结果
                log_import_result(conn, file_name, processed_records, 
                                "SUCCESS", f"处理了{len(all_processed_data)}条记录")
            except Exception as e:
                logger.error(f"保存数据失败: {e}")
                return 0
            finally:
                if conn:
                    conn.close()
        else:
            # 如果没有提取到数据，创建一个空的CSV文件
            save_empty_csv(file_date.strftime('%Y%m%d'))
            logger.warning(f"文件 {file_path} 没有提取到有效数据")
        
        # 记录处理时间
        end_time = perf_counter()
        logger.info(f"文件处理完成: {file_path}, 处理记录数: {processed_records}, 耗时: {end_time - start_time:.2f}秒")
        
        return processed_records
    except Exception as e:
        logger.error(f"处理文件失败: {file_path}, 错误: {e}")
        # 提取文件中的日期并创建空文件
        try:
            file_name = os.path.basename(file_path)
            date_str = file_name.replace('china_cities_', '').replace('.csv', '')
            save_empty_csv(date_str)
        except:
            pass
        return 0

def process_city_data_local(city_col, group, date_str, hour, indicator_data):
    """处理单个城市的数据"""
    try:
        # 获取城市名称，保留"市"字
        city_name = None
        for city in GUANGDONG_CITIES:
            city_without_suffix = city.replace('市', '')  # 去掉"市"字进行比较
            if city in city_col or city_without_suffix in city_col or city_col in city:
                city_name = city  # 使用完整城市名（带"市"字）
                break
        
        if not city_name:
            return None
        
        # 获取AQI值
        aqi_value = group[city_col].iloc[0] if not pd.isna(group[city_col].iloc[0]) else None
        if aqi_value is None or (isinstance(aqi_value, str) and not aqi_value.strip()):
            return None
        
        # 转换为数值类型
        try:
            aqi_value = float(aqi_value)
        except (ValueError, TypeError):
            return None
        
        # 创建记录
        record = {
            'city': city_name,  # 保留完整城市名，包括"市"字
            'date': date_str,
            'aqi': aqi_value,
            'pm25': None,
            'pm10': None,
            'so2': None,
            'no2': None,
            'o3': None,
            'co': None,
            'quality_level': determine_quality_level(aqi_value)
        }
        
        # 获取所有指标值
        indicators = [
            ('PM2.5', 'pm25'),
            ('PM10', 'pm10'),
            ('SO2', 'so2'),
            ('NO2', 'no2'),
            ('O3', 'o3'),
            ('CO', 'co')
        ]
        
        for indicator_type, field_name in indicators:
            if indicator_type in indicator_data:
                indicator_group = indicator_data[indicator_type]
                indicator_group = indicator_group[(indicator_group['date'] == group['date'].iloc[0]) & 
                                               (indicator_group['hour'] == hour)]
                
                if len(indicator_group) > 0 and city_col in indicator_group.columns:
                    indicator_value = indicator_group[city_col].iloc[0] if not pd.isna(indicator_group[city_col].iloc[0]) else None
                    try:
                        record[field_name] = float(indicator_value) if indicator_value is not None else None
                    except (ValueError, TypeError):
                        pass
        
        # 验证数据合理性
        if validate_record(record):
            return record
    except Exception as e:
        logger.error(f"处理城市数据失败，城市={city_col}, 错误={e}")
    
    return None

def save_to_csv(data, file_date):
    """将处理好的数据保存为CSV文件，以日期命名"""
    if not data:
        logger.warning(f"{file_date}没有数据可保存")
        return
    
    # 构建完整的输出路径
    output_dir = Path('D:/CODE/data/new_data/processed_newdata')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建输出文件名，使用年月日格式
    date_obj = datetime.strptime(file_date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%Y%m%d')
    output_path = output_dir / f"{formatted_date}.csv"
        
    try:
        # 按日期和城市排序
        df = pd.DataFrame(data)
        # 转换日期列
        date_column = 'date'
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values([date_column, 'city']).reset_index(drop=True)
        
        # 写入CSV文件
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"数据已保存至: {output_path}, 共{len(df)}条记录")
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")

def save_empty_csv(date_str):
    """为没有数据的日期创建一个空的CSV文件，以防止重复处理"""
    output_dir = Path('D:/CODE/data/new_data/processed_newdata')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 确保日期格式是YYYYMMDD
    if len(date_str) == 10 and '-' in date_str:  # 如果是YYYY-MM-DD格式
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%Y%m%d')
    else:
        formatted_date = date_str
    
    output_path = output_dir / f"{formatted_date}.csv"
    
    try:
        # 创建一个空的DataFrame，但包含所有的列名
        columns = ['city', 'date', 'aqi', 'pm25', 'pm10', 'so2', 'no2', 'o3', 'co', 'quality_level']
        empty_df = pd.DataFrame(columns=columns)
        
        # 写入CSV文件
        empty_df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"创建了空的CSV文件: {output_path}")
    except Exception as e:
        logger.error(f"创建空CSV文件失败: {e}")

def main():
    # 初始化日志
    global logger
    logger = setup_logging()
    
    start_time = perf_counter()
    logger.info("===== 开始处理已下载未处理的数据文件 =====")
    
    # 初始化数据库连接池
    if not init_db_pool():
        logger.error("初始化数据库连接池失败，程序终止")
        return
    
    # 获取已下载和已处理的文件列表
    raw_files = get_raw_files()
    processed_files = get_processed_files()
    
    # 找出缺失的文件
    missing_files = find_missing_files(raw_files, processed_files)
    logger.info(f"发现 {len(missing_files)} 个已下载但未处理的文件")
    
    if not missing_files:
        logger.info("所有已下载文件均已处理，无需操作")
        return
    
    # 显示时间范围
    try:
        start_date = datetime.strptime(missing_files[0].stem.replace('china_cities_', ''), '%Y%m%d')
        end_date = datetime.strptime(missing_files[-1].stem.replace('china_cities_', ''), '%Y%m%d')
        logger.info(f"将处理从 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')} 的数据")
    except Exception as e:
        logger.warning(f"无法解析文件日期范围: {e}")
    
    # 串行处理文件，避免多进程导致的问题
    total_processed = 0
    for file_path in missing_files:
        try:
            processed_count = read_and_process_file(file_path)
            total_processed += processed_count
            logger.info(f"文件 {file_path} 处理完成，处理了 {processed_count} 条记录")
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {e}")
    
    # 计算总运行时间
    end_time = perf_counter()
    logger.info(f"所有文件处理完成，共处理 {total_processed} 条记录")
    logger.info(f"===== 处理完成，总耗时: {end_time - start_time:.2f}秒 =====")

if __name__ == '__main__':
    main() 