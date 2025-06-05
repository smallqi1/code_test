#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
重新构建初始序列数据的脚本
"""

import os
import sys
import shutil
import logging
import json
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(backend_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# 设置脚本路径
SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
ROOT_PATH = os.path.abspath(os.path.join(SCRIPT_PATH, "..", "..", ".."))
sys.path.append(ROOT_PATH)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/rebuild_initial_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('rebuild_initial_data')

# 设置项目根目录和模型目录
if 'PROJECT_ROOT' in os.environ:
    PROJECT_ROOT = os.environ['PROJECT_ROOT']
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))

# 全局变量
MODELS_DIR = os.path.join(PROJECT_ROOT, 'data', 'models')
INITIAL_DATA_DIR = os.path.join(MODELS_DIR, "initial_data")

def delete_all_initial_data():
    """删除所有初始序列数据"""
    try:
        logger.info(f"删除初始序列数据目录: {INITIAL_DATA_DIR}")
        
        # 检查目录是否存在
        if not os.path.exists(INITIAL_DATA_DIR):
            logger.info(f"初始序列数据目录不存在，无需删除")
            return True
        
        # 删除目录中的所有文件，但保留目录
        for filename in os.listdir(INITIAL_DATA_DIR):
            file_path = os.path.join(INITIAL_DATA_DIR, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件时出错: {file_path}, 错误: {str(e)}")
        
        logger.info("所有初始序列数据已删除")
        return True
    except Exception as e:
        logger.error(f"删除初始序列数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def rebuild_initial_data():
    """重新构建初始序列数据"""
    try:
        logger.info("开始重新构建初始序列数据")
        
        # 导入模型初始化模块
        sys.path.insert(0, SCRIPT_PATH)
        from backend.src.scripts.model_train.models import initialize_all_models
        
        # 初始化所有模型
        success = initialize_all_models()
        
        if success:
            logger.info("初始序列数据重建成功")
            return True
        else:
            logger.error("初始序列数据重建失败")
            return False
    except ImportError as e:
        logger.error(f"导入模块失败: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"重建初始序列数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("开始重建初始序列数据")
    
    try:
        # 1. 删除所有现有的初始序列数据
        if not delete_all_initial_data():
            logger.error("删除初始序列数据失败")
            return 1
            
        # 2. 重新构建初始序列数据
        if not rebuild_initial_data():
            logger.error("重建初始序列数据失败")
            return 1
            
        logger.info("初始序列数据重建完成")
        return 0
    except Exception as e:
        logger.error(f"重建过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 