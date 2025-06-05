#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
广东省空气质量数据提取处理脚本
功能：
    1. 先检查air_quality_monitoring数据库中已有的air_quality_data表的最新日期
    2. 再检查新创建的air_quality_newdata表
    3. 如果数据不是最新的，从网络自动下载从最新日期的后一天到当前日期的所有数据到指定文件夹(每5秒下载一次)
    4. 全部下载完成后，从指定文件夹读取并依次处理所有文件
    5. 从下载的全国空气质量数据中提取广东省各城市的数据
    6. 数据有多条则优先使用每日首小时数据，若为空则依次尝试后续小时数据
    7. 判断空气质量等级
    8. 将处理后的数据保存到MySQL数据库的air_quality_newdata表中
"""

import os
import csv
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import glob
import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool
import requests
import time
import logging
from logging.handlers import RotatingFileHandler
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from time import perf_counter
from pathlib import Path
import pickle
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 移除这里的基础日志配置，完全依赖setup_logging函数
# 初始化一个简单的默认logger，后续会被setup_logging替换
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # 防止未配置日志时的警告

# 性能优化: 使用LRU缓存装饰器缓存配置加载结果
@lru_cache(maxsize=1)
def load_config():
    """加载配置，支持环境变量覆盖"""
    try:
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 从环境变量覆盖配置
        if 'PROJECT_ROOT' in os.environ:
            PROJECT_ROOT = os.environ['PROJECT_ROOT']
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))))
        
        # 覆盖数据库配置
        if 'DB_PASSWORD' in os.environ:
            config['database']['password'] = os.environ['DB_PASSWORD']
        if 'DB_HOST' in os.environ:
            config['database']['host'] = os.environ['DB_HOST']
        if 'DB_USER' in os.environ:
            config['database']['user'] = os.environ['DB_USER']
        if 'DB_NAME' in os.environ:
            config['database']['database'] = os.environ['DB_NAME']
        
        # 覆盖路径配置
        config['paths'] = {
            'download_dir': os.path.join(PROJECT_ROOT, 'data', 'new_data', 'raw_data'),
            'processed_dir': os.path.join(PROJECT_ROOT, 'data', 'new_data', 'processed_newdata'),
            'log_dir': os.path.join(PROJECT_ROOT, 'backend', 'logs'),
            'backup_dir': os.path.join(PROJECT_ROOT, 'data', 'new_data', 'backup')
        }
        
        # 验证数据库密码是否已加载
        if not config['database']['password']:
            raise ValueError("DB_PASSWORD environment variable is required but not set")
        
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        sys.exit(1)

CONFIG = load_config()

# 初始化全局数据库连接池变量
db_pool = None

# 配置日志
def setup_logging():
    try:
        # 检查是否已经配置了相同的handler，避免重复
        root_logger = logging.getLogger()
        if root_logger.handlers:
            # 如果根日志已经有处理器，就返回现有logger避免重复配置
            return logger
        
        log_path = Path(CONFIG['paths']['log_dir'])
        log_path.mkdir(parents=True, exist_ok=True)
        
        log_file = log_path / CONFIG['logging']['filename']
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=CONFIG['logging']['max_bytes'],
            backupCount=CONFIG['logging']['backup_count']
        )
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # 配置根logger，确保所有模块都使用相同的配置
        root_logger.setLevel(CONFIG.get('logging', {}).get('level', 'INFO'))
        root_logger.addHandler(handler)
        
        # 配置本模块的logger
        module_logger = logging.getLogger(__name__)
        
        # 性能优化: 仅在DEBUG模式下添加控制台输出
        if CONFIG.get('debug', False):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        return module_logger
    except Exception as e:
        print(f"设置日志失败: {e}")
        sys.exit(1)

# 初始化数据库连接池
def init_db_pool():
    """初始化数据库连接池"""
    global db_pool
    try:
        # 性能优化: 增加连接池大小，提高并发处理能力
        db_config = {
            'pool_name': 'mypool',
            'pool_size': CONFIG.get('database', {}).get('pool_size', 10),
            'pool_reset_session': True,  # 重置会话状态
            'host': CONFIG['database']['host'],
            'user': CONFIG['database']['user'],
            'password': CONFIG['database']['password'],
            'database': CONFIG['database']['database'],
            # 性能优化: 添加数据库连接优化参数
            'use_pure': False,           # 使用C扩展提高性能
            'autocommit': True,          # 自动提交
            'buffered': True,            # 缓冲结果
            'consume_results': True,     # 自动消费结果
            'connection_timeout': 10,    # 连接超时
            'use_unicode': True,         # 使用Unicode
            'charset': 'utf8mb4'         # 设置字符集
        }
        db_pool = MySQLConnectionPool(**db_config)
        logger.info("数据库连接池初始化成功")
        return True
    except Error as e:
        logger.error(f"数据库连接池初始化失败: {e}")
        return False

# 广东省城市列表
GUANGDONG_CITIES = [
    '广州市', '深圳市', '珠海市', '汕头市', '佛山市', '韶关市', '湛江市', '肇庆市', 
    '江门市', '茂名市', '惠州市', '梅州市', '汕尾市', '河源市', '阳江市', '清远市', 
    '东莞市', '中山市', '潮州市', '揭阳市', '云浮市'
]

# 优化: 创建城市名称到ID的映射缓存
CITY_ID_CACHE = {city: idx for idx, city in enumerate(GUANGDONG_CITIES)}

def get_db_connection():
    """从连接池获取数据库连接"""
    global db_pool # 确保我们引用的是全局变量
    try:
        # 检查db_pool是否未初始化
        if db_pool is None:
            logger.info("数据库连接池尚未初始化，尝试进行初始化...")
            if not init_db_pool(): # 尝试初始化
                # 如果初始化失败，init_db_pool 会记录错误
                logger.error("尝试初始化数据库连接池失败")
                raise ConnectionError("无法初始化数据库连接池")
            else:
                logger.info("数据库连接池初始化成功")

        # 现在 db_pool 应该已经被初始化了 (如果成功的话)
        # 如果 init_db_pool 失败，上面的 raise 应该已经执行
        if db_pool is None:
             # 添加额外的保险检查，虽然理论上不应该到达这里
             logger.error("数据库连接池在尝试初始化后仍然无效")
             raise ConnectionError("数据库连接池初始化后仍无效")

        return db_pool.get_connection()
    except Error as e:
        logger.error(f"从连接池获取连接失败: {e}")
        raise
    except Exception as e:
        # 捕获上面可能抛出的 ConnectionError 或其他意外错误
        logger.error(f"获取数据库连接时发生错误: {e}")
        raise

def validate_data(data):
    """验证数据完整性"""
    if not data:
        return False
        
    required_fields = ['city', 'date', 'aqi', 'quality_level']
    try:
        for record in data:
            if not all(field in record for field in required_fields):
                logger.warning(f"数据记录缺少必要字段")
                return False
        return True
    except Exception as e:
        logger.error(f"数据验证失败: {e}")
        return False

# 性能优化: 使用缓存保存处理进度
PROGRESS_CACHE = {}

def save_progress(file_path, processed_records):
    """保存处理进度"""
    try:
        # 首先更新内存缓存
        PROGRESS_CACHE[str(file_path)] = {
            'processed_records': processed_records,
            'timestamp': datetime.now().isoformat()
        }
        
        # 每10个文件或者最后一个文件才写入磁盘
        if len(PROGRESS_CACHE) >= 10 or processed_records == 0:
            progress_file = Path(CONFIG['paths']['log_dir']) / 'progress.json'
            
            # 读取现有进度
            existing_progress = {}
            if progress_file.exists():
                try:
                    with open(progress_file, 'r') as f:
                        existing_progress = json.load(f)
                except:
                    pass  # 如果读取失败，使用空字典
            
            # 更新进度
            existing_progress.update(PROGRESS_CACHE)
            
            # 写入文件
            with open(progress_file, 'w') as f:
                json.dump(existing_progress, f)
            
            # 清空缓存
            PROGRESS_CACHE.clear()
            
    except Exception as e:
        logger.error(f"保存进度失败: {e}")

# 性能优化: 使用缓存减少相同URL的下载请求
DOWNLOAD_CACHE = {}

def download_air_data(date_obj):
    """从网络下载指定日期的空气质量数据"""
    date_str = date_obj.strftime('%Y%m%d')
    url = f"https://quotsoft.net/air/data/china_cities_{date_str}.csv"
    
    # 检查缓存
    if url in DOWNLOAD_CACHE:
        return DOWNLOAD_CACHE[url]
    
    download_dir = Path(CONFIG['paths']['download_dir'])
    file_path = download_dir / f"china_cities_{date_str}.csv"
    
    # 检查文件是否已存在
    if file_path.exists():
        DOWNLOAD_CACHE[url] = file_path
        return file_path
    
    logger.info(f"准备下载文件到: {file_path}")
    
    for attempt in range(CONFIG['download']['retry_attempts']):
        try:
            # 性能优化: 使用会话维持连接，添加超时和头信息
            session = requests.Session()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = session.get(url, timeout=CONFIG['download']['timeout'], headers=headers)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"数据下载成功: {file_path}")
                DOWNLOAD_CACHE[url] = file_path
                return file_path
            else:
                logger.warning(f"下载失败，状态码: {response.status_code}, 尝试次数: {attempt + 1}")
                if attempt < CONFIG['download']['retry_attempts'] - 1:
                    time.sleep(CONFIG['download']['retry_delay'])
        except Exception as e:
            logger.error(f"下载出错: {e}, 尝试次数: {attempt + 1}")
            if attempt < CONFIG['download']['retry_attempts'] - 1:
                time.sleep(CONFIG['download']['retry_delay'])
    
    return None

# 性能优化: 缓存城市索引结果
city_indices_cache = {}

def get_city_indices(header):
    """获取广东省城市在数据中的索引位置"""
    # 使用缓存机制
    cache_key = ','.join(header)
    if cache_key in city_indices_cache:
        return city_indices_cache[cache_key]
    
    city_indices = {}
    for city in GUANGDONG_CITIES:
        for i, col_name in enumerate(header):
            try:
                # 尝试解码中文名称处理
                decoded_col = col_name
                # 检查城市名是否包含在列名中，或列名是否包含在城市名中
                city_without_suffix = city.replace('市', '')  # 去掉"市"字进行比较
                if city in decoded_col or city_without_suffix in decoded_col or decoded_col in city:
                    city_indices[city] = i
                    break
            except Exception as e:
                continue
    
    # 保存到缓存
    city_indices_cache[cache_key] = city_indices
    return city_indices

# 优化流程: 使用共享的数据检测日期范围，避免重复检查文件
PROCESSED_DATES = set()

def process_data_file(file_path):
    """处理单个数据文件"""
    try:
        start_time = perf_counter()
        logger.info(f"开始处理文件: {file_path}")
        processed_records = 0
        
        # 提取文件中的日期
        try:
            file_name = os.path.basename(file_path)
            date_str = file_name.replace('china_cities_', '').replace('.csv', '')
            file_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            # 检查是否已经处理过这个日期
            if file_date in PROCESSED_DATES:
                logger.info(f"文件 {file_path} 对应的日期 {file_date} 已处理过，跳过")
                return 0
        except Exception as e:
            logger.warning(f"无法从文件名提取日期: {e}")
        
        # 尝试不同的编码方式读取文件
        encodings = ['utf-8', 'gbk', 'gb2312', 'cp936']
        df = None
        
        for encoding in encodings:
            try:
                # 性能优化: 使用chunksize参数分批读取大文件
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"读取文件时出错: {e}")
                continue
        
        if df is None:
            logger.error(f"无法读取文件: {file_path}")
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
            return 0
        
        # 性能优化: 预先创建指标类型的数据集，避免多次筛选
        indicator_data = {}
        for indicator in ['AQI', 'PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'CO']:
            if indicator in df['type'].values:
                indicator_data[indicator] = df[df['type'] == indicator]
        
        # 处理文件中的数据
        all_processed_data = []
        
        # 获取AQI类型的数据
        aqi_data = indicator_data.get('AQI', df[df['type'] == 'AQI'])
        if len(aqi_data) == 0:
            logger.warning(f"文件中没有AQI类型的数据: {file_path}")
            return 0
        
        # 性能优化: 创建按日期和小时分组的字典，避免每次重新分组
        date_hour_groups = {}
        for _, row in aqi_data.iterrows():
            key = (row['date'], row['hour'])
            if key not in date_hour_groups:
                date_hour_groups[key] = []
            date_hour_groups[key].append(row)
        
        # 按日期小时分组处理
        for (date, hour), group_rows in date_hour_groups.items():
            # 格式化日期
            try:
                date_str = str(date)
                # 如果日期格式是YYYYMMDD，转换为YYYY-MM-DD
                if len(date_str) == 8 and date_str.isdigit():
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    date_str = date_obj.strftime('%Y-%m-%d')
                    
                # 记录处理过的日期
                PROCESSED_DATES.add(date_obj.date())
            except Exception as e:
                logger.warning(f"日期格式错误: {date}, {e}")
                continue
            
            # 创建groupby DataFrame
            group = pd.DataFrame(group_rows)
            
            # 并行处理每个城市的记录
            city_records = []
            
            # 优化: 使用线程池处理多个城市的数据
            with ThreadPoolExecutor(max_workers=min(len(gd_cities_cols), 10)) as executor:
                # 准备城市任务
                future_to_city = {
                    executor.submit(process_city_data, 
                                   city_col, 
                                   group, 
                                   date_str, 
                                   hour, 
                                   indicator_data): city_col 
                    for city_col in gd_cities_cols
                }
                
                # 收集结果
                for future in future_to_city:
                    try:
                        result = future.result()
                        if result:
                            city_records.append(result)
                    except Exception as e:
                        logger.error(f"处理城市数据失败: {e}")
            
            all_processed_data.extend(city_records)
            processed_records += len(city_records)
        
        if all_processed_data:
            # 性能优化: 使用批量插入提高数据库写入性能
            try:
                conn = get_db_connection()
                # 增大批量处理的大小
                batch_size = 1000
                for i in range(0, len(all_processed_data), batch_size):
                    batch = all_processed_data[i:i+batch_size]
                    inserted_count = insert_data_to_db(conn, batch)
                    logger.info(f"已插入 {inserted_count} 条记录（批次 {i//batch_size + 1}/{(len(all_processed_data) + batch_size - 1) // batch_size}）")
                
                # 记录导入结果
                file_name = os.path.basename(file_path)
                log_import_result(conn, file_name, processed_records, 
                               "SUCCESS", f"处理了{len(all_processed_data)}条记录")
                
                # 保存到CSV（可选）
                if CONFIG.get('save_csv', True):
                    # 获取文件日期
                    file_date_str = file_name.replace('china_cities_', '').replace('.csv', '')
                    file_date = datetime.strptime(file_date_str, '%Y%m%d').strftime('%Y-%m-%d')
                    save_to_csv(all_processed_data, file_date)
            except Exception as e:
                logger.error(f"保存数据失败: {e}")
                return 0
            finally:
                if conn:
                    conn.close()
        
        # 保存处理进度
        save_progress(file_path, processed_records)
        
        # 记录处理时间
        end_time = perf_counter()
        logger.info(f"文件处理完成: {file_path}, 处理记录数: {processed_records}, 耗时: {end_time - start_time:.2f}秒")
        
        return processed_records
    except Exception as e:
        logger.error(f"处理文件失败: {file_path}, 错误: {e}")
        return 0

def process_city_data(city_col, group, date_str, hour, indicator_data):
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
        
        # 优化: 一次获取所有指标值
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

def validate_record(record):
    """验证单条记录的数据合理性"""
    try:
        # 兼容新旧字段名，添加字段映射
        record_with_standard_fields = record.copy()
        
        # 将date映射到record_date字段
        if 'date' in record and 'record_date' not in record:
            record_with_standard_fields['record_date'] = record['date']
            
        # 将aqi映射到aqi_index字段
        if 'aqi' in record and 'aqi_index' not in record:
            record_with_standard_fields['aqi_index'] = record['aqi']
            
        # 检查必要字段是否存在
        required_fields_original = ['city', 'record_date', 'aqi_index', 'quality_level']
        required_fields_alternative = ['city', 'date', 'aqi', 'quality_level']
        
        # 使用原始字段名检查
        has_original_fields = all(field in record_with_standard_fields for field in required_fields_original)
        # 或使用替代字段名检查
        has_alternative_fields = all(field in record for field in required_fields_alternative)
        
        if not (has_original_fields or has_alternative_fields):
            missing_fields = [field for field in required_fields_original 
                             if field not in record_with_standard_fields]
            logger.warning(f"记录缺少必要字段: {missing_fields}")
            return False
            
        # 检查数值范围，使用转换后的字段或原始字段
        aqi_value = record_with_standard_fields.get('aqi_index', record.get('aqi'))
        if aqi_value is None or not (0 <= float(aqi_value) <= 500):
            if aqi_value is not None:
                logger.warning(f"AQI值超出范围: {aqi_value}")
            return False
            
        # 检查其他指标的合理范围，兼容两种可能的字段名
        indicators = {
            'pm25_avg': ('pm25', 0, 500),
            'pm10_avg': ('pm10', 0, 600),
            'so2_avg': ('so2', 0, 800),
            'no2_avg': ('no2', 0, 200),
            'o3_avg': ('o3', 0, 300),
            'co_avg': ('co', 0, 20)
        }
        
        for std_name, (alt_name, min_val, max_val) in indicators.items():
            # 获取标准字段名或替代字段名的值
            value = record_with_standard_fields.get(std_name, record.get(alt_name))
            if value is not None:
                try:
                    float_value = float(value)
                    if not min_val <= float_value <= max_val:
                        logger.warning(f"{std_name}值超出范围: {float_value}")
                        return False
                except (ValueError, TypeError):
                    logger.warning(f"{std_name}值无法转换为浮点数: {value}")
                    return False
        
        return True
    except Exception as e:
        logger.error(f"数据验证失败: {e}")
        return False

def determine_quality_level(aqi):
    """根据AQI指数确定空气质量等级"""
    if aqi <= 50:
        return "优"
    elif aqi <= 100:
        return "良"
    elif aqi <= 150:
        return "轻度污染"
    elif aqi <= 200:
        return "中度污染"
    elif aqi <= 300:
        return "重度污染"
    else:
        return "严重污染"

# 性能优化: 使用批量插入优化数据库插入性能
def insert_data_to_db(conn, data_batch, table_name='air_quality_newdata'):
    """批量插入数据到数据库"""
    if not data_batch:
        return 0
        
    cursor = conn.cursor()
    inserted_count = 0
    
    try:
        # 构建插入语句
        query = f"""
        INSERT INTO {table_name} 
        (city, province, record_date, aqi_index, quality_level, aqi_rank, pm25_avg, pm10_avg, so2_avg, no2_avg, co_avg, o3_avg, data_year)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        province = VALUES(province),
        aqi_index = VALUES(aqi_index),
        quality_level = VALUES(quality_level),
        pm25_avg = COALESCE(VALUES(pm25_avg), pm25_avg),
        pm10_avg = COALESCE(VALUES(pm10_avg), pm10_avg),
        so2_avg = COALESCE(VALUES(so2_avg), so2_avg),
        no2_avg = COALESCE(VALUES(no2_avg), no2_avg),
        co_avg = COALESCE(VALUES(co_avg), co_avg),
        o3_avg = COALESCE(VALUES(o3_avg), o3_avg)
        """
        
        # 准备批量数据
        values = []
        for record in data_batch:
            # 提取年份
            date_obj = datetime.strptime(record['date'], '%Y-%m-%d')
            year = date_obj.year
            
            # 准备数据
            row = (
                record['city'],
                "广东省",  # 添加省份信息
                record['date'],
                record['aqi'],
                record['quality_level'],
                None,  # aqi_rank 暂时为空
                record['pm25'],
                record['pm10'],
                record['so2'],
                record['no2'],
                record['co'],
                record['o3'],
                year
            )
            values.append(row)
        
        # 性能优化: 使用executemany进行批量插入
        cursor.executemany(query, values)
        conn.commit()
        
        inserted_count = cursor.rowcount
    except Error as e:
        logger.error(f"数据库插入错误: {e}")
        if hasattr(e, 'errno'):
            logger.error(f"错误号: {e.errno}")
        if hasattr(e, 'sqlstate'):
            logger.error(f"SQL状态: {e.sqlstate}")
        if hasattr(e, 'msg'):
            logger.error(f"错误信息: {e.msg}")
            
        # 尝试进行部分插入
        try:
            if len(data_batch) > 1:
                logger.info(f"尝试逐条插入 {len(data_batch)} 条记录...")
                for record in data_batch:
                    try:
                        # 提取年份
                        date_obj = datetime.strptime(record['date'], '%Y-%m-%d')
                        year = date_obj.year
                        
                        # 逐条插入
                        cursor.execute(query, (
                            record['city'],
                            "广东省",  # 添加省份信息
                            record['date'],
                            record['aqi'],
                            record['quality_level'],
                            None,  # aqi_rank 暂时为空
                            record['pm25'],
                            record['pm10'],
                            record['so2'],
                            record['no2'],
                            record['co'],
                            record['o3'],
                            year
                        ))
                        conn.commit()
                        inserted_count += 1
                    except Error as e2:
                        logger.warning(f"单条记录插入失败: {e2}")
                logger.info(f"逐条插入完成，成功插入 {inserted_count} 条记录")
        except Exception as e2:
            logger.error(f"逐条插入过程发生错误: {e2}")
    finally:
        cursor.close()
        
    return inserted_count

def check_and_update_data():
    """检查数据库中的最新日期，并下载更新数据"""
    try:
        # 使用连接池获取连接
        try:
            conn = get_db_connection()
        except NameError as ne:
            if 'db_pool' in str(ne):
                logger.error("数据库连接池未初始化")
                return []
            else:
                raise
        except Exception as ce:
            logger.error(f"获取数据库连接失败: {ce}")
            return []
        
        # 获取两个表中的最新日期
        latest_date_main = get_latest_date_from_db(conn, 'air_quality_data')
        latest_date_new = get_latest_date_from_db(conn, 'air_quality_newdata')
        
        # 取两个日期中的较新日期
        latest_date = None
        if latest_date_main and latest_date_new:
            latest_date = max(latest_date_main, latest_date_new)
            logger.info(f"两个表中最新的数据日期为: {latest_date}")
        elif latest_date_main:
            latest_date = latest_date_main
            logger.info(f"只有air_quality_data表有数据，最新日期为: {latest_date}")
        elif latest_date_new:
            latest_date = latest_date_new
            logger.info(f"只有air_quality_newdata表有数据，最新日期为: {latest_date}")
        
        # 当前日期的前一天作为下载的结束日期
        current_date = datetime.now().date() - timedelta(days=1)
        logger.info(f"设置下载结束日期为当前日期的前一天: {current_date}")
        
        if latest_date is None:
            # 如果没有数据，从30天前开始下载
            start_date = current_date - timedelta(days=30)
            logger.info(f"数据库中没有数据，将从{start_date}开始下载")
        else:
            # 从最新日期的下一天开始下载
            start_date = latest_date + timedelta(days=1)
            logger.info(f"数据库中最新日期为{latest_date}，将从{start_date}开始下载")
        
        # 释放数据库连接
        conn.close()
        
        if start_date > current_date:
            logger.info("数据已是最新，无需下载")
            return []
            
        # 生成需要下载的日期范围
        date_range = [start_date + timedelta(days=i) for i in range((current_date - start_date).days + 1)]
        
        logger.info(f"计划下载从{start_date}到{current_date}的数据，共{len(date_range)}天")
        
        return date_range
    except Exception as e:
        logger.error(f"检查和更新数据时出错: {e}")
        return []

def get_latest_date_from_db(conn, table_name='air_quality_newdata'):
    """获取数据库中指定表最新的数据日期"""
    try:
        cursor = conn.cursor()
        date_column = 'record_date'  # 统一使用record_date作为日期列名
        query = f"""
        SELECT MAX({date_column}) FROM {table_name}
        """
        cursor.execute(query)
        result = cursor.fetchone()[0]
        if result:
            logger.info(f"{table_name}表中最新数据日期: {result}\n")
            return result
        else:
            logger.info(f"{table_name}表中没有数据\n")
            return None
    except Error as e:
        logger.error(f"获取{table_name}表最新日期时出错: {e}\n")
        return None
    finally:
        if cursor:
            cursor.close()

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
        date_column = 'record_date'
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values([date_column, 'city']).reset_index(drop=True)
        elif 'date' in df.columns:
            # 兼容旧列名
            logger.warning("数据中使用了旧列名'date'，而不是'record_date'")
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(['date', 'city']).reset_index(drop=True)
        
        # 写入CSV文件
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"数据已保存至: {output_path}, 共{len(df)}条记录")
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")

def log_import_result(conn, filename, records_count, status, message):
    """记录导入结果到日志表"""
    try:
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO import_logs 
        (filename, records_count, status, message)
        VALUES (%s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (filename, records_count, status, message))
        conn.commit()
        logger.info(f"记录导入日志: {filename}, {status}")
        
    except Error as e:
        logger.error(f"记录日志时出错: {e}")
    finally:
        if cursor:
            cursor.close()

def check_table_exists(conn, table_name):
    """检查表是否存在"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = '{CONFIG['database']['database']}'
            AND table_name = '{table_name}'
        """)
        if cursor.fetchone()[0] == 1:
            logger.info(f"表 {table_name} 已存在")
            return True
        else:
            logger.info(f"表 {table_name} 不存在")
            return False
    except Error as e:
        logger.error(f"检查表是否存在时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()

def create_tables_if_not_exist(conn):
    """如果不存在则创建必要的表"""
    try:
        # 检查空气质量数据表是否存在
        if not check_table_exists(conn, 'air_quality_data'):
            cursor = conn.cursor()
            # 创建空气质量数据表
            create_table_query = """
            CREATE TABLE IF NOT EXISTS air_quality_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                city VARCHAR(50) NOT NULL,
                province VARCHAR(50) NOT NULL,
                record_date DATE NOT NULL,
                aqi_index FLOAT,
                quality_level VARCHAR(20),
                aqi_rank FLOAT,
                pm25_avg FLOAT,
                pm10_avg FLOAT,
                so2_avg FLOAT,
                no2_avg FLOAT,
                co_avg FLOAT,
                o3_avg FLOAT,
                data_year INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uc_city_date (city, record_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            cursor.execute(create_table_query)
            logger.info("创建空气质量数据表")
            cursor.close()
        
        # 检查新的空气质量数据表是否存在
        if not check_table_exists(conn, 'air_quality_newdata'):
            cursor = conn.cursor()
            # 创建新的空气质量数据表
            create_table_query = """
            CREATE TABLE IF NOT EXISTS air_quality_newdata (
                id INT AUTO_INCREMENT PRIMARY KEY,
                city VARCHAR(50) NOT NULL,
                province VARCHAR(50) NOT NULL,
                record_date DATE NOT NULL,
                aqi_index FLOAT,
                quality_level VARCHAR(20),
                aqi_rank FLOAT,
                pm25_avg FLOAT,
                pm10_avg FLOAT,
                so2_avg FLOAT,
                no2_avg FLOAT,
                co_avg FLOAT,
                o3_avg FLOAT,
                data_year INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uc_city_date (city, record_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            cursor.execute(create_table_query)
            logger.info("创建新的空气质量数据表")
            cursor.close()
        
        # 检查导入日志表是否存在
        if not check_table_exists(conn, 'import_logs'):
            cursor = conn.cursor()
            # 创建导入日志表
            create_log_table_query = """
            CREATE TABLE IF NOT EXISTS import_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                records_count INT NOT NULL,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20),
                message TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
            cursor.execute(create_log_table_query)
            logger.info("创建导入日志表")
            cursor.close()
            
        conn.commit()
        logger.info("数据表已检查完成")
        return True
        
    except Error as e:
        logger.error(f"创建表时出错: {e}")
        return False

def create_database_if_not_exists():
    """创建数据库（如果不存在）"""
    try:
        # 创建没有指定数据库的连接
        conn = mysql.connector.connect(
            host=CONFIG['database']['host'],
            user=CONFIG['database']['user'],
            password=CONFIG['database']['password']
        )
        
        cursor = conn.cursor()
        
        # 创建数据库
        cursor.execute(f"""
        CREATE DATABASE IF NOT EXISTS {CONFIG['database']['database']}
        DEFAULT CHARACTER SET utf8mb4
        DEFAULT COLLATE utf8mb4_general_ci
        """)
        
        logger.info(f"确保数据库 {CONFIG['database']['database']} 存在")
        
        # 使用数据库
        cursor.execute(f"USE {CONFIG['database']['database']}")
        
        conn.commit()
        return True
        
    except Error as e:
        logger.error(f"创建数据库失败: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def connect_to_db():
    """连接到数据库"""
    try:
        logger.debug("正在连接到数据库...")
        conn = mysql.connector.connect(
            host=CONFIG['database']['host'],
            user=CONFIG['database']['user'],
            password=CONFIG['database']['password'],
            database=CONFIG['database']['database']
        )
        if conn.is_connected():
            logger.debug("数据库连接成功")
        return conn
    except Error as e:
        logger.error(f"数据库连接错误: {e}")
        return None

def main():
    try:
        # 初始化日志
        global logger
        logger = setup_logging()
        
        start_time = perf_counter()
        logger.info("===== 开始运行空气质量数据处理脚本 =====")
        
        # 创建必要的目录
        for path in CONFIG['paths'].values():
            Path(path).mkdir(parents=True, exist_ok=True)
        
        # !! 初始化数据库连接池提前 !!
        if not init_db_pool():
            logger.error("初始化数据库连接池失败，程序终止")
            # 如果池初始化失败，则无法进行后续需要池的操作，直接返回
            return 

        # 创建数据库（如果不存在） - 使用直接连接
        if not create_database_if_not_exists():
            logger.error("创建数据库失败，程序终止")
            return
            
        # 获取数据库连接（用于创建表） - 使用直接连接
        conn = connect_to_db()
        if not conn:
            logger.error("无法连接到数据库（用于表结构检查），程序终止")
            return
            
        # 创建必要的表（如果不存在） - 使用直接连接
        if not create_tables_if_not_exist(conn):
            logger.error("创建数据表失败，程序终止")
            conn.close()
            return
        conn.close() # 关闭用于检查/创建表的直接连接
            
        # !! 原 init_db_pool() 位置移除 !!
        # 连接池已在上面成功初始化，可以继续执行
        
        # 确定需要下载的日期范围 - 现在会使用 get_db_connection() 从池中获取连接
        date_range = check_and_update_data()
        
        if not date_range:
            logger.info("没有新数据需要下载，程序终止")
            return
            
        download_dir = Path(CONFIG['paths']['download_dir'])
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # 性能优化: 并行下载数据
        logger.info(f"开始下载数据，共 {len(date_range)} 天")
        
        # 使用多线程并行下载
        with ThreadPoolExecutor(max_workers=min(5, len(date_range))) as executor:
            # 提交下载任务
            future_to_date = {executor.submit(download_air_data, date_obj): date_obj for date_obj in date_range}
            
            # 收集下载结果
            downloaded_files = []
            for future in future_to_date:
                try:
                    result = future.result()
                    if result:
                        downloaded_files.append(result)
                        logger.info(f"成功下载: {result}")
                    else:
                        date_obj = future_to_date[future]
                        logger.warning(f"下载失败: {date_obj}")
                except Exception as e:
                    logger.error(f"下载过程出错: {e}")
        
        if not downloaded_files:
            logger.info("没有找到下载的文件")
            return
            
        logger.info(f"下载完成，找到 {len(downloaded_files)} 个文件等待处理")
        
        # 性能优化: 使用进程池并行处理文件
        with ProcessPoolExecutor(max_workers=min(os.cpu_count(), len(downloaded_files))) as executor:
            # 提交处理任务
            future_to_file = {executor.submit(process_data_file, file_path): file_path for file_path in downloaded_files}
            
            # 收集处理结果
            total_processed = 0
            for future in future_to_file:
                try:
                    processed_count = future.result()
                    total_processed += processed_count
                    file_path = future_to_file[future]
                    logger.info(f"文件 {file_path} 处理完成，处理了 {processed_count} 条记录")
                except Exception as e:
                    file_path = future_to_file[future]
                    logger.error(f"处理文件 {file_path} 时出错: {e}")
        
        logger.info(f"所有文件处理完成，共处理 {total_processed} 条记录")
        
        # 计算总运行时间
        end_time = perf_counter()
        logger.info(f"===== 空气质量数据处理脚本运行完成，总耗时: {end_time - start_time:.2f}秒 =====")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()