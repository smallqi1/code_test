#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
实时数据API服务
提供实时空气质量数据查询接口，通过和风天气API获取数据
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import logging
import os
import concurrent.futures
import warnings
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 禁用Flask开发服务器警告
os.environ['WERKZEUG_SILENCE_STARTUP'] = '1'
# 完全禁用werkzeug日志输出
logging.getLogger('werkzeug').disabled = True
# 禁用警告
warnings.filterwarnings('ignore')

# 保存原始stdout
original_stdout = sys.stdout

# 创建应用实例
app = Flask(__name__)
# 使用 CORS 扩展，配置允许的源和凭证
CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True, "allow_headers": "*"}})

# 添加响应头以允许CORS请求
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization, Cache-Control, pragma'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '86400'  # 24小时
    return response

# 和风天气API密钥
QWEATHER_API_KEY = os.environ.get('QWEATHER_API_KEY')
if not QWEATHER_API_KEY:
    raise ValueError("QWEATHER_API_KEY environment variable is required but not set")

# 广东省的城市列表（包含所有21个地级市）
GUANGDONG_CITIES = [
    {
        'name': '广州市',
        'code': 'GZ',
        'latitude': 23.129110,
        'longitude': 113.264385
    },
    {
        'name': '深圳市',
        'code': 'SZ',
        'latitude': 22.543096,
        'longitude': 114.057868
    },
    {
        'name': '珠海市',
        'code': 'ZH',
        'latitude': 22.270978,
        'longitude': 113.576677
    },
    {
        'name': '汕头市',
        'code': 'ST',
        'latitude': 23.354091,
        'longitude': 116.681972
    },
    {
        'name': '佛山市',
        'code': 'FS',
        'latitude': 23.021478,
        'longitude': 113.121435
    },
    {
        'name': '韶关市',
        'code': 'SG',
        'latitude': 24.810403,
        'longitude': 113.594461
    },
    {
        'name': '湛江市',
        'code': 'ZJ',
        'latitude': 21.270708,
        'longitude': 110.359377
    },
    {
        'name': '肇庆市',
        'code': 'ZQ',
        'latitude': 23.047500,
        'longitude': 112.465091
    },
    {
        'name': '江门市',
        'code': 'JM',
        'latitude': 22.578738,
        'longitude': 113.081901
    },
    {
        'name': '茂名市',
        'code': 'MM',
        'latitude': 21.662999,
        'longitude': 110.925456
    },
    {
        'name': '惠州市',
        'code': 'HZ',
        'latitude': 23.111847,
        'longitude': 114.416196
    },
    {
        'name': '梅州市',
        'code': 'MZ',
        'latitude': 24.288615,
        'longitude': 116.122238
    },
    {
        'name': '汕尾市',
        'code': 'SW',
        'latitude': 22.774485,
        'longitude': 115.364238
    },
    {
        'name': '河源市',
        'code': 'HY',
        'latitude': 23.746266,
        'longitude': 114.700447
    },
    {
        'name': '阳江市',
        'code': 'YJ',
        'latitude': 21.857958,
        'longitude': 111.982232
    },
    {
        'name': '清远市',
        'code': 'QY',
        'latitude': 23.681764,
        'longitude': 113.056031
    },
    {
        'name': '东莞市',
        'code': 'DG',
        'latitude': 23.020673,
        'longitude': 113.751799
    },
    {
        'name': '中山市',
        'code': 'ZS',
        'latitude': 22.517646,
        'longitude': 113.392782
    },
    {
        'name': '潮州市',
        'code': 'CZ',
        'latitude': 23.661701,
        'longitude': 116.622603
    },
    {
        'name': '揭阳市',
        'code': 'JY',
        'latitude': 23.549993,
        'longitude': 116.372831
    },
    {
        'name': '云浮市',
        'code': 'YF',
        'latitude': 22.915094,
        'longitude': 112.044491
    }
]

# 设置日志
class ColoredFormatter(logging.Formatter):
    """为日志添加颜色"""
    COLORS = {
        'INFO': '\033[92m',  # 绿色
        'WARNING': '\033[93m',  # 黄色
        'ERROR': '\033[91m',  # 红色
        'CRITICAL': '\033[91m\033[1m',  # 红色加粗
        'DEBUG': '\033[94m',  # 蓝色
        'RESET': '\033[0m'  # 重置颜色
    }

    def format(self, record):
        log_message = super().format(record)
        if record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message

# 配置彩色日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 移除所有处理器
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 设置格式
formatter = ColoredFormatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def get_air_quality_category(aqi):
    """根据AQI值获取空气质量等级"""
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

def get_city_air_quality(city_info):
    """
    从和风天气API获取城市的空气质量数据
    
    参数:
        city_info (dict): 城市信息字典
        ++`
    返回:
        dict: 包含空气质量数据的字典
    """
    # 构建和风天气API请求URL
    url = f"https://devapi.qweather.com/v7/air/now?location={city_info['longitude']},{city_info['latitude']}&key={QWEATHER_API_KEY}&lang=zh"
    
    try:
        logger.info(f"正在从和风天气API获取{city_info['name']}的实时空气质量数据...")
        response = requests.get(url, timeout=10)
        data = response.json()
        
        # 获取当前日期
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if data.get('code') == '200':
            aqi_data = data['now']
            
            # 将API数据转换为前端期望的格式
            result = {
                'name': city_info['name'],
                'aqi': int(aqi_data['aqi']),
                'level': aqi_data['category'],
                'pm25': float(aqi_data['pm2p5']),
                'pm2_5': float(aqi_data['pm2p5']),
                'pm10': float(aqi_data['pm10']),
                'so2': float(aqi_data['so2']),
                'no2': float(aqi_data['no2']),
                'o3': float(aqi_data['o3']),
                'co': str(aqi_data['co']),
                'update_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'date': current_date
            }
            
            logger.info(f"{city_info['name']}数据获取成功")
            return result
        else:
            logger.error(f"数据获取失败：{data.get('code')} - {data.get('message', '未知错误')}")
            return None
            
    except Exception as e:
        logger.error(f"请求发生错误：{str(e)}")
        return None

@app.route('/api/realtime/<city_name>', methods=['GET'])
def get_city_data(city_name):
    """获取指定城市的实时数据"""
    try:
        # 当前日期
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 查找城市信息
        city_info = None
        for city in GUANGDONG_CITIES:
            if city['name'] == city_name or city['name'].replace('市', '') == city_name:
                city_info = city
                break
                
        if not city_info:
            logger.error(f"未找到城市: {city_name}")
            return jsonify({
                'status': 'error',
                'message': f'未找到{city_name}的信息',
                'name': city_name,
                'aqi': 0,
                'level': '无数据',
                'pm25': 0,
                'pm2_5': 0,
                'pm10': 0,
                'so2': 0,
                'no2': 0,
                'o3': 0,
                'co': '0',
                'update_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'date': current_date
            })
            
        # 从和风天气API获取数据
        result = get_city_air_quality(city_info)
        
        if result:
            # 确保result包含日期字段
            result['date'] = current_date
            return jsonify(result)
        else:
            # 未找到数据时返回错误信息
            return jsonify({
                'status': 'error',
                'message': f'未找到{city_name}的实时数据',
                'name': city_name,
                'aqi': 0,
                'level': '无数据',
                'pm25': 0,
                'pm2_5': 0,
                'pm10': 0,
                'so2': 0,
                'no2': 0,
                'o3': 0,
                'co': '0',
                'update_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'date': current_date
            })
    except Exception as e:
        logger.error(f"获取城市实时数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取实时数据失败: {str(e)}'
        }), 500

@app.route('/api/province', methods=['GET'])
def get_province_data():
    """获取全省空气质量数据"""
    try:
        # 当前日期
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 使用线程池并行获取所有城市的空气质量数据
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # 提交所有任务
            future_to_city = {executor.submit(get_city_air_quality, city): city for city in GUANGDONG_CITIES}
            
            # 获取结果
            for future in concurrent.futures.as_completed(future_to_city):
                result = future.result()
                if result:
                    # 确保每个结果都有日期字段
                    if 'date' not in result:
                        result['date'] = current_date
                    results.append(result)
        
        if results:
            return jsonify(results)
        else:
            # 未找到数据时返回错误信息
            return jsonify({
                'status': 'error',
                'message': '未能获取到任何城市的空气质量数据'
            }), 500
    except Exception as e:
        logger.error(f"获取省份数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取全省实时数据失败: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'time': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'service': '实时数据API服务'
    })

# 添加健康检查路由OPTIONS预检请求处理
@app.route('/api/health', methods=['OPTIONS'])
def handle_health_options():
    resp = app.make_default_options_response()
    headers = resp.headers
    headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization, Cache-Control, pragma'
    headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Credentials'] = 'true'
    return resp

def print_startup_message():
    """打印启动消息"""
    message = f"""
    ╭──────────────────────────────────────────────╮
    │           实时数据API服务已启动              │ 
    │                                              │
    │  API地址: http://localhost:5001              │
    │  健康检查: http://localhost:5001/api/health  │
    │                                              │
    ╰──────────────────────────────────────────────╯
    """
    print(message)

if __name__ == '__main__':
    logger.info("启动实时数据API服务，访问地址: http://localhost:5001")
    
    # 启动服务前打印启动消息
    print_startup_message()
    
    # 禁用Flask应用的启动输出
    import io
    sys.stdout = io.StringIO()
    
    try:
        # 启动Flask应用，不输出启动信息
        app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    finally:
        # 恢复标准输出
        sys.stdout = original_stdout 