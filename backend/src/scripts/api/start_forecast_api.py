#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
空气质量预测API服务启动脚本
功能：提供空气质量预测的API接口
"""

# 如果直接运行此脚本，则启动服务
if __name__ == '__main__':
    import logging
    import os
    import sys
    from pathlib import Path
    
    # 设置项目根目录（确保是D:\CODE而不是D:\CODE\backend）
    current_script_path = Path(__file__).resolve()
    # 向上4层目录到达D:\CODE (脚本路径>api>scripts>src>backend)
    PROJECT_ROOT = "D:\\CODE"
    
    # 指定固定的模型目录路径
    MODELS_DIR = "D:\\CODE\\data\\models"
    SCALERS_DIR = "D:\\CODE\\data\\models\\scalers"
    INITIAL_DATA_DIR = "D:\\CODE\\data\\models\\initial_data"
    
    # 确保这些目录存在
    for dir_path in [MODELS_DIR, SCALERS_DIR, INITIAL_DATA_DIR]:
        if not os.path.exists(dir_path):
            print(f"目录不存在，创建目录: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
    
    # 将项目根目录添加到Python路径
    sys.path.append(PROJECT_ROOT)
    
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "forecast_api.log"), mode='a'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger('start_forecast_api')
    logger.info("启动空气质量预测API服务")
    logger.info(f"项目根目录: {PROJECT_ROOT}")
    logger.info(f"模型目录: {MODELS_DIR}")
    logger.info(f"标准化器目录: {SCALERS_DIR}")
    logger.info(f"初始数据目录: {INITIAL_DATA_DIR}")
    
    # 检查模型目录是否存在
    if not os.path.exists(MODELS_DIR):
        logger.error(f"模型目录不存在: {MODELS_DIR}")
    else:
        logger.info(f"模型目录存在，包含 {len(os.listdir(MODELS_DIR))} 个子目录/文件")
    
    # 检查标准化器目录是否存在
    if not os.path.exists(SCALERS_DIR):
        logger.error(f"标准化器目录不存在: {SCALERS_DIR}")
        os.makedirs(SCALERS_DIR, exist_ok=True)
        logger.info(f"已创建标准化器目录: {SCALERS_DIR}")
    else:
        logger.info(f"标准化器目录存在，包含 {len(os.listdir(SCALERS_DIR))} 个文件")
    
    # 设置环境变量，供forecast_api.py使用
    os.environ["PROJECT_ROOT"] = PROJECT_ROOT
    os.environ["MODELS_DIR"] = MODELS_DIR
    os.environ["SCALERS_DIR"] = SCALERS_DIR
    os.environ["INITIAL_DATA_DIR"] = INITIAL_DATA_DIR
    
    try:
        # 启动API服务
        def start_api():
            print("启动空气质量预测API服务...")
            
            # 导入forecast_api运行Flask应用
            try:
                import sys
                
                # 将目录添加到系统路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                if current_dir not in sys.path:
                    sys.path.append(current_dir)
                
                # 设置环境变量
                os.environ["MODELS_DIR"] = MODELS_DIR
                os.environ["SCALERS_DIR"] = SCALERS_DIR
                os.environ["INITIAL_DATA_DIR"] = INITIAL_DATA_DIR
                
                # 导入并运行API
                from forecast_api import app
                
                port = int(os.environ.get('PORT', 5002))
                host = os.environ.get('HOST', '0.0.0.0')
                
                logger.info(f"启动API服务，监听 {host}:{port}")
                app.run(host=host, port=port, debug=False, threaded=True)
                
            except Exception as e:
                print(f"启动API服务失败: {str(e)}")
                raise
        
        start_api()
        
    except Exception as e:
        logger.error(f"启动API服务失败: {str(e)}")
        logger.exception("启动错误详情：")
        import traceback
        logger.error(traceback.format_exc())
        raise 