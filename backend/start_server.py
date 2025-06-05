#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
广东省空气质量监测系统后端服务启动脚本
功能：同时启动历史数据API服务、实时数据API服务、预测数据API服务和报告生成服务
"""

import os
import sys
import subprocess
import multiprocessing
import time
import signal
import logging
from pathlib import Path
import importlib.util
from logging.handlers import RotatingFileHandler
import datetime
import socket
import concurrent.futures

# 日志和颜色配置
LOG_COLORS = {
    'ERROR': '\033[31m', 'WARNING': '\033[33m', 'INFO': '\033[32m', 'RESET': '\033[0m',
    'HISTORICAL': '\033[38;5;33m', 'REALTIME': '\033[38;5;208m', 'FORECAST': '\033[38;5;141m',
    'DATA_PROCESS': '\033[38;5;36m', 'SYSTEM': '\033[38;5;248m', 'REPORTS': '\033[38;5;112m'
}

SERVICE_TAGS = {
    'historical': f"{LOG_COLORS['HISTORICAL']}[历史数据]{LOG_COLORS['RESET']}",
    'realtime': f"{LOG_COLORS['REALTIME']}[实时数据]{LOG_COLORS['RESET']}",
    'forecast': f"{LOG_COLORS['FORECAST']}[预测数据]{LOG_COLORS['RESET']}",
    'data_process': f"{LOG_COLORS['DATA_PROCESS']}[数据处理]{LOG_COLORS['RESET']}",
    'system': f"{LOG_COLORS['SYSTEM']}[系统]{LOG_COLORS['RESET']}",
    'reports': f"{LOG_COLORS['REPORTS']}[报告服务]{LOG_COLORS['RESET']}",
    'auth': f"{LOG_COLORS['INFO']}[用户认证]{LOG_COLORS['RESET']}"
}

# 项目路径设置
project_root = str(Path(__file__).resolve().parent)
sys.path.append(project_root)

# API服务路径
api_base_dir = os.path.join(project_root, 'src', 'scripts', 'api')
historical_api_path = os.path.join(api_base_dir, 'historical_data_api.py')
realtime_api_path = os.path.join(api_base_dir, 'realtime_service_api.py')
forecast_api_path = os.path.join(api_base_dir, 'start_forecast_api.py')
reports_api_path = os.path.join(api_base_dir, 'reports', 'start_reports_api.py')
user_auth_api_path = os.path.join(api_base_dir, 'user_auth_api.py')

# 创建日志目录
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)

# 日志过滤器
class LogFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.filter_patterns = [
            "WARNING: This is a development server", "Running on", "Debug mode:", 
            "Restarting with", "Debugger is", "Environment: production", 
            "Press CTRL+C to quit", "* Serving Flask app", "127.0.0.1 - -", 
            "确保报告目录存在", "下载模块中的日志", "欢迎使用", "初始化报告API服务", 
            "启动中", "数据处理线程已启动", "Python路径:", "正在导入历史数据API模块"
        ]
    
    def filter(self, record):
        if not hasattr(record, 'msg'):
            return True
        message = str(record.msg)
        return not any(pattern in message for pattern in self.filter_patterns)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            os.path.join(log_dir, 'api_server.log'),
            maxBytes=10*1024*1024, 
            backupCount=5,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('server_manager')

# 减少其他库的日志级别
for log_name in ['werkzeug', 'urllib3', 'matplotlib']:
    logging.getLogger(log_name).setLevel(logging.WARNING)

# 添加日志过滤器
logger.addFilter(LogFilter())

def log(level, message, service=None):
    """记录带颜色和服务标识的日志"""
    service_tag = SERVICE_TAGS.get(service, "") + " " if service else ""
    
    if level == 'ERROR':
        colored_msg = f"{LOG_COLORS['ERROR']}{service_tag}{message}{LOG_COLORS['RESET']}"
        logger.error(colored_msg)
    elif level == 'WARNING':
        colored_msg = f"{LOG_COLORS['WARNING']}{service_tag}{message}{LOG_COLORS['RESET']}"
        logger.warning(colored_msg)
    elif level == 'INFO':
        colored_msg = f"{LOG_COLORS['INFO']}{service_tag}{message}{LOG_COLORS['RESET']}"
        logger.info(colored_msg)
    else:
        logger.debug(f"{service_tag}{message}")

# 导入数据更新模块
def import_data_modules():
    try:
        from src.scripts.process.new_stage.download_data_process import check_and_update_data, init_db_pool, setup_logging
        return check_and_update_data, init_db_pool, setup_logging
    except ImportError as e:
        log('WARNING', f"无法导入数据更新模块，但将继续启动服务: {e}", service='system')
        return None, None, None

check_and_update_data, init_db_pool, setup_logging = import_data_modules()

def run_historical_api():
    """运行历史数据API服务"""
    try:
        if not os.path.exists(historical_api_path):
            log('ERROR', f"历史数据API文件不存在: {historical_api_path}", service='historical')
            return 1
            
        # 切换到API目录并导入模块
        original_dir = os.getcwd()
        os.chdir(api_base_dir)
        
        spec = importlib.util.spec_from_file_location("historical_data_api", historical_api_path)
        if not spec or not spec.loader:
            log('ERROR', f"无法加载历史数据API模块", service='historical')
            os.chdir(original_dir)
            return 1
        
        historical_data_api = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(historical_data_api)
            app = historical_data_api.app
            
            # 初始化数据库连接
            try:
                if setup_logging and init_db_pool:
                    setup_logging()
                    if init_db_pool():
                        log('INFO', "数据库连接池初始化成功", service='historical')
                    else:
                        log('WARNING', "数据库连接池初始化失败，系统将在需要时重试", service='historical')
            except Exception as e:
                log('WARNING', f"数据库连接池初始化失败: {e}", service='historical')
            
            # 启动Flask应用
            log('INFO', "启动历史数据API服务 [端口:5000]", service='historical')
            os.environ['FLASK_ENV'] = 'production'
            os.environ['WERKZEUG_RUN_MAIN'] = 'true'
            os.environ['WERKZEUG_SILENCE_WARNINGS'] = 'true'
            
            from werkzeug.serving import run_simple
            from werkzeug.middleware.proxy_fix import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app)
            run_simple('0.0.0.0', 5000, app, use_reloader=False, threaded=True, use_debugger=False)
            
        except Exception as e:
            log('ERROR', f"启动历史数据API服务失败: {e}", service='historical')
            import traceback
            log('ERROR', traceback.format_exc(), service='historical')
            os.chdir(original_dir)
            return 1
            
    except Exception as e:
        log('ERROR', f"历史数据API服务出错: {e}", service='historical')
        import traceback
        log('ERROR', traceback.format_exc(), service='historical')
        return 1

def run_api_service(api_path, port, service_name, service_tag):
    """通用API服务启动函数"""
    try:
        if not os.path.exists(api_path):
            log('ERROR', f"{service_name}服务文件不存在: {api_path}", service=service_tag)
            return 1
            
        log('INFO', f"启动{service_name}服务 [端口:{port}]", service=service_tag)
        
        log_file = os.path.join(log_dir, f'{service_tag}_api.log')
        
        env = os.environ.copy()
        env["FLASK_ENV"] = "production"
        env["FLASK_DEBUG"] = "false"
        env["WERKZEUG_SILENCE_WARNINGS"] = "true"
        env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
        
        # 确保日志文件目录存在
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, 'a', encoding='utf-8') as f:
            process = subprocess.Popen(
                [sys.executable, api_path],
                stdout=f, stderr=f, env=env
            )
        
            # 等待启动完成
            start_time = time.time()
            max_wait_time = 10  # 最长等待10秒
            
            # 检查进程是否已退出
            while time.time() - start_time < max_wait_time:
                if process.poll() is not None:
                    log('ERROR', f"{service_name}服务启动失败，进程已退出", service=service_tag)
                    return 1
                
                # 如果端口已经在监听，则服务已成功启动
                if check_port_status(port):
                    break
                    
                time.sleep(0.5)
                
            log('INFO', f"{service_name}服务成功启动", service=service_tag)
            
            # 持续监控进程状态
            while True:
                if process.poll() is not None:
                    log('ERROR', f"{service_name}进程已退出", service=service_tag)
                    return 1
                time.sleep(5)
        
    except Exception as e:
        log('ERROR', f"{service_name}服务出错: {e}", service=service_tag)
        import traceback
        log('ERROR', traceback.format_exc(), service=service_tag)
        return 1

def run_realtime_api():
    """运行实时数据API服务"""
    return run_api_service(realtime_api_path, 5001, "实时数据API", "realtime")

def run_forecast_api():
    """运行预测数据API服务"""
    return run_api_service(forecast_api_path, 5002, "预测数据API", "forecast")

def run_reports_api():
    """运行报告生成API服务"""
    return run_api_service(reports_api_path, 5003, "报告生成API", "reports")

def run_user_auth_api():
    """运行用户认证API服务"""
    return run_api_service(user_auth_api_path, 5004, "用户认证API", "auth")

def run_data_process():
    """定时运行数据处理脚本"""
    log('INFO', "数据处理线程已启动", service='data_process')
    
    script_path = os.path.join(project_root, 'src', 'scripts', 'process', 'new_stage', 'download_data_process.py')
    python_path = sys.executable
    last_success_time = datetime.datetime.now()
    
    # 检查数据处理脚本是否存在
    if not os.path.exists(script_path):
        log('ERROR', f"数据处理脚本不存在: {script_path}", service='data_process')
        return 1
    
    # 计算首次执行时间（每6小时：0点、6点、12点、18点）
    now = datetime.datetime.now()
    hour_interval = 6
    next_slot = (now.hour // hour_interval + 1) * hour_interval % 24
    next_hour = now.replace(hour=next_slot, minute=0, second=0, microsecond=0)
    next_hour = next_hour + datetime.timedelta(days=1) if next_hour <= now else next_hour
    
    log('INFO', f"首次数据更新将在 {next_hour.strftime('%Y-%m-%d %H:%M:%S')} 进行", service='data_process')
    
    while True:
        try:
            now = datetime.datetime.now()
            
            # 如果距离上次成功执行不足30分钟，跳过本次执行
            if (now - last_success_time).total_seconds() < 1800:
                pass
            else:
                # 执行数据更新
                log('INFO', "开始执行定时数据更新", service='data_process')
                
                env = os.environ.copy()
                env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
                
                process = subprocess.run(
                    [python_path, script_path],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    universal_newlines=True, env=env, check=False
                )
                
                if process.returncode == 0:
                    log('INFO', "数据更新成功完成", service='data_process')
                    last_success_time = datetime.datetime.now()
                else:
                    error_output = process.stdout[:500] + "..." if len(process.stdout) > 500 else process.stdout
                    log('ERROR', f"数据更新失败，返回码: {process.returncode}, 错误信息: {error_output}", service='data_process')
            
            # 计算下次执行时间
            now = datetime.datetime.now()
            next_slot = (now.hour // hour_interval + 1) * hour_interval % 24
            next_hour = now.replace(hour=next_slot, minute=0, second=0, microsecond=0)
            next_hour = next_hour + datetime.timedelta(days=1) if next_hour <= now else next_hour
            
            sleep_seconds = (next_hour - now).total_seconds()
            log('INFO', f"下次数据更新将在 {next_hour.strftime('%Y-%m-%d %H:%M:%S')} 进行", service='data_process')
            
            # 分段休眠，便于响应系统信号
            remaining_sleep = sleep_seconds
            while remaining_sleep > 0:
                sleep_interval = min(remaining_sleep, 60)
                time.sleep(sleep_interval)
                remaining_sleep -= sleep_interval
                
        except Exception as e:
            log('ERROR', f"数据处理出错: {e}", service='data_process')
            import traceback
            log('ERROR', f"详细错误: {traceback.format_exc()[:500]}...", service='data_process')
            time.sleep(900)  # 出错后等待15分钟再重试

def check_port_status(port):
    """检查端口是否可访问"""
    if not port:
        return True
    
    # 增加检查重试次数，提高成功率
    max_retries = 5
    retry_interval = 0.5
    
    for attempt in range(max_retries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.5)  # 增加超时时间
                result = s.connect_ex(('127.0.0.1', port))
                if result == 0:
                    return True
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    time.sleep(retry_interval)
        except Exception:
            # 忽略连接错误，继续重试
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
    
    return False

def check_services_status(services_info):
    """并行检查所有服务状态，提高效率"""
    def check_service(service_id, info):
        try:
            if info['process'].is_alive():
                status = '运行中' if info['port'] is None or check_port_status(info['port']) else '端口未响应'
                return service_id, status
            else:
                return service_id, '启动失败'
        except Exception as e:
            log('WARNING', f"检查服务{service_id}状态时出错: {e}", service='system')
            return service_id, '状态未知'
    
    # 使用线程池并行检查所有服务
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(services_info)) as executor:
        futures = {executor.submit(check_service, service_id, info): service_id 
                  for service_id, info in services_info.items()}
        
        for future in concurrent.futures.as_completed(futures):
            try:
                service_id, status = future.result()
                services_info[service_id]['status'] = status
            except Exception as e:
                log('WARNING', f"获取服务状态结果时出错: {e}", service='system')
    
    return services_info

def show_status_summary(services_info):
    """显示服务状态汇总"""
    print("\n╔═════════════════════════════════════════════════════════════════╗")
    print(f"║ {LOG_COLORS['INFO']}服务启动状态汇总{LOG_COLORS['RESET']}                                            ║")
    print("╠═════════════════════════════════════════════════════════════════╣")
    
    for _, info in services_info.items():
        port_str = f"端口: {LOG_COLORS['INFO']}{info['port']}{LOG_COLORS['RESET']}" if info['port'] else "后台任务"
        status_color = LOG_COLORS['INFO'] if info['status'] == '运行中' else LOG_COLORS['ERROR']
        status_str = f"{status_color}{info['status']}{LOG_COLORS['RESET']}"
        print(f"║ {SERVICE_TAGS[info['tag']]} - {port_str} - 状态: {status_str}{'        ' if info['status'] == '运行中' else '      '}║")
    
    print("╠═════════════════════════════════════════════════════════════════╣")
    print(f"║ {LOG_COLORS['INFO']}前端访问地址: http://localhost:3001/login{LOG_COLORS['RESET']}                         ║")
    print("╚═════════════════════════════════════════════════════════════════╝")

def safe_terminate(process):
    """安全终止进程"""
    if process and process.is_alive():
        try:
            process.terminate()
            process.join(2.0)  # 等待更长时间
            if process.is_alive() and hasattr(process, 'kill'):
                process.kill()
                process.join(1.0)
        except Exception as e:
            log('WARNING', f"终止进程时出错: {e}", service='system')

def restart_service(service_config, services_info, processes, index):
    """重启服务函数"""
    name = service_config["name"]
    info = services_info[name]
    
    try:
        # 先终止旧进程
        old_process = info['process']
        if old_process and old_process.is_alive():
            safe_terminate(old_process)
            
        # 创建新进程
        new_process = multiprocessing.Process(
            target=service_config['function'],
            name=service_config['name']
        )
        new_process.daemon = True
        new_process.start()
        
        # 更新进程引用
        processes[index] = new_process
        services_info[name]['process'] = new_process
        services_info[name]['status'] = '重启中'
        
        log('INFO', f"{info['display']}进程已重启", service='system')
        
        # 等待进程启动
        time.sleep(3)
        return True
    except Exception as e:
        log('ERROR', f"重启{info['display']}进程时出错: {e}", service='system')
        return False

def main():
    """主函数：启动所有服务并监控"""
    processes = []  # 存储所有进程
    
    try:
        # 显示启动横幅
        print(f"""
╔═══════════════════════════════════════════════════╗
║                                                   ║
║  {LOG_COLORS['INFO']}广东省空气质量监测系统{LOG_COLORS['RESET']}                          ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
""")
        
        log('INFO', "正在启动广东省空气质量监测系统所有服务...", service='system')
        
        # 服务配置
        services_config = [
            {"name": "historical_api", "function": run_historical_api, "display": "历史数据API", "port": 5000, "tag": "historical"},
            {"name": "realtime_api", "function": run_realtime_api, "display": "实时数据API", "port": 5001, "tag": "realtime"},
            {"name": "forecast_api", "function": run_forecast_api, "display": "预测数据API", "port": 5002, "tag": "forecast"},
            {"name": "reports_api", "function": run_reports_api, "display": "报告生成API", "port": 5003, "tag": "reports"},
            {"name": "user_auth_api", "function": run_user_auth_api, "display": "用户认证API", "port": 5004, "tag": "auth"},
            {"name": "data_process", "function": run_data_process, "display": "数据处理服务", "port": None, "tag": "data_process"}
        ]
        
        # 启动所有服务
        services_info = {}
        
        # 首先启动历史数据API，因为它包含数据库初始化
        first_service = services_config[0]
        log('INFO', f"启动{first_service['display']}...", service='system')
        first_process = multiprocessing.Process(
            target=first_service['function'],
            name=first_service['name']
        )
        first_process.daemon = True
        first_process.start()
        processes.append(first_process)
        
        services_info[first_service['name']] = {
            'process': first_process,
            'port': first_service['port'],
            'display': first_service['display'],
            'tag': first_service['tag'],
            'status': '启动中'
        }
        
        # 等待历史数据API启动并初始化数据库
        time.sleep(3)
        
        # 启动其余服务
        for config in services_config[1:]:
            log('INFO', f"启动{config['display']}...", service='system')
            process = multiprocessing.Process(
                target=config['function'],
                name=config['name']
            )
            process.daemon = True
            process.start()
            processes.append(process)
            
            services_info[config['name']] = {
                'process': process,
                'port': config['port'],
                'display': config['display'],
                'tag': config['tag'],
                'status': '启动中'
            }
            
            # 每启动一个服务暂停片刻，避免资源竞争
            time.sleep(0.5)
        
        # 信号处理器：安全关闭所有服务
        def signal_handler(sig, frame):
            log('INFO', "接收到终止信号，正在关闭所有服务...", service='system')
            
            # 忽略后续信号
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            
            # 终止所有进程
            for process in processes:
                safe_terminate(process)
            
            log('INFO', "所有服务已关闭", service='system')
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 等待服务启动
        log('INFO', "等待服务启动...", service='system')
        time.sleep(5)  # 确保所有服务有足够时间完成启动
        
        # 检查服务状态
        services_info = check_services_status(services_info)
        show_status_summary(services_info)
        
        # 如果有服务未启动，再等待并检查
        running_count = sum(1 for info in services_info.values() if info['status'] == '运行中')
        if running_count < len(services_info):
            log('INFO', "部分服务尚未就绪，等待后重新检查...", service='system')
            time.sleep(5)
            services_info = check_services_status(services_info)
            show_status_summary(services_info)
            running_count = sum(1 for info in services_info.values() if info['status'] == '运行中')
        
        log('INFO', "所有服务已启动，按 Ctrl+C 停止", service='system')
        log('INFO', f"{running_count}/{len(services_info)}个服务运行正常", service='system')
        
        # 主循环：监控服务状态并自动重启
        last_check_time = time.time()
        consecutive_failures = {name: 0 for name in services_info.keys()}
        
        while True:
            # 检查进程状态并尝试重启已停止的服务
            for i, (name, info) in enumerate(services_info.items()):
                config = next(c for c in services_config if c['name'] == name)
                if not info['process'].is_alive():
                    consecutive_failures[name] += 1
                    log('ERROR', f"{info['display']}进程已停止，正在尝试第{consecutive_failures[name]}次重启...", service='system')
                    
                    # 重启服务
                    restart_success = restart_service(config, services_info, processes, i)
                    
                    # 如果多次重启失败，降低重启频率
                    if not restart_success or consecutive_failures[name] > 3:
                        wait_time = min(consecutive_failures[name] * 10, 300)  # 最长等待5分钟
                        log('WARNING', f"{info['display']}重启多次失败，将在{wait_time}秒后再次尝试", service='system')
                        time.sleep(wait_time)
                else:
                    # 进程正常运行，重置失败计数
                    consecutive_failures[name] = 0
            
            # 定期检查所有服务状态
            current_time = time.time()
            if current_time - last_check_time >= 60:
                services_info = check_services_status(services_info)
                running_count = sum(1 for info in services_info.values() if info['status'] == '运行中')
                if running_count == len(services_info):
                    log('INFO', "所有服务运行正常", service='system')
                else:
                    log('WARNING', f"仅有{running_count}/{len(services_info)}个服务运行正常", service='system')
                    
                    # 尝试重启未响应的服务
                    for i, (name, info) in enumerate(services_info.items()):
                        if info['status'] != '运行中' and info['process'].is_alive():
                            config = next(c for c in services_config if c['name'] == name)
                            log('WARNING', f"{info['display']}服务未响应，尝试重启", service='system')
                            restart_service(config, services_info, processes, i)
                
                last_check_time = current_time
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        log('INFO', "收到用户中断请求，正在关闭所有服务...", service='system')
        for process in processes:
            safe_terminate(process)
        log('INFO', "所有服务已关闭", service='system')
        sys.exit(0)
    except Exception as e:
        log('ERROR', f"启动服务失败: {e}", service='system')
        import traceback
        log('ERROR', traceback.format_exc(), service='system')
        
        # 确保关闭所有已启动的进程
        for process in processes:
            safe_terminate(process)
            
        sys.exit(1)

if __name__ == '__main__':
    main() 