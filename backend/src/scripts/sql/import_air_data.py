#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
导入空气质量数据到MySQL数据库
将data/air_data/processed/stage3目录下的所有CSV文件导入到MySQL数据库中
"""

import os
import csv
import mysql.connector
from mysql.connector import Error
import glob
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME', 'air_quality_monitoring')
}

# Validate that password is loaded
if not DB_CONFIG['password']:
    raise ValueError("DB_PASSWORD environment variable is required but not set")

# 设置项目根目录和数据目录
if 'PROJECT_ROOT' in os.environ:
    PROJECT_ROOT = os.environ['PROJECT_ROOT']
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))

# 数据目录
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "air_data", "processed", "stage3")

def create_database_if_not_exists():
    """创建数据库(如果不存在)"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} DEFAULT CHARACTER SET utf8mb4")
        print(f"数据库 {DB_CONFIG['database']} 已创建或已存在")
        
        conn.close()
        return True
        
    except Error as e:
        print(f"创建数据库时出错: {e}")
        return False

def create_tables():
    """创建必要的表结构"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 创建空气质量数据表
        cursor.execute("""
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
            INDEX idx_city (city),
            INDEX idx_date (record_date),
            INDEX idx_year (data_year),
            UNIQUE KEY uc_city_date (city, record_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        print("数据表已成功创建")
        conn.close()
        return True
        
    except Error as e:
        print(f"创建表时出错: {e}")
        return False

def import_csv_file(file_path):
    """导入单个CSV文件到数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        file_name = os.path.basename(file_path)
        
        # 从文件名中提取年份
        year = file_name.split('_')[-1].split('.')[0]
        
        # 读取CSV文件
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            headers = next(csv_reader)  # 跳过表头
            
            records_count = 0
            errors_count = 0
            
            # 准备插入语句
            insert_query = """
            INSERT INTO air_quality_data 
            (city, province, record_date, aqi_index, quality_level, aqi_rank, 
            pm25_avg, pm10_avg, so2_avg, no2_avg, co_avg, o3_avg, data_year)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            aqi_index = VALUES(aqi_index),
            quality_level = VALUES(quality_level),
            aqi_rank = VALUES(aqi_rank),
            pm25_avg = VALUES(pm25_avg),
            pm10_avg = VALUES(pm10_avg),
            so2_avg = VALUES(so2_avg),
            no2_avg = VALUES(no2_avg),
            co_avg = VALUES(co_avg),
            o3_avg = VALUES(o3_avg)
            """
            
            # 批量处理，每500条提交一次
            batch_size = 500
            batch_data = []
            
            for row in csv_reader:
                try:
                    # 解析CSV行数据
                    city = row[0]
                    province = row[1]
                    date = row[2]
                    aqi = None if row[3] == '' else float(row[3])
                    quality = row[4]
                    rank = None if row[5] == '' else float(row[5])
                    pm25 = None if row[6] == '' else float(row[6])
                    pm10 = None if row[7] == '' else float(row[7])
                    so2 = None if row[8] == '' else float(row[8])
                    no2 = None if row[9] == '' else float(row[9])
                    co = None if row[10] == '' else float(row[10])
                    o3 = None if row[11] == '' else float(row[11])
                    
                    # 准备数据
                    data = (
                        city, province, date, aqi, quality, rank,
                        pm25, pm10, so2, no2, co, o3, year
                    )
                    
                    batch_data.append(data)
                    records_count += 1
                    
                    # 达到批处理大小时执行批量插入
                    if len(batch_data) >= batch_size:
                        cursor.executemany(insert_query, batch_data)
                        conn.commit()
                        batch_data = []
                        
                except Exception as e:
                    errors_count += 1
                    print(f"处理行数据时出错: {e}, 行: {row}")
                    
            # 处理最后一批数据
            if batch_data:
                cursor.executemany(insert_query, batch_data)
                conn.commit()
            
            print(f"已成功导入文件 {file_name}，共 {records_count} 条记录")
            
        conn.close()
        return records_count, errors_count
        
    except Error as e:
        print(f"导入文件 {file_path} 时出错: {e}")
        return 0, 0

def main():
    """主函数"""
    start_time = datetime.datetime.now()
    print("开始导入数据")
    
    # 创建数据库（如果不存在）
    if not create_database_if_not_exists():
        print("创建数据库失败，程序终止")
        return
    
    # 创建必要的表
    if not create_tables():
        print("创建表失败，程序终止")
        return
    
    # 获取所有CSV文件
    csv_files = glob.glob(os.path.join(DATA_DIR, "air_quality_*.csv"))
    total_files = len(csv_files)
    print(f"发现 {total_files} 个CSV文件")
    
    # 导入所有文件
    total_records = 0
    total_errors = 0
    
    for i, file_path in enumerate(csv_files, 1):
        print(f"正在导入文件 [{i}/{total_files}]: {os.path.basename(file_path)}")
        records, errors = import_csv_file(file_path)
        total_records += records
        total_errors += errors
    
    # 计算总耗时
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("数据导入完成")
    print(f"总计导入 {total_files} 个文件，{total_records} 条记录")
    print(f"错误记录数: {total_errors}")
    print(f"总耗时: {duration:.2f} 秒")

if __name__ == "__main__":
    main() 