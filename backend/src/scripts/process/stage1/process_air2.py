import pandas as pd
import os
from pathlib import Path
import logging
from datetime import datetime
import json
import psutil
import time
from tqdm import tqdm
import gc
import numpy as np
import warnings

# 忽略特定的警告
warnings.filterwarnings('ignore', category=RuntimeWarning, message='Mean of empty slice')

# 广东省的城市列表
GUANGDONG_CITIES = [
    '广州', '深圳', '珠海', '汕头', '佛山', '韶关', '湛江', '肇庆', 
    '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', '清远',
    '东莞', '中山', '潮州', '揭阳', '云浮'
]

def get_memory_usage():
    """获取当前内存使用情况"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # 转换为MB

def setup_logging(name='air2'):
    """设置日志记录"""
    log_dir = os.path.join('data', 'logs')
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'process_{name}_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def safe_numeric_stats(series):
    """安全地计算数值统计信息"""
    try:
        if series.empty or series.isna().all():
            return {
                '最小值': None,
                '最大值': None,
                '平均值': None,
                '中位数': None
            }
        return {
            '最小值': float(series.min()) if not pd.isna(series.min()) else None,
            '最大值': float(series.max()) if not pd.isna(series.max()) else None,
            '平均值': float(series.mean()) if not pd.isna(series.mean()) else None,
            '中位数': float(series.median()) if not pd.isna(series.median()) else None
        }
    except:
        return {
            '最小值': None,
            '最大值': None,
            '平均值': None,
            '中位数': None
        }

def generate_statistics_report(df, report_path, file_name):
    """生成数据统计报告"""
    stats = {
        '文件名': file_name,
        '总行数': len(df),
        '列统计': {}
    }
    
    for column in df.columns:
        column_stats = {
            '非空值数量': int(df[column].count()),
            '空值数量': int(df[column].isnull().sum()),
            '唯一值数量': int(df[column].nunique())
        }
        
        if pd.api.types.is_numeric_dtype(df[column]):
            column_stats.update(safe_numeric_stats(df[column]))
        
        stats['列统计'][column] = column_stats
    
    return stats

def process_file(input_file, output_file, cities, logger, chunk_size=100000):
    """处理单个文件"""
    start_time = time.time()
    try:
        logger.info(f'开始处理文件: {input_file}')
        
        # 读取数据
        df = pd.read_csv(input_file, encoding='utf-8', low_memory=False)
        original_stats = generate_statistics_report(df, None, os.path.basename(input_file))
        
        # 选择必要的列
        base_columns = ['date', 'hour', 'type']
        city_columns = [col for col in df.columns if col in cities]
        selected_columns = base_columns + city_columns
        
        if not city_columns:
            logger.warning(f'文件中没有广东省的城市数据: {input_file}')
            return original_stats, None
        
        # 选择相关列并转换为长格式
        df_selected = df[selected_columns].copy()
        
        # 清理数据
        numeric_columns = [col for col in city_columns if pd.api.types.is_numeric_dtype(df_selected[col])]
        df_selected[numeric_columns] = df_selected[numeric_columns].fillna(method='ffill')
        
        df_long = df_selected.melt(
            id_vars=base_columns,
            value_vars=city_columns,
            var_name='city',
            value_name='value'
        )
        
        # 添加省份列
        df_long['Prvn'] = '广东省'
        
        # 保存处理后的数据
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df_long.to_csv(output_file, index=False, encoding='utf-8')
        
        processed_stats = generate_statistics_report(df_long, None, f'processed_{os.path.basename(input_file)}')
        
        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f'文件处理完成，耗时: {processing_time:.2f}秒')
        logger.info(f'处理前行数: {len(df)}, 处理后行数: {len(df_long)}')
        
        return original_stats, processed_stats
        
    except Exception as e:
        logger.error(f'处理文件时发生错误: {str(e)}')
        return None, None

def process_air2_data(input_dir, output_dir):
    """处理air2目录下的数据"""
    start_time = time.time()
    logger = setup_logging('air2')
    logger.info('开始处理air2数据')
    logger.info(f'初始内存使用: {get_memory_usage():.2f}MB')
    
    # 创建输出目录
    output_dir = os.path.join(output_dir, 'stage1', 'air2')
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建报告目录
    reports_dir = os.path.join( 'reports', 'air2')
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_stats = []
    processed_stats = []
    
    # 处理air2目录
    air2_path = os.path.join(input_dir, 'air2')
    if os.path.exists(air2_path):
        for root, dirs, files in os.walk(air2_path):
            for file in files:
                if file.endswith('.csv'):
                    try:
                        input_file = os.path.join(root, file)
                        rel_path = os.path.relpath(input_file, air2_path)
                        output_file = os.path.join(output_dir, rel_path)
                        
                        orig_stats, proc_stats = process_file(
                            input_file, 
                            output_file,
                            GUANGDONG_CITIES,
                            logger
                        )
                        
                        if orig_stats:
                            original_stats.append(orig_stats)
                        if proc_stats:
                            processed_stats.append(proc_stats)
                            
                    except Exception as e:
                        logger.error(f'处理文件 {input_file} 时发生错误: {str(e)}')
                        continue
    
    # 保存统计报告
    with open(os.path.join(reports_dir, f'original_stats_{timestamp}.json'), 'w', encoding='utf-8') as f:
        json.dump(original_stats, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(reports_dir, f'processed_stats_{timestamp}.json'), 'w', encoding='utf-8') as f:
        json.dump(processed_stats, f, ensure_ascii=False, indent=2)
    
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f'air2数据处理完成，总耗时: {total_time:.2f}秒')
    logger.info(f'最终内存使用: {get_memory_usage():.2f}MB')

if __name__ == '__main__':
    # 设置输入和输出目录
    input_dir = os.path.join('code', 'data', 'origin')
    output_dir = os.path.join('code', 'data', 'processed')
    
    # 处理数据
    process_air2_data(input_dir, output_dir)