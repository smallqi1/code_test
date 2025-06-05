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

def get_memory_usage():
    """获取当前内存使用情况"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # 转换为MB

def setup_logging(name='air1'):
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

def process_file(input_file, output_file, province, logger, chunk_size=100000):
    """处理单个文件"""
    start_time = time.time()
    total_rows = 0
    processed_rows = 0
    
    try:
        # 首先计算总行数
        logger.info(f'计算文件总行数: {input_file}')
        for chunk in pd.read_csv(input_file, encoding='utf-8', chunksize=chunk_size, low_memory=False):
            total_rows += len(chunk)
        
        logger.info(f'文件总行数: {total_rows}')
        
        # 创建进度条
        pbar = tqdm(total=total_rows, desc=f'处理文件: {os.path.basename(input_file)}')
        
        # 分块处理数据
        original_stats = None
        processed_chunks = []
        
        for chunk_num, chunk in enumerate(pd.read_csv(input_file, encoding='utf-8', chunksize=chunk_size, low_memory=False)):
            pbar.update(len(chunk))
            
            # 只保留指定省份的数据
            chunk_province = chunk[chunk['Prvn'] == province].copy()
            processed_rows += len(chunk_province)
            
            if chunk_num == 0:
                original_stats = generate_statistics_report(chunk, None, os.path.basename(input_file))
            
            if not chunk_province.empty:
                # 清理数据
                numeric_columns = chunk_province.select_dtypes(include=[np.number]).columns
                chunk_province[numeric_columns] = chunk_province[numeric_columns].fillna(method='ffill')
                processed_chunks.append(chunk_province)
            
            if chunk_num % 5 == 0:
                gc.collect()
            
            if chunk_num % 10 == 0:
                logger.info(f'当前内存使用: {get_memory_usage():.2f}MB')
        
        pbar.close()
        
        if processed_chunks:
            final_df = pd.concat(processed_chunks, ignore_index=True)
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            final_df.to_csv(output_file, index=False, encoding='utf-8')
            processed_stats = generate_statistics_report(final_df, None, f'processed_{os.path.basename(input_file)}')
        else:
            processed_stats = None
            logger.warning(f'文件中没有{province}的数据')
        
        del processed_chunks
        gc.collect()
        
        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f'文件处理完成，耗时: {processing_time:.2f}秒')
        logger.info(f'处理前行数: {total_rows}, 处理后行数: {processed_rows}')
        
        return original_stats, processed_stats
    
    except Exception as e:
        logger.error(f'处理文件时发生错误: {str(e)}')
        return None, None

def process_air1_data(input_dir, output_dir, province='广东省'):
    """处理air1目录下的数据"""
    start_time = time.time()
    logger = setup_logging('air1')
    logger.info(f'开始处理air1数据，目标省份: {province}')
    logger.info(f'初始内存使用: {get_memory_usage():.2f}MB')
    
    # 创建输出目录
    output_dir = os.path.join(output_dir, 'stage1', 'air1')
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建报告目录
    reports_dir = os.path.join( 'reports', 'air1')
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_stats = []
    processed_stats = []
    
    # 处理air1目录
    air1_path = os.path.join(input_dir, 'air1')
    if os.path.exists(air1_path):
        files = [f for f in os.listdir(air1_path) if f.endswith('.csv')]
        logger.info(f'在air1目录中找到{len(files)}个CSV文件')
        
        for file in files:
            try:
                input_file = os.path.join(air1_path, file)
                output_file = os.path.join(output_dir, f'processed_{file}')
                
                orig_stats, proc_stats = process_file(input_file, output_file, province, logger)
                
                if orig_stats:
                    original_stats.append(orig_stats)
                if proc_stats:
                    processed_stats.append(proc_stats)
                    
            except Exception as e:
                logger.error(f'处理文件 {file} 时发生错误: {str(e)}')
                continue
    
    # 保存统计报告
    with open(os.path.join(reports_dir, f'original_stats_{timestamp}.json'), 'w', encoding='utf-8') as f:
        json.dump(original_stats, f, ensure_ascii=False, indent=2)
    
    with open(os.path.join(reports_dir, f'processed_stats_{timestamp}.json'), 'w', encoding='utf-8') as f:
        json.dump(processed_stats, f, ensure_ascii=False, indent=2)
    
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f'air1数据处理完成，总耗时: {total_time:.2f}秒')
    logger.info(f'最终内存使用: {get_memory_usage():.2f}MB')

if __name__ == '__main__':
    # 设置输入和输出目录
    input_dir = os.path.join('code', 'data', 'origin')
    output_dir = os.path.join('code', 'data', 'processed')
    
    # 处理数据
    process_air1_data(input_dir, output_dir)