#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
分析空气质量数据
提供各种查询功能来分析空气质量数据库中的数据
"""

import mysql.connector
from mysql.connector import Error
import argparse
import csv
import os
import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '20040102a',
    'database': 'air_quality_monitoring'
}

def connect_to_db():
    """连接到数据库"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"数据库连接错误: {e}")
        return None

def get_available_cities():
    """获取所有可用的城市列表"""
    conn = connect_to_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT city FROM air_quality_data ORDER BY city")
    cities = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return cities

def get_year_range():
    """获取数据库中的年份范围"""
    conn = connect_to_db()
    if not conn:
        return None, None
    
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(data_year), MAX(data_year) FROM air_quality_data")
    min_year, max_year = cursor.fetchone()
    
    conn.close()
    return min_year, max_year

def get_city_annual_stats(city, year=None):
    """获取指定城市的年度统计数据"""
    conn = connect_to_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    
    if year:
        query = """
        SELECT 
            %s AS city,
            data_year AS year,
            COUNT(*) AS days_count,
            ROUND(AVG(aqi_index), 2) AS avg_aqi,
            ROUND(AVG(pm25_avg), 2) AS avg_pm25,
            ROUND(AVG(pm10_avg), 2) AS avg_pm10,
            ROUND(AVG(so2_avg), 2) AS avg_so2,
            ROUND(AVG(no2_avg), 2) AS avg_no2,
            ROUND(AVG(co_avg), 2) AS avg_co,
            ROUND(AVG(o3_avg), 2) AS avg_o3,
            SUM(CASE WHEN quality_level = '优' THEN 1 ELSE 0 END) AS excellent_days,
            SUM(CASE WHEN quality_level = '良' THEN 1 ELSE 0 END) AS good_days,
            SUM(CASE WHEN quality_level = '轻度污染' THEN 1 ELSE 0 END) AS light_pollution_days,
            SUM(CASE WHEN quality_level = '中度污染' THEN 1 ELSE 0 END) AS medium_pollution_days,
            SUM(CASE WHEN quality_level = '重度污染' THEN 1 ELSE 0 END) AS heavy_pollution_days,
            SUM(CASE WHEN quality_level = '严重污染' THEN 1 ELSE 0 END) AS severe_pollution_days
        FROM 
            air_quality_data
        WHERE 
            city = %s AND data_year = %s
        GROUP BY 
            data_year
        """
        cursor.execute(query, (city, city, year))
    else:
        query = """
        SELECT 
            %s AS city,
            data_year AS year,
            COUNT(*) AS days_count,
            ROUND(AVG(aqi_index), 2) AS avg_aqi,
            ROUND(AVG(pm25_avg), 2) AS avg_pm25,
            ROUND(AVG(pm10_avg), 2) AS avg_pm10,
            ROUND(AVG(so2_avg), 2) AS avg_so2,
            ROUND(AVG(no2_avg), 2) AS avg_no2,
            ROUND(AVG(co_avg), 2) AS avg_co,
            ROUND(AVG(o3_avg), 2) AS avg_o3,
            SUM(CASE WHEN quality_level = '优' THEN 1 ELSE 0 END) AS excellent_days,
            SUM(CASE WHEN quality_level = '良' THEN 1 ELSE 0 END) AS good_days,
            SUM(CASE WHEN quality_level = '轻度污染' THEN 1 ELSE 0 END) AS light_pollution_days,
            SUM(CASE WHEN quality_level = '中度污染' THEN 1 ELSE 0 END) AS medium_pollution_days,
            SUM(CASE WHEN quality_level = '重度污染' THEN 1 ELSE 0 END) AS heavy_pollution_days,
            SUM(CASE WHEN quality_level = '严重污染' THEN 1 ELSE 0 END) AS severe_pollution_days
        FROM 
            air_quality_data
        WHERE 
            city = %s
        GROUP BY 
            data_year
        ORDER BY 
            data_year
        """
        cursor.execute(query, (city, city))
    
    result = cursor.fetchall()
    conn.close()
    return result

def compare_cities(cities, year=None, pollutant='aqi_index'):
    """比较多个城市的空气质量"""
    if not cities:
        return None
    
    conn = connect_to_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    
    # 确保污染物字段安全
    valid_pollutants = ['aqi_index', 'pm25_avg', 'pm10_avg', 'so2_avg', 'no2_avg', 'co_avg', 'o3_avg']
    if pollutant not in valid_pollutants:
        pollutant = 'aqi_index'
    
    city_list = ', '.join(['%s'] * len(cities))
    
    if year:
        query = f"""
        SELECT 
            city,
            data_year AS year,
            ROUND(AVG({pollutant}), 2) AS avg_value,
            COUNT(*) AS days_count,
            SUM(CASE WHEN quality_level = '优' THEN 1 ELSE 0 END) AS excellent_days,
            SUM(CASE WHEN quality_level = '良' THEN 1 ELSE 0 END) AS good_days,
            SUM(CASE WHEN quality_level = '轻度污染' THEN 1 ELSE 0 END) AS light_pollution_days,
            SUM(CASE WHEN quality_level = '中度污染' THEN 1 ELSE 0 END) AS medium_pollution_days,
            SUM(CASE WHEN quality_level = '重度污染' THEN 1 ELSE 0 END) AS heavy_pollution_days
        FROM 
            air_quality_data
        WHERE 
            city IN ({city_list}) AND data_year = %s
        GROUP BY 
            city, data_year
        ORDER BY 
            avg_value ASC
        """
        params = cities + [year]
        cursor.execute(query, params)
    else:
        query = f"""
        SELECT 
            city,
            ROUND(AVG({pollutant}), 2) AS avg_value,
            COUNT(*) AS days_count,
            SUM(CASE WHEN quality_level = '优' THEN 1 ELSE 0 END) AS excellent_days,
            SUM(CASE WHEN quality_level = '良' THEN 1 ELSE 0 END) AS good_days,
            SUM(CASE WHEN quality_level = '轻度污染' THEN 1 ELSE 0 END) AS light_pollution_days,
            SUM(CASE WHEN quality_level = '中度污染' THEN 1 ELSE 0 END) AS medium_pollution_days,
            SUM(CASE WHEN quality_level = '重度污染' THEN 1 ELSE 0 END) AS heavy_pollution_days
        FROM 
            air_quality_data
        WHERE 
            city IN ({city_list})
        GROUP BY 
            city
        ORDER BY 
            avg_value ASC
        """
        cursor.execute(query, cities)
    
    result = cursor.fetchall()
    conn.close()
    return result

def get_monthly_trend(city, year):
    """获取指定城市某年的月度趋势"""
    conn = connect_to_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    
    query = """
    SELECT 
        MONTH(record_date) AS month,
        ROUND(AVG(aqi_index), 2) AS avg_aqi,
        ROUND(AVG(pm25_avg), 2) AS avg_pm25,
        ROUND(AVG(pm10_avg), 2) AS avg_pm10,
        ROUND(AVG(so2_avg), 2) AS avg_so2,
        ROUND(AVG(no2_avg), 2) AS avg_no2,
        ROUND(AVG(co_avg), 2) AS avg_co,
        ROUND(AVG(o3_avg), 2) AS avg_o3,
        COUNT(*) AS days_count
    FROM 
        air_quality_data
    WHERE 
        city = %s AND data_year = %s
    GROUP BY 
        MONTH(record_date)
    ORDER BY 
        MONTH(record_date)
    """
    
    cursor.execute(query, (city, year))
    result = cursor.fetchall()
    conn.close()
    return result

def export_to_csv(data, filename):
    """将数据导出到CSV文件"""
    if not data or len(data) == 0:
        print("没有数据可导出")
        return False
    
    try:
        # 确保输出目录存在
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        # 写入CSV文件
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # 获取字段名
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # 写入表头和数据
            writer.writeheader()
            writer.writerows(data)
        
        print(f"数据已成功导出到 {output_path}")
        return True
    
    except Exception as e:
        print(f"导出数据时出错: {e}")
        return False

def display_city_stats(stats):
    """显示城市统计数据"""
    if not stats:
        print("没有可用的统计数据")
        return
    
    for stat in stats:
        print(f"\n{stat['city']} {stat.get('year', '全部年份')} 空气质量统计")
        print("=" * 50)
        print(f"平均AQI指数: {stat['avg_aqi']}")
        
        if 'avg_pm25' in stat:
            print(f"平均PM2.5浓度: {stat['avg_pm25']} μg/m³")
        
        if 'avg_pm10' in stat:
            print(f"平均PM10浓度: {stat['avg_pm10']} μg/m³")
        
        print(f"优良天数: {stat['excellent_days'] + stat['good_days']} " + 
              f"({round((stat['excellent_days'] + stat['good_days']) / stat['days_count'] * 100, 2)}%)")
        print(f"其中优质天数: {stat['excellent_days']} " + 
              f"({round(stat['excellent_days'] / stat['days_count'] * 100, 2)}%)")
        print(f"其中良好天数: {stat['good_days']} " + 
              f"({round(stat['good_days'] / stat['days_count'] * 100, 2)}%)")
        
        print(f"污染天数: {stat['light_pollution_days'] + stat['medium_pollution_days'] + stat.get('heavy_pollution_days', 0)} " + 
              f"({round((stat['light_pollution_days'] + stat['medium_pollution_days'] + stat.get('heavy_pollution_days', 0)) / stat['days_count'] * 100, 2)}%)")
        print(f"其中轻度污染: {stat['light_pollution_days']} " + 
              f"({round(stat['light_pollution_days'] / stat['days_count'] * 100, 2)}%)")
        print(f"其中中度污染: {stat['medium_pollution_days']} " + 
              f"({round(stat['medium_pollution_days'] / stat['days_count'] * 100, 2)}%)")
        
        if 'heavy_pollution_days' in stat and stat['heavy_pollution_days'] > 0:
            print(f"其中重度污染: {stat['heavy_pollution_days']} " + 
                  f"({round(stat['heavy_pollution_days'] / stat['days_count'] * 100, 2)}%)")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='分析空气质量数据')
    
    # 命令行参数
    parser.add_argument('--city', type=str, help='指定城市名称')
    parser.add_argument('--cities', type=str, help='多个城市（用逗号分隔）用于比较')
    parser.add_argument('--year', type=int, help='指定年份')
    parser.add_argument('--month', type=int, help='指定月份')
    parser.add_argument('--pollutant', type=str, default='aqi_index', 
                        choices=['aqi_index', 'pm25_avg', 'pm10_avg', 'so2_avg', 'no2_avg', 'co_avg', 'o3_avg'],
                        help='指定污染物指标')
    parser.add_argument('--export', action='store_true', help='导出结果到CSV文件')
    parser.add_argument('--list-cities', action='store_true', help='列出所有可用城市')
    parser.add_argument('--trend', action='store_true', help='显示月度趋势')
    
    args = parser.parse_args()
    
    # 列出所有城市
    if args.list_cities:
        cities = get_available_cities()
        if cities:
            print("可用的城市列表:")
            for i, city in enumerate(cities, 1):
                print(f"{i}. {city}")
        else:
            print("无法获取城市列表")
        return
    
    # 显示城市年度统计
    if args.city and not args.cities:
        if args.trend and args.year:
            # 显示月度趋势
            monthly_data = get_monthly_trend(args.city, args.year)
            if monthly_data:
                print(f"\n{args.city} {args.year}年 月度空气质量趋势")
                print("=" * 60)
                print("月份  | 平均AQI | PM2.5   | PM10    | SO2     | NO2     | CO      | O3      | 天数")
                print("-" * 60)
                for month in monthly_data:
                    print(f"{month['month']:<5} | {month['avg_aqi']:<7} | {month['avg_pm25']:<7} | {month['avg_pm10']:<7} | {month['avg_so2']:<7} | {month['avg_no2']:<7} | {month['avg_co']:<7} | {month['avg_o3']:<7} | {month['days_count']}")
                
                if args.export:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    export_to_csv(monthly_data, f"{args.city}_{args.year}_monthly_trend_{timestamp}.csv")
            else:
                print(f"无法获取 {args.city} {args.year}年 的月度趋势数据")
        else:
            # 显示年度统计
            stats = get_city_annual_stats(args.city, args.year)
            if stats:
                display_city_stats(stats)
                
                if args.export:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    export_to_csv(stats, f"{args.city}_stats_{timestamp}.csv")
            else:
                print(f"无法获取 {args.city} 的统计数据")
    
    # 比较多个城市
    elif args.cities:
        cities = [city.strip() for city in args.cities.split(',')]
        comparison = compare_cities(cities, args.year, args.pollutant)
        
        if comparison:
            pollutant_name = {
                'aqi_index': 'AQI指数',
                'pm25_avg': 'PM2.5浓度',
                'pm10_avg': 'PM10浓度',
                'so2_avg': 'SO2浓度',
                'no2_avg': 'NO2浓度',
                'co_avg': 'CO浓度',
                'o3_avg': 'O3浓度'
            }.get(args.pollutant, args.pollutant)
            
            year_str = f" {args.year}年" if args.year else ""
            
            print(f"\n城市{year_str}平均{pollutant_name}比较")
            print("=" * 60)
            print("城市     | 平均值   | 优良天数比例  | 优良天数  | 总天数")
            print("-" * 60)
            
            for city_data in comparison:
                good_days = city_data['excellent_days'] + city_data['good_days']
                good_days_percent = round(good_days / city_data['days_count'] * 100, 2)
                print(f"{city_data['city']:<8} | {city_data['avg_value']:<7} | {good_days_percent:<10}% | {good_days:<8} | {city_data['days_count']}")
            
            if args.export:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                year_str = f"_{args.year}" if args.year else ""
                export_to_csv(comparison, f"city_comparison{year_str}_{args.pollutant}_{timestamp}.csv")
        else:
            print("无法获取城市比较数据")
    
    # 如果没有参数，显示使用说明
    else:
        min_year, max_year = get_year_range()
        print("\n空气质量数据分析工具")
        print("=" * 60)
        print("使用方法示例:")
        print(f"1. 列出所有可用城市: python {__file__} --list-cities")
        print(f"2. 查看某个城市的所有年份数据: python {__file__} --city 广州市")
        print(f"3. 查看某个城市特定年份的数据: python {__file__} --city 广州市 --year 2022")
        print(f"4. 查看某个城市特定年份的月度趋势: python {__file__} --city 广州市 --year 2022 --trend")
        print(f"5. 比较多个城市的空气质量: python {__file__} --cities 广州市,深圳市,佛山市")
        print(f"6. 比较多个城市的特定年份的数据: python {__file__} --cities 广州市,深圳市,佛山市 --year 2022")
        print(f"7. 比较多个城市的特定污染物: python {__file__} --cities 广州市,深圳市,佛山市 --pollutant pm25_avg")
        print(f"8. 导出数据到CSV文件: 添加 --export 参数到任意命令")
        
        if min_year and max_year:
            print(f"\n可用的数据年份范围: {min_year} - {max_year}")

if __name__ == "__main__":
    main() 