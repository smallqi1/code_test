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
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("backend/logs/train_extended_model.log"),
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

# 设置项目根目录
if 'PROJECT_ROOT' in os.environ:
    PROJECT_ROOT = os.environ['PROJECT_ROOT']
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))

# 模型保存路径
MODEL_DIR = os.path.join(PROJECT_ROOT, 'data', 'models')
SCALER_DIR = os.path.join(PROJECT_ROOT, 'data', 'models', 'scalers')
INFO_DIR = os.path.join(PROJECT_ROOT, 'data', 'models', 'info')

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
        # 检查NVIDIA驱动是否正确安装
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            logging.info(f"NVIDIA-SMI输出:\n{result.stdout}")
            if result.returncode != 0:
                logging.error(f"NVIDIA-SMI错误: {result.stderr}")
        except Exception as e:
            logging.error(f"无法运行nvidia-smi: {str(e)}")
        
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
        
        query = "SELECT DISTINCT city_name FROM air_quality_data"
        cursor.execute(query)
        cities = [row[0] for row in cursor.fetchall()]
        
        logging.info(f"获取到 {len(cities)} 个城市")
        return cities
        
    except Exception as e:
        logging.error(f"获取城市列表失败: {str(e)}")
        return []
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def get_training_data(city_name):
    """获取训练数据，包括SO2、CO、NO2、AQI排名和空气质量等级"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 构建查询
        query = """
        SELECT date, aqi, pm25, pm10, so2, no2, co, aqi_rank, quality_level 
        FROM air_quality_data 
        WHERE city_name = %s 
        ORDER BY date
        """
        cursor.execute(query, (city_name,))
        rows = cursor.fetchall()
        
        if not rows:
            logging.error(f"未找到城市 {city_name} 的数据")
            return None
            
        # 创建DataFrame
        df = pd.DataFrame(rows, columns=['date', 'aqi', 'pm25', 'pm10', 'so2', 'no2', 'co', 'aqi_rank', 'quality_level'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # 确保数值型数据
        numeric_columns = ['aqi', 'pm25', 'pm10', 'so2', 'no2', 'co', 'aqi_rank']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 尝试将quality_level转换为数值
        # 首先检查是否为数值型
        try:
            df['quality_level'] = pd.to_numeric(df['quality_level'], errors='raise')
        except:
            # 如果是字符型，创建映射
            quality_mapping = {
                '优': 1,
                '良': 2,
                '轻度污染': 3,
                '中度污染': 4,
                '重度污染': 5,
                '严重污染': 6
            }
            # 尝试应用映射
            try:
                df['quality_level'] = df['quality_level'].map(quality_mapping).fillna(0).astype(int)
            except:
                logging.warning(f"无法将quality_level转换为数值，将使用原始值")
        
        # 填充缺失值
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        logging.info(f"城市 {city_name} 获取到 {len(df)} 条训练数据")
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
    """构建优化的LSTM模型"""
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

def train_model_for_column(city_name, df, column, look_back=30, batch_size=64, epochs=40):
    """训练单个指标的模型"""
    try:
        start_time = time.time()
        logging.info(f"开始训练城市 {city_name} 的 {column} 模型")
        
        # 数据归一化
        scaler = MinMaxScaler()
        values = scaler.fit_transform(df[column].values.reshape(-1, 1))
        
        # 创建训练集
        X, y = create_dataset(values, look_back)
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        # 根据数据量调整批次大小
        adjusted_batch_size = min(batch_size, len(X) // 10) if len(X) > 100 else 32
        
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
            epochs=epochs, 
            batch_size=adjusted_batch_size, 
            verbose=1,
            callbacks=[early_stopping, reduce_lr]
        )
        
        # 生成安全的文件名
        safe_name = get_safe_filename(city_name)
        
        # 保存模型和归一化器
        model_path = os.path.join(MODEL_DIR, f'{safe_name}_{column}')
        scaler_path = os.path.join(SCALER_DIR, f'{safe_name}_{column}.npy')
        
        model.save(model_path)
        np.save(scaler_path, scaler)
        
        elapsed_time = time.time() - start_time
        logging.info(f"完成 {city_name} 的 {column} 模型训练和保存，耗时: {elapsed_time:.2f}秒")
        
        return {
            'column': column,
            'model_path': model_path,
            'scaler_path': scaler_path,
            'training_time': elapsed_time
        }
        
    except Exception as e:
        logging.error(f"训练城市 {city_name} 的 {column} 模型时出错: {str(e)}")
        return None

def train_city_model(city_name):
    """训练单个城市的所有扩展指标模型"""
    try:
        df = get_training_data(city_name)
        if df is None or df.empty:
            logging.error(f"城市 {city_name} 没有足够的训练数据")
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
        
        # 要训练的指标列表
        columns = ['so2', 'no2', 'co', 'aqi_rank', 'quality_level']
        
        # 检查数据中是否存在这些列
        available_columns = [col for col in columns if col in df.columns]
        if len(available_columns) < len(columns):
            missing_columns = set(columns) - set(available_columns)
            logging.warning(f"城市 {city_name} 缺少以下列: {missing_columns}")
        
        if not available_columns:
            logging.error(f"城市 {city_name} 没有任何需要训练的列")
            return False
        
        # 使用线程池并行训练多个模型
        # 根据CPU核心数调整并行度
        max_workers = min(len(available_columns), max(1, os.cpu_count() - 1))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有训练任务
            future_to_column = {
                executor.submit(train_model_for_column, city_name, df, column): column
                for column in available_columns
            }
            
            # 收集结果
            for future in as_completed(future_to_column):
                column = future_to_column[future]
                try:
                    result = future.result()
                    if result:
                        model_info['models'][column] = {
                            'model_path': result['model_path'],
                            'scaler_path': result['scaler_path'],
                            'training_time': result['training_time']
                        }
                except Exception as e:
                    logging.error(f"处理城市 {city_name} 的 {column} 模型结果时出错: {str(e)}")
        
        # 保存模型信息
        info_path = os.path.join(INFO_DIR, f'{safe_name}_extended_info.json')
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
        logging.error(f"训练城市 {city_name} 的模型时出错: {str(e)}")
        return False

def train_all_models():
    """训练所有城市的扩展指标模型"""
    try:
        # 获取城市列表
        cities = get_all_cities()
        if not cities:
            logging.error("未获取到任何城市数据")
            return
        
        total_start_time = time.time()
        logging.info(f"开始训练扩展指标模型，共有 {len(cities)} 个城市需要处理")
        
        success_count = 0
        for i, city in enumerate(cities):
            try:
                city_start_time = time.time()
                logging.info(f"[{i+1}/{len(cities)}] 开始训练城市 {city} 的扩展指标模型")
                if train_city_model(city):
                    success_count += 1
                    city_elapsed_time = time.time() - city_start_time
                    logging.info(f"城市 {city} 的扩展指标模型训练成功，耗时: {city_elapsed_time:.2f}秒")
                else:
                    logging.error(f"城市 {city} 的扩展指标模型训练失败")
            except Exception as e:
                logging.error(f"处理城市 {city} 时发生错误: {str(e)}")
                continue
        
        total_elapsed_time = time.time() - total_start_time
        logging.info(f"扩展指标模型训练完成，成功训练 {success_count}/{len(cities)} 个城市的模型，总耗时: {total_elapsed_time:.2f}秒")
        
    except Exception as e:
        logging.error(f"训练过程中发生错误: {str(e)}")

if __name__ == "__main__":
    try:
        logging.info("开始扩展指标模型训练过程...")
        train_all_models()
        logging.info("扩展指标模型训练过程结束")
    except KeyboardInterrupt:
        logging.info("用户中断了训练过程")
    except Exception as e:
        logging.error(f"程序执行过程中发生错误: {str(e)}") 