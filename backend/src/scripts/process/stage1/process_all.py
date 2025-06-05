import os
import logging
from datetime import datetime
from pathlib import Path
import time
from process_air1 import process_air1_data
from process_air2 import process_air2_data

def setup_logging():
    """设置日志记录"""
    log_dir = os.path.join('data', 'logs')
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'process_all_{timestamp}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """主函数"""
    logger = setup_logging()
    start_time = time.time()
    
    # 设置输入和输出目录
    input_dir = os.path.join('data', 'origin')
    output_dir = os.path.join('data', 'processed')
    
    logger.info('开始处理所有数据')
    
    # 第一阶段：处理air1数据
    logger.info('开始处理air1数据')
    process_air1_data(input_dir, output_dir)
    
    # 第一阶段：处理air2数据
    logger.info('开始处理air2数据')
    process_air2_data(input_dir, output_dir)
    
    end_time = time.time()
    total_time = end_time - start_time
    logger.info(f'所有数据处理完成，总耗时: {total_time:.2f}秒')

if __name__ == '__main__':
    main()