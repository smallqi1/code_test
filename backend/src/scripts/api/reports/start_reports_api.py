#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
广东省空气质量监测系统 - 报告API服务启动脚本
"""

import os
import sys
import logging
from pathlib import Path
import traceback
import importlib.util

# 获取当前脚本目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
project_root = str(Path(__file__).resolve().parents[4])
# 添加项目根目录到Python路径
sys.path.append(project_root)

# 配置日志级别
log_level = os.environ.get("API_LOG_LEVEL", "INFO")
if log_level == "DEBUG":
    logging_level = logging.DEBUG
elif log_level == "ERROR":
    logging_level = logging.ERROR
elif log_level == "WARNING":
    logging_level = logging.WARNING
else:
    logging_level = logging.INFO

# 降低werkzeug和Flask日志级别
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('flask').setLevel(logging.ERROR)

# 设置日志文件路径
log_file = os.path.join(project_root, 'src', 'scripts', 'api', 'logs', 'reports_api_startup.log')

# 配置日志
logging.basicConfig(
    level=logging_level,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger('reports_api_startup')

def run_setup():
    """运行设置脚本进行初始化"""
    try:
        logger.info("运行环境初始化脚本...")
        setup_path = os.path.join(current_dir, 'setup.py')
        
        if os.path.exists(setup_path):
            # 加载setup模块
            spec = importlib.util.spec_from_file_location("setup", setup_path)
            setup_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(setup_module)
            
            # 运行初始化函数
            setup_module.ensure_directories()
            setup_module.check_reports_metadata()
            setup_module.clean_up_logs()
            
            logger.info("环境初始化完成")
            return True
        else:
            logger.warning(f"未找到设置脚本: {setup_path}")
            return False
    except Exception as e:
        logger.error(f"运行初始化脚本失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# 导入报告API模块
try:
    # 先运行初始化
    setup_success = run_setup()
    if not setup_success:
        logger.warning("环境初始化失败，服务可能无法正常运行")
    
    from src.scripts.api.reports.reports_api import app, logger, init_reports_api
    
    # 设置日志级别
    logger.setLevel(logging_level)
    
    # 启动报告API服务
    if __name__ == "__main__":
        try:
            logger.info("正在启动报告API服务...")
            
            # 初始化报告API服务
            logger.info("初始化报告API服务...")
            init_result = init_reports_api()
            if not init_result:
                logger.error("报告API服务初始化失败，服务将不会启动")
                sys.exit(1)
            logger.info("报告API服务初始化完成")
            
            # 根据环境变量决定是否使用调试模式
            debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
            
            # 生产环境不使用调试模式，以减少不必要的日志
            app.run(
                host='0.0.0.0', 
                port=5003, 
                debug=debug_mode,
                use_reloader=False,  # 禁用重载器以避免进程重启
                threaded=True  # 启用线程支持，提高并发处理能力
            )
        except Exception as e:
            logger.error(f"启动报告API服务失败: {str(e)}")
            # 添加详细错误跟踪
            logger.error(f"详细错误: {traceback.format_exc()}")
            sys.exit(1)
            
except ImportError as e:
    print(f"导入报告API模块失败: {str(e)}")
    # 打印更详细的报错信息
    print(f"详细错误: {traceback.format_exc()}")
    sys.exit(1)