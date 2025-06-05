import numpy as np
import pandas as pd
from keras.models import Sequential, save_model
from keras.layers import Dense, LSTM, Dropout
from sklearn.preprocessing import MinMaxScaler
import mysql.connector
import logging
import os
from datetime import datetime
import json
import re
import hashlib
import tensorflow as tf
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
# This file is in backend/src/scripts/model_train/
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 设置项目根目录
if 'PROJECT_ROOT' in os.environ:
    PROJECT_ROOT = os.environ['PROJECT_ROOT']
else:
    # 根据当前文件位置推断
    current_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backend/logs/train_o3_model.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

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

# 模型保存路径
MODEL_DIR = 'data/models'
SCALER_DIR = 'data/models/scalers'
INFO_DIR = 'data/models/info'

# 确保目录存在
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(SCALER_DIR, exist_ok=True)
os.makedirs(INFO_DIR, exist_ok=True)
os.makedirs("data/logs", exist_ok=True)

# 设置TensorFlow配置以提高性能
logging.info("检查GPU可用性...")
try:
    # 强制TensorFlow重新检测设备
    tf.config.experimental.reset_memory_stats('GPU:0')
    physical_devices = tf.config.list_physical_devices('GPU')
    logging.info(f"TensorFlow检测到的物理设备: {physical_devices}")
    
    if not physical_devices:
        # 尝试手动设置CUDA环境变量
        logging.info("尝试手动设置CUDA环境变量...")
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'
        # 重新检测
        physical_devices = tf.config.list_physical_devices('GPU')
        logging.info(f"重新检测GPU设备: {physical_devices}")
    
    if physical_devices:
        try:
            # 启用GPU内存增长，避免一次性分配所有内存
            for device in physical_devices:
                tf.config.experimental.set_memory_growth(device, True)
            logging.info(f"找到 {len(physical_devices)} 个GPU设备，已启用内存增长")
            
            # 配置TensorFlow以使用混合精度训练（仅在GPU模式下）
            tf.keras.mixed_precision.set_global_policy('mixed_float16')
            logging.info("已启用混合精度训练以提高性能")
            
            # 打印GPU详细信息
            gpu_info = tf.config.experimental.get_device_details(physical_devices[0])
            logging.info(f"GPU详细信息: {gpu_info}")
        except Exception as e:
            logging.warning(f"无法设置GPU内存增长: {str(e)}")
    else:
        logging.warning("未检测到GPU，将使用CPU进行训练")
        # CPU优化设置
        try:
            # 设置线程数，通常设置为CPU核心数
            tf.config.threading.set_inter_op_parallelism_threads(os.cpu_count())
            tf.config.threading.set_intra_op_parallelism_threads(os.cpu_count())
            logging.info(f"已设置CPU优化参数，使用 {os.cpu_count()} 个线程")
        except Exception as e:
            logging.warning(f"无法设置CPU优化参数: {str(e)}")
except Exception as e:
    logging.error(f"GPU检测过程中发生错误: {str(e)}")
    # 继续使用CPU
    logging.info("将使用CPU进行训练")

# 打印TensorFlow版本和设备信息
logging.info(f"TensorFlow版本: {tf.__version__}")
logging.info(f"可用设备: {tf.config.list_physical_devices()}")
logging.info(f"默认设备: {tf.config.list_logical_devices()}")

def get_safe_filename(city_name):
    """将中文城市名转换为安全的文件名"""
    # 使用MD5哈希生成唯一标识符
    city_hash = hashlib.md5(city_name.encode('utf-8')).hexdigest()[:8]
    return f"city_{city_hash}"

def get_all_cities():
    """获取所有城市列表"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT city FROM air_quality_data WHERE o3_avg IS NOT NULL"
        cursor.execute(query)
        cities = [row[0] for row in cursor.fetchall()]
        
        logging.info(f"获取到 {len(cities)} 个有O3数据的城市")
        return cities
        
    except Exception as e:
        logging.error(f"获取城市列表失败: {str(e)}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def get_training_data(city_name):
    """获取训练数据，主要是O3数据"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 构建查询，主要获取O3数据
        query = """
        SELECT record_date, o3_avg 
        FROM air_quality_data 
        WHERE city = %s AND o3_avg IS NOT NULL
        ORDER BY record_date
        """
        cursor.execute(query, (city_name,))
        rows = cursor.fetchall()
        
        if not rows:
            logging.error(f"未找到城市 {city_name} 的O3数据")
            return None
            
        # 创建DataFrame
        df = pd.DataFrame(rows, columns=['date', 'o3'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # 确保数值型数据
        df['o3'] = pd.to_numeric(df['o3'], errors='coerce')
        
        # 填充缺失值
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        logging.info(f"城市 {city_name} 获取到 {len(df)} 条O3训练数据")
        return df
        
    except Exception as e:
        logging.error(f"获取数据失败: {str(e)}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def create_dataset(dataset, look_back=30):
    """创建训练数据集，优化版本"""
    dataX, dataY = [], []
    for i in range(len(dataset) - look_back):
        dataX.append(dataset[i:(i + look_back)])
        dataY.append(dataset[i + look_back])
    return np.array(dataX), np.array(dataY)

def build_model(look_back):
    """构建优化的LSTM模型，特别针对O3数据"""
    # 根据是否有GPU选择不同的模型复杂度
    if tf.config.list_physical_devices('GPU'):
        # GPU版本 - 更复杂的模型
        model = Sequential([
            LSTM(64, input_shape=(look_back, 1), return_sequences=True, 
                 kernel_initializer='he_normal', recurrent_dropout=0.0),
            Dropout(0.2),
            LSTM(32, kernel_initializer='he_normal', recurrent_dropout=0.0),
            Dropout(0.2),
            Dense(1, kernel_initializer='he_normal')
        ])
    else:
        # CPU版本 - 更简单的模型以加快训练速度
        model = Sequential([
            LSTM(32, input_shape=(look_back, 1), return_sequences=True, 
                 kernel_initializer='he_normal', recurrent_dropout=0.0),
            Dropout(0.2),
            LSTM(16, kernel_initializer='he_normal', recurrent_dropout=0.0),
            Dropout(0.2),
            Dense(1, kernel_initializer='he_normal')
        ])
    
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def train_city_model(city_name):
    """训练单个城市的O3模型"""
    try:
        df = get_training_data(city_name)
        if df is None or df.empty:
            logging.error(f"城市 {city_name} 没有足够的O3训练数据")
            return False
            
        look_back = 30
        
        # 生成安全的文件名
        safe_name = get_safe_filename(city_name)
        
        # 创建模型信息字典
        model_info = {
            'city_name': city_name,
            'look_back': look_back,
            'training_date': datetime.now().strftime('%Y-%m-%d'),
            'data_points': len(df),
            'models': {}
        }
        
        # 开始训练O3模型
        start_time = time.time()
        logging.info(f"开始训练城市 {city_name} 的O3模型")
        
        # 数据归一化
        scaler = MinMaxScaler()
        values = scaler.fit_transform(df['o3'].values.reshape(-1, 1))
        
        # 创建训练集
        X, y = create_dataset(values, look_back)
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        # 根据数据量调整批次大小
        adjusted_batch_size = min(64, len(X) // 10) if len(X) > 100 else 32
        
        # 构建和训练模型
        model = build_model(look_back)
        
        # 使用早停法避免过拟合
        early_stopping = tf.keras.callbacks.EarlyStopping(
            monitor='loss', patience=3, restore_best_weights=True
        )
        
        # 减少验证频率以加快训练
        reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
            monitor='loss', factor=0.2, patience=2, min_lr=0.001
        )
        
        # 训练模型
        model.fit(
            X, y, 
            epochs=40, 
            batch_size=adjusted_batch_size, 
            verbose=1,
            callbacks=[early_stopping, reduce_lr]
        )
        
        # 保存模型和归一化器
        model_path = os.path.join(MODEL_DIR, f'{safe_name}_o3')
        scaler_path = os.path.join(SCALER_DIR, f'{safe_name}_o3.npy')
        
        model.save(model_path)
        np.save(scaler_path, scaler)
        
        elapsed_time = time.time() - start_time
        logging.info(f"完成 {city_name} 的O3模型训练和保存，耗时: {elapsed_time:.2f}秒")
        
        # 记录模型信息
        model_info['models']['o3'] = {
            'model_path': model_path,
            'scaler_path': scaler_path,
            'training_time': elapsed_time
        }
        
        # 保存模型信息
        info_path = os.path.join(INFO_DIR, f'{safe_name}_o3_info.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
            
        # 更新城市名称映射文件
        city_map_path = os.path.join(INFO_DIR, 'city_map.json')
        city_map = {}
        if os.path.exists(city_map_path):
            try:
                with open(city_map_path, 'r', encoding='utf-8') as f:
                    city_map = json.load(f)
            except:
                city_map = {}
        
        city_map[safe_name] = city_name
        with open(city_map_path, 'w', encoding='utf-8') as f:
            json.dump(city_map, f, ensure_ascii=False, indent=2)
        
        return True
        
    except Exception as e:
        logging.error(f"训练城市 {city_name} 的O3模型时出错: {str(e)}")
        return False

def train_all_models():
    """训练所有城市的O3模型"""
    try:
        # 获取城市列表
        cities = get_all_cities()
        if not cities:
            logging.error("未获取到任何有O3数据的城市")
            return
        
        total_start_time = time.time()
        logging.info(f"开始训练O3模型，共有 {len(cities)} 个城市需要处理")
        
        success_count = 0
        for i, city in enumerate(cities):
            try:
                city_start_time = time.time()
                logging.info(f"[{i+1}/{len(cities)}] 开始训练城市 {city} 的O3模型")
                if train_city_model(city):
                    success_count += 1
                    city_elapsed_time = time.time() - city_start_time
                    logging.info(f"城市 {city} 的O3模型训练成功，耗时: {city_elapsed_time:.2f}秒")
                else:
                    logging.error(f"城市 {city} 的O3模型训练失败")
            except Exception as e:
                logging.error(f"处理城市 {city} 时发生错误: {str(e)}")
                continue
        
        total_elapsed_time = time.time() - total_start_time
        logging.info(f"O3模型训练完成，成功训练 {success_count}/{len(cities)} 个城市的模型，总耗时: {total_elapsed_time:.2f}秒")
        
    except Exception as e:
        logging.error(f"训练过程中发生错误: {str(e)}")

if __name__ == "__main__":
    try:
        logging.info("开始O3模型训练过程...")
        train_all_models()
        logging.info("O3模型训练过程结束")
    except KeyboardInterrupt:
        logging.info("用户中断了训练过程")
    except Exception as e:
        logging.error(f"程序执行过程中发生错误: {str(e)}") 