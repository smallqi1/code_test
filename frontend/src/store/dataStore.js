import { defineStore } from 'pinia'
import axios from 'axios'
import { ref, computed } from 'vue'
import { getAqiLevelName, getAqiLevel } from '@/utils/aqi'

/**
 * API基础URL配置，从环境变量获取
 * 在.env文件中通过VITE_API_BASE_URL设置
 * 例如: VITE_API_BASE_URL=http://api.example.com
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const REALTIME_API_BASE_URL = import.meta.env.VITE_REALTIME_API_BASE_URL || 'http://localhost:5001'

// 配置两种不同的axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL
})

const realtimeApiClient = axios.create({
  baseURL: REALTIME_API_BASE_URL
})

// 添加数据缓存过期时间设置（单位：毫秒）
const CACHE_TTL = {
  PROVINCE_DATA: 5 * 60 * 1000, // 5分钟
  REALTIME_DATA: 10 * 60 * 1000, // 10分钟
  HISTORICAL_DATA: 60 * 60 * 1000, // 1小时
  PREDICTION_DATA: 60 * 60 * 1000, // 1小时
  ALERTS: 5 * 60 * 1000 // 5分钟
}

// 日志级别控制
const LOG_LEVEL = {
  NONE: 0,   // 不输出任何日志
  ERROR: 1,  // 只输出错误
  INFO: 2,   // 输出信息和错误
  DEBUG: 3,  // 输出所有包括调试信息
  VERBOSE: 4 // 输出全部详细信息
}

// 当前日志级别设置 - 设置为ERROR级别，减少INFO级别日志
const currentLogLevel = LOG_LEVEL.ERROR;

// 日志输出方法
const log = {
  error: (message) => {
    if (currentLogLevel >= LOG_LEVEL.ERROR) {
      console.error(`[数据存储] ${message}`);
    }
  },
  info: (message) => {
    if (currentLogLevel >= LOG_LEVEL.INFO) {
      console.info(`[数据存储] ${message}`);
    }
  },
  debug: (message) => {
    if (currentLogLevel >= LOG_LEVEL.DEBUG) {
      console.log(`[数据存储] ${message}`);
    }
  },
  verbose: (message) => {
    if (currentLogLevel >= LOG_LEVEL.VERBOSE) {
      console.log(`[数据存储] [详细] ${message}`);
    }
  }
}

export const useDataStore = defineStore('data', {
  state: () => ({
    realTimeData: {
      loading: false,
      error: null,
      cityData: {},
      provinceData: [],
      lastUpdated: null
    },
    historicalData: {
      loading: false,
      error: null,
      data: [],
      timeRange: {
        start: null,
        end: null
      },
      lastUpdated: null
    },
    predictionData: {
      loading: false,
      error: null,
      data: [],
      generatedAt: null,
      lastUpdated: null
    },
    alerts: {
      loading: false,
      error: null,
      items: [],
      unreadCount: 0,
      lastUpdated: null
    },
    isProvinceLoading: false,
    provinceError: null,
    provinceData: [],
    lastProvinceDataFetch: null,
    airQualityData: [],
    stats: {
      totalCities: 0,
      goodQuality: 0,
      lightPollution: 0,
      heavyPollution: 0
    },
    lastUpdateTime: null,
    // 加载中占位数据，用于UI展示
    loadingPlaceholders: {
      provinceCities: false,
      alerts: false
    }
  }),
  
  getters: {
    getCurrentData: (state) => (cityName) => {
      if (!cityName) {
        return {}; // 如果没有提供城市名，返回空对象
      }
      
      const cityData = state.realTimeData.cityData[cityName];
      if (!cityData) {
        log.info(`没有找到${cityName}的数据，返回空对象`);
        return {}; // 返回空对象而不是null
      }
      
      return cityData;
    },
    
    getProvinceData: (state) => {
      return state.realTimeData.provinceData
    },
    
    getHistoricalData: (state) => {
      return state.historicalData.data
    },
    
    getPredictionData: (state) => {
      return state.predictionData.data
    },
    
    getAlerts: (state) => {
      return state.alerts.items
    },
    
    getUnreadAlertCount: (state) => {
      return state.alerts.unreadCount
    },
    
    getAirQualityData: (state) => {
      return state.airQualityData
    },

    // 添加缓存状态检查getter
    isProvinceCacheValid: (state) => {
      if (!state.realTimeData.lastUpdated || !state.realTimeData.provinceData || state.realTimeData.provinceData.length === 0) {
        return false;
      }
      const now = new Date().getTime();
      const lastUpdate = new Date(state.realTimeData.lastUpdated).getTime();
      return (now - lastUpdate) < CACHE_TTL.PROVINCE_DATA;
    },

    isCityDataCacheValid: (state) => (cityName) => {
      const cityData = state.realTimeData.cityData[cityName];
      if (!cityData || !state.realTimeData.lastUpdated) {
        return false;
      }
      const now = new Date().getTime();
      const lastUpdate = new Date(state.realTimeData.lastUpdated).getTime();
      return (now - lastUpdate) < CACHE_TTL.REALTIME_DATA;
    }
  },
  
  actions: {
    /**
     * 获取指定城市的实时空气质量数据
     * @param {string} cityName - 城市名称，默认为"广州"
     * @returns {Promise<Object>} - 返回城市实时空气质量数据
     * 
     * API接口: GET /api/realtime/{cityName}
     * 示例: /api/realtime/广州
     */
    async fetchRealTimeData(cityName = '广州市') {
      // 检查缓存
      if (this.isCityDataCacheValid(cityName)) {
        log.info(`使用缓存的${cityName}实时数据`);
        return this.realTimeData.cityData[cityName];
      }

      this.realTimeData.loading = true;
      this.realTimeData.error = null;
      
      try {
        const response = await realtimeApiClient.get(`/api/realtime/${cityName}`);
        
        if (!response.data) {
          throw new Error('暂无数据');
        }
        
        // 规范化数据字段，确保与省级数据字段一致
        const data = {
          ...response.data,
          // 确保两种格式的字段都存在
          name: cityName,
          pm25: Number(response.data.pm25 || response.data.pm2_5 || 0),
          pm2_5: Number(response.data.pm25 || response.data.pm2_5 || 0),
          pm10: Number(response.data.pm10 || 0),
          so2: Number(response.data.so2 || 0),
          no2: Number(response.data.no2 || 0),
          o3: Number(response.data.o3 || 0),
          co: Number(response.data.co || 0),
          aqi: Number(response.data.aqi || 0),
          level: response.data.level || this.getAqiLevel(Number(response.data.aqi || 0)),
          update_time: response.data.update_time || new Date().toISOString()
        };
        
        this.realTimeData.cityData[cityName] = data;
        this.realTimeData.lastUpdated = new Date().toISOString();
        this.realTimeData.loading = false;
        
        return data;
      } catch (error) {
        log.error(`获取${cityName}实时数据失败:`, error);
        this.realTimeData.error = error.message || '获取数据失败，请稍后重试';
        this.realTimeData.loading = false;
        throw error;
      }
    },
    
    /**
     * 获取全省各城市的空气质量数据
     * @returns {Promise<Array>} - 返回省内所有城市的空气质量数据数组
     * 
     * API接口: GET /api/province
     */
    async fetchProvinceData() {
      // 检查缓存
      if (this.isProvinceCacheValid) {
        log.info('使用缓存的省份数据');
        return this.provinceData;
      }

      // 确保stats永远有效，即使在加载失败的情况下
      if (!this.stats || typeof this.stats !== 'object') {
        this.stats = {
          totalCities: 0,
          goodQuality: 0,
          lightPollution: 0,
          heavyPollution: 0
        };
      }

      this.isProvinceLoading = true;
      this.provinceError = null;
      
      try {
        const response = await realtimeApiClient.get('/api/province');
        
        // 检查响应格式，处理包含status、message和data的标准格式
        if (response.data && response.data.status === 'success' && response.data.data) {
          // 如果data中有cities数组，使用cities数组
          const citiesData = response.data.data.cities || response.data.data;
          
          if (!Array.isArray(citiesData)) {
            throw new Error('无效的省份数据格式，期望数组但收到: ' + typeof citiesData);
          }
          
          // 如果数据为空数组，也抛出错误
          if (citiesData.length === 0) {
            throw new Error('省份数据为空');
          }
          
          // 确保AQI是数字类型
          this.provinceData = citiesData.map(city => {
            // 转换AQI为数字
            let aqi = Number(city.aqi_index || city.aqi);
            
            // 如果AQI值无效或为0，设置一个默认值
            if (isNaN(aqi) || aqi <= 0) {
              aqi = 50; // 设置默认值确保地图显示颜色
            }
            
            return {
              ...city, // 保留原始数据的所有字段
              aqi: aqi, // 更新AQI为数字
              level: city.aqi_category || city.level || this.getAqiLevel(aqi)
            };
          });
        } else if (Array.isArray(response.data)) {
          // 兼容旧版API直接返回数组的情况
          if (response.data.length === 0) {
            throw new Error('省份数据为空');
          }
          
          this.provinceData = response.data.map(city => {
            let aqi = Number(city.aqi_index || city.aqi);
            if (isNaN(aqi) || aqi <= 0) {
              aqi = 50;
            }
            return {
              ...city,
              aqi: aqi,
              level: city.aqi_category || city.level || this.getAqiLevel(aqi)
            };
          });
        } else {
          throw new Error('无效的省份数据格式: ' + JSON.stringify(response.data).substring(0, 100) + '...');
        }
        
        // 更新统计数据
        this.calculateStats(this.provinceData);
        this.lastUpdateTime = Date.now();
        this.lastProvinceDataFetch = new Date().getTime();
      } catch (error) {
        log.error('获取省份数据失败:', error);
        this.provinceError = `获取数据失败: ${error.message}`;
        
        // 即使加载失败，也确保stats有效初始化
        this.calculateStats([]);
      } finally {
        this.isProvinceLoading = false;
      }
      
      return this.provinceData;
    },
    
    /**
     * 获取指定城市在指定时间范围内的历史空气质量数据
     * @param {string} cityName - 城市名称
     * @param {string} startDate - 开始日期，格式为YYYY-MM-DD
     * @param {string} endDate - 结束日期，格式为YYYY-MM-DD
     * @returns {Promise<Array>} - 返回历史数据数组
     * 
     * API接口: GET /api/historical/{cityName}?start_date={startDate}&end_date={endDate}
     * 示例: /api/historical/广州?start_date=2023-01-01&end_date=2023-01-07
     */
    async fetchHistoricalData(cityName, startDate, endDate) {
      this.historicalData.loading = true
      this.historicalData.error = null
      
      try {
        const response = await apiClient.get(`/api/historical/${cityName}`, {
          params: {
            start_date: startDate,
            end_date: endDate
          }
        })
        
        if (!response.data) {
          throw new Error('暂无数据')
        }
        
        this.historicalData.data = response.data
        this.historicalData.timeRange = { start: startDate, end: endDate }
        this.historicalData.loading = false
        
        return response.data
      } catch (error) {
        log.error('获取历史数据失败:', error)
        this.historicalData.error = error.message || '获取数据失败，请稍后重试'
        this.historicalData.loading = false
        throw error
      }
    },
    
    /**
     * 获取指定城市未来几天的空气质量预测数据
     * @param {string} cityName - 城市名称
     * @param {number} days - 预测天数，默认为7天
     * @returns {Promise<Array>} - 返回预测数据数组
     * 
     * API接口: GET /api/prediction/{cityName}?days={days}
     * 示例: /api/prediction/广州?days=7
     */
    async fetchPredictionData(cityName, days = 7) {
      this.predictionData.loading = true
      this.predictionData.error = null
      
      try {
        const response = await apiClient.get(`/api/prediction/${cityName}`, {
          params: {
            days: days
          }
        })
        
        if (!response.data) {
          throw new Error('暂无数据')
        }
        
        this.predictionData.data = response.data
        this.predictionData.generatedAt = new Date().toISOString()
        this.predictionData.loading = false
        
        return response.data
      } catch (error) {
        log.error('获取预测数据失败:', error)
        this.predictionData.error = error.message || '获取数据失败，请稍后重试'
        this.predictionData.loading = false
        throw error
      }
    },
    
    /**
     * 获取预警信息
     * @param {boolean} forceRefresh - 是否强制刷新，忽略缓存
     * @returns {Promise<Array>} - 返回预警信息数组
     */
    async fetchAlerts(forceRefresh = false) {
      this.alerts.loading = true
      this.alerts.error = null
      
      try {
        // 1. 检查内存缓存
        const currentTime = new Date().getTime();
        if (!forceRefresh && this.alerts.lastUpdated && (currentTime - this.alerts.lastUpdated) < CACHE_TTL.ALERTS && this.alerts.items.length > 0) {
          log.info('使用内存缓存的预警数据');
          this.alerts.loading = false;
          return this.alerts.items;
        }
        
        // 2. 如果强制刷新，跳过本地存储缓存检查
        if (!forceRefresh) {
          try {
            const storedAlertsData = localStorage.getItem('alerts_data');
            const storedAlertsTime = localStorage.getItem('alerts_timestamp');
            
            if (storedAlertsData && storedAlertsTime) {
              const alertsTime = parseInt(storedAlertsTime);
              if ((currentTime - alertsTime) < CACHE_TTL.ALERTS) {
                const parsedAlerts = JSON.parse(storedAlertsData);
                if (parsedAlerts && Array.isArray(parsedAlerts) && parsedAlerts.length > 0) {
                  log.info('使用本地存储的预警数据');
                  this.alerts.items = parsedAlerts;
                  this.alerts.unreadCount = parsedAlerts.filter(alert => !alert.read).length;
                  this.alerts.loading = false;
                  this.alerts.lastUpdated = alertsTime;
                  return parsedAlerts;
                }
              }
            }
          } catch (storageError) {
            log.info('读取本地存储的预警数据失败:', storageError.message);
            // 继续执行，不阻断流程
          }
        }
        
        // 使用现有省份数据生成预警
        if (this.provinceData && this.provinceData.length > 0) {
          log.info('使用现有省份数据生成预警信息');
          const generatedAlerts = this.generateAlertsFromAirQualityData(this.provinceData);
          this.alerts.items = generatedAlerts;
          this.alerts.unreadCount = generatedAlerts.length;
          this.alerts.lastUpdated = currentTime;
          this.alerts.loading = false;
          
          // 保存到本地存储
          localStorage.setItem('alerts_data', JSON.stringify(generatedAlerts));
          localStorage.setItem('alerts_timestamp', currentTime.toString());
          
          return generatedAlerts;
        }
        
        // 如果没有省份数据，先获取省份数据再生成预警
        await this.fetchProvinceData();
        if (this.provinceData && this.provinceData.length > 0) {
          const generatedAlerts = this.generateAlertsFromAirQualityData(this.provinceData);
          this.alerts.items = generatedAlerts;
          this.alerts.unreadCount = generatedAlerts.length;
          this.alerts.lastUpdated = currentTime;
          this.alerts.loading = false;
          
          // 保存到本地存储
          localStorage.setItem('alerts_data', JSON.stringify(generatedAlerts));
          localStorage.setItem('alerts_timestamp', currentTime.toString());
          
          return generatedAlerts;
        }
        
        return [];
        
      } catch (error) {
        log.info('获取预警数据失败，使用本地生成:', error.message);
        this.alerts.error = null; // 不向用户显示错误
        this.alerts.loading = false;
        // 尝试使用本地生成
        return this.generateAlertsFromAirQualityData(this.provinceData);
      }
    },
    
    /**
     * 从空气质量数据动态生成预警信息
     * @private
     * @returns {Promise<Array>} - 返回生成的预警信息数组
     */
    generateAlertsFromAirQualityData(provinceData) {
      // 只在有省份数据时生成预警
      if (!provinceData || !provinceData.length) {
        log.info('没有省份数据，无法生成预警')
        return []
      }

      const now = new Date()
      
      // 格式化时间为ISO格式
      const formatTime = (date) => {
        if (!date) return new Date().toISOString() // 确保始终有时间值
        try {
          return date.toISOString()
        } catch (e) {
          log.error('时间格式化错误:', e)
          return new Date().toISOString() // 确保始终有时间值
        }
      }

      // 使用当前时间戳生成ID的一部分
      const timestamp = Date.now()

      // 获取所有城市数据
      const allCities = []
      provinceData.forEach(province => {
        if (province.cities && province.cities.length) {
          allCities.push(...province.cities)
        } else if (province.name) {
          // 如果是扁平结构的城市数据
          allCities.push(province)
        }
      })

      // 生成预警信息 - 为所有城市生成对应级别的预警
      const alerts = []

      // 为每个城市生成对应的预警信息
      allCities.forEach(city => {
        const aqi = Number(city.aqi) || 0;
        let level, title, message, measures;
        
        // 根据AQI值确定预警级别和内容
        if (aqi > 200) {
          level = 'critical';
          title = `${city.name}空气质量严重污染预警`;
          message = `${city.name}当前AQI指数为${aqi}，处于严重污染水平，请注意防护。`;
          measures = [
            '避免户外活动',
            '关闭门窗',
            '使用空气净化器',
            '外出务必佩戴口罩'
          ];
        } else if (aqi > 150) {
          level = 'warning';
          title = `${city.name}空气质量污染预警`;
          message = `${city.name}当前AQI指数为${aqi}，处于中度污染水平，敏感人群应注意防护。`;
          measures = [
            '敏感人群避免户外活动',
            '建议戴口罩出行',
            '关闭门窗'
          ];
        } else if (aqi > 100) {
          level = 'info';
          title = `${city.name}空气质量轻度污染提示`;
          message = `${city.name}当前AQI指数为${aqi}，空气质量为轻度污染，请注意防护。`;
          measures = [
            '敏感人群注意防护',
            '建议减少户外活动'
          ];
        } else if (aqi > 50) {
          level = 'warning';
          title = `${city.name}空气质量提示`;
          message = `${city.name}当前AQI指数为${aqi}，空气质量为良好，但敏感人群可能会受到轻微影响。`;
          measures = [
            '敏感人群注意日常防护',
            '有慢性呼吸道疾病者应适当关注空气质量变化'
          ];
        } else {
          // AQI <= 50，优良空气质量，不生成警告级别的预警
          // 不需要为优良空气质量生成预警
          return; // 直接跳过，不添加到预警列表
        }
        
        // 创建预警对象
        alerts.push({
          id: `${level}-${city.id || Math.random().toString(36).substring(2)}-${timestamp}`,
          title: title,
          message: message,
          description: message,
          level: level,
          city: city.name,
          cityId: city.id || Math.random().toString(36).substring(2),
          province: city.province,
          aqi: aqi,
          status: 'active',
          time: formatTime(now),
          read: false,
          pollutants: {
            aqi: aqi,
            pm2_5: city.pm2_5 || city.pm25 || 0,
            pm10: city.pm10 || 0,
            so2: city.so2 || 0,
            no2: city.no2 || 0,
            o3: city.o3 || 0,
            co: city.co || 0
          },
          measures: measures
        });
      });

      return alerts;
    },
    
    /**
     * 标记预警为已读
     * @param {number|string} id - 预警ID
     */
    markAlertAsRead(id) {
      const alertIndex = this.alerts.items.findIndex(alert => alert.id === id);
      if (alertIndex !== -1) {
        if (!this.alerts.items[alertIndex].read) {
          this.alerts.items[alertIndex].read = true;
          this.alerts.unreadCount = Math.max(0, this.alerts.unreadCount - 1);
          
          // 将已读状态保存到localStorage
          try {
            const alerts = JSON.stringify(this.alerts.items);
            localStorage.setItem('air_quality_alerts', alerts);
          } catch (e) {
            log.error('保存警报状态到本地存储时出错:', e);
          }
        }
      }
    },
    
    // 计算统计数据
    calculateStats(data) {
      if (!data || !Array.isArray(data)) {
        this.stats = {
          totalCities: 0,
          goodQuality: 0,
          lightPollution: 0,
          heavyPollution: 0
        };
        return;
      }
      
      const validData = data.filter(item => item && typeof item.aqi === 'number');
      
      this.stats = {
        totalCities: validData.length,
        goodQuality: validData.filter(item => item.aqi <= 100).length,
        lightPollution: validData.filter(item => item.aqi > 100 && item.aqi <= 200).length,
        heavyPollution: validData.filter(item => item.aqi > 200).length
      };
    },

    // 初始化占位数据，在加载前显示
    initLoadingPlaceholders() {
      // 如果省份数据为空，生成占位数据
      if (!this.provinceData || this.provinceData.length === 0) {
        this.loadingPlaceholders.provinceCities = true;
        
        // 设置基本统计数据占位
        this.stats = {
          totalCities: '...',
          goodQuality: '...',
          lightPollution: '...',
          heavyPollution: '...'
        };
      }
      
      // 如果警告数据为空，生成占位数据
      if (!this.alerts.items || this.alerts.items.length === 0) {
        this.loadingPlaceholders.alerts = true;
      }
    },
    
    // 清除占位数据
    clearLoadingPlaceholders() {
      this.loadingPlaceholders.provinceCities = false;
      this.loadingPlaceholders.alerts = false;
      
      // 如果统计数据仍然是占位符，置为0
      if (this.stats.totalCities === '...') {
        this.stats = {
          totalCities: 0,
          goodQuality: 0,
          lightPollution: 0, 
          heavyPollution: 0
        };
      }
    }
  }
}) 