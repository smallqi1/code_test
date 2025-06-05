# 广东省空气质量监测与预测系统

## 目录
- [项目概述](#项目概述)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [核心功能](#核心功能)
- [项目结构](#项目结构)
- [数据库设计](#数据库设计)
- [机器学习模型](#机器学习模型)
- [安装与部署](#安装与部署)
- [API接口](#api接口)
- [常见问题](#常见问题)

## 项目概述

本系统是一个用于监测、分析和预测广东省空气质量的综合平台，结合历史数据分析和LSTM深度学习模型预测，通过直观的可视化界面展示实时监测、历史趋势和未来预测结果。系统采用前后端分离设计，支持广东省21个城市的空气质量数据管理。

### 特色亮点

- **实时监测**: 地图与图表展示21个城市实时空气质量状况
- **数据分析**: 多维度分析历史数据，支持城市间、时间段间对比
- **智能预测**: 基于LSTM模型提供短期(3天)、中期(7天)和长期(14天)预测
- **响应式设计**: 支持从桌面到移动设备的全尺寸显示
- **多服务架构**: 分离的API服务提高系统性能和可扩展性

## 系统架构

系统采用前后端分离的多层次架构设计：

```
+------------------------+
|   前端应用层(Vue 3)     |
|------------------------|
| - 仪表盘页面           |
| - 历史数据分析页面     |
| - 智能预测页面         |
| - 趋势分析页面         |
| - 报告生成页面         |
+------------------------+
           |  HTTP请求
           v
+------------------------+
|   API服务层(Flask)     |
|------------------------|
| - 历史数据API(5000端口)|
| - 实时数据API(5001端口)|
| - 预测数据API(5002端口)|
+------------------------+
           |
           v
+------------------------+
|     业务处理层         |
|------------------------|
| - 数据采集与清洗       |
| - 数据分析与统计       |
| - LSTM模型训练         |
| - 预测逻辑实现         |
+------------------------+
           |
           v
+------------------------+
|     数据持久层         |
|------------------------|
| - MySQL数据库          |
| - 训练模型文件存储     |
| - 原始数据与处理数据   |
+------------------------+
           |
           v
+------------------------+
|     硬件基础层         |
|------------------------|
| - 服务器硬件           |
| - 操作系统             |
| - 网络基础设施         |
+------------------------+
```

### 数据流

1. **前端应用层**: 提供用户界面，通过HTTP请求与后端API交互
2. **API服务层**: 提供历史数据、实时数据和预测数据的API服务
3. **业务处理层**: 负责数据处理、分析与模型训练
4. **数据持久层**: 存储历史和实时数据，以及训练好的模型
5. **硬件基础层**: 提供系统运行的硬件和网络基础设施

## 技术栈

### 前端
- **核心框架**: Vue 3 (Composition API)
- **状态管理**: Pinia 2.x
- **UI框架**: Element Plus, Vuetify
- **数据可视化**: Chart.js, ECharts
- **构建工具**: Vite

### 后端
- **Web框架**: Flask 2.0.3
- **数据库**: MySQL 8.0.33
- **数据处理**: pandas, numpy
- **机器学习**: TensorFlow/Keras, scikit-learn, LSTM模型
- **多服务协同**: multiprocessing

## 核心功能

### 1. 实时监测
- 基于ECharts地图组件展示广东省空气质量分布
- 提供AQI、PM2.5、PM10、SO2、NO2、CO、O3等多种指标监测
- 色彩区分不同空气质量等级，支持城市排名

### 2. 历史数据分析
- 支持多维度筛选(城市、时间、指标)的历史数据查询
- 动态生成趋势图表，支持多城市多指标对比
- 提供数据导出功能，方便进一步分析

### 3. 智能预测
- 每个城市每种指标单独训练LSTM模型
- 支持短期、中期和长期预测
- 展示预测置信区间，评估预测可靠性
- 支持不同城市间预测结果对比

## 项目结构

```
.
├── frontend/                    # 前端(Vue 3 + Vite)
│   ├── src/                     # 源代码
│   │   ├── assets/              # 静态资源文件
│   │   ├── components/          # 通用组件
│   │   ├── views/               # 页面组件
│   │   ├── router/              # 路由配置
│   │   ├── store/               # Pinia状态管理
│   │   ├── services/            # API服务封装
│   │   ├── utils/               # 工具函数
│   │   ├── App.vue              # 主应用组件
│   │   └── main.js              # 入口文件
│
├── backend/                     # 后端(Python Flask)
│   ├── src/                     # 源代码
│   │   ├── scripts/             # 核心脚本
│   │   │   ├── api/             # API接口实现
│   │   │   ├── model_train/     # 模型训练脚本
│   │   │   ├── process/         # 数据处理脚本
│   │   │   └── sql/             # 数据库操作脚本
│   │   └── app.py               # Flask应用入口
│   ├── logs/                    # 日志文件
│   └── requirements.txt         # Python依赖包
│
└── data/                        # 数据目录
    ├── models/                  # 模型文件存储
    └── air_data/                # 空气质量数据
```

## 数据库设计

系统使用MySQL存储空气质量数据，主要包含以下表：

### 空气质量数据表 (air_quality_data)
存储历史空气质量数据，包括城市、日期、AQI指数、PM2.5、PM10等污染物浓度。

### 实时空气质量数据表 (air_quality_newdata)
存储实时采集的最新数据，结构与历史表一致，定期整合到历史表。

### 数据导入日志表 (import_logs)
记录数据导入操作详情，包括文件名、记录数量、导入时间和状态。

## 机器学习模型

系统使用LSTM深度学习模型进行空气质量预测：

### 模型架构
```python
def create_lstm_model(input_shape, output_shape):
    model = Sequential()
    model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(32))
    model.add(Dropout(0.2))
    model.add(Dense(output_shape))
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model
```

### 数据预处理
- 使用MinMaxScaler标准化数据
- 采用滑动窗口技术创建时间序列特征
- 训练集和测试集按8:2分割

### 模型训练与评估
- 每个城市每种污染物指标单独训练模型
- 使用早停(Early Stopping)防止过拟合
- 通过MSE和MAE评估模型性能

## 安装与部署

### 系统要求
- **操作系统**: Windows 10/11, Linux, macOS
- **内存**: 推荐8GB以上
- **软件依赖**: Node.js 16+, Python 3.8.10+, MySQL 8.0+

### 前端部署
```bash
# 安装依赖
cd frontend
npm install

# 配置环境变量
cp .env.example .env
# 编辑.env文件，设置API地址

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

### 后端部署
```bash
# 创建并激活虚拟环境
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置数据库
# 编辑 src/scripts/sql/config.py

# 启动服务
python start_server.py
```

## API接口

系统提供三种API服务：

### 1. 历史数据API (端口:5000)
- `GET /api/health` - 健康检查
- `GET /api/cities` - 获取城市列表
- `GET /api/historical` - 获取历史数据
- `GET /api/stats` - 获取统计数据

### 2. 实时数据API (端口:5001)
- `GET /api/health` - 健康检查
- `GET /api/realtime` - 获取最新数据
- `GET /api/rank` - 获取排名数据

### 3. 预测数据API (端口:5002)
- `GET /api/health` - 健康检查
- `GET /api/forecast` - 获取预测数据
- `GET /api/forecast/multi` - 获取多城市预测

## 常见问题

### 数据库连接问题
检查数据库配置(src/scripts/sql/config.py)，确保MySQL服务运行正常。

### 数据更新问题
系统默认每6小时更新一次数据。可手动触发更新：
```bash
python src/scripts/process/new_stage/download_data_process.py
```

### 预测模型问题
对于新城市或数据缺失严重的城市，需重新训练模型：
```bash
python src/scripts/model_train/train_model.py --city 城市名
```

## 关键代码示例

以下是系统各个关键功能模块的核心伪代码：

### 用户认证模块

#### 用户注册
```
function register(username, email, password):
    // 验证输入数据格式
    if !isValidEmail(email) or !isValidPassword(password):
        return error("格式不正确")
    
    // 检查用户名和邮箱唯一性
    if userExists(username) or emailExists(email):
        return error("用户名或邮箱已存在")
    
    // 哈希密码并创建用户
    passwordHash = hashPassword(password)
    userId = createUser(username, email, passwordHash)
    
    // 创建令牌并返回
    token = createJwtToken(userId, username, "user")
    return success(token)
```

#### 用户登录
```
function login(usernameOrEmail, password):
    // 查询用户信息
    user = findUserByUsernameOrEmail(usernameOrEmail)
    if !user:
        return error("用户名或密码错误")
    
    // 验证密码
    if !verifyPassword(password, user.passwordHash):
        return error("用户名或密码错误")
    
    // 创建令牌并返回
    token = createJwtToken(user.id, user.username, user.role)
    return success(token)
```

#### 密保问题设置
```
function setupSecurityQuestions(userId, questions):
    // 验证问题格式
    if questions.length != 3:
        return error("请选择3个密保问题及答案")
    
    // 存储密保问题
    saveSecurityQuestions(userId, questions)
    return success("密保问题设置成功")
```

#### 密码重置
```
function resetPassword(userId, token, newPassword):
    // 验证令牌
    if !isValidToken(userId, token):
        return error("令牌无效")
    
    // 验证令牌是否过期
    if isTokenExpired(token):
        return error("令牌已过期")
    
    // 更新密码
    updatePassword(userId, hashPassword(newPassword))
    clearResetToken(userId)
    
    return success("密码重置成功")
```

### 用户权限模块

#### 角色定义
```
// 用户角色常量
ROLE_SUPER_ADMIN = "super_admin"  // 超级管理者
ROLE_ADMIN = "admin"              // 管理员
ROLE_USER = "user"                // 普通用户
MAX_ADMIN_COUNT = 5               // 管理员数量上限
```

#### 权限分级查看用户
```
function getAllUsers(currentRole):
    if currentRole == ROLE_SUPER_ADMIN:
        // 超级管理者可以看到所有用户
        return queryAllUsers()
    else:
        // 普通管理员只能看到普通用户
        return queryRegularUsers()
```

#### 用户封禁功能(管理员)
```
function updateUserStatus(adminId, targetUserId, newStatus):
    // 权限检查
    if !isAdmin(adminId):
        return error("权限不足")
    
    targetUser = getUserById(targetUserId)
    
    // 普通管理员不能管理其他管理员
    if isAdmin(targetUserId) && !isSuperAdmin(adminId):
        return error("普通管理员不能管理其他管理员")
    
    // 更新用户状态
    setUserStatus(targetUserId, newStatus)
    return success("用户状态已更新")
```

#### 管理员任命与撤销(超级管理员)
```
function updateUserRole(adminId, targetUserId, newRole):
    // 只有超级管理员可执行
    if !isSuperAdmin(adminId):
        return error("权限不足")
    
    // 提升为管理员时检查数量上限
    if newRole == ROLE_ADMIN:
        if getAdminCount() >= MAX_ADMIN_COUNT:
            return error("管理员数量已达上限")
    
    // 执行角色修改
    setUserRole(targetUserId, newRole)
    return success("用户角色已更新")
```

#### 权限验证中间件
```
function authMiddleware(request, requiredRole = null):
    // 1. 获取请求头中的令牌
    token = extractTokenFromHeader(request)
    if !token:
        return error("未提供认证令牌", 401)
    
    // 2. 验证令牌有效性
    payload = verifyJwtToken(token)
    if !payload:
        return error("令牌无效或已过期", 401)
    
    // 3. 检查用户账号状态
    user = getUserById(payload.userId)
    if !user:
        return error("用户不存在", 404)
    
    if user.status != "active":
        return error("账号已被禁用", 403)
    
    // 4. 权限级别检查
    if requiredRole:
        if requiredRole == ROLE_SUPER_ADMIN && user.role != ROLE_SUPER_ADMIN:
            return error("需要超级管理员权限", 403)
        
        if requiredRole == ROLE_ADMIN && 
           user.role != ROLE_ADMIN && 
           user.role != ROLE_SUPER_ADMIN:
            return error("需要管理员权限", 403)
    
    // 5. 在请求中附加用户信息
    request.user = {
        id: user.id,
        username: user.username,
        role: user.role,
        isSuperAdmin: (user.role == ROLE_SUPER_ADMIN),
        isAdmin: (user.role == ROLE_ADMIN || user.role == ROLE_SUPER_ADMIN)
    }
    
    // 继续处理请求
    return next()
```

#### 资源访问控制
```
function checkResourceAccess(userId, resourceType, resourceId, action):
    // 获取用户角色
    user = getUserById(userId)
    if !user:
        return false
    
    // 超级管理员拥有所有权限
    if user.role == ROLE_SUPER_ADMIN:
        return true
    
    // 资源类型权限控制
    switch(resourceType):
        case "report":
            // 报表资源权限控制
            return checkReportAccess(user, resourceId, action)
            
        case "forecast":
            // 预测数据权限控制
            return checkForecastAccess(user, resourceId, action)
            
        case "user":
            // 用户数据权限控制
            if action == "view" && user.role == ROLE_ADMIN:
                targetUser = getUserById(resourceId)
                // 管理员只能查看普通用户信息
                return targetUser && targetUser.role == ROLE_USER
            return false
            
        case "system_settings":
            // 系统设置权限控制
            return user.role == ROLE_SUPER_ADMIN
            
        case "air_data":
            // 空气质量数据权限控制
            if action == "view":
                return true  // 所有用户可查看
            else if action == "export":
                return true  // 所有用户可导出
            else if action == "edit" || action == "delete":
                return user.role == ROLE_ADMIN || user.role == ROLE_SUPER_ADMIN
            
        default:
            return false
```

### 实时数据监测模块

```
function getRealTimeMonitoringData():
    // 获取所有城市最新空气质量数据
    cityDataMap = {}
    
    // 1. 从传感器API获取广东省21个城市实时数据
    rawData = fetchSensorApiData()
    
    // 2. 数据清洗与标准化处理
    for each record in rawData:
        validateAndStandardize(record)
        
        // 计算AQI指数和空气质量等级
        if !record.aqi:
            record.aqi = calculateAQI(record.pm25, record.pm10, record.so2, record.no2, record.co, record.o3)
        
        record.level = determineAirQualityLevel(record.aqi)
        record.mainPollutant = identifyMainPollutant(record)
        
        // 保存城市最新数据
        cityDataMap[record.city] = record
    
    // 3. 污染预警分析
    for each city, data in cityDataMap:
        if data.aqi > 200:  // 重度污染
            generateAlert(city, data, "重度污染预警")
        else if data.aqi > 150:  // 中度污染
            generateAlert(city, data, "中度污染预警")
            
    // 4. 整合GIS地理数据进行可视化
    geoData = {
        "type": "FeatureCollection",
        "features": []
    }
    
    for each city, data in cityDataMap:
        // 获取城市GIS坐标
        coordinates = getCityGeoCoordinates(city)
        
        // 添加到GeoJSON
        geoData.features.push({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": coordinates
            },
            "properties": {
                "city": city,
                "aqi": data.aqi,
                "level": data.level,
                "mainPollutant": data.mainPollutant,
                "pm25": data.pm25,
                "colorCode": getColorByAQI(data.aqi)
            }
        })
    
    // 5. 保存实时数据到数据库
    storeRealTimeData(cityDataMap.values())
    
    // 返回处理后的完整数据
    return {
        "timestamp": getCurrentTimestamp(),
        "cityData": cityDataMap.values(),
        "geoData": geoData,
        "warningCities": getWarningCities()
    }
```

### 历史数据分析模块

```
function getHistoricalData(city, startDate, endDate, indicators):
    // 构建查询条件
    query = "基础查询"
    params = []
    
    if city:
        query += "添加城市筛选条件"
        params.append(city)
    if startDate:
        query += "添加开始日期筛选条件"
        params.append(startDate)
    if endDate:
        query += "添加结束日期筛选条件"
        params.append(endDate)
    
    // 执行查询
    results = executeQuery(query, params)
    
    // 处理结果
    formattedData = []
    for each row in results:
        dataPoint = {city: row.city, date: row.date}
        for each indicator in indicators:
            if indicator in row:
                dataPoint[indicator] = row[indicator]
        formattedData.append(dataPoint)
    
    return success(formattedData)
```

### 智能预测模块

```
function createLstmModel():
    model = Sequential()
    model.add(LSTM(64, returnSequences=true))
    model.add(Dropout(0.2))
    model.add(LSTM(32))
    model.add(Dropout(0.2))
    model.add(Dense(outputShape))
    model.compile(optimizer="adam", loss="mse")
    return model

function getForecast(city, days, indicator):
    // 加载预训练模型
    model = loadModel(f"{city}_{indicator}_model")
    
    // 获取最近历史数据作为输入
    recentData = getRecentData(city, indicator, 14)
    
    // 准备输入数据
    inputData = processDataForModel(recentData)
    
    // 使用模型预测
    prediction = model.predict(inputData)[0][:days]
    
    // 生成预测日期和结果
    forecastData = []
    lastDate = recentData[0].date
    
    for i in range(days):
        forecastDate = lastDate + (i+1) days
        forecastData.append({
            date: forecastDate,
            value: prediction[i]
        })
    
    return success({
        city: city,
        indicator: indicator,
        data: forecastData
    })
```
