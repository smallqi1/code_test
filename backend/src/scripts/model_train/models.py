import os
import json
import logging
import numpy as np
import pandas as pd
import mysql.connector
from datetime import datetime, timedelta
import traceback
from dotenv import load_dotenv

# Determine the backend directory and load .env from there
# models.py is in backend/src/scripts/model_train/models.py
# .env is in backend/.env
_current_file_path = os.path.abspath(__file__)
_model_train_dir = os.path.dirname(_current_file_path) # backend/src/scripts/model_train
_scripts_dir = os.path.dirname(_model_train_dir)       # backend/src/scripts
_src_dir = os.path.dirname(_scripts_dir)                # backend/src
backend_dir = os.path.dirname(_src_dir)                 # backend

dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    # logging.info(f"Loaded .env file from: {dotenv_path} in models.py") # Optional: for debugging
else:
    # logging.warning(f".env file not found at: {dotenv_path} in models.py") # Optional: for debugging
    pass

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "models.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('models')

# 全局变量 - Paths will now be relative to PROJECT_ROOT from .env or a default
PROJECT_ROOT_ENV = os.getenv('PROJECT_ROOT')
if PROJECT_ROOT_ENV:
    PROJECT_BASE_PATH = PROJECT_ROOT_ENV
else:
    # Fallback if PROJECT_ROOT is not in .env - assumes 'backend' is one level down from project root
    PROJECT_BASE_PATH = os.path.dirname(backend_dir) 
    # logging.warning(f"PROJECT_ROOT not found in .env, defaulting to {PROJECT_BASE_PATH} in models.py")

MODELS_DIR = os.path.join(PROJECT_BASE_PATH, 'data', 'models')
SCALERS_DIR = os.path.join(PROJECT_BASE_PATH, 'data', 'models', 'scalers')
CITY_MAP_PATH = os.path.join(PROJECT_BASE_PATH, 'data', 'models', 'info', 'city_map.json')

# 数据库配置 - Now loaded from .env
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'), # No default for password
    'database': os.getenv('DB_NAME', 'air_quality_monitoring'),
    'port': int(os.getenv('DB_PORT', 3306))
}

# 定义空气质量指标
INDICATORS = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co', 'aqi']

# 定义指标名称到数据库列名的映射
INDICATOR_DB_MAPPING = {
    'pm25': 'pm25_avg',
    'pm10': 'pm10_avg',
    'o3': 'o3_avg',
    'no2': 'no2_avg',
    'so2': 'so2_avg',
    'co': 'co_avg',
    'aqi': 'aqi_index'
}

# 连接到数据库
def connect_to_db():
    """连接到MySQL数据库"""
    try:
        logger.info(f"尝试连接到数据库: host={DB_CONFIG['host']}, database={DB_CONFIG['database']}, port={DB_CONFIG['port']}")
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return None

# 加载城市映射
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

# 通过城市ID获取城市名称
def get_city_name_from_id(city_id):
    """根据城市ID获取城市名称"""
    try:
        city_map = load_city_map()
        if not city_map:
            logger.error("无法加载城市映射")
            return None
        
        city_name = city_map.get(city_id)
        if not city_name:
            logger.error(f"找不到城市ID的对应城市名称: {city_id}")
            return None
        
        return city_name
    except Exception as e:
        logger.error(f"获取城市名称时出错: {str(e)}")
        return None

# 获取数据库表信息
def get_db_tables():
    """获取数据库中的表信息"""
    try:
        conn = connect_to_db()
        if not conn:
            logger.error("数据库连接失败，无法获取表信息")
            return None
            
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        logger.info(f"成功获取数据库表信息，共{len(tables)}个表: {', '.join(tables)}")
        return tables
    except Exception as e:
        logger.error(f"获取数据库表信息出错: {str(e)}")
        if conn:
            conn.close()
        return None

# 从数据库获取最近的数据
def get_recent_data_from_db(city_name, indicator, days=30):
    """从数据库获取最近n天的数据"""
    conn = connect_to_db()
    if not conn:
        logger.error("数据库连接失败，无法获取历史数据")
        return None
    
    try:
        # 计算起始日期 - 增加查询范围以确保获取足够数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')  # 扩大查询范围
        
        cursor = conn.cursor()
        
        # 先获取数据库中的表
        tables = get_db_tables()
        if not tables:
            logger.error("无法获取数据库表信息")
            return None
            
        rows = []
        
        # 检查并查询air_quality_newdata表
        if 'air_quality_newdata' in tables:
            db_column = INDICATOR_DB_MAPPING.get(indicator, f"{indicator}_avg")
            new_data_query = f"""
            SELECT record_date, {db_column} 
            FROM air_quality_newdata 
            WHERE city = %s AND record_date BETWEEN %s AND %s
            ORDER BY record_date ASC
            """
            try:
                cursor.execute(new_data_query, (city_name, start_date, end_date))
                new_data_rows = cursor.fetchall()
                logger.info(f"从air_quality_newdata表获取了{len(new_data_rows)}条记录")
                rows.extend(new_data_rows)
            except Exception as e:
                logger.error(f"查询air_quality_newdata表出错: {str(e)}")
        
        # 检查并查询air_quality_data表
        if 'air_quality_data' in tables:
            db_column = INDICATOR_DB_MAPPING.get(indicator, f"{indicator}_avg")
            historical_query = f"""
            SELECT record_date, {db_column} 
            FROM air_quality_data 
            WHERE city = %s AND record_date BETWEEN %s AND %s
            ORDER BY record_date ASC
            """
            try:
                cursor.execute(historical_query, (city_name, start_date, end_date))
                historical_rows = cursor.fetchall()
                logger.info(f"从air_quality_data表获取了{len(historical_rows)}条记录")
                rows.extend(historical_rows)
            except Exception as e:
                logger.error(f"查询air_quality_data表出错: {str(e)}")
                
        cursor.close()
        conn.close()
        
        if not rows:
            logger.warning(f"未找到城市 {city_name} 的 {indicator} 数据")
            return None
        
        # 删除可能的重复数据（按日期）
        unique_dates = {}
        unique_rows = []
        for row in rows:
            if row[0] not in unique_dates:
                unique_dates[row[0]] = True
                unique_rows.append(row)
        
        # 按日期排序
        unique_rows.sort(key=lambda x: x[0])
        
        # 构建数据帧
        df = pd.DataFrame(unique_rows, columns=['date', indicator])
        df[indicator] = df[indicator].astype(float)
        
        # 确保至少有30条记录，如果不够从最近的记录复制
        if len(df) < 30:
            logger.warning(f"只找到 {len(df)} 条记录，少于所需的30条。尝试通过复制最近的记录补充")
            while len(df) < 30 and len(df) > 0:
                # 复制最后一条记录
                last_record = df.iloc[-1:].copy()
                # 修改日期为下一天
                last_date = pd.to_datetime(last_record['date'].values[0])
                last_record['date'] = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
                # 添加到数据框
                df = pd.concat([df, last_record], ignore_index=True)
        
        logger.info(f"成功获取城市 {city_name} 的 {indicator} 历史数据，共 {len(df)} 条记录")
        return df
    except Exception as e:
        logger.error(f"获取历史数据时出错: {str(e)}")
        logger.error(traceback.format_exc())
        if conn:
            conn.close()
        return None

# 生成并保存初始序列数据
def generate_initial_data(city_id, indicator, force_mock=False):
    """
    为指定城市和指标生成并保存初始序列数据
    
    Args:
        city_id: 城市ID
        indicator: 指标名称
    
    Returns:
        是否成功生成初始数据
    """
    try:
        # 检查模型是否存在
        model_path = os.path.join(MODELS_DIR, f"{city_id}_{indicator}")
        if not os.path.exists(model_path):
            logger.error(f"模型不存在: {model_path}")
            return False
            
        # 获取城市名称
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            logger.error(f"无法获取城市ID {city_id} 的城市名称")
            return False
            
        # 从数据库获取真实数据
        df = get_recent_data_from_db(city_name, indicator, days=30)
        if df is None or len(df) < 30:
            logger.error(f"无法获取足够的历史数据用于预测，城市={city_name}，指标={indicator}")
            return False
            
        # 提取最近30天的数据
        last_30_values = df[indicator].values[-30:]
        logger.info(f"成功从数据库获取最近30天的数据用于初始序列")
                
        # 确保目录存在
        initial_data_dir = os.path.join(MODELS_DIR, "initial_data")
        os.makedirs(initial_data_dir, exist_ok=True)
        
        # 保存初始序列数据
        initial_data_path = os.path.join(initial_data_dir, f"{city_id}_{indicator}_initial.npy")
        np.save(initial_data_path, last_30_values)
        
        logger.info(f"成功生成并保存初始序列数据: {initial_data_path}")
        return True
    except Exception as e:
        logger.error(f"生成初始序列数据时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# 初始化所有模型的初始序列数据
def initialize_all_models():
    """为所有模型生成初始序列数据"""
    try:
        logger.info("开始初始化所有模型的初始序列数据")
        
        # 确保初始数据目录存在
        initial_data_dir = os.path.join(MODELS_DIR, "initial_data")
        os.makedirs(initial_data_dir, exist_ok=True)
        
        # 加载城市映射
        city_map = load_city_map()
        if not city_map:
            logger.error("无法加载城市映射")
            return False
            
        success_count = 0
        failure_count = 0
        
        # 检查是否有模型目录
        for city_id in city_map.keys():
            for indicator in INDICATORS:
                model_path = os.path.join(MODELS_DIR, f"{city_id}_{indicator}")
                if not os.path.exists(model_path):
                    logger.info(f"模型不存在，跳过: {model_path}")
                    continue
                    
                # 检查初始序列数据是否已存在
                initial_data_path = os.path.join(initial_data_dir, f"{city_id}_{indicator}_initial.npy")
                if os.path.exists(initial_data_path):
                    logger.info(f"初始序列数据已存在: {initial_data_path}")
                    success_count += 1
                    continue
                    
                # 生成初始序列数据
                logger.info(f"正在为城市ID={city_id}，指标={indicator}生成初始序列数据")
                if generate_initial_data(city_id, indicator):
                    success_count += 1
                else:
                    failure_count += 1
                    
        logger.info(f"模型初始化完成。成功: {success_count}, 失败: {failure_count}")
        return True
    except Exception as e:
        logger.error(f"初始化模型时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# 获取历史数据，用于初始化预测序列
def get_historical_data(city_name, indicator, days=30):
    """从数据库获取历史数据，用于初始化预测序列"""
    try:
        conn = connect_to_db()
        if not conn:
            return []
        
        cursor = conn.cursor()
        
        # 扩大查询范围以确保获取足够数据
        extended_days = days * 2 
        
        # 尝试从新数据表查询
        try:
            db_column = INDICATOR_DB_MAPPING.get(indicator, f"{indicator}_avg")
            query = """
            SELECT record_date, {0} FROM air_quality_newdata 
            WHERE city = %s AND record_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY record_date DESC
            """.format(db_column)
            
            cursor.execute(query, (city_name, extended_days))
            results_new = cursor.fetchall()
            if results_new:
                logger.info(f"从air_quality_newdata表获取到{len(results_new)}条{city_name}的{indicator}数据")
        except Exception as e:
            logger.error(f"查询air_quality_newdata表出错: {str(e)}")
            results_new = []
        
        # 尝试从历史数据表查询
        try:
            db_column = INDICATOR_DB_MAPPING.get(indicator, f"{indicator}_avg")
            query = """
            SELECT record_date, {0} FROM air_quality_data 
            WHERE city = %s AND record_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY record_date DESC
            """.format(db_column)
            
            cursor.execute(query, (city_name, extended_days))
            results_old = cursor.fetchall()
            if results_old:
                logger.info(f"从air_quality_data表获取到{len(results_old)}条{city_name}的{indicator}数据")
        except Exception as e:
            logger.error(f"查询air_quality_data表出错: {str(e)}")
            results_old = []
            
        # 合并结果并按日期排序
        all_results = results_new + results_old
        
        # 关闭连接
        cursor.close()
        conn.close()
        
        if not all_results:
            logger.warning(f"未找到城市 {city_name} 的 {indicator} 数据")
            return []
            
        # 去除重复的日期
        unique_dates = {}
        unique_results = []
        for result in all_results:
            if result[0] not in unique_dates:
                unique_dates[result[0]] = True
                unique_results.append(result)
        
        # 排序，确保日期有序
        unique_results.sort(key=lambda x: x[0], reverse=True)
            
        # 将结果转换为浮点数列表
        values = [float(result[1]) for result in unique_results if result[1] is not None]
        
        # 如果仍然不够30条记录，复制最后几条记录来补充
        if len(values) < days:
            logger.warning(f"只找到 {len(values)} 条记录，少于所需的 {days} 条。尝试通过复制最近的记录补充")
            if len(values) > 0:
                while len(values) < days:
                    # 复制最后一条记录
                    values.append(values[-1])
        
        # 只返回需要的天数
        return values[:days]
    except Exception as e:
        logger.error(f"获取历史数据时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return []

# 模块初始化
if __name__ == "__main__":
    initialize_all_models() 