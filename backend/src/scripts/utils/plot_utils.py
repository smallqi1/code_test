#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
绘图工具函数
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import seaborn as sns
import io
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 设置Matplotlib中文字体
try:
    # 查找系统中文字体
    font_list = ['SimHei', 'Microsoft YaHei', 'STHeiti', 'STSong', 'STFangsong']
    chinese_font = None
    
    for font in font_list:
        try:
            chinese_font = FontProperties(fname=font)
            break
        except:
            continue
    
    if chinese_font is None:
        logger.warning("未找到中文字体，图表中文可能无法正确显示")
except Exception as e:
    logger.error(f"设置中文字体失败: {str(e)}")

# 设置Seaborn样式
sns.set(style="whitegrid")

def create_bar_chart(data, x_column, y_column, title=None, xlabel=None, ylabel=None, 
                    color='#1890ff', figsize=(10, 6), save_path=None, show=False):
    """
    创建柱状图
    
    Args:
        data: DataFrame数据
        x_column: X轴列名
        y_column: Y轴列名
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        color: 柱状图颜色
        figsize: 图表尺寸
        save_path: 保存路径
        show: 是否显示图表
        
    Returns:
        bytes或None: 图表二进制数据或None
    """
    try:
        if data.empty:
            logger.warning("数据为空，无法创建柱状图")
            return None
            
        plt.figure(figsize=figsize)
        
        # 绘制柱状图
        ax = sns.barplot(x=x_column, y=y_column, data=data, color=color)
        
        # 设置标题和标签
        if title:
            plt.title(title, fontproperties=chinese_font, fontsize=14)
        if xlabel:
            plt.xlabel(xlabel, fontproperties=chinese_font, fontsize=12)
        if ylabel:
            plt.ylabel(ylabel, fontproperties=chinese_font, fontsize=12)
            
        # 设置刻度标签字体
        plt.xticks(fontproperties=chinese_font, fontsize=10)
        plt.yticks(fontsize=10)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或返回图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        if show:
            plt.show()
            
        # 将图表转换为二进制数据
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', dpi=100, bbox_inches='tight')
        img_data.seek(0)
        
        plt.close()
        
        return img_data.getvalue()
        
    except Exception as e:
        logger.error(f"创建柱状图失败: {str(e)}")
        plt.close()
        return None

def create_line_chart(data, x_column, y_columns, title=None, xlabel=None, ylabel=None,
                     colors=None, figsize=(12, 6), save_path=None, show=False, 
                     include_markers=True, grid=True):
    """
    创建折线图
    
    Args:
        data: DataFrame数据
        x_column: X轴列名
        y_columns: Y轴列名列表
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        colors: 线条颜色列表
        figsize: 图表尺寸
        save_path: 保存路径
        show: 是否显示图表
        include_markers: 是否包含数据点标记
        grid: 是否显示网格
        
    Returns:
        bytes或None: 图表二进制数据或None
    """
    try:
        if data.empty:
            logger.warning("数据为空，无法创建折线图")
            return None
            
        # 确保y_columns是列表
        if isinstance(y_columns, str):
            y_columns = [y_columns]
            
        # 默认颜色
        if not colors:
            colors = plt.cm.tab10.colors[:len(y_columns)]
        elif len(colors) < len(y_columns):
            colors = colors + list(plt.cm.tab10.colors[:len(y_columns) - len(colors)])
            
        plt.figure(figsize=figsize)
        
        # 绘制折线图
        for i, y_col in enumerate(y_columns):
            if y_col in data.columns:
                if include_markers:
                    plt.plot(data[x_column], data[y_col], marker='o', label=y_col, color=colors[i])
                else:
                    plt.plot(data[x_column], data[y_col], label=y_col, color=colors[i])
                    
        # 设置标题和标签
        if title:
            plt.title(title, fontproperties=chinese_font, fontsize=14)
        if xlabel:
            plt.xlabel(xlabel, fontproperties=chinese_font, fontsize=12)
        if ylabel:
            plt.ylabel(ylabel, fontproperties=chinese_font, fontsize=12)
            
        # 设置网格
        plt.grid(grid)
        
        # 设置图例
        plt.legend(prop=chinese_font, loc='best')
        
        # 设置X轴日期格式（如果是日期）
        if pd.api.types.is_datetime64_any_dtype(data[x_column]):
            date_range = (data[x_column].max() - data[x_column].min()).days
            
            if date_range <= 14:  # 两周以内显示天
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                plt.gca().xaxis.set_major_locator(mdates.DayLocator())
            elif date_range <= 180:  # 半年以内显示周
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
            else:  # 更长时间显示月
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
                
            plt.gcf().autofmt_xdate()
            
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或返回图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        if show:
            plt.show()
            
        # 将图表转换为二进制数据
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', dpi=100, bbox_inches='tight')
        img_data.seek(0)
        
        plt.close()
        
        return img_data.getvalue()
        
    except Exception as e:
        logger.error(f"创建折线图失败: {str(e)}")
        plt.close()
        return None

def create_heatmap(data, x_column, y_column, value_column, title=None, 
                  xlabel=None, ylabel=None, cmap='YlOrRd', figsize=(12, 8), 
                  save_path=None, show=False):
    """
    创建热力图
    
    Args:
        data: DataFrame数据
        x_column: X轴列名
        y_column: Y轴列名
        value_column: 值列名
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        cmap: 颜色映射
        figsize: 图表尺寸
        save_path: 保存路径
        show: 是否显示图表
        
    Returns:
        bytes或None: 图表二进制数据或None
    """
    try:
        if data.empty:
            logger.warning("数据为空，无法创建热力图")
            return None
            
        # 将数据转换为热力图格式
        pivot_data = data.pivot(index=y_column, columns=x_column, values=value_column)
        
        plt.figure(figsize=figsize)
        
        # 绘制热力图
        ax = sns.heatmap(pivot_data, cmap=cmap, annot=True, fmt=".1f", linewidths=.5)
        
        # 设置标题和标签
        if title:
            plt.title(title, fontproperties=chinese_font, fontsize=14)
        if xlabel:
            plt.xlabel(xlabel, fontproperties=chinese_font, fontsize=12)
        if ylabel:
            plt.ylabel(ylabel, fontproperties=chinese_font, fontsize=12)
            
        # 设置刻度标签字体
        plt.xticks(fontproperties=chinese_font, fontsize=10, rotation=45)
        plt.yticks(fontproperties=chinese_font, fontsize=10)
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或返回图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        if show:
            plt.show()
            
        # 将图表转换为二进制数据
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', dpi=100, bbox_inches='tight')
        img_data.seek(0)
        
        plt.close()
        
        return img_data.getvalue()
        
    except Exception as e:
        logger.error(f"创建热力图失败: {str(e)}")
        plt.close()
        return None

def create_pie_chart(data, labels, values, title=None, colors=None, 
                    figsize=(8, 8), save_path=None, show=False, autopct='%1.1f%%'):
    """
    创建饼图
    
    Args:
        data: DataFrame数据
        labels: 标签列名或标签列表
        values: 值列名或值列表
        title: 图表标题
        colors: 颜色列表
        figsize: 图表尺寸
        save_path: 保存路径
        show: 是否显示图表
        autopct: 百分比格式
        
    Returns:
        bytes或None: 图表二进制数据或None
    """
    try:
        plt.figure(figsize=figsize)
        
        # 获取标签和值
        if isinstance(labels, str) and isinstance(values, str):
            if data.empty:
                logger.warning("数据为空，无法创建饼图")
                return None
            label_data = data[labels]
            value_data = data[values]
        else:
            label_data = labels
            value_data = values
            
        # 绘制饼图
        plt.pie(value_data, labels=label_data, autopct=autopct, startangle=90, 
                shadow=False, colors=colors)
        
        # 设置标题
        if title:
            plt.title(title, fontproperties=chinese_font, fontsize=14)
            
        # 等比例显示
        plt.axis('equal')
        
        # 自动调整布局
        plt.tight_layout()
        
        # 保存或返回图表
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            
        if show:
            plt.show()
            
        # 将图表转换为二进制数据
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png', dpi=100, bbox_inches='tight')
        img_data.seek(0)
        
        plt.close()
        
        return img_data.getvalue()
        
    except Exception as e:
        logger.error(f"创建饼图失败: {str(e)}")
        plt.close()
        return None 