#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
按城市名称对stage2的数据进行排序，删除城市编号，结果存放在stage3中
排序规则：先按城市名分组，相同城市内按时间排序
"""

import os
import pandas as pd
import glob
from pathlib import Path
# 自定义路径配置
DATA_DIR = r"D:\CODE\data\air_data\processed"
STAGE2_DIR = os.path.join(DATA_DIR, "stage2") 
STAGE3_DIR = os.path.join(DATA_DIR, "stage3")

# 确保目标文件夹存在
os.makedirs(STAGE3_DIR, exist_ok=True)

# 确保目标文件夹存在
os.makedirs(STAGE3_DIR, exist_ok=True)

def sort_data_by_city_and_date():
    """读取stage2数据，删除城市编号，按城市和日期排序后保存到stage3"""
    # 获取stage2目录下的所有CSV文件
    all_files = glob.glob(os.path.join(STAGE2_DIR, "air_quality_*.csv"))
    
    if not all_files:
        print("警告：stage2目录下没有找到CSV文件")
        return False
    
    print(f"找到{len(all_files)}个数据文件，开始处理...")
    
    # 处理每个文件
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        print(f"处理文件：{file_name}")
        
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 检查必要的列是否存在
            if 'Ctn' not in df.columns or 'Date' not in df.columns:
                print(f"错误：文件{file_name}中缺少必要的列，跳过")
                continue
            
            # 确保日期列是正确的日期格式（用于排序）
            df['Date'] = pd.to_datetime(df['Date'])
            
            # 删除城市编号列
            if 'Ctnb' in df.columns:
                df = df.drop(columns=['Ctnb'])
            
            # 按城市分组并在每个分组内按日期排序
            # 首先按城市名排序，然后在每个城市内按日期排序
            df_sorted = df.sort_values(by=['Ctn', 'Date'])
            
            # 将日期转换回字符串格式
            df_sorted['Date'] = df_sorted['Date'].dt.strftime('%Y-%m-%d')
            
            # 确保数值格式保持一致
            numeric_cols = ['AQIind', 'AQIrnk', '24hPM2.5avg', '24hPM10avg', '24hSO2avg', '24hNO2avg', '24hCOavg', '24hO3avg']
            for col in numeric_cols:
                if col in df_sorted.columns:
                    df_sorted[col] = df_sorted[col].round(1)
            
            # 保存到stage3目录
            output_path = os.path.join(STAGE3_DIR, file_name)
            df_sorted.to_csv(output_path, index=False, encoding='utf-8')
            print(f"已保存排序后的文件：{output_path}")
            
        except Exception as e:
            print(f"处理文件{file_name}时发生错误：{e}")
    
    return True

def main():
    """主函数"""
    print("开始处理stage2数据：删除城市编号并按城市和日期排序...")
    
    # 排序数据并保存
    success = sort_data_by_city_and_date()
    
    if success:
        print("数据处理完成！结果已保存到stage3目录")
        print("- 已删除城市编号列")
        print("- 已按城市名称分组")
        print("- 同一城市内的数据按日期排序")
    else:
        print("数据处理失败")

if __name__ == "__main__":
    main() 