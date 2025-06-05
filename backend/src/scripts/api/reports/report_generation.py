#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
广东省空气质量监测系统 - 报告生成模块
处理报告的生成、格式化和存储
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
from threading import Thread
from pathlib import Path
import pandas as pd
import mysql.connector
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Circle
import seaborn as sns
import io
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 获取项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = str(Path(__file__).resolve().parents[4])
sys.path.append(project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(project_root, 'src', 'scripts', 'api', 'logs', 'report_generation.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger('report_generation')

# 报告存储目录
REPORTS_DIR = os.path.join(project_root, 'data', 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# 报告子目录（按类型）
REPORTS_PDF_DIR = os.path.join(REPORTS_DIR, 'pdf')
REPORTS_EXCEL_DIR = os.path.join(REPORTS_DIR, 'excel')
REPORTS_WORD_DIR = os.path.join(REPORTS_DIR, 'word')
REPORTS_HTML_DIR = os.path.join(REPORTS_DIR, 'html')

# 创建所有报告目录
for dir_path in [REPORTS_DIR, REPORTS_PDF_DIR, REPORTS_EXCEL_DIR, REPORTS_WORD_DIR, REPORTS_HTML_DIR]:
    os.makedirs(dir_path, exist_ok=True)
    logger.info(f"确保报告目录存在: {dir_path}")

# 数据库配置 - 从环境变量加载
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME', 'air_quality_monitoring')
}

# Validate that password is loaded
if not DB_CONFIG['password']:
    raise ValueError("DB_PASSWORD environment variable is required but not set")

# 报告元数据存储路径
REPORT_METADATA_PATH = os.path.join(REPORTS_DIR, 'reports_metadata.json')

def save_report(report_id, report_info):
    """保存报告信息到元数据文件
    
    Args:
        report_id (str): 报告ID
        report_info (dict): 报告信息
    """
    try:
        # 加载现有的报告元数据
        metadata = load_reports_metadata()
        
        # 查找并更新或添加报告信息
        found = False
        for i, report in enumerate(metadata['reports']):
            if report.get('id') == report_id:
                metadata['reports'][i] = report_info
                found = True
                break
                
        if not found:
            metadata['reports'].append(report_info)
            
        # 保存更新后的元数据，确保设置正确的编码
        with open(REPORT_METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        logger.info(f"报告信息保存成功: {report_id}")
        return True
    except Exception as e:
        logger.error(f"保存报告信息失败: {str(e)}", exc_info=True)
        return False

def load_reports_metadata():
    """加载所有报告的元数据"""
    if os.path.exists(REPORT_METADATA_PATH):
        try:
            with open(REPORT_METADATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载报告元数据失败: {str(e)}")
    return {'reports': []}

def get_pollutant_data(region_id, start_date, end_date, pollutant):
    """获取指定区域和时间范围的污染物数据
    
    Args:
        region_id (str): 区域ID
        start_date (str): 开始日期，格式YYYY-MM-DD
        end_date (str): 结束日期，格式YYYY-MM-DD
        pollutant (str): 污染物类型，例如'AQI'
        
    Returns:
        list: 包含时间序列数据的列表
    """
    conn = None
    cursor = None
    try:
        # 连接数据库
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 准备查询条件
        where_clause = "record_date BETWEEN %s AND %s"
        params = [start_date, end_date]
        
        # 处理区域条件
        if region_id and region_id != 'all':
            # 尝试转换区域ID为城市名称
            region_map = {
                'guangzhou': '广州市',
                'shenzhen': '深圳市',
                'pearl_delta': ['广州市', '深圳市', '珠海市', '佛山市', '惠州市', '东莞市', '中山市', '江门市', '肇庆市'],
                'east': ['汕头市', '梅州市', '揭阳市', '潮州市', '汕尾市'],
                'west': ['湛江市', '茂名市', '阳江市'],
                'north': ['韶关市', '清远市', '河源市', '云浮市']
            }
            
            if region_id in region_map:
                if isinstance(region_map[region_id], list):
                    placeholders = ', '.join(['%s'] * len(region_map[region_id]))
                    where_clause += f" AND city IN ({placeholders})"
                    params.extend(region_map[region_id])
                else:
                    where_clause += " AND city = %s"
                    params.append(region_map[region_id])
        
        # 确定要查询的列
        column_map = {
            'AQI': 'aqi_index',
            'PM25': 'pm25_avg',
            'PM10': 'pm10_avg',
            'SO2': 'so2_avg',
            'NO2': 'no2_avg',
            'CO': 'co_avg',
            'O3': 'o3_avg'
        }
        
        column = column_map.get(pollutant.upper(), 'aqi_index')
        
        # 构建查询
        query = f"""
        SELECT record_date as date, {column} as value, city
        FROM air_quality_data
        WHERE {where_clause}
        ORDER BY record_date, city
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 转换为时间序列数据列表
        timeseries = []
        for row in rows:
            if row['value'] is not None:
                # 转换日期格式
                date_str = row['date'].strftime('%Y-%m-%d')
                timeseries.append({
                    'date': date_str,
                    'value': float(row['value']),
                    'city': row['city']
                })
        
        logger.info(f"获取到 {len(timeseries)} 条污染物数据")
        return timeseries
    
    except Exception as e:
        logger.error(f"获取污染物数据失败: {str(e)}", exc_info=True)
        return []
    finally:
        # 确保资源释放
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def calculate_summary_statistics(region_id, start_date, end_date, pollutant):
    """计算指定区域和时间范围内的污染物统计信息
    
    Args:
        region_id (str): 区域ID
        start_date (str): 开始日期，格式YYYY-MM-DD
        end_date (str): 结束日期，格式YYYY-MM-DD
        pollutant (str): 污染物类型，例如'AQI'
        
    Returns:
        dict: 包含统计信息的字典
    """
    try:
        # 获取时间序列数据
        timeseries = get_pollutant_data(region_id, start_date, end_date, pollutant)
        
        if not timeseries:
            logger.warning(f"无法获取数据进行统计: 区域={region_id}, 日期={start_date}至{end_date}, 污染物={pollutant}")
            return {
                'count': 0,
                'min': None,
                'max': None,
                'avg': None,
                'median': None
            }
            
        # 提取值进行计算
        values = [item['value'] for item in timeseries]
        
        # 计算统计信息
        min_val = min(values)
        max_val = max(values)
        avg_val = sum(values) / len(values)
        median_val = sorted(values)[len(values) // 2]  # 简单中位数计算
        
        # 返回统计信息
        return {
            'count': len(values),
            'min': min_val,
            'max': max_val,
            'avg': avg_val,
            'median': median_val
        }
        
    except Exception as e:
        logger.error(f"计算统计信息失败: {str(e)}", exc_info=True)
        return {
            'count': 0,
            'min': None,
            'max': None,
            'avg': None,
            'median': None,
            'error': str(e)
        }

def get_region_info(region_id):
    """获取区域信息
    
    Args:
        region_id (str): 区域ID
        
    Returns:
        dict: 包含区域信息的字典
    """
    # 区域名称映射
    region_names = {
        'all': '广东省',
        'guangzhou': '广州市',
        'shenzhen': '深圳市',
        'pearl_delta': '珠三角',
        'east': '粤东地区',
        'west': '粤西地区',
        'north': '粤北地区'
    }
    
    # 返回区域信息
    return {
        'id': region_id,
        'name': region_names.get(region_id, '广东省'),
        'type': 'province' if region_id == 'all' else 'city' if region_id in ['guangzhou', 'shenzhen'] else 'region'
    }

def generate_pdf_report(data, report_data, output_dir):
    """生成PDF格式的报告
    
    Args:
        data (dict): 报告数据
        report_data (dict): 报告设置
        output_dir (str): 输出目录
        
    Returns:
        str: 生成的报告文件路径
    """
    try:
        # 导入reports_api模块中的函数
        import importlib.util
        import sys
        
        # 构建reports_api模块的路径
        module_path = os.path.join(current_dir, 'reports_api.py')
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location('reports_api', module_path)
        reports_api = importlib.util.module_from_spec(spec)
        sys.modules['reports_api'] = reports_api
        spec.loader.exec_module(reports_api)
        
        # 获取generate_pdf_report函数
        api_generate_pdf = reports_api.generate_pdf_report
        
        # 生成文件路径
        report_filename = f"{os.path.basename(output_dir)}.pdf"
        output_path = os.path.join(output_dir, report_filename)
        
        # 转换data格式以适配api_generate_pdf函数
        api_data = convert_data_format(data)
        
        # 提取内容选项
        content_options = report_data.get('content_options', {})
        if not content_options:
            content_options = {
                'overview': True,
                'pollution': True,
                'trend': True,
                'warning': False,
                'policy': False
            }
            
        # 调用API中的PDF生成函数
        api_generate_pdf(
            api_data, 
            content_options, 
            output_path, 
            report_data.get('type', 'daily'),
            report_data.get('region_id', 'all'),
            report_data.get('start_date', ''),
            report_data.get('end_date', '')
        )
        
        logger.info(f"PDF报告生成成功: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"生成PDF报告失败: {str(e)}", exc_info=True)
        return None

def generate_word_report(data, report_data, output_dir):
    """生成Word格式的报告"""
    try:
        # 导入reports_api模块中的函数
        import importlib.util
        import sys
        
        # 构建reports_api模块的路径
        module_path = os.path.join(current_dir, 'reports_api.py')
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location('reports_api', module_path)
        reports_api = importlib.util.module_from_spec(spec)
        sys.modules['reports_api'] = reports_api
        spec.loader.exec_module(reports_api)
        
        # 获取generate_word_report函数
        api_generate_word = reports_api.generate_word_report
        
        # 生成文件路径
        report_filename = f"{os.path.basename(output_dir)}.docx"
        output_path = os.path.join(output_dir, report_filename)
        
        # 转换data格式以适配api_generate_word函数
        api_data = convert_data_format(data)
        
        # 提取内容选项
        content_options = report_data.get('content_options', {})
        if not content_options:
            content_options = {
                'overview': True,
                'pollution': True,
                'trend': True,
                'warning': False,
                'policy': False
            }
            
        # 调用API中的Word生成函数
        api_generate_word(
            api_data, 
            content_options, 
            output_path, 
            report_data.get('type', 'daily'),
            report_data.get('region_id', 'all'),
            report_data.get('start_date', ''),
            report_data.get('end_date', '')
        )
        
        logger.info(f"Word报告生成成功: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"生成Word报告失败: {str(e)}", exc_info=True)
        return None

def generate_excel_report(data, report_data, output_dir):
    """生成Excel格式的报告"""
    try:
        # 导入reports_api模块中的函数
        import importlib.util
        import sys
        
        # 构建reports_api模块的路径
        module_path = os.path.join(current_dir, 'reports_api.py')
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location('reports_api', module_path)
        reports_api = importlib.util.module_from_spec(spec)
        sys.modules['reports_api'] = reports_api
        spec.loader.exec_module(reports_api)
        
        # 获取generate_excel_report函数
        api_generate_excel = reports_api.generate_excel_report
        
        # 生成文件路径
        report_filename = f"{os.path.basename(output_dir)}.xlsx"
        output_path = os.path.join(output_dir, report_filename)
        
        # 转换data格式以适配api_generate_excel函数
        api_data = convert_data_format(data)
        
        # 提取内容选项
        content_options = report_data.get('content_options', {})
        if not content_options:
            content_options = {
                'overview': True,
                'pollution': True,
                'trend': True,
                'warning': False,
                'policy': False
            }
            
        # 调用API中的Excel生成函数
        api_generate_excel(
            api_data, 
            content_options, 
            output_path, 
            report_data.get('type', 'daily'),
            report_data.get('region_id', 'all'),
            report_data.get('start_date', ''),
            report_data.get('end_date', '')
        )
        
        logger.info(f"Excel报告生成成功: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"生成Excel报告失败: {str(e)}", exc_info=True)
        return None

def generate_html_report(data, report_data, output_dir):
    """生成HTML格式的报告"""
    try:
        # 导入reports_api模块中的函数
        import importlib.util
        import sys
        
        # 构建reports_api模块的路径
        module_path = os.path.join(current_dir, 'reports_api.py')
        
        # 动态加载模块
        spec = importlib.util.spec_from_file_location('reports_api', module_path)
        reports_api = importlib.util.module_from_spec(spec)
        sys.modules['reports_api'] = reports_api
        spec.loader.exec_module(reports_api)
        
        # 获取generate_html_report函数
        api_generate_html = reports_api.generate_html_report
        
        # 生成文件路径
        report_filename = f"{os.path.basename(output_dir)}.html"
        output_path = os.path.join(output_dir, report_filename)
        
        # 转换data格式以适配api_generate_html函数
        api_data = convert_data_format(data)
        
        # 提取内容选项
        content_options = report_data.get('content_options', {})
        if not content_options:
            content_options = {
                'overview': True,
                'pollution': True,
                'trend': True,
                'warning': False,
                'policy': False
            }
            
        # 调用API中的HTML生成函数
        api_generate_html(
            api_data, 
            content_options, 
            output_path, 
            report_data.get('type', 'daily'),
            report_data.get('region_id', 'all'),
            report_data.get('start_date', ''),
            report_data.get('end_date', '')
        )
        
        logger.info(f"HTML报告生成成功: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"生成HTML报告失败: {str(e)}", exc_info=True)
        return None

def convert_data_format(data):
    """将fetch_report_data返回的数据格式转换为reports_api中generate_*_report函数需要的格式
    
    Args:
        data (dict): fetch_report_data返回的数据
        
    Returns:
        dict: 转换后的数据格式
    """
    try:
        # 提取时间序列数据
        timeseries = data.get('timeseries', [])
        
        # 转换为api需要的格式
        aqi_data = []
        pollutants_data = []
        
        # 根据报告数据类型进行转换
        for item in timeseries:
            date = item.get('date')
            value = item.get('value')
            city = item.get('city')
            
            # 按日期分组，创建AQI和污染物数据
            if date and value is not None:
                # 根据污染物类型确定数据去向
                pollutant_type = data.get('metadata', {}).get('pollutant', 'AQI').upper()
                
                if pollutant_type == 'AQI':
                    aqi_data.append({
                        'date': date,
                        'aqi': value,
                        'city': city
                    })
                else:
                    # 污染物数据
                    pollutant_entry = {
                        'date': date,
                        'city': city
                    }
                    
                    # 根据污染物类型设置对应的字段
                    if pollutant_type == 'PM25':
                        pollutant_entry['pm25'] = value
                    elif pollutant_type == 'PM10':
                        pollutant_entry['pm10'] = value
                    elif pollutant_type == 'SO2':
                        pollutant_entry['so2'] = value
                    elif pollutant_type == 'NO2':
                        pollutant_entry['no2'] = value
                    elif pollutant_type == 'CO':
                        pollutant_entry['co'] = value
                    elif pollutant_type == 'O3':
                        pollutant_entry['o3'] = value
                        
                    pollutants_data.append(pollutant_entry)
        
        # 转换为DataFrame
        aqi_df = pd.DataFrame(aqi_data) if aqi_data else pd.DataFrame()
        pollutants_df = pd.DataFrame(pollutants_data) if pollutants_data else pd.DataFrame()
        
        # 返回API所需的格式
        return {
            'aqi_data': aqi_df,
            'pollutants': pollutants_df,
            'region': data.get('metadata', {}).get('region_id', 'all'),
            'start_date': data.get('metadata', {}).get('start_date', ''),
            'end_date': data.get('metadata', {}).get('end_date', '')
        }
        
    except Exception as e:
        logger.error(f"转换数据格式失败: {str(e)}", exc_info=True)
        # 返回空数据结构
        return {
            'aqi_data': pd.DataFrame(),
            'pollutants': pd.DataFrame(),
            'region': 'all',
            'start_date': '',
            'end_date': ''
        }

def generate_report(report_data):
    """生成报告并返回报告信息
    
    Args:
        report_data (dict): 包含报告生成所需的所有数据
        
    Returns:
        dict: 包含报告ID和状态的信息
    """
    try:
        logger.info(f"开始生成报告: {report_data}")
        
        # 验证必要的参数
        required_fields = ['format', 'start_date', 'end_date', 'pollutant']
        missing_fields = [field for field in required_fields if field not in report_data]
        if missing_fields:
            error_msg = f"缺少必要的报告参数: {', '.join(missing_fields)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # 生成唯一的报告ID
        report_id = str(uuid.uuid4())
        
        # 创建报告记录
        report_info = {
            'id': report_id,
            'status': 'processing',
            'created_at': datetime.now().isoformat(),
            'format': report_data.get('format', 'pdf'),
            'region_id': report_data.get('region_id'),
            'region_name': report_data.get('region_name', '全国'),
            'start_date': report_data.get('start_date'),
            'end_date': report_data.get('end_date'),
            'pollutant': report_data.get('pollutant', 'AQI'),
            'files': {}
        }
        
        # 保存报告信息
        save_report(report_id, report_info)
        
        # 使用非阻塞IO来避免使用线程
        # Thread(target=_generate_report_async, args=(report_id, report_data, report_info)).start()
        
        # 直接返回结果，让客户端后续查询进度
        return {'success': True, 'report_id': report_id, 'status': 'processing'}
    
    except Exception as e:
        error_msg = f"生成报告时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


# 从Thread中分离出来的函数，现在需要单独调用
def _generate_report_async(report_id, report_data, report_info):
    """异步生成报告的后台任务
    
    Args:
        report_id (str): 报告ID
        report_data (dict): 报告生成数据
        report_info (dict): 报告信息记录
    """
    try:
        logger.info(f"开始异步生成报告 ID: {report_id}")
        
        # 更新报告状态
        report_info['status'] = 'processing'
        save_report(report_id, report_info)
        
        # 获取数据
        data = fetch_report_data(report_data)
        if not data:
            error_msg = "获取报告数据失败: 返回空数据"
            logger.error(f"报告 {report_id} 获取数据失败: {error_msg}")
            report_info['status'] = 'failed'
            report_info['error'] = error_msg
            save_report(report_id, report_info)
            return
            
        if 'error' in data:
            error_msg = data.get('error', '获取报告数据失败')
            logger.error(f"报告 {report_id} 获取数据失败: {error_msg}")
            report_info['status'] = 'failed'
            report_info['error'] = error_msg
            save_report(report_id, report_info)
            return
            
        # 检查数据是否为空
        if not data.get('timeseries'):
            error_msg = "没有找到匹配的数据"
            logger.error(f"报告 {report_id} 数据为空: {error_msg}")
            report_info['status'] = 'failed'
            report_info['error'] = error_msg
            save_report(report_id, report_info)
            return
        
        # 获取格式并生成对应的报告
        report_format = report_data.get('format', 'pdf').lower()
        
        # 验证格式是否支持
        supported_formats = ['pdf', 'excel', 'word', 'html']
        if report_format not in supported_formats:
            error_msg = f"不支持的报告格式: {report_format}"
            logger.error(f"报告 {report_id}: {error_msg}")
            report_info['status'] = 'failed'
            report_info['error'] = error_msg
            save_report(report_id, report_info)
            return
        
        # 根据格式选择相应的目录
        format_dir_map = {
            'pdf': REPORTS_PDF_DIR,
            'excel': REPORTS_EXCEL_DIR,
            'word': REPORTS_WORD_DIR,
            'html': REPORTS_HTML_DIR
        }
        target_dir = format_dir_map.get(report_format, REPORTS_DIR)
        
        # 确定报告输出目录和文件名前缀
        output_dir = os.path.join(target_dir, report_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成报告文件
        file_path = None
        
        try:
            if report_format == 'pdf':
                file_path = generate_pdf_report(data, report_data, output_dir)
            elif report_format == 'word':
                file_path = generate_word_report(data, report_data, output_dir)
            elif report_format == 'excel':
                file_path = generate_excel_report(data, report_data, output_dir)
            elif report_format == 'html':
                file_path = generate_html_report(data, report_data, output_dir)
        except Exception as gen_error:
            error_msg = f"报告生成过程出错: {str(gen_error)}"
            logger.error(error_msg, exc_info=True)
            report_info['status'] = 'failed'
            report_info['error'] = error_msg
            save_report(report_id, report_info)
            return
        
        if not file_path:
            logger.error(f"报告 {report_id} 文件生成失败: 未返回有效路径")
            report_info['status'] = 'failed'
            report_info['error'] = "报告文件生成失败: 未返回有效路径"
            save_report(report_id, report_info)
            return
        
        if isinstance(file_path, dict) and 'error' in file_path:
            logger.error(f"报告 {report_id} 文件生成失败: {file_path['error']}")
            report_info['status'] = 'failed'
            report_info['error'] = file_path['error']
            save_report(report_id, report_info)
            return
        
        if not os.path.exists(file_path):
            logger.error(f"报告 {report_id} 文件生成失败: 文件不存在")
            report_info['status'] = 'failed'
            report_info['error'] = "报告文件生成失败: 文件不存在"
            save_report(report_id, report_info)
            return
        
        # 更新报告信息
        report_info['status'] = 'completed'
        report_info['completed_at'] = datetime.now().isoformat()
        if 'files' not in report_info:
            report_info['files'] = {}
        report_info['files'][report_format] = file_path
        
        # 保存更新后的报告信息
        save_report(report_id, report_info)
        logger.info(f"报告 {report_id} 生成完成，文件路径: {file_path}")
        
    except Exception as e:
        error_msg = f"生成报告过程中发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # 更新报告状态为失败
        try:
            report_info['status'] = 'failed'
            report_info['error'] = error_msg
            save_report(report_id, report_info)
        except Exception as save_err:
            logger.error(f"更新报告状态失败: {str(save_err)}")


def fetch_report_data(report_data):
    """获取报告所需的数据
    
    Args:
        report_data (dict): 报告请求数据
        
    Returns:
        dict: 包含报告所需的所有数据
    """
    try:
        # 提取参数
        start_date = report_data.get('start_date')
        end_date = report_data.get('end_date')
        region_id = report_data.get('region_id')
        pollutant = report_data.get('pollutant', 'AQI')
        
        logger.info(f"开始获取报告数据: 区域={region_id}, 日期={start_date}至{end_date}, 污染物={pollutant}")
        
        # 验证日期格式
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 检查日期范围是否合理
            if end_dt < start_dt:
                return {'error': '结束日期不能早于开始日期'}
                
            # 限制日期范围（例如不超过一年）
            if (end_dt - start_dt).days > 365:
                return {'error': '日期范围不能超过一年'}
        except ValueError:
            return {'error': '日期格式无效，请使用YYYY-MM-DD格式'}
        
        # 从数据库获取数据
        data = {
            'timeseries': get_pollutant_data(region_id, start_date, end_date, pollutant),
            'summary': calculate_summary_statistics(region_id, start_date, end_date, pollutant),
            'region_info': get_region_info(region_id),
            'metadata': {
                'start_date': start_date,
                'end_date': end_date,
                'pollutant': pollutant,
                'region_id': region_id
            }
        }
        
        return data
        
    except Exception as e:
        logger.error(f"获取报告数据失败: {str(e)}", exc_info=True)
        return {'error': f"获取报告数据时出错: {str(e)}"} 