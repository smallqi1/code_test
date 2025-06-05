# 广东省空气质量数据库文档

## 数据概述

本数据库存储了2014年至2025年广东省各城市的空气质量监测数据。数据来源于 `D:/CODE/data/air_data/processed/stage3` 目录下的CSV文件，经过导入处理后存储在MySQL数据库中。

## 数据库信息

- **数据库名称**: `air_quality_monitoring`
- **字符集**: `utf8mb4`
- **排序规则**: `utf8mb4_general_ci`

## 表结构

### 1. 空气质量数据表 (air_quality_data)

该表存储所有城市的空气质量监测数据。

| 字段名 | 数据类型 | 描述 | 备注 |
|--------|---------|------|------|
| id | INT | 自增主键 | AUTO_INCREMENT |
| city | VARCHAR(50) | 城市名称 | 非空，例如：广州市、深圳市 |
| province | VARCHAR(50) | 省份名称 | 非空，例如：广东省 |
| record_date | DATE | 记录日期 | 非空，格式：YYYY-MM-DD |
| aqi_index | FLOAT | 空气质量指数 | AQI值 |
| quality_level | VARCHAR(20) | 空气质量等级 | 优、良、轻度污染、中度污染、重度污染、严重污染 |
| aqi_rank | FLOAT | AQI排名 | 省内排名 |
| pm25_avg | FLOAT | PM2.5日均浓度 | 单位：μg/m³ |
| pm10_avg | FLOAT | PM10日均浓度 | 单位：μg/m³ |
| so2_avg | FLOAT | 二氧化硫日均浓度 | 单位：μg/m³ |
| no2_avg | FLOAT | 二氧化氮日均浓度 | 单位：μg/m³ |
| co_avg | FLOAT | 一氧化碳日均浓度 | 单位：mg/m³ |
| o3_avg | FLOAT | 臭氧日均浓度 | 单位：μg/m³ |
| data_year | INT | 数据所属年份 | 用于快速筛选特定年份数据 |
| created_at | TIMESTAMP | 数据创建时间 | 默认为当前时间戳 |

**索引**:
- `PRIMARY KEY`: id
- `INDEX idx_city`: city - 城市名索引，用于快速按城市查询
- `INDEX idx_date`: record_date - 日期索引，用于日期范围查询
- `INDEX idx_year`: data_year - 年份索引，用于年度数据查询
- `UNIQUE KEY uc_city_date`: (city, record_date) - 确保每个城市每天只有一条记录

### 2. 导入日志表 (import_logs)

该表记录数据导入的历史记录和结果。

| 字段名 | 数据类型 | 描述 | 备注 |
|--------|---------|------|------|
| id | INT | 自增主键 | AUTO_INCREMENT |
| filename | VARCHAR(255) | 导入的文件名 | 非空 |
| records_count | INT | 导入的记录数量 | 非空 |
| import_date | TIMESTAMP | 导入日期时间 | 默认为当前时间戳 |
| status | VARCHAR(20) | 导入状态 | SUCCESS, PARTIAL, FAILED |
| message | TEXT | 导入结果消息 | 包含详细的导入结果信息 |

## 数据字典

### 空气质量指数(AQI)等级对照表

| AQI范围 | 空气质量等级 | 对健康影响 |
|---------|------------|----------|
| 0-50 | 优 | 空气质量令人满意，基本无空气污染 |
| 51-100 | 良 | 空气质量可接受，但某些污染物可能对极少数异常敏感人群健康有较弱影响 |
| 101-150 | 轻度污染 | 敏感人群症状有轻度加剧，健康人群出现刺激症状 |
| 151-200 | 中度污染 | 进一步加剧敏感人群症状，可能对健康人群心脏、呼吸系统有影响 |
| 201-300 | 重度污染 | 健康人群运动耐受力降低，有明显强烈症状，提前出现某些疾病 |
| >300 | 严重污染 | 健康人群运动耐受力降低，有明显强烈症状，提前出现某些疾病 |

### 主要污染物说明

- **PM2.5**: 细颗粒物，粒径小于等于2.5微米的颗粒物
- **PM10**: 可吸入颗粒物，粒径小于等于10微米的颗粒物
- **SO2**: 二氧化硫
- **NO2**: 二氧化氮
- **CO**: 一氧化碳
- **O3**: 臭氧

## 数据覆盖范围

- **时间范围**: 2014年至2025年
- **城市范围**: 广东省21个地级市，包括广州、深圳、珠海、汕头、佛山、韶关、湛江、肇庆、江门、茂名、惠州、梅州、汕尾、河源、阳江、清远、东莞、中山、潮州、揭阳、云浮

## 数据用途

此数据库可用于：

1. **实时空气质量监测**: 展示当前和历史空气质量状况
2. **趋势分析**: 分析空气质量的长期变化趋势和季节性变化
3. **城市空气质量比较**: 对比不同城市的空气质量状况
4. **污染物相关性研究**: 研究不同污染物之间的相关性
5. **预测模型训练**: 为空气质量预测模型提供训练数据

## 数据导入脚本

数据通过`backend/src/scripts/import_air_data.py`脚本导入，该脚本会自动创建数据库和表结构，并将CSV文件中的数据导入到数据库中。

### 导入流程

1. 检查并创建数据库和表结构
2. 读取指定目录下的所有空气质量CSV文件
3. 解析CSV数据并批量导入到数据库
4. 记录导入日志和导入结果

### 导入命令示例

```bash
# 安装所需依赖
pip install mysql-connector-python

# 运行导入脚本
cd backend/src/scripts
python import_air_data.py
```

## 查询示例

### 1. 获取特定城市最近30天的空气质量数据

```sql
SELECT 
    city, record_date, aqi_index, quality_level, 
    pm25_avg, pm10_avg
FROM 
    air_quality_data
WHERE 
    city = '广州市' 
    AND record_date >= CURDATE() - INTERVAL 30 DAY
ORDER BY 
    record_date DESC;
```

### 2. 计算各城市2023年AQI平均值并排名

```sql
SELECT 
    city, 
    AVG(aqi_index) as avg_aqi,
    AVG(pm25_avg) as avg_pm25,
    AVG(pm10_avg) as avg_pm10
FROM 
    air_quality_data
WHERE 
    data_year = 2023
GROUP BY 
    city
ORDER BY 
    avg_aqi ASC;
```

### 3. 分析广州市空气质量年度变化趋势

```sql
SELECT 
    data_year,
    AVG(aqi_index) as avg_aqi,
    AVG(pm25_avg) as avg_pm25,
    AVG(pm10_avg) as avg_pm10,
    AVG(so2_avg) as avg_so2,
    AVG(no2_avg) as avg_no2,
    AVG(o3_avg) as avg_o3
FROM 
    air_quality_data
WHERE 
    city = '广州市'
GROUP BY 
    data_year
ORDER BY 
    data_year ASC;
```

## 注意事项

1. 数据库包含部分预测数据（2024-2025年），这些数据可能与实际情况有偏差
2. 建议定期对数据库进行备份，特别是在导入新数据之前
3. 对于大量数据查询，建议使用分页查询以提高性能
4. 对于时间序列分析，可考虑按月或按季度对数据进行聚合，以减少数据量并提高查询性能 