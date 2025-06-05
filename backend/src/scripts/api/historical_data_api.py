#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
历史数据API
提供历史空气质量数据查询接口
"""

import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime, timedelta, date
import csv
import io
from flask import Flask, request, jsonify, Response, Blueprint
from flask_cors import CORS
import pandas as pd
import numpy as np
import subprocess
import os
import sys
import threading
import atexit
import signal
import logging
import traceback
from scipy import stats as scipy_stats
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 配置日志
api_logger = logging.getLogger('historical_api')
if not api_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    api_logger.addHandler(handler)
    api_logger.setLevel(logging.INFO)

# 创建Blueprint对象，供start_api.py导入使用
historical_bp = Blueprint('historical', __name__)

# 跟踪正在运行的后台进程
BACKGROUND_PROCESSES = []

# 定义一个清理函数，确保程序退出时终止所有子进程
def cleanup_processes():
    for process in BACKGROUND_PROCESSES:
        if process.poll() is None:  # 如果进程仍在运行
            try:
                process.terminate()  # 尝试终止进程
                process.wait(timeout=5)  # 等待进程终止，最多5秒
            except:
                try:
                    process.kill()  # 如果无法终止，则强制杀死
                except:
                    pass  # 如果仍然失败，则忽略

# 注册退出处理函数
atexit.register(cleanup_processes)

# 注册信号处理器
def signal_handler(sig, frame):
    cleanup_processes()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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

# 创建Flask应用实例
app = Flask(__name__)

# 配置Flask应用
app.config.update(
    ENV='production',      # 设置为生产环境
    PROPAGATE_EXCEPTIONS=True,  # 异常传播到日志系统
    JSON_SORT_KEYS=False,  # 不对JSON响应的键进行排序
    JSONIFY_PRETTYPRINT_REGULAR=False,  # 不美化JSON输出，减少网络传输
    SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 静态文件缓存时间1年(以秒为单位)
)

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

# 注册Blueprint到应用实例
app.register_blueprint(historical_bp)

# 简化处理，不再尝试直接访问Blueprint的url_map
# 改为直接在app上添加健康检查路由
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success',
        'message': '历史数据API服务运行正常'
    })

# 添加健康检查路由OPTIONS预检请求处理
@app.route('/health', methods=['OPTIONS'])
@app.route('/api/health', methods=['OPTIONS'])
def handle_health_options():
    resp = app.make_default_options_response()
    headers = resp.headers
    headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization, Cache-Control, pragma'
    headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Credentials'] = 'true'
    return resp

def connect_to_db():
    """连接到数据库"""
    try:
        api_logger.debug("正在连接数据库...")
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            api_logger.debug("数据库连接成功")
            return conn
        else:
            api_logger.error("数据库连接失败：未能建立连接")
            return None
    except Error as e:
        api_logger.error(f"数据库连接错误: {e}")
        # 更详细的错误信息
        if hasattr(e, 'errno'):
            api_logger.error(f"错误号: {e.errno}")
        if hasattr(e, 'sqlstate'):
            api_logger.error(f"SQL状态: {e.sqlstate}")
        if hasattr(e, 'msg'):
            api_logger.error(f"错误信息: {e.msg}")
        return None

class DateTimeEncoder(json.JSONEncoder):
    """处理JSON序列化datetime对象"""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

@historical_bp.route('/api/air-quality/latest-date', methods=['GET'])
def get_latest_date():
    """获取数据库中最新的数据日期"""
    try:
        conn = connect_to_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': '数据库连接失败',
                'data': None
            }), 500
        
        cursor = conn.cursor()
        
        # 从两个表中获取最新日期
        query = """
        SELECT MAX(record_date) as latest_date FROM (
            SELECT record_date FROM air_quality_data
            UNION ALL
            SELECT record_date FROM air_quality_newdata
        ) as combined_dates
        """
        
        cursor.execute(query)
        result = cursor.fetchone()
        latest_date = result[0] if result and result[0] else None
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': '查询成功',
            'data': {
                'latest_date': latest_date.isoformat() if latest_date else None
            }
        }), 200
        
    except Exception as e:
        api_logger.error(f"获取最新日期时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取最新日期时出错: {str(e)}',
            'data': None
        }), 500

@historical_bp.route('/api/air-quality/date-range', methods=['GET'])
def get_date_range():
    """获取数据可用的日期范围"""
    try:
        # 使用固定的日期范围，从2018年到当前
        start_date = '2018-01-01'
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        return jsonify({
            'status': 'success',
            'data': {
                'startDate': start_date,
                'endDate': end_date
            }
        })
    except Exception as e:
        api_logger.error(f"获取日期范围失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@historical_bp.route('/api/air-quality/historical', methods=['GET'])
@historical_bp.route('/air-quality/historical', methods=['GET'])
def get_historical_data():
    """获取历史空气质量数据"""
    try:
        # 记录请求参数，帮助调试
        api_logger.debug(f"历史数据请求参数: {dict(request.args)}")
        api_logger.debug(f"请求URL: {request.url}")
        api_logger.debug(f"原始请求: {request.query_string.decode('utf-8')}")
        
        city = request.args.get('city', '广州市')
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        data_type = request.args.get('data_type', 'all')
        quality_level = request.args.get('quality_level', 'all')
        
        api_logger.debug(f"处理后参数: city={city}, start_date={start_date}, end_date={end_date}, data_type={data_type}, quality_level={quality_level}")
        
        # 验证日期格式
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 验证日期不能在未来
            current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if start_date_obj > current_date or end_date_obj > current_date:
                return jsonify({
                    'status': 'error',
                    'message': '查询日期不能在未来，请选择当前日期或过去的日期'
                }), 400
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '日期格式错误，请使用YYYY-MM-DD格式'
            }), 400
        
        # 连接数据库
        conn = connect_to_db()
        if not conn:
            # 如果数据库连接失败，返回错误信息
            return jsonify({
                'status': 'error',
                'message': '数据库连接失败'
            }), 500
            
        cursor = conn.cursor(dictionary=True)
        
        try:
            results = []
            
            # 分别查询两个表，然后合并结果
            # 第一个表: air_quality_data
            query1 = """
            SELECT 
                city,
                DATE_FORMAT(record_date, '%Y-%m-%d') as date,
                aqi_index as aqi,
                quality_level,
                pm25_avg as pm25,
                pm10_avg as pm10,
                so2_avg as so2,
                no2_avg as no2,
                o3_avg as o3,
                co_avg as co
            FROM air_quality_data
            WHERE city = %s AND record_date BETWEEN %s AND %s
            """
            
            params1 = [city, start_date, end_date]
            
            # 添加空气质量等级筛选
            if quality_level != 'all':
                query1 += " AND quality_level = %s"
                params1.append(quality_level)
            
            api_logger.debug(f"执行SQL查询1: {query1}")
            api_logger.debug(f"查询参数1: {params1}")
            
            cursor.execute(query1, params1)
            results1 = cursor.fetchall()
            results.extend(results1)
            
            # 第二个表: air_quality_newdata
            query2 = """
            SELECT 
                city,
                DATE_FORMAT(record_date, '%Y-%m-%d') as date,
                aqi_index as aqi,
                quality_level,
                pm25_avg as pm25,
                pm10_avg as pm10,
                so2_avg as so2,
                no2_avg as no2,
                o3_avg as o3,
                co_avg as co
            FROM air_quality_newdata
            WHERE city = %s AND record_date BETWEEN %s AND %s
            """
            
            params2 = [city, start_date, end_date]
            
            # 添加空气质量等级筛选
            if quality_level != 'all':
                query2 += " AND quality_level = %s"
                params2.append(quality_level)
            
            api_logger.debug(f"执行SQL查询2: {query2}")
            api_logger.debug(f"查询参数2: {params2}")
            
            cursor.execute(query2, params2)
            results2 = cursor.fetchall()
            results.extend(results2)
            
            # 如果数据类型不是全部，过滤数据
            if data_type != 'all' and results:
                filtered_results = []
                for row in results:
                    if data_type in row and row[data_type] is not None:
                        filtered_results.append(row)
                results = filtered_results
            
            # 处理结果中的日期格式，确保可以被JSON序列化
            for row in results:
                for key, value in row.items():
                    if isinstance(value, (date, datetime)):
                        row[key] = value.isoformat()
            
            # 根据日期降序排序
            results.sort(key=lambda x: x['date'], reverse=True)
            
            api_logger.debug(f"查询结果行数: {len(results)}")
            
            return jsonify({
                'status': 'success',
                'data': results
            })
        except Exception as db_error:
            api_logger.error(f"SQL执行错误: {str(db_error)}")
            return jsonify({
                'status': 'error',
                'message': f'数据库查询错误: {str(db_error)}'
            }), 500
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        api_logger.error(f"获取历史数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'服务器处理错误: {str(e)}'
        }), 500

@app.route('/api/air-quality/export', methods=['GET'])
def export_data():
    """导出历史空气质量数据为CSV"""
    try:
        city = request.args.get('city', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        quality_level = request.args.get('quality_level', 'all')
        
        # 参数验证
        if not city or not start_date or not end_date:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数',
                'data': None
            }), 400
        
        conn = connect_to_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': '数据库连接失败',
                'data': None
            }), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # 构建查询条件 - 使用UNION ALL合并两个表的数据
        query = """
        (SELECT *, 'historical' as data_source FROM air_quality_data 
        WHERE city = %s AND record_date BETWEEN %s AND %s
        """
        
        params = [city, start_date, end_date]
        
        # 添加空气质量等级筛选
        if quality_level != 'all':
            query += " AND quality_level = %s"
            params.extend([quality_level])
        
        query += ")"
        
        # 添加新数据表查询
        query += """
        UNION ALL
        (SELECT *, 'new' as data_source FROM air_quality_newdata 
        WHERE city = %s AND record_date BETWEEN %s AND %s
        """
        
        params.extend([city, start_date, end_date])
        
        # 添加空气质量等级筛选
        if quality_level != 'all':
            query += " AND quality_level = %s"
            params.extend([quality_level])
        
        query += ")"
        
        # 排序
        query += " ORDER BY record_date DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # 创建CSV文件
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['日期', '城市', '省份', 'AQI指数', '空气质量等级', 'AQI排名', 
                         'PM2.5均值', 'PM10均值', 'SO2均值', 'NO2均值', 'CO均值', 'O3均值', '年份', '数据来源'])
        
        # 写入数据
        for row in results:
            writer.writerow([
                row['record_date'],
                row['city'],
                row['province'],
                row['aqi_index'],
                row['quality_level'],
                row['aqi_rank'],
                row['pm25_avg'],
                row['pm10_avg'],
                row['so2_avg'],
                row['no2_avg'],
                row['co_avg'],
                row['o3_avg'],
                row['data_year'],
                row['data_source']
            ])
        
        conn.close()
        
        # 设置响应
        output.seek(0)
        
        # 生成文件名
        filename = f"空气质量数据_{city}_{start_date}至{end_date}.csv"
        
        # 修正Content-Disposition头信息，确保文件名正确编码
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8",
                "Cache-Control": "no-cache"
            }
        )
        
        return response
        
    except Exception as e:
        api_logger.error(f"导出数据时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'导出数据时出错: {str(e)}',
            'data': None
        }), 500

@app.route('/api/air-quality/cities', methods=['GET'])
def get_cities():
    """获取可用的城市列表"""
    try:
        conn = connect_to_db()
        if not conn:
            return jsonify({
                'status': 'error',
                'message': '数据库连接失败'
            }), 500
            
        cursor = conn.cursor()
        
        # 从两个表中获取城市名称并去重
        query = """
        SELECT DISTINCT city FROM (
            SELECT city FROM air_quality_data
            UNION
            SELECT city FROM air_quality_newdata
        ) as cities
        ORDER BY city
        """
        
        cursor.execute(query)
        cities = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # 如果数据库中没有城市数据，使用默认列表
        if not cities:
            cities = [
                '广州市', '深圳市', '珠海市', '汕头市', '佛山市', '韶关市', 
                '湛江市', '肇庆市', '江门市', '茂名市', '惠州市', '梅州市', 
                '汕尾市', '河源市', '阳江市', '清远市', '东莞市', '中山市', 
                '潮州市', '揭阳市', '云浮市'
            ]
        
        return jsonify({
            'status': 'success',
            'data': cities
        })
    except Exception as e:
        api_logger.error(f"获取城市列表失败: {str(e)}")
        # 返回默认城市列表
        default_cities = [
            '广州市', '深圳市', '珠海市', '汕头市', '佛山市', '韶关市', 
            '湛江市', '肇庆市', '江门市', '茂名市', '惠州市', '梅州市', 
            '汕尾市', '河源市', '阳江市', '清远市', '东莞市', '中山市', 
            '潮州市', '揭阳市', '云浮市'
        ]
        return jsonify({
            'status': 'success',
            'data': default_cities
        })

@app.route('/api/air-quality/refresh-data', methods=['POST'])
def refresh_data():
    """触发运行数据处理脚本以获取最新数据"""
    try:
        api_logger.info("开始刷新数据，异步运行download_data_process.py脚本...")
        
        # 构建脚本路径 - 使用绝对路径而不是相对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(current_dir, '..', 'process', 'new_stage', 'download_data_process.py')
        script_path = os.path.abspath(script_path)  # 确保路径是绝对路径
        
        api_logger.info(f"数据处理脚本路径: {script_path}")
        
        # 确保路径存在
        if not os.path.exists(script_path):
            api_logger.error(f"脚本路径不存在: {script_path}")
            return jsonify({
                'status': 'error',
                'message': f'无法找到数据处理脚本: {script_path}'
            }), 404
            
        # 创建日志目录（如果不存在）
        log_dir = os.path.join(current_dir, '..', '..', '..', 'logs')
        log_dir = os.path.abspath(log_dir)
        os.makedirs(log_dir, exist_ok=True)
        
        # 准备日志文件
        log_file_path = os.path.join(log_dir, f"refresh_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # 获取项目根目录，用于设置PYTHONPATH环境变量
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
        
        # 设置环境变量，确保脚本能正确找到项目模块
        env = os.environ.copy()
        # 将项目根目录添加到PYTHONPATH
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{project_root}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = project_root
        
        api_logger.info(f"设置PYTHONPATH: {env['PYTHONPATH']}")
        
        # 使用Popen异步执行脚本，并传递正确的环境变量
        with open(log_file_path, 'w') as log_file:
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,  # 传递修改后的环境变量
                # 在Windows中使用CREATE_NEW_PROCESS_GROUP标志
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            # 将进程添加到跟踪列表
            BACKGROUND_PROCESSES.append(process)
            
            # 启动一个线程来等待进程完成并从跟踪列表中移除
            def wait_and_cleanup():
                process.wait()
                if process in BACKGROUND_PROCESSES:
                    BACKGROUND_PROCESSES.remove(process)
                api_logger.info(f"数据刷新进程已完成，退出代码: {process.returncode}")
                
                # 检查进程是否成功完成
                if process.returncode != 0:
                    api_logger.error(f"数据刷新进程未成功完成，退出代码: {process.returncode}")
                    # 读取日志文件最后几行查看错误
                    try:
                        with open(log_file_path, 'r') as f:
                            # 读取最后20行
                            lines = f.readlines()
                            if lines:
                                last_lines = lines[-20:]
                                error_log = ''.join(last_lines)
                                api_logger.error(f"错误日志内容: {error_log}")
                    except Exception as e:
                        api_logger.error(f"读取错误日志失败: {str(e)}")
                
            threading.Thread(target=wait_and_cleanup, daemon=True).start()
        
        # 立即向前端返回响应
        return jsonify({
            'status': 'success',
            'message': '数据刷新脚本已启动！系统将在后台处理数据，完成后将自动更新。',
            'log_file': os.path.basename(log_file_path)
        }), 202  # 使用202 Accepted状态码
            
    except Exception as e:
        api_logger.error(f"启动数据刷新脚本时出错: {str(e)}")
        import traceback
        api_logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'启动数据刷新脚本时出错: {str(e)}'
        }), 500

@app.route('/api/air-quality/trend-data', methods=['POST'])
@app.route('/air-quality/trend-data', methods=['POST'])
def get_trend_data():
    """获取趋势分析数据"""
    # 配置日志
    logger = logging.getLogger('trend_analysis')
    logger.setLevel(logging.INFO)
    
    # 如果没有处理器，添加一个
    if not logger.handlers:
        # 添加文件处理器
        file_handler = logging.FileHandler('logs/trend_analysis.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
    
    request_id = datetime.now().strftime('%Y%m%d%H%M%S')
    logger.info(f"[{request_id}] === 开始处理趋势分析数据请求 ===")
    
    # 设置CORS头
    response_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        return jsonify({
            'status': 'success',
            'message': 'CORS preflight request handled'
        }), 200, response_headers
    
    try:
        # 获取请求参数
        data = request.get_json()
        logger.info(f"[{request_id}] 接收到的请求参数: {data}")
        
        # 参数验证与提取
        if not data:
            logger.error(f"[{request_id}] 错误: 未接收到有效的请求数据")
            return jsonify({
                'status': 'error',
                'message': '请求数据无效'
            }), 400, response_headers
        
        cities = data.get('cities', [])
        start_year = int(data.get('startYear', 2018))
        end_year = int(data.get('endYear', datetime.now().year))
        pollutant = data.get('pollutant', 'aqi')
        analysis_type = data.get('analysisType', 'annual')
        
        logger.info(f"[{request_id}] 解析后的参数: cities={cities}, start_year={start_year}, end_year={end_year}, pollutant={pollutant}, analysis_type={analysis_type}")
        
        # 参数校验
        if not cities:
            logger.error(f"[{request_id}] 错误: 未选择城市")
            return jsonify({
                'status': 'error',
                'message': '请选择至少一个城市'
            }), 400, response_headers
            
        # 污染物参数验证
        valid_pollutants = ['aqi', 'pm25', 'pm10', 'so2', 'no2', 'co', 'o3']
        if pollutant not in valid_pollutants:
            logger.error(f"[{request_id}] 错误: 无效的污染物类型 {pollutant}")
            return jsonify({
                'status': 'error',
                'message': f'无效的污染物类型。有效选项: {", ".join(valid_pollutants)}'
            }), 400, response_headers
        
        # 年份参数验证
        current_year = datetime.now().year
        if start_year < 2015 or start_year > current_year:
            logger.error(f"[{request_id}] 错误: 起始年份无效 {start_year}")
            return jsonify({
                'status': 'error',
                'message': f'起始年份必须在2015和{current_year}之间'
            }), 400, response_headers
        
        if end_year < start_year or end_year > current_year:
            logger.error(f"[{request_id}] 错误: 结束年份无效 {end_year}")
            return jsonify({
                'status': 'error',
                'message': f'结束年份必须在起始年份和{current_year}之间'
            }), 400, response_headers
            
        # 尝试连接到数据库
        logger.info(f"[{request_id}] 尝试连接数据库...")
        conn = connect_to_db()
        if not conn:
            logger.error(f"[{request_id}] 错误: 数据库连接失败")
            return jsonify({
                'status': 'error',
                'message': '数据库连接失败，请稍后再试'
            }), 500, response_headers
            
        cursor = conn.cursor(dictionary=True)
        
        # 字段映射
        field_map = {
            'aqi': 'aqi_index',
            'pm25': 'pm25_avg',
            'pm10': 'pm10_avg',
            'so2': 'so2_avg',
            'no2': 'no2_avg',
            'co': 'co_avg',
            'o3': 'o3_avg'
        }
        
        field_name = field_map.get(pollutant, 'aqi_index')
        logger.info(f"[{request_id}] 查询数据库字段: {field_name}")
        
        # 构建日期范围
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        logger.info(f"[{request_id}] 查询日期范围: {start_date} 至 {end_date}")
        
        # 准备数据容器
        all_data = []
        
        # 对每个城市查询数据
        for city in cities:
            logger.info(f"[{request_id}] 查询城市 {city} 的数据")
            
            # 构建SQL查询
            query = f"""
            SELECT 
                city, 
                DATE_FORMAT(record_date, '%Y-%m-%d') as date,
                YEAR(record_date) as year,
                MONTH(record_date) as month,
                DAY(record_date) as day,
                CASE 
                    WHEN MONTH(record_date) IN (3,4,5) THEN '春季'
                    WHEN MONTH(record_date) IN (6,7,8) THEN '夏季'
                    WHEN MONTH(record_date) IN (9,10,11) THEN '秋季'
                    ELSE '冬季'
                END as season,
                {field_name} as value
            FROM (
                SELECT * FROM air_quality_data
                WHERE city = %s AND record_date BETWEEN %s AND %s
                UNION ALL
                SELECT * FROM air_quality_newdata
                WHERE city = %s AND record_date BETWEEN %s AND %s
            ) as combined_data
            ORDER BY record_date
            """
            
            params = (city, start_date, end_date, city, start_date, end_date)
            logger.info(f"[{request_id}] 执行SQL查询: {query}")
            
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                logger.info(f"[{request_id}] 城市 {city} 查询结果: {len(rows)} 条记录")
            
                # 将城市数据添加到结果集
                for row in rows:
                    row['pollutant'] = pollutant  # 添加污染物类型标记
                    all_data.append(row)
            
            except Exception as db_error:
                logger.error(f"[{request_id}] 查询城市 {city} 数据时出错: {str(db_error)}")
                logger.error(f"[{request_id}] {traceback.format_exc()}")
                # 继续查询其他城市，不中断请求
        
        # 关闭数据库连接
        conn.close()
        logger.info(f"[{request_id}] 数据库查询完成，共获取 {len(all_data)} 条记录")
        
        # 如果没有查询到数据，返回空数据结构
        if not all_data:
            logger.warning(f"[{request_id}] 未查询到任何数据，返回空结构")
            return jsonify({
                'status': 'success',
                'message': '未查询到符合条件的数据',
                'data': create_empty_result_structure()
            }), 200, response_headers
        
        # 转换为DataFrame进行高效数据处理
        df = pd.DataFrame(all_data)
        
        # 数据质量检查
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        na_count = df['value'].isna().sum()
        if na_count > 0:
            logger.warning(f"[{request_id}] 发现 {na_count} 条无效数据，已进行过滤")
            df = df.dropna(subset=['value'])
        
        # 异常值处理（去除超过3个标准差的值）
        df_filtered = df.copy()
        for city in df['city'].unique():
            city_data = df[df['city'] == city]
            if len(city_data) > 10:  # 只有数据点足够多时才进行异常值检测
                mean = city_data['value'].mean()
                std = city_data['value'].std()
                upper_bound = mean + 3 * std
                lower_bound = mean - 3 * std
                outliers = df_filtered[(df_filtered['city'] == city) & 
                                     ((df_filtered['value'] > upper_bound) | 
                                      (df_filtered['value'] < lower_bound))]
                if len(outliers) > 0:
                    logger.info(f"[{request_id}] 城市 {city} 发现 {len(outliers)} 个异常值，范围: {lower_bound:.2f}-{upper_bound:.2f}")
                    # 标记异常值但不删除
                    df_filtered.loc[(df_filtered['city'] == city) & 
                                  ((df_filtered['value'] > upper_bound) | 
                                   (df_filtered['value'] < lower_bound)), 'is_outlier'] = True
                    
        # 确保is_outlier列存在
        if 'is_outlier' not in df_filtered.columns:
            df_filtered['is_outlier'] = False
                    
        # 开始数据处理
        logger.info(f"[{request_id}] 开始按分析类型 {analysis_type} 处理数据")
        
        # 调用处理函数
        try:
            result = process_trend_data_improved(df_filtered, cities, pollutant, analysis_type, request_id, logger)
            logger.info(f"[{request_id}] 数据处理成功完成")
            
            # 返回结果
            return jsonify({
            'status': 'success',
            'data': result
            }), 200, response_headers
            
        except Exception as proc_error:
            logger.error(f"[{request_id}] 数据处理过程中出错: {str(proc_error)}")
            logger.error(f"[{request_id}] {traceback.format_exc()}")
            return jsonify({
                'status': 'error',
                'message': f'数据处理失败: {str(proc_error)}',
                'data': create_empty_result_structure()
            }), 500, response_headers
            
    except Exception as e:
        logger.error(f"[{request_id}] 趋势分析请求处理失败: {str(e)}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'请求处理失败: {str(e)}',
            'data': create_empty_result_structure()
        }), 500, response_headers

def create_empty_result_structure():
    """创建空的结果数据结构"""
    return {
        'annualData': [],
        'seasonalData': [],
        'monthlyData': [],
        'comparisonData': [],
        'correlationMatrix': {},
        'forecastData': [],
        'complianceData': [],
        'basicStats': {},
        'improvementStats': {},
        'summary': {
            'findings': [],
            'suggestions': []
        }
    }

def process_trend_data_improved(df, cities, pollutant, analysis_type, request_id, logger):
    """处理趋势分析数据 - 改进版
    
    Args:
        df: 数据DataFrame
        cities: 城市列表
        pollutant: 污染物类型
        analysis_type: 分析类型
        request_id: 请求ID
        logger: 日志记录器
        
    Returns:
        处理后的数据结构
    """
    logger.info(f"[{request_id}] === 开始处理趋势数据 ===")
    
    # 初始化结果结构
    result = create_empty_result_structure()
    
    # 确保year是整数类型
    df['year'] = df['year'].astype(int)
    df['month'] = df['month'].astype(int)
    
    try:
        # 1. 处理年度数据
        logger.info(f"[{request_id}] 处理年度数据")
        annual_data = []
        
        for city in cities:
            city_df = df[df['city'] == city]
            if len(city_df) == 0:
                logger.warning(f"[{request_id}] 城市 {city} 没有数据")
                continue
                    
            # 按年份分组计算均值
            yearly_data = city_df.groupby('year')['value'].agg(['mean', 'min', 'max', 'std', 'count']).reset_index()
            
            for _, row in yearly_data.iterrows():
                year = int(row['year'])
                mean_value = float(row['mean'])
                min_value = float(row['min'])
                max_value = float(row['max'])
                std_value = float(row['std']) if not pd.isna(row['std']) else 0
                count = int(row['count'])
                
                annual_entry = {
                        'city': city,
                        'year': year,
                    'value': round(mean_value, 2),
                    'min': round(min_value, 2),
                    'max': round(max_value, 2),
                    'std': round(std_value, 2),
                    'count': count
                }
                
                annual_data.append(annual_entry)
        
        # 按城市和年份排序
        annual_data.sort(key=lambda x: (x['city'], x['year']))
        result['annualData'] = annual_data
        
        # 2. 处理季节数据
        logger.info(f"[{request_id}] 处理季节数据")
        seasonal_data = []
        
        for city in cities:
            city_df = df[df['city'] == city]
            if len(city_df) == 0:
                continue
                    
            # 按年份和季节分组
            season_data = city_df.groupby(['year', 'season'])['value'].agg(['mean', 'min', 'max', 'count']).reset_index()
            
            for _, row in season_data.iterrows():
                year = int(row['year'])
                season = row['season']
                mean_value = float(row['mean'])
                min_value = float(row['min'])
                max_value = float(row['max'])
                count = int(row['count'])
                
                seasonal_entry = {
                        'city': city,
                    'year': year,
                        'season': season,
                    'value': round(mean_value, 2),
                    'min': round(min_value, 2),
                    'max': round(max_value, 2),
                    'count': count
                }
                
                seasonal_data.append(seasonal_entry)
        
        # 按城市、年份和季节排序
        seasonal_data.sort(key=lambda x: (x['city'], x['year'], convert_season_to_sort_key(x['season'])))
        result['seasonalData'] = seasonal_data
            
        # 3. 处理月度数据
        logger.info(f"[{request_id}] 处理月度数据")
        monthly_data = []
        
        for city in cities:
            city_df = df[df['city'] == city]
            if len(city_df) == 0:
                continue
                    
            # 按年份和月份分组
            monthly_grouped = city_df.groupby(['year', 'month'])['value'].agg(['mean', 'min', 'max', 'count']).reset_index()
            
            for _, row in monthly_grouped.iterrows():
                year = int(row['year'])
                month = int(row['month'])
                mean_value = float(row['mean'])
                min_value = float(row['min'])
                max_value = float(row['max'])
                count = int(row['count'])
                
                monthly_entry = {
                        'city': city,
                    'year': year,
                        'month': month,
                    'value': round(mean_value, 2),
                    'min': round(min_value, 2),
                    'max': round(max_value, 2),
                    'count': count
                }
                
                monthly_data.append(monthly_entry)
        
        # 按城市、年份和月份排序
        monthly_data.sort(key=lambda x: (x['city'], x['year'], x['month']))
        result['monthlyData'] = monthly_data
        
        # 4. 城市比较数据
        logger.info(f"[{request_id}] 处理城市比较数据")
        comparison_data = []
        
        # 计算每个城市的总体统计
        for city in cities:
            city_df = df[df['city'] == city]
            if len(city_df) == 0:
                continue
                
            city_stats_data = {
                        'city': city,
                'mean': round(float(city_df['value'].mean()), 2),
                'min': round(float(city_df['value'].min()), 2),
                'max': round(float(city_df['value'].max()), 2),
                'median': round(float(city_df['value'].median()), 2),
                'std': round(float(city_df['value'].std()), 2) if len(city_df) > 1 else 0,
                'count': int(len(city_df)),
                'improvement': 0  # 初始值
            }
            
            # 计算改善率（第一年与最后一年的比较）
            years = sorted(city_df['year'].unique())
            if len(years) >= 2:
                first_year = years[0]
                last_year = years[-1]
                
                first_year_mean = city_df[city_df['year'] == first_year]['value'].mean()
                last_year_mean = city_df[city_df['year'] == last_year]['value'].mean()
                
                if first_year_mean > 0:  # 避免除以零
                    improvement = (first_year_mean - last_year_mean) / first_year_mean * 100
                    city_stats_data['improvement'] = round(float(improvement), 2)
                    city_stats_data['first_year'] = int(first_year)
                    city_stats_data['last_year'] = int(last_year)
                    city_stats_data['first_year_value'] = round(float(first_year_mean), 2)
                    city_stats_data['last_year_value'] = round(float(last_year_mean), 2)
            
            comparison_data.append(city_stats_data)
            
        # 按平均值排序
        comparison_data.sort(key=lambda x: x['mean'])
        result['comparisonData'] = comparison_data
        
        # 5. 相关性矩阵（不同城市之间的相关性）
        logger.info(f"[{request_id}] 处理相关性矩阵")
        if len(cities) > 1:
            try:
                # 创建透视表以便计算相关性
                pivot_df = pd.pivot_table(df, values='value', index=['date'], columns=['city'], aggfunc='mean')
                
                # 计算相关性矩阵
                corr_matrix = pivot_df.corr().round(3)
                
                # 转换为Python字典
                corr_dict = {}
                for city1 in corr_matrix.index:
                    corr_dict[city1] = {}
                    for city2 in corr_matrix.columns:
                        if pd.notna(corr_matrix.loc[city1, city2]):
                            corr_dict[city1][city2] = float(corr_matrix.loc[city1, city2])
                        else:
                            corr_dict[city1][city2] = 0.0
                
                result['correlationMatrix'] = corr_dict
            except Exception as e:
                logger.warning(f"[{request_id}] 计算相关性矩阵时出错: {str(e)}")
                result['correlationMatrix'] = {}
        
        # 6. 基础统计信息
        logger.info(f"[{request_id}] 处理基础统计信息")
        basic_stats = {}
        
        for city in cities:
            city_df = df[df['city'] == city]
            if len(city_df) == 0:
                continue
                
            # 计算基本统计量
            city_stat_info = {
                'count': int(len(city_df)),
                'mean': round(float(city_df['value'].mean()), 2),
                'median': round(float(city_df['value'].median()), 2),
                'std': round(float(city_df['value'].std()), 2) if len(city_df) > 1 else 0,
                'min': round(float(city_df['value'].min()), 2),
                'max': round(float(city_df['value'].max()), 2),
                'percentile_25': round(float(city_df['value'].quantile(0.25)), 2),
                'percentile_75': round(float(city_df['value'].quantile(0.75)), 2)
            }
            
            # 检测趋势
            years = sorted(city_df['year'].unique())
            yearly_means = []
            
            for year in years:
                year_mean = city_df[city_df['year'] == year]['value'].mean()
                yearly_means.append(float(year_mean))
            
            # 简单线性回归
            if len(yearly_means) > 1:
                try:
                    x = np.array(years)
                    y = np.array(yearly_means)
                    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)
                    
                    city_stat_info['trend'] = {
                        'slope': round(float(slope), 4),
                        'r_value': round(float(r_value), 4),
                        'p_value': round(float(p_value), 4),
                        'yearly_means': [round(float(mean), 2) for mean in yearly_means],
                        'years': [int(year) for year in years]
                    }
                    
                    # 趋势判断
                    if p_value < 0.05:  # 统计显著
                        if slope < 0:
                            city_stat_info['trend_direction'] = '显著下降'
                        elif slope > 0:
                            city_stat_info['trend_direction'] = '显著上升'
                        else:
                            city_stat_info['trend_direction'] = '无明显变化'
                    else:
                        city_stat_info['trend_direction'] = '无明显变化'
                except Exception as e:
                    logger.warning(f"[{request_id}] 计算城市 {city} 趋势时出错: {str(e)}")
                    city_stat_info['trend'] = {}
                    city_stat_info['trend_direction'] = '无法计算'
            
            basic_stats[city] = city_stat_info
        
        result['basicStats'] = basic_stats
        
        # 7. 改善统计
        logger.info(f"[{request_id}] 处理改善统计")
        improvement_stats = {}
        
        # 使用已经计算好的comparison_data
        for city_data in comparison_data:
            city = city_data['city']
            if 'improvement' in city_data:
                # 计算年份差
                years_diff = int(city_data.get('last_year', 0)) - int(city_data.get('first_year', 0))
                # 计算年均改善率
                yearly_rate = 0.0
                if years_diff > 0:  # 避免除以零
                    yearly_rate = float(city_data['improvement']) / years_diff
                
                improvement_stats[city] = {
                    'improvement_percentage': float(city_data['improvement']),
                    'first_year': int(city_data.get('first_year', 0)),
                    'last_year': int(city_data.get('last_year', 0)),
                    'first_year_value': float(city_data.get('first_year_value', 0)),
                    'last_year_value': float(city_data.get('last_year_value', 0)),
                    'yearly_rate': round(yearly_rate, 2)  # 添加年均改善率
                }
        
        result['improvementStats'] = improvement_stats
        
        # 8. 生成分析总结
        logger.info(f"[{request_id}] 生成分析总结")
        findings = []
        suggestions = []
        
        try:
            # 提取关键发现
            if len(comparison_data) > 0:
                # 找出改善最好的城市
                best_improvement_city = max(comparison_data, key=lambda x: x.get('improvement', 0))
                if best_improvement_city.get('improvement', 0) > 0:
                    findings.append(f"{best_improvement_city['city']}从{best_improvement_city.get('first_year', '初始年')}到{best_improvement_city.get('last_year', '最终年')}的改善最显著，{pollutant.upper()}指标下降了{abs(best_improvement_city['improvement']):.2f}%。")
                
                # 找出当前空气质量最好的城市
                if pollutant in ['aqi', 'pm25', 'pm10', 'so2', 'no2', 'co']:
                    best_city = min(comparison_data, key=lambda x: x['mean'])
                    findings.append(f"{best_city['city']}的平均{pollutant.upper()}水平最低，为{best_city['mean']}，表明空气质量相对较好。")
                elif pollutant == 'o3':
                    best_city = min(comparison_data, key=lambda x: x['mean'])
                    findings.append(f"{best_city['city']}的平均{pollutant.upper()}水平最低，为{best_city['mean']}，臭氧污染相对较轻。")
            
            # 检查季节性模式
            seasonal_patterns = {}
            for city in cities:
                city_seasonal = [item for item in seasonal_data if item['city'] == city]
                if city_seasonal:
                    seasons = ['春季', '夏季', '秋季', '冬季']
                    season_values = {}
                    
                    for season in seasons:
                        season_items = [item for item in city_seasonal if item['season'] == season]
                        if season_items:
                            avg_value = sum(item['value'] for item in season_items) / len(season_items)
                            season_values[season] = avg_value
                    
                    if season_values:
                        worst_season = max(season_values.items(), key=lambda x: x[1])
                        seasonal_patterns[city] = worst_season[0]
            
            if seasonal_patterns:
                common_worst_season = most_common(list(seasonal_patterns.values()))
                findings.append(f"多数城市在{common_worst_season}的{pollutant.upper()}水平最高，可能需要在这个季节加强管控措施。")
            
            # 生成建议
            if pollutant in ['aqi', 'pm25', 'pm10']:
                suggestions.append("强化源头排放控制，重点关注工业排放、机动车尾气和扬尘防治。")
                suggestions.append("增加城市绿化覆盖率，建设绿色屏障减少颗粒物扩散。")
            elif pollutant in ['so2', 'no2']:
                suggestions.append("严格控制燃煤电厂和工业锅炉的排放标准。")
                suggestions.append("推广使用清洁能源，减少化石燃料使用。")
            elif pollutant == 'co':
                suggestions.append("加强机动车尾气排放监管，推广新能源汽车使用。")
            elif pollutant == 'o3':
                suggestions.append("在夏季臭氧高发期，实施错峰生产，减少前体物(VOCs和NOx)排放。")
                suggestions.append("增加城市绿地和水体面积，降低城市热岛效应。")
            
            # 根据总体趋势提供建议
            overall_trend = 0
            trend_count = 0
            for city, stats_data in basic_stats.items():
                if 'trend' in stats_data and 'slope' in stats_data['trend']:
                    overall_trend += stats_data['trend']['slope']
                    trend_count += 1
            
            if trend_count > 0:
                overall_trend /= trend_count
                if overall_trend > 0:
                    suggestions.append("当前空气质量指标呈上升趋势，建议加强环境监管和污染治理措施。")
                elif overall_trend < 0:
                    suggestions.append("当前空气质量指标呈下降趋势，建议继续保持并完善现有的环境政策。")
        except Exception as e:
            logger.warning(f"[{request_id}] 生成分析总结时出错: {str(e)}")
            # 如果出错，添加一些默认建议
            findings = ["数据分析过程中出现问题，无法生成详细发现。"]
            suggestions = ["建议收集更多数据进行更详细的分析。"]
        
        result['summary'] = {
            'findings': findings,
            'suggestions': suggestions
        }
        
        logger.info(f"[{request_id}] 趋势数据处理完成")
        
        # 确保返回结果包含所有必要字段
        for key in create_empty_result_structure().keys():
            if key not in result:
                logger.warning(f"[{request_id}] 结果中缺少 {key} 字段，已添加默认空结构")
                result[key] = create_empty_result_structure()[key]
        
        # 把所有numpy类型转换为Python原生类型
        result = convert_numpy_types(result)
        
        return result
    except Exception as e:
        logger.error(f"[{request_id}] 处理趋势数据时出错: {str(e)}")
        logger.error(f"[{request_id}] {traceback.format_exc()}")
        return create_empty_result_structure()

def convert_numpy_types(obj):
    """递归转换所有numpy类型为Python原生类型"""
    import numpy as np
    
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj

def convert_season_to_sort_key(season):
    """将季节转换为排序键"""
    season_order = {
        '春季': 1,
        '夏季': 2,
        '秋季': 3,
        '冬季': 4
    }
    return season_order.get(season, 5)  # 默认值5确保未知季节排在后面

def most_common(lst):
    """返回列表中出现次数最多的元素"""
    if not lst:
        return None
    return max(set(lst), key=lst.count)

# 直接在主应用上添加关键路由
@app.route('/api/air-quality/date-range', methods=['GET'])
def app_get_date_range():
    """主应用版本的日期范围API"""
    return get_date_range()
    
@app.route('/api/air-quality/historical', methods=['GET'])
@app.route('/air-quality/historical', methods=['GET'])
def app_get_historical_data():
    """主应用版本的历史数据API"""
    return get_historical_data()
    
@app.route('/api/air-quality/latest-date', methods=['GET'])
def app_get_latest_date():
    """主应用版本的最新日期API"""
    return get_latest_date()

if __name__ == '__main__':
    # 设置环境变量以禁止显示警告
    import os
    os.environ['WERKZEUG_RUN_MAIN'] = 'true'
    os.environ['WERKZEUG_SILENCE_WARNINGS'] = 'true'
    
    # 添加自定义启动信息，替代Flask开发服务器的警告
    print("\n=== 启动历史数据API服务 [端口:5000] ===")
    print("提示: 此服务仅用于开发和测试环境")
    print("=================================\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 