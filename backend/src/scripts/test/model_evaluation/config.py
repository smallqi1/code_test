#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
模型评估配置文件
配置评估所需的路径、数据库连接等参数
"""

import os
from datetime import datetime

# 项目根目录
PROJECT_ROOT = "D:\\CODE"

# 模型和数据目录
MODELS_DIR = os.path.join(PROJECT_ROOT, 'data', 'models')
SCALERS_DIR = os.path.join(MODELS_DIR, 'scalers')
CITY_MAP_PATH = os.path.join(MODELS_DIR, 'info', 'city_map.json')
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'new_data', 'processed_newdata')

# 评估结果输出目录
EVALUATION_DIR = os.path.join(PROJECT_ROOT, 'model_evaluation')
RESULTS_DIR = os.path.join(EVALUATION_DIR, 'results')
CHARTS_DIR = os.path.join(EVALUATION_DIR, 'charts')
LOGS_DIR = os.path.join(EVALUATION_DIR, 'logs')

# 确保目录存在
for dir_path in [RESULTS_DIR, CHARTS_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# 数据库配置
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '20040102a',
    'database': 'air_quality_monitoring',
    'port': 3306
}

# 模型参数
LOOK_BACK = 30  # 时间窗口大小

# 评估时间范围 (从4月3日到5月13日)
TEST_START_DATE = datetime(2025, 4, 3)
TEST_END_DATE = datetime(2025, 5, 13)

# 指标到数据库列名的映射
INDICATOR_DB_MAPPING = {
    'pm25': 'pm25_avg',
    'pm10': 'pm10_avg',
    'o3': 'o3_avg',
    'no2': 'no2_avg',
    'so2': 'so2_avg',
    'co': 'co_avg',
    'aqi': 'aqi_index'
}

# 所有城市ID列表 (评估时将自动从城市映射文件中加载)
CITY_IDS = []  # 初始为空，运行时会自动填充

# 所有要评估的指标列表
INDICATORS = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co', 'aqi'] 