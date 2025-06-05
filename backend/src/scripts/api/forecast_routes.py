import os
import json
import logging
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
import mysql.connector
from datetime import datetime, timedelta, date
import traceback
from dotenv import load_dotenv, find_dotenv

# 导入模型初始化模块
from backend.src.scripts.model_train.models import generate_initial_data, initialize_all_models

# Determine the backend directory and load .env from there
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    # logging.info(f"Loaded .env file from: {dotenv_path}") # Optional: for debugging
else:
    # logging.warning(f".env file not found at: {dotenv_path}") # Optional: for debugging
    # Fallback or error handling if .env is critical and not found
    pass

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "forecast_api.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('forecast_routes')

# 全局变量，将由forecast_api.py设置
MODELS_DIR = 'data/models'
SCALERS_DIR = 'data/models/scalers'
CITY_MAP_PATH = 'data/models/info/city_map.json'

# 数据库配置 - Now loaded from .env
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'), # No default for password for security
    'database': os.getenv('DB_NAME', 'air_quality_monitoring'),
    'port': int(os.getenv('DB_PORT', 3306)) # Ensure port is an integer
}

# 创建Blueprint
forecast_bp = Blueprint('forecast', __name__)

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

# 从数据库获取最近的数据
def get_recent_data(city_id, indicator, days=30):
    """从数据库获取最近n天的数据"""
    conn = connect_to_db()
    if not conn:
        logger.error("数据库连接失败，无法获取历史数据")
        return None
    
    try:
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            logger.error(f"无法获取城市ID {city_id} 的城市名称")
            return None
        
        # 计算起始日期 - 增加查询范围以确保获取足够数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')  # 扩大查询范围
        
        cursor = conn.cursor()
        
        # 先从air_quality_newdata表获取最新数据
        new_data_query = f"""
        SELECT record_date, {INDICATOR_DB_MAPPING[indicator]} 
        FROM air_quality_newdata 
        WHERE city = %s AND record_date BETWEEN %s AND %s
        ORDER BY record_date ASC
        """
        try:
            cursor.execute(new_data_query, (city_name, start_date, end_date))
            new_data_rows = cursor.fetchall()
            logger.info(f"从air_quality_newdata表获取了{len(new_data_rows)}条记录")
        except Exception as e:
            logger.error(f"查询air_quality_newdata表出错: {str(e)}")
            new_data_rows = []
        
        # 再从air_quality_data表获取历史数据
        historical_query = f"""
        SELECT record_date, {INDICATOR_DB_MAPPING[indicator]} 
        FROM air_quality_data 
        WHERE city = %s AND record_date BETWEEN %s AND %s
        ORDER BY record_date ASC
        """
        try:
            cursor.execute(historical_query, (city_name, start_date, end_date))
            historical_rows = cursor.fetchall()
            logger.info(f"从air_quality_data表获取了{len(historical_rows)}条记录")
        except Exception as e:
            logger.error(f"查询air_quality_data表出错: {str(e)}")
            historical_rows = []
        
        # 合并结果
        rows = historical_rows + new_data_rows
        
        # 删除可能的重复数据（按日期）
        unique_dates = {}
        unique_rows = []
        for row in rows:
            if row[0] not in unique_dates:
                unique_dates[row[0]] = True
                unique_rows.append(row)
        
        cursor.close()
        conn.close()
        
        if not unique_rows:
            logger.warning(f"未找到城市 {city_name} 的 {indicator} 数据")
            return None
        
        # 按日期排序
        unique_rows.sort(key=lambda x: 
            x[0] if isinstance(x[0], datetime) 
            else datetime.combine(x[0], datetime.min.time()) if isinstance(x[0], date) 
            else datetime.strptime(x[0], '%Y-%m-%d'))
        
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
def generate_initial_data(city_id, indicator):
    """
    为指定城市和指标生成并保存初始序列数据
    
    Args:
        city_id: 城市ID
        indicator: 指标名称
    
    Returns:
        是否成功生成初始数据
    """
    try:
        # 从数据库获取最近30天的数据
        df = get_recent_data(city_id, indicator, days=30)
        if df is None or len(df) < 30:
            logger.error(f"无法获取足够的历史数据来生成初始序列，城市ID={city_id}，指标={indicator}")
            return False
        
        # 提取最近30天的数据
        last_30_values = df[indicator].values[-30:]
        
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

# 使用LSTM模型进行预测
def predict_with_model(city_id, indicator, prediction_length=7):
    """
    使用LSTM模型预测未来air指标
    
    Args:
        city_id: 城市ID
        indicator: 要预测的指标
        prediction_length: 预测天数
        
    Returns:
        预测结果的列表或None（发生错误时）
    """
    try:
        # 获取城市名称
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            logger.error(f"无法获取城市ID {city_id} 的城市名称")
            return None
            
        # 检查模型文件是否存在
        model_path = os.path.join(MODELS_DIR, f"{city_id}_{indicator}")
        scaler_path = os.path.join(SCALERS_DIR, f"{city_id}_{indicator}.npy")
        initial_data_path = os.path.join(MODELS_DIR, f"initial_data/{city_id}_{indicator}_initial.npy")
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            logger.error(f"模型或归一化器文件不存在: {model_path} 或 {scaler_path}")
            return None
            
        # 加载模型和归一化器
        model = load_model(model_path)
        scaler = np.load(scaler_path, allow_pickle=True).item()
        
        # 加载初始序列数据
        if os.path.exists(initial_data_path):
            # 使用预先保存的初始数据序列
            initial_sequence = np.load(initial_data_path, allow_pickle=True)
            logger.info(f"使用预定义的初始序列数据: {initial_data_path}")
        else:
            # 如果没有找到初始序列数据，尝试重新生成
            logger.warning(f"找不到初始序列数据: {initial_data_path}，正在尝试重新生成")
            if generate_initial_data(city_id, indicator):
                initial_sequence = np.load(initial_data_path, allow_pickle=True)
                logger.info(f"成功重新生成初始序列数据: {initial_data_path}")
            else:
                logger.error(f"无法生成初始序列数据: {initial_data_path}")
                return None
            
        # 确保初始序列是正确的形状
        if initial_sequence.shape[0] != 30:  # 假设模型需要30天的初始数据
            logger.error(f"初始序列数据形状不正确: {initial_sequence.shape}")
            return None
            
        # 预处理数据
        initial_sequence_scaled = scaler.transform(initial_sequence.reshape(-1, 1))
        
        # 准备输入数据
        X = initial_sequence_scaled.reshape(1, 30, 1)
        
        # 进行预测
        predictions = []
        for i in range(prediction_length):
            # 预测下一天的值
            next_pred = model.predict(X, verbose=0)
            predictions.append(next_pred[0, 0])
            
            # 更新输入数据以预测后续天数
            X = np.append(X[:, 1:, :], next_pred.reshape(1, 1, 1), axis=1)
        
        # 反归一化
        predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        
        # 转换为列表并确保值非负，保留两位小数
        predictions = [round(max(0, float(val[0])), 2) for val in predictions]
        
        # 确保预测结果长度与请求的预测长度一致
        if len(predictions) < prediction_length:
            logger.warning(f"预测结果长度 ({len(predictions)}) 小于请求长度 ({prediction_length})，自动补充最后一个值")
            # 使用最后一个值填充缺失的预测
            while len(predictions) < prediction_length:
                if predictions:
                    predictions.append(predictions[-1])
                else:
                    predictions.append(0.0)
        
        logger.info(f"成功为城市 {city_name} 的 {indicator} 指标生成 {prediction_length} 天的预测")
        
        return predictions
    except Exception as e:
        logger.error(f"预测过程中发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return None

# API路由
@forecast_bp.route('/api/prediction', methods=['POST'])
def get_prediction():
    """
    获取预测数据API
    接收参数:
    - city_id: 城市ID
    - indicator: 指标类型(pm25, aqi等)
    - prediction_length: 预测长度(天数)
    - time_period: 时间周期类别(short, medium, long)
    返回:
    - 预测数据和对应的历史数据
    """
    try:
        data = request.get_json()
        
        city_id = data.get('city_id')
        indicator = data.get('indicator')
        prediction_length = int(data.get('prediction_length', 7))
        time_period = data.get('time_period', 'short')  # 新增时间周期参数
        
        # 验证必要参数
        if not city_id or not indicator:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: city_id 或 indicator'
            }), 400
            
        # 根据时间周期确定历史数据天数
        history_days = 0
        if time_period == 'short':
            history_days = 7  # 短期预测提供一周历史数据
        elif time_period == 'medium':
            history_days = 30  # 中期预测提供一个月历史数据
        elif time_period == 'long':
            history_days = 90  # 长期预测提供三个月历史数据
            
        # 获取预测数据
        forecast_result = get_forecast_data(city_id, indicator, prediction_length)
        
        # 获取历史数据
        history_data = []
        if history_days > 0:
            # 从数据库获取历史数据
            history_data = get_historical_data(city_id, indicator, history_days)
            
        # 合并结果
        result = {
            'city_id': city_id,
            'city_name': get_city_name_from_id(city_id),
            'indicator': indicator,
            'forecast_dates': forecast_result['dates'],
            'forecast_values': forecast_result['values'],
            'history_dates': [d['date'] for d in history_data],
            'history_values': [d['value'] for d in history_data],
            'success': True
        }
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"预测接口错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'服务器错误: {str(e)}'
        }), 500

def get_historical_data(city_id, indicator, days):
    """
    从数据库获取历史数据
    
    参数:
    - city_id: 城市ID
    - indicator: 指标类型 (前端传入，如 'aqi')
    - days: 获取的天数
    
    返回:
    - 历史数据列表
    """
    try:
        # 1. 根据city_id获取城市名称
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            logger.error(f"无法根据city_id {city_id} 找到城市名称")
            return []
            
        # 2. 根据前端指标名称获取数据库列名
        db_column_name = INDICATOR_DB_MAPPING.get(indicator.lower())
        if not db_column_name:
            logger.error(f"无法找到指标 {indicator} 对应的数据库列名")
            return []

        # 计算开始日期(今天往前推days天)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 格式化日期为字符串
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # 从数据库查询数据
        conn = connect_to_db()
        if not conn:
             logger.error("无法连接数据库获取历史数据")
             return []
             
        cursor = conn.cursor()
        
        # 同时查询新数据表和历史数据表
        # 先从air_quality_newdata表获取最新数据
        new_data_rows = []
        try:
            new_data_query = f"""
            SELECT record_date, {db_column_name} 
            FROM air_quality_newdata 
            WHERE city = %s AND record_date BETWEEN %s AND %s
            ORDER BY record_date ASC
            """
            cursor.execute(new_data_query, (city_name, start_date_str, end_date_str))
            new_data_rows = cursor.fetchall()
            logger.info(f"历史查询: 从air_quality_newdata表获取了{len(new_data_rows)}条记录")
        except Exception as e:
            logger.error(f"历史查询: 查询air_quality_newdata表出错: {str(e)}")
            new_data_rows = []
        
        # 再从air_quality_data表获取历史数据
        historical_rows = []
        try:
            historical_query = f"""
            SELECT record_date, {db_column_name} 
            FROM air_quality_data 
            WHERE city = %s AND record_date BETWEEN %s AND %s
            ORDER BY record_date ASC
            """
            cursor.execute(historical_query, (city_name, start_date_str, end_date_str))
            historical_rows = cursor.fetchall()
            logger.info(f"历史查询: 从air_quality_data表获取了{len(historical_rows)}条记录")
        except Exception as e:
            logger.error(f"历史查询: 查询air_quality_data表出错: {str(e)}")
            historical_rows = []
        
        # 合并结果
        combined_rows = historical_rows + new_data_rows
        
        # 删除可能的重复数据（按日期）
        unique_dates = {}
        unique_rows = []
        for row in combined_rows:
            date_key = row[0]
            if isinstance(date_key, datetime):
                date_key = date_key.strftime('%Y-%m-%d')
                
            if date_key not in unique_dates:
                unique_dates[date_key] = True
                unique_rows.append(row)
        
        # 结果集按日期排序
        unique_rows.sort(key=lambda x: 
            x[0] if isinstance(x[0], datetime) 
            else datetime.combine(x[0], datetime.min.time()) if isinstance(x[0], date) 
            else datetime.strptime(x[0], '%Y-%m-%d'))
        
        logger.info(f"历史查询: 合并后获取到 {len(unique_rows)} 条非重复记录")
        
        # 处理结果
        history_data = []
        for row in unique_rows:
            # 确保日期是datetime对象或可解析的字符串
            record_date_obj = None
            if isinstance(row[0], datetime):
                record_date_obj = row[0]
            elif isinstance(row[0], date):
                # 添加对datetime.date类型的处理
                record_date_obj = datetime.combine(row[0], datetime.min.time())
            elif isinstance(row[0], str):
                 try:
                     record_date_obj = datetime.strptime(row[0], '%Y-%m-%d')
                 except ValueError:
                     logger.warning(f"历史查询: 无法解析日期字符串: {row[0]}")
                     continue # 跳过无法解析的日期
            else:
                 logger.warning(f"历史查询: 未知的日期格式: {type(row[0])}, 值: {row[0]}")
                 continue # 跳过未知格式
                 
            # 尝试将值转换为浮点数
            try:
                # 检查值是否为None或空字符串
                if row[1] is None or str(row[1]).strip() == '':
                    value_float = None
                else:
                    value_float = float(row[1])
            except (ValueError, TypeError) as conversion_error:
                logger.warning(f"历史查询: 无法将值 '{row[1]}' (类型: {type(row[1])}) 转换为浮点数: {conversion_error}")
                value_float = None # 设置为None如果转换失败

            history_data.append({
                'date': record_date_obj.strftime('%Y-%m-%d'),
                'value': value_float
            })
            
        cursor.close()
        conn.close()
        
        logger.info(f"历史查询: 最终处理后返回 {len(history_data)} 条历史数据")
        return history_data
    except Exception as e:
        logger.error(f"获取历史数据错误: {str(e)}")
        logger.error(traceback.format_exc())
        return []
        
def get_database_connection():
    """获取数据库连接"""
    return connect_to_db()

# 获取可用城市列表
@forecast_bp.route('/api/cities', methods=['GET'])
def get_cities():
    """获取可用城市列表"""
    try:
        city_map = load_city_map()
        if not city_map:
            return jsonify({
                'status': 'error',
                'message': '无法加载城市映射'
            }), 500
        
        # 提取城市列表
        cities = list(city_map.values())
        
        return jsonify({
            'status': 'success',
            'message': '获取城市列表成功',
            'data': cities
        })
    except Exception as e:
        logger.error(f"获取城市列表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取城市列表失败: {str(e)}'
        }), 500

# 获取可用指标列表
@forecast_bp.route('/api/indicators', methods=['GET'])
def get_indicators():
    """获取可用指标列表"""
    try:
        return jsonify({
            'status': 'success',
            'message': '获取指标列表成功',
            'data': INDICATORS
        })
    except Exception as e:
        logger.error(f"获取指标列表失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取指标列表失败: {str(e)}'
        }), 500

# 初始化函数，用于生成所有初始序列数据
def init_forecast_module():
    """初始化预测模块，确保所有必要的初始序列数据都已生成"""
    try:
        logger.info("开始初始化预测模块")
        
        # 调用models模块的初始化函数
        success = initialize_all_models()
        
        if success:
            logger.info("预测模块初始化成功，所有需要的初始序列数据都已生成")
        else:
            logger.error("预测模块初始化失败，部分初始序列数据可能缺失")
            
        return success
    except Exception as e:
        logger.error(f"初始化预测模块时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# 初始化模块
init_forecast_module()

def get_forecast_data(city_id, indicator, prediction_length):
    """
    获取预测数据
    
    参数:
    - city_id: 城市ID
    - indicator: 指标类型
    - prediction_length: 预测天数
    
    返回:
    - 包含日期和预测值的字典
    """
    try:
        logger.info(f"获取预测数据: 城市ID={city_id}, 指标={indicator}, 预测天数={prediction_length}")
        
        # 生成日期列表（从明天开始）
        dates = [(datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(prediction_length)]
        
        # 调用预测模型
        predictions = predict_with_model(city_id, indicator, prediction_length)
        
        if predictions is None:
            logger.warning(f"预测失败，返回默认值数组")
            predictions = [0.0] * prediction_length
        
        # 确保预测结果长度与日期长度一致
        if len(predictions) < prediction_length:
            # 使用最后一个值填充缺失的预测
            last_value = predictions[-1] if predictions else 0.0
            predictions.extend([last_value] * (prediction_length - len(predictions)))
        
        return {
            'dates': dates,
            'values': predictions
        }
    except Exception as e:
        logger.error(f"获取预测数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        # 返回空数据
        dates = [(datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(prediction_length)]
        return {
            'dates': dates,
            'values': [0.0] * prediction_length
        }

# 批量预测路由 - 同时预测多个指标
@forecast_bp.route('/api/batch_prediction', methods=['POST'])
def batch_prediction():
    """
    批量获取多个指标的预测数据API
    
    接收参数:
    - city_id: 城市ID
    - indicators: 指标类型列表(aqi, pm25等)
    - prediction_length: 预测长度(天数)
    - time_period: 时间周期类别(short, medium, long)
    
    返回:
    - 包含所有指标预测数据的合并结果
    """
    try:
        data = request.get_json()
        
        # 获取参数
        city_id = data.get('city_id')
        indicators = data.get('indicators', [])
        prediction_length = int(data.get('prediction_length', 7))
        time_period = data.get('time_period', 'short')
        
        # 验证必要参数
        if not city_id:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数: city_id'
            }), 400
            
        if not indicators or not isinstance(indicators, list):
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数: indicators 必须是指标列表'
            }), 400
        
        # 统一指标格式为大写
        indicators = [ind.upper() for ind in indicators]
        
        # 获取城市名称
        city_name = get_city_name_from_id(city_id)
        if not city_name:
            return jsonify({
                'status': 'error',
                'message': f'无法找到城市ID: {city_id}'
            }), 404
            
        # 根据时间周期确定历史数据天数
        history_days = 0
        if time_period == 'short':
            history_days = 7  # 短期预测提供一周历史数据
        elif time_period == 'medium':
            history_days = 30  # 中期预测提供一个月历史数据
        elif time_period == 'long':
            history_days = 90  # 长期预测提供三个月历史数据
        
        # 结果对象
        result = {
            'status': 'success',
            'message': '批量预测成功',
            'data': {
                'city_id': city_id,
                'city_name': city_name,
                'indicators': {}
            }
        }
        
        # 追踪成功和失败的指标数量
        success_count = 0
        failed_count = 0
        
        # 处理每个指标
        for indicator in indicators:
            try:
                # 获取预测数据
                forecast_result = get_forecast_data(city_id, indicator, prediction_length)
                
                # 获取历史数据
                history_data = []
                if history_days > 0:
                    history_data = get_historical_data(city_id, indicator, history_days)
                
                # 构建指标数据
                indicator_data = {
                    'forecast': [],
                    'historical': []
                }
                
                # 格式化预测数据
                for i, date in enumerate(forecast_result['dates']):
                    indicator_data['forecast'].append({
                        'date': date,
                        'value': forecast_result['values'][i] if i < len(forecast_result['values']) else None
                    })
                
                # 格式化历史数据
                for item in history_data:
                    indicator_data['historical'].append({
                        'date': item['date'],
                        'value': item['value']
                    })
                
                # 添加到结果中
                result['data']['indicators'][indicator] = indicator_data
                success_count += 1
                
            except Exception as e:
                logger.error(f"批量预测: 处理指标 {indicator} 时出错: {str(e)}")
                # 添加空数据结构以保持一致性
                result['data']['indicators'][indicator] = {
                    'forecast': [],
                    'historical': []
                }
                failed_count += 1
        
        # 更新状态信息
        if success_count == 0:
            result['status'] = 'error'
            result['message'] = '所有指标预测失败'
        elif failed_count > 0:
            result['status'] = 'partial'
            result['message'] = f'部分指标预测成功 ({success_count}/{len(indicators)})'
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"批量预测API错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500 