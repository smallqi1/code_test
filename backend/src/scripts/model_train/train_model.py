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
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

#pm2.5,pm10,aqi
# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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

def get_safe_filename(city_name):
    """将中文城市名转换为安全的文件名"""
    # 使用MD5哈希生成唯一标识符
    city_hash = hashlib.md5(city_name.encode('utf-8')).hexdigest()[:8]
    # 移除不安全字符
    safe_name = re.sub(r'[^\w\-_\.]', '_', city_name)
    # 组合哈希和安全名称
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
            conn.close()

def get_training_data(city_name):
    """获取所有历史训练数据"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
        SELECT date, aqi, pm25, pm10 
        FROM air_quality_data 
        WHERE city_name = %s 
        ORDER BY date
        """
        cursor.execute(query, (city_name,))
        rows = cursor.fetchall()
        
        if not rows:
            logging.error(f"未找到城市 {city_name} 的数据")
            return None
            
        df = pd.DataFrame(rows, columns=['date', 'aqi', 'pm25', 'pm10'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        logging.info(f"城市 {city_name} 获取到 {len(df)} 条训练数据")
        return df
        
    except Exception as e:
        logging.error(f"获取数据失败: {str(e)}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def create_dataset(dataset, look_back=30):
    """创建训练数据集"""
    X, y = [], []
    for i in range(len(dataset) - look_back):
        X.append(dataset[i:(i + look_back)])
        y.append(dataset[i + look_back])
    return np.array(X), np.array(y)

def build_model(look_back):
    """构建LSTM模型"""
    model = Sequential([
        LSTM(50, input_shape=(look_back, 1), return_sequences=True),
        Dropout(0.2),
        LSTM(50),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def train_city_model(city_name):
    """训练单个城市的模型"""
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
        
        # 训练每个指标的模型
        for column in ['aqi', 'pm25', 'pm10']:
            try:
                logging.info(f"开始训练城市 {city_name} 的 {column} 模型")
                
                # 数据归一化
                scaler = MinMaxScaler()
                values = scaler.fit_transform(df[column].values.reshape(-1, 1))
                
                # 创建训练集
                X, y = create_dataset(values, look_back)
                X = X.reshape((X.shape[0], X.shape[1], 1))
                
                # 构建和训练模型
                model = build_model(look_back)
                model.fit(X, y, epochs=50, batch_size=32, verbose=1)
                
                # 保存模型和归一化器
                model_path = os.path.join(MODEL_DIR, f'{safe_name}_{column}')
                scaler_path = os.path.join(SCALER_DIR, f'{safe_name}_{column}.npy')
                
                # 保存模型和归一化器
                model.save(model_path)
                np.save(scaler_path, scaler)
                
                # 记录模型信息
                model_info['models'][column] = {
                    'model_path': model_path,
                    'scaler_path': scaler_path
                }
                
                logging.info(f"完成 {city_name} 的 {column} 模型训练和保存")
            except Exception as e:
                logging.error(f"训练城市 {city_name} 的 {column} 模型时出错: {str(e)}")
                continue
        
        # 保存模型信息
        info_path = os.path.join(INFO_DIR, f'{safe_name}_info.json')
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
            
        # 创建城市名称映射文件
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
    """训练所有城市的模型"""
    try:
        # 获取城市列表
        cities = get_all_cities()
        if not cities:
            logging.error("未获取到任何城市数据")
            return
        
        logging.info(f"开始训练，共有 {len(cities)} 个城市需要处理")
        
        # 确保目录存在
        os.makedirs(MODEL_DIR, exist_ok=True)
        os.makedirs(SCALER_DIR, exist_ok=True)
        os.makedirs(INFO_DIR, exist_ok=True)
        
        success_count = 0
        for i, city in enumerate(cities):
            try:
                logging.info(f"[{i+1}/{len(cities)}] 开始训练城市 {city} 的模型")
                if train_city_model(city):
                    success_count += 1
                    logging.info(f"城市 {city} 的模型训练成功")
                else:
                    logging.error(f"城市 {city} 的模型训练失败")
            except Exception as e:
                logging.error(f"处理城市 {city} 时发生错误: {str(e)}")
                continue
        
        logging.info(f"模型训练完成，成功训练 {success_count}/{len(cities)} 个城市的模型")
        
    except Exception as e:
        logging.error(f"训练过程中发生错误: {str(e)}")

if __name__ == "__main__":
    try:
        logging.info("开始模型训练过程...")
        train_all_models()
        logging.info("训练过程结束")
    except KeyboardInterrupt:
        logging.info("用户中断了训练过程")
    except Exception as e:
        logging.error(f"程序执行过程中发生错误: {str(e)}") 