import { fetchCities } from './api';

/**
 * 预测服务
 * 封装与预测API交互的方法
 */

// 获取基础API URL，可以从环境变量或默认值获取
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5002';
const API_TIMEOUT = 30000; // 30秒超时，更长的时间避免频繁超时

// 添加请求缓存和防抖机制
const API_CACHE = new Map();
const PENDING_REQUESTS = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 缓存有效期5分钟

// 定义默认API请求选项
const defaultOptions = {
  model_path: 'data/models',  // 默认模型路径
  use_real_model: true,       // 默认使用真实模型
  mode: 'balanced'            // 默认使用平衡模式
};

/**
 * 生成缓存键
 * @param {string} endpoint API端点
 * @param {Object} params 请求参数
 * @returns {string} 缓存键
 */
function generateCacheKey(endpoint, params) {
  return `${endpoint}:${JSON.stringify(params)}`;
}

/**
 * 缓存API响应
 * @param {string} key 缓存键
 * @param {Object} data 响应数据
 */
function cacheApiResponse(key, data) {
  API_CACHE.set(key, {
    data: JSON.parse(JSON.stringify(data)), // 深拷贝，避免引用问题
    timestamp: Date.now()
  });
  // 简化缓存日志，移除冗长输出
  if (import.meta.env.DEV && import.meta.env.VITE_VERBOSE_LOGGING === 'true') {
    console.log(`缓存API响应: ${key.split(':')[0]}`);
  }
}

/**
 * 从缓存获取API响应
 * @param {string} key 缓存键
 * @returns {Object|null} 缓存的响应数据或null
 */
function getApiResponseFromCache(key) {
  const cachedItem = API_CACHE.get(key);
  if (!cachedItem) return null;
  
  // 验证缓存是否过期
  if (Date.now() - cachedItem.timestamp > CACHE_TTL) {
    API_CACHE.delete(key);
    return null;
  }
  
  // 简化日志输出
  if (import.meta.env.DEV && import.meta.env.VITE_VERBOSE_LOGGING === 'true') {
    console.log(`使用缓存: ${key.split(':')[0]}`);
  }
  return JSON.parse(JSON.stringify(cachedItem.data)); // 返回深拷贝
}

/**
 * 发送API请求并处理重复请求
 * @param {string} endpoint API端点
 * @param {Object} params 请求参数
 * @param {Object} options 请求选项
 * @returns {Promise<Object>} 响应数据
 */
async function sendApiRequest(endpoint, params, options = {}) {
  const cacheKey = generateCacheKey(endpoint, params);
  
  // 检查是否有缓存
  if (!options.ignoreCache) {
    const cachedResponse = getApiResponseFromCache(cacheKey);
    if (cachedResponse) {
      return Promise.resolve(cachedResponse);
    }
  }
  
  // 检查是否有相同的请求正在进行中
  if (PENDING_REQUESTS.has(cacheKey)) {
    if (import.meta.env.DEV && import.meta.env.VITE_VERBOSE_LOGGING === 'true') {
      console.log(`请求合并: ${endpoint}`);
    }
    return PENDING_REQUESTS.get(cacheKey);
  }
  
  // 创建新请求的Promise
  const requestPromise = (async () => {
    try {
      const response = await makeApiCall(endpoint, params, options);
      // 缓存成功的响应
      if (response && response.status === 'success') {
        cacheApiResponse(cacheKey, response);
      }
      return response;
    } finally {
      // 请求完成后，从等待队列中移除
      PENDING_REQUESTS.delete(cacheKey);
    }
  })();
  
  // 将请求添加到等待队列
  PENDING_REQUESTS.set(cacheKey, requestPromise);
  return requestPromise;
}

/**
 * 发送API请求
 * @param {string} endpoint API端点
 * @param {Object} params 请求参数
 * @param {Object} options 选项
 * @returns {Promise<any>} API响应
 */
async function makeApiCall(endpoint, params, options = {}) {
  // 移除路径中的前导斜杠，确保endpoint格式正确
  endpoint = endpoint.replace(/^\/+/, '');
  const apiUrl = `${API_BASE_URL}/api/${endpoint}`; // 使用环境变量中的API_BASE_URL
  
  try {
    // 只在开发环境下打印简化的请求信息
    if (import.meta.env.DEV && (options.debug || import.meta.env.VITE_VERBOSE_LOGGING === 'true')) {
      console.log(`API请求: ${endpoint}`, Object.keys(params));
    }
    
    const fetchOptions = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      credentials: 'same-origin',
      body: JSON.stringify(params)
    };
    
    // 请求超时控制
    const controller = new AbortController();
    const timeout = setTimeout(() => {
      controller.abort();
    }, options.timeout || 30000);
    
    fetchOptions.signal = controller.signal;
    
    const response = await fetch(apiUrl, fetchOptions);
    clearTimeout(timeout);
    
    if (!response.ok) {
      // 处理HTTP错误 - 保留错误日志
      const errorMessage = `API请求错误: ${response.status} ${response.statusText} (${endpoint})`;
      console.error(errorMessage);
      
      try {
        // 尝试解析错误响应
        const errorBody = await response.json();
        return {
          status: 'error',
          message: errorBody.message || errorMessage,
          code: response.status,
          details: errorBody
        };
      } catch (parseError) {
        // 无法解析错误响应
        return {
          status: 'error',
          message: errorMessage,
          code: response.status
        };
      }
    }
    
    const data = await response.json();
    // 简化缓存日志逻辑
    if (!options.noCache) {
      API_CACHE.set(`${endpoint}:${JSON.stringify(params)}`, {
        data: JSON.parse(JSON.stringify(data)),
        timestamp: Date.now()
      });
    }
    return data;
  } catch (error) {
    // 保留错误处理日志 - 这些对于调试很重要
    if (error.name === 'AbortError') {
      console.warn(`API请求超时 (${endpoint})`);
      return { 
        status: 'error', 
        message: `API请求超时 (${endpoint})`,
        code: 'TIMEOUT'
      };
    } else if (error.message?.includes('Failed to fetch')) {
      console.error(`网络错误 (${endpoint})`);
      return { 
        status: 'error', 
        message: `API网络错误 (${endpoint})`,
        code: 'NETWORK_ERROR',
        cors: true
      };
    } else {
      console.error(`API请求错误: ${error.message || '未知错误'}`);
      return {
        status: 'error',
        message: `API请求错误: ${error.message || '未知错误'}`,
        code: 'UNKNOWN_ERROR'
      };
    }
  }
}

/**
 * 清除预测API缓存，确保获取最新数据
 * @param {string} indicator - 指标名称，如果提供则只清除该指标的缓存
 */
export function clearPredictionCache(indicator = null) {
  // 如果指定了indicator，只清除该指标相关的缓存
  if (indicator) {
    const cacheKeyPattern = new RegExp(`prediction:.*"indicator":"${indicator}".*`);
    
    // 遍历缓存键，移除匹配的项
    for (const key of API_CACHE.keys()) {
      if (cacheKeyPattern.test(key)) {
        console.log(`清除指标 ${indicator} 的预测缓存: ${key}`);
        API_CACHE.delete(key);
      }
    }
  } else {
    // 清除所有预测相关的缓存
    const predictionKeyPattern = /prediction:/;
    
    for (const key of API_CACHE.keys()) {
      if (predictionKeyPattern.test(key)) {
        console.log(`清除预测缓存: ${key}`);
        API_CACHE.delete(key);
      }
    }
  }
  
  console.log('预测缓存已清除');
}

/**
 * 获取完整预测数据 - 简化流程，直接使用单独API请求
 */
export async function getCompleteForecast(cityId, indicator, predictionLength, options = {}) {
  // 确保城市ID正确
  if (typeof cityId !== 'string') {
    console.warn(`cityId不是字符串类型: ${typeof cityId}`, cityId);
    cityId = String(cityId);
  }
  
  if (!cityId.startsWith('city_')) {
    const cityIdFound = await getCityIdByName(cityId);
    cityId = cityIdFound || cityId;
  }
  
  // 清除指标的预测缓存，确保获取最新数据
  clearPredictionCache(indicator);

  console.log('开始获取预测数据，直接使用单独API调用流程');
  return getForecastWithFallback(cityId, indicator, predictionLength, options);
}

/**
 * 简化的预测获取流程 - 直接使用单独API获取所有数据
 */
async function getForecastWithFallback(cityId, indicator, predictionLength, options) {
  try {
    // 获取基础预测数据
    console.log(`正在获取基础预测数据: 城市=${cityId}, 指标=${indicator}, 周期=${predictionLength}天`);
    const forecast = await getForecast(cityId, indicator, predictionLength, options);
    
    // 如果基础预测失败，直接返回错误
    if (forecast.status !== 'success' || !forecast.data) {
      console.error('基础预测获取失败:', forecast.message);
      return forecast;
    }
    
    // 并行获取其他数据
    console.log('正在并行获取次要指标、影响因素和预测建议...');
    const [secondaryRes, factorsRes, suggestionsRes] = await Promise.all([
      // 获取次要指标
      getSecondaryIndicators(cityId, ['pm25', 'pm10', 'o3', 'no2'].filter(i => i !== indicator), options)
        .catch(err => { 
          console.warn('次要指标获取失败:', err); 
          return { status: 'error', message: '次要指标获取失败' }; 
        }),
      // 获取影响因素
      getInfluencingFactors(cityId, indicator, options)
        .catch(err => { 
          console.warn('影响因素获取失败:', err); 
          return { status: 'error', message: '影响因素获取失败' }; 
        }),
      // 获取预测建议
      getPredictionSuggestions(cityId, indicator, options)
        .catch(err => { 
          console.warn('预测建议获取失败:', err);
          return { status: 'error', message: '预测建议获取失败' }; 
        })
    ]);
    
    // 获取置信区间 (对预测结果的进一步处理)
    console.log('正在获取置信区间数据...');
    const confidenceRes = await getConfidenceIntervals(
      cityId, 
      indicator, 
      forecast.data.forecast, 
      options
    ).catch(err => {
      console.warn('置信区间获取失败，将使用生成的置信区间:', err);
      return null;
    });
    
    // 合并结果
    const result = { ...forecast };
    
    // 添加次要指标
    if (secondaryRes.status === 'success' && secondaryRes.data) {
      result.data.secondary_indicators = secondaryRes.data;
    } else {
      console.warn('使用空次要指标数据');
      result.data.secondary_indicators = { status: 'error', message: '数据获取失败' };
    }
    
    // 添加影响因素
    if (factorsRes.status === 'success' && factorsRes.data) {
      result.data.influencing_factors = factorsRes.data;
    } else {
      console.warn('使用空影响因素数据');
      result.data.influencing_factors = { status: 'error', message: '数据获取失败' };
    }
    
    // 添加预测建议
    if (suggestionsRes.status === 'success' && suggestionsRes.data) {
      result.data.suggestions = suggestionsRes.data;
    } else {
      console.warn('使用空预测建议数据');
      result.data.suggestions = { status: 'error', message: '数据获取失败' };
    }
    
    // 添加置信区间
    if (confidenceRes && confidenceRes.status === 'success' && confidenceRes.data) {
      result.data.confidence_intervals = confidenceRes.data;
    } else {
      console.warn('无法获取置信区间数据');
      result.data.confidence_intervals = [];
    }
    
    console.log('预测数据获取和整合完成');
    return result;
  } catch (error) {
    console.error('预测数据获取过程出错:', error);
    return {
      status: 'error',
      message: `预测处理错误: ${error.message || '未知错误'}`,
      data: null
    };
  }
}

/**
 * 获取城市和指标的预测数据，包括历史数据
 * @param {string} cityId - 城市ID
 * @param {string} indicator - 指标
 * @param {number} predictionLength - 预测天数
 * @param {string} timePeriod - 时间周期(short, medium, long)
 * @param {object} options - 请求选项
 * @returns {Promise<object>} 预测结果
 */
export async function getForecast(cityId, indicator, predictionLength = 7, timePeriod = 'short', options = {}) {
  // 确保指标名称是小写
  indicator = indicator.toLowerCase();
  
  console.log(`请求预测数据: 城市ID=${cityId}, 指标=${indicator}, 预测天数=${predictionLength}, 时间周期=${timePeriod}`);
  
  try {
    // 创建请求参数
    const requestParams = {
      city_id: cityId,
      indicator: indicator,
      prediction_length: predictionLength,
      time_period: timePeriod  // 添加时间周期参数
    };
    
    // 发送请求获取预测和历史数据
    console.log('向后端API发送预测请求:', requestParams);
    
    // 使用sendApiRequest函数代替直接fetch调用
    const response = await sendApiRequest('prediction', requestParams, options);
    
    console.log('预测请求已完成，开始处理结果');
    
    if (response.status === 'success' || response.success) {
      // 处理API返回的数据
      const forecastData = {
        status: 'success',
        message: '预测成功',
        data: {
          city_name: response.city_name || '',
          city_id: response.city_id || cityId,
          indicators: {}
        }
      };
      
      // 将预测数据转换为前端期望的格式
      const forecastDates = response.forecast_dates || [];
      const forecastValues = response.forecast_values || [];
      const historyDates = response.history_dates || [];
      const historyValues = response.history_values || [];
      
      // 添加预测和历史数据
      forecastData.data.indicators[indicator.toUpperCase()] = {
        forecast: forecastDates.map((date, index) => ({
          date: date,
          value: index < forecastValues.length ? forecastValues[index] : null
        })),
        historical: historyDates.map((date, index) => ({
          date: date,
          value: index < historyValues.length ? historyValues[index] : null
        }))
      };
      
      console.log(`成功处理指标 ${indicator} 的预测数据: 
        ${forecastDates.length} 条预测数据, 
        ${historyDates.length} 条历史数据`);
      
      return forecastData;
    } else {
      console.error('预测请求失败:', response.error || response.message || '未知错误');
      
      // 返回错误信息，不使用回退数据
      return {
        status: 'error',
        message: response.error || response.message || '预测请求失败，未能获取数据',
        data: null
      };
    }
  } catch (error) {
    console.error('预测请求处理错误:', error);
    
    // 返回错误信息，不使用回退数据
    return {
      status: 'error',
      message: `预测请求失败: ${error.message || '未知错误'}`,
      data: null
    };
  }
}

/**
 * 获取置信区间 - 修复参数类型问题
 */
export async function getConfidenceIntervals(cityId, indicator, forecastData, options = {}) {
  if (typeof cityId !== 'string') {
    console.warn(`getConfidenceIntervals: cityId不是字符串类型: ${typeof cityId}`, cityId);
    cityId = String(cityId);
  }
  
  if (!cityId.startsWith('city_')) {
    const cityIdFound = await getCityIdByName(cityId);
    cityId = cityIdFound || cityId;
  }
  
  // 确保forecast_data是数组格式
  const forecastArray = Array.isArray(forecastData) ? forecastData : [forecastData];
  
  const endpoint = 'prediction/confidence';
  const params = {
    city_id: cityId,
    indicator,
    forecast_data: forecastArray,
    ...options
  };
  
  return sendApiRequest(endpoint, params);
}

/**
 * 获取城市ID映射关系
 * @returns {Promise<Object>} 城市ID映射对象，格式：{city_id: cityName}
 */
const getCityIdMap = async () => {
  // 这是默认的城市ID映射，如果API无法获取将使用此映射
  const defaultCityMap = {
    'city_e1a4ccc0': '广州', 
    'city_c75415d5': '深圳', 
    'city_88901f7a': '珠海', 
    'city_8b16da5b': '汕头', 
    'city_1cda4de3': '佛山', 
    'city_e801bd81': '韶关', 
    'city_9b8f28c4': '湛江', 
    'city_99ecc477': '肇庆',
    'city_2703d0ae': '江门', 
    'city_3282a0da': '茂名', 
    'city_58159d46': '惠州', 
    'city_53ef6a54': '梅州',
    'city_f8696158': '汕尾', 
    'city_6f7bcb19': '河源', 
    'city_721618dc': '阳江', 
    'city_7d787af8': '清远',
    'city_7829e4bd': '东莞', 
    'city_ecace404': '中山', 
    'city_6f3c5fc7': '潮州', 
    'city_b0e8511e': '揭阳',
    'city_aec423c3': '云浮'
  };
  
  try {
    // 理想情况下应该从API获取城市映射，但这里使用硬编码的映射
    // 未来可以实现获取实际映射的接口
    return defaultCityMap;
  } catch (error) {
    console.error('获取城市ID映射失败:', error);
    return defaultCityMap;
  }
};

/**
 * 获取指标的显示名称
 * @param {string} indicator 指标代码
 * @returns {string} 指标显示名称
 */
const getIndicatorLabel = (indicator) => {
  const labels = {
    'aqi': 'AQI',
    'pm25': 'PM2.5',
    'pm10': 'PM10',
    'so2': 'SO2',
    'no2': 'NO2',
    'co': 'CO',
    'o3': 'O3'
  };
  
  return labels[indicator] || indicator.toUpperCase();
};

/**
 * 获取可用城市列表
 * @returns {Promise} 城市列表
 */
const getAvailableCities = async () => {
  // 使用相对路径让Vite代理处理
  const url = `/api/cities`;
  
  try {
    console.log('请求城市列表:', url);
    
    // 发送请求，带超时（2秒）
    const response = await apiRequest(url, {}, 2000);
    
    // 处理响应
    const data = await handleResponse(response);
    
    // 检查API返回的状态
    if (data.status !== 'success') {
      throw new Error(data.message || '获取城市列表API返回错误状态');
    }
    
    return data;
  } catch (error) {
    console.warn('获取城市列表失败:', error.message);
    
    // 检查是否为网络错误
    const isNetworkError = error.message.includes('Failed to fetch') || 
                           error.message.includes('Network Error') ||
                           error.message.includes('请求超时');
    
    // 返回标准错误响应
    return {
      status: 'error',
      message: isNetworkError ? '无法连接到城市列表服务' : error.message,
      error: error.toString()
    };
  }
};

/**
 * 获取次要指标数据
 * @param {string} cityId 城市ID
 * @param {Array} indicators 指标列表
 * @param {Object} options 选项
 * @returns {Promise<Object>} 次要指标数据
 */
export async function getSecondaryIndicators(cityId, indicators = ['pm25', 'pm10', 'o3', 'no2'], options = {}) {
  if (typeof cityId !== 'string') {
    console.warn(`getSecondaryIndicators: cityId不是字符串类型: ${typeof cityId}`, cityId);
    cityId = String(cityId);
  }
  
  if (!cityId.startsWith('city_')) {
    const cityIdFound = await getCityIdByName(cityId);
    cityId = cityIdFound || cityId;
  }
  
  const endpoint = 'prediction/secondary_indicators';
  const params = {
    city_id: cityId,
    indicators: indicators,
    days: options.days || 30,
    ...options
  };
  
  return sendApiRequest(endpoint, params);
}

/**
 * 获取影响因素数据
 * @param {string} cityId 城市ID
 * @param {string} indicator 指标
 * @param {Object} options 选项
 * @returns {Promise<Object>} 影响因素数据
 */
export async function getInfluencingFactors(cityId, indicator, options = {}) {
  if (typeof cityId !== 'string') {
    console.warn(`getInfluencingFactors: cityId不是字符串类型: ${typeof cityId}`, cityId);
    cityId = String(cityId);
  }
  
  if (!cityId.startsWith('city_')) {
    const cityIdFound = await getCityIdByName(cityId);
    cityId = cityIdFound || cityId;
  }
  
  const endpoint = 'prediction/factors';
  const params = {
    city_id: cityId,
    indicator,
    ...options
  };
  
  return sendApiRequest(endpoint, params);
}

/**
 * 获取预测建议
 * @param {string} cityId 城市ID
 * @param {string} indicator 指标
 * @param {Object} options 选项
 * @returns {Promise<Object>} 预测建议数据
 */
export async function getPredictionSuggestions(cityId, indicator, options = {}) {
  if (typeof cityId !== 'string') {
    console.warn(`getPredictionSuggestions: cityId不是字符串类型: ${typeof cityId}`, cityId);
    cityId = String(cityId);
  }
  
  if (!cityId.startsWith('city_')) {
    const cityIdFound = await getCityIdByName(cityId);
    cityId = cityIdFound || cityId;
  }
  
  const endpoint = 'prediction/suggestions';
  const params = {
    city_id: cityId,
    indicator,
    ...options
  };
  
  return sendApiRequest(endpoint, params);
}

/**
 * 健康检查 - 检查API服务是否可用
 * @returns {Promise<Object>} 健康状态
 */
export async function checkHealth() {
  // 使用标准API路径格式和统一的API_BASE_URL
  const url = `${API_BASE_URL}/api/health`;
  
  try {
    // 创建一个AbortController来实现请求超时
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);  // 5秒超时
    
    // 发送请求，使用AbortController实现超时控制
    const response = await fetch(url, { 
      signal: controller.signal 
    }).catch(error => {
      return null;
    });
    
    // 清除超时计时器
    clearTimeout(timeoutId);
    
    // 检查响应
    if (!response) {
      return {
        success: false,
        status: 'error',
        message: '预测服务不可用',
        data: null
      };
    }
    
    if (!response.ok) {
      return {
        success: false,
        status: 'error',
        message: `预测服务返回错误状态: ${response.status}`,
        data: null
      };
    }
    
    // 尝试解析JSON
    let data;
    try {
      data = await response.json();
    } catch (e) {
      // 尝试读取文本
      const text = await response.text();
      
      if (text.includes('success') || text.includes('正常')) {
        return {
          success: true,
          status: 'success',
          message: '预测服务正常',
          data: { status: 'success', message: text }
        };
      } else {
        return {
          success: false,
          status: 'error',
          message: '预测服务返回无效响应',
          data: text
        };
      }
    }
    
    // 处理正常JSON响应
    if (data && (data.status === 'success' || data.status === 'ok')) {
      return {
        success: true,
        status: 'success',
        message: '预测服务正常',
        data: data
      };
    } else {
      return {
        success: false,
        status: 'error',
        message: data?.message || '预测服务异常',
        data: data
      };
    }
  } catch (error) {
    return {
      success: false,
      status: 'error',
      message: '无法连接到预测服务',
      error: error.message
    };
  }
}

/**
 * 标准化API响应数据
 * @param {Object} response API响应对象
 * @param {string} cityId 城市ID
 * @param {string} indicator 指标
 * @returns {Object} 标准化的响应数据
 */
function normalizeResponseData(response, cityId, indicator) {
  let result = {
    city_id: cityId,
    indicator: indicator,
    historical: [],
    forecast: []
  };
  
  // 从响应中提取数据
  const data = response.data || response;
  
  // 提取城市名
  if (data.city_name) {
    result.city_name = data.city_name;
  }
  
  // 提取历史数据
  if (data.historical && Array.isArray(data.historical)) {
    result.historical = data.historical;
  }
  
  // 提取预测数据
  if (data.forecast && Array.isArray(data.forecast)) {
    result.forecast = data.forecast;
  }
  
  // 提取置信度
  if (data.confidence || response.confidence) {
    result.confidence = data.confidence || response.confidence;
  }
  
  return result;
}

/**
 * 通过城市名称获取城市ID
 * @param {string} cityName 城市名称
 * @returns {Promise<string|null>} 城市ID或null
 */
export async function getCityIdByName(cityName) {
  try {
    // 获取城市ID映射
    const cityMap = await getCityIdMap();
    if (!cityMap) {
      console.error('无法获取城市ID映射');
      return null;
    }
    
    // 查找城市对应的ID
    const cityId = Object.keys(cityMap).find(key => cityMap[key] === cityName);
    if (!cityId) {
      console.error(`找不到城市"${cityName}"的ID映射`);
      return null;
    }
    
    console.log(`为城市 "${cityName}" 找到对应ID: ${cityId}`);
    return cityId;
  } catch (error) {
    console.error('获取城市ID失败:', error);
    return null;
  }
}

/**
 * 获取所有指标的预测数据 - 使用更高性能的批量接口
 * @param {string} cityId - 城市ID
 * @param {number} predictionLength - 预测天数
 * @param {string} timePeriod - 时间周期
 * @param {object} options - 请求选项
 * @returns {Promise<object>} 预测结果
 */
export async function getAllIndicatorsForecast(cityId, predictionLength = 7, timePeriod = 'short', options = {}) {
  const indicators = ['aqi', 'pm25', 'pm10', 'so2', 'no2', 'co', 'o3'];
  
  // 只在开发环境或debug模式下记录详细日志
  if (import.meta.env.DEV || options.debug) {
    console.log(`正在获取所有指标预测，城市ID=${cityId}, 预测天数=${predictionLength}, 时间周期=${timePeriod}`);
  }
  
  try {
    // 检查是否支持批量API
    const useBatchApi = options.useBatchApi !== false;
    
    if (useBatchApi) {
      try {
        // 确保predictionLength是整数
        const predictionDays = parseInt(predictionLength, 10);
        
        // 尝试使用批量API获取所有指标数据
        const batchResult = await sendApiRequest('batch_prediction', {
          city_id: cityId,
          indicators: indicators,
          prediction_length: predictionDays, // 确保使用整数值
          time_period: timePeriod
        }, options);
        
        if (batchResult && batchResult.status === 'success') {
          // 处理结果，确保预测天数正确
          if (batchResult.data && batchResult.data.indicators) {
            for (const indicator in batchResult.data.indicators) {
              if (batchResult.data.indicators[indicator] && 
                  batchResult.data.indicators[indicator].forecast && 
                  Array.isArray(batchResult.data.indicators[indicator].forecast)) {
                  
                // 获取预测数据
                const forecast = batchResult.data.indicators[indicator].forecast;
                
                // 如果预测数据超过请求的天数，截取到请求的天数
                if (forecast.length > predictionDays) {
                  console.log(`指标 ${indicator} 截取预测数据从 ${forecast.length} 到 ${predictionDays} 天`);
                  
                  // 获取所有有效的未来日期点（非插值点）
                  const futureDates = forecast
                    .filter(point => !point.isInterpolated)
                    .sort((a, b) => new Date(a.date) - new Date(b.date))
                    .slice(0, predictionDays);
                  
                  // 只保留实际预测的天数
                  if (futureDates.length > 0) {
                    const lastPredictionDate = new Date(futureDates[futureDates.length - 1].date);
                    
                    // 只保留到最后一个有效预测日期的数据点
                    batchResult.data.indicators[indicator].forecast = forecast.filter(point => {
                      const pointDate = new Date(point.date);
                      return pointDate <= lastPredictionDate;
                    });
                  }
                }
              }
            }
          }
          
          return batchResult; // 返回处理后的批量API结果
        }
        
        // 如果批量API失败，记录一次警告，然后回退到单个请求
        console.warn('批量API请求失败，回退到单独请求');
      } catch (batchError) {
        console.warn('批量API请求错误，回退到单独请求');
      }
    }
    
    // 并行获取所有指标的预测数据
    const results = await Promise.all(
      indicators.map(async (indicator) => {
        try {
          const forecast = await getForecast(
            cityId, 
            indicator, 
            predictionLength, 
            timePeriod,
            { ...options, cache: true }  // 使用缓存
          );
          
          return {
            indicator,
            result: forecast
          };
        } catch (error) {
          // 简化错误日志
          return {
            indicator,
            result: {
              status: 'error',
              message: `获取 ${indicator} 预测数据失败`,
              data: null
            }
          };
        }
      })
    );
    
    // 合并结果
    const mergedResult = {
      status: 'success',
      message: '预测成功',
      data: {
        city_id: cityId,
        indicators: {}
      }
    };
    
    // 找出第一个有城市名称的结果
    const cityNameResult = results.find(r => 
      r.result.status === 'success' && 
      r.result.data && 
      r.result.data.city_name
    );
    
    if (cityNameResult) {
      mergedResult.data.city_name = cityNameResult.result.data.city_name;
    } else {
      // 尝试从城市ID映射中获取城市名
      const cityMap = await getCityIdMap();
      mergedResult.data.city_name = cityMap[cityId] || '未知城市';
    }
    
    // 处理所有指标结果
    let successCount = 0;
    let failureCount = 0;
    
    results.forEach(({ indicator, result }) => {
      if (result.status === 'success' && result.data && result.data.indicators && result.data.indicators[indicator.toUpperCase()]) {
        // 如果成功获取预测数据，添加到合并结果中
        mergedResult.data.indicators[indicator.toUpperCase()] = result.data.indicators[indicator.toUpperCase()];
        successCount++;
      } else {
        // 失败指标计数
        failureCount++;
        
        // 对于失败的预测，添加空数据
        mergedResult.data.indicators[indicator.toUpperCase()] = {
          forecast: [],
          historical: []
        };
      }
    });
    
    // 更新状态信息
    if (successCount === 0) {
      // 只在所有指标都失败时显示一条汇总错误
      if (failureCount > 0) {
        console.warn(`所有 ${failureCount} 个指标的预测请求都失败了`);
      }
      
      mergedResult.status = 'error';
      mergedResult.message = '所有指标预测失败';
    } else if (successCount < indicators.length) {
      mergedResult.status = 'partial';
      mergedResult.message = `部分指标预测成功 (${successCount}/${indicators.length})`;
    }
    
    return mergedResult;
  } catch (error) {
    console.error('获取预测数据失败');
    return {
      status: 'error',
      message: `获取所有指标预测数据失败`,
      data: null
    };
  }
}

// 导出服务方法
export {
  getAvailableCities,
  getCityIdMap,
  // 添加其他需要导出的函数，但不包括已经使用export async function导出的函数
  // getForecast, getSecondaryIndicators, getInfluencingFactors, 
  // getPredictionSuggestions, getConfidenceIntervals 已经在上面导出，这里不再重复
}; 

export async function getPrediction(options = {}) {
  const {
    city_id,
    indicator = 'aqi',
    days = 7,
    use_real_model = true
  } = options;

  logger.info('正在请求预测数据', { city_id, indicator, days, use_real_model });

  try {
    const response = await apiClient.post(`${API_BASE_URL}/predict`, {
      city_id,
      indicator,
      days,
      use_real_model
    });

    logger.info('预测数据API响应成功', response.data);
    return response.data;
  } catch (error) {
    logger.error('预测数据API请求失败', error);
    throw error;
  }
} 

const handlePredictionResponse = (response, indicator) => {
  try {
    if (!response.data || !response.data.success) {
      console.error(`预测指标 ${indicator} 失败: ${response.data?.error || '未知错误'}`);
      return null;
    }

    // 提取响应数据
    const { forecast_dates, forecast_values, history_dates, history_values } = response.data;
    
    // 添加详细日志
    console.log(`[${indicator}] 历史数据检查: ${history_dates?.length || 0} 条历史数据, ${forecast_dates?.length || 0} 条预测数据`);
    if (history_dates?.length > 0) {
      console.log(`[${indicator}] 历史数据范围: ${history_dates[0]} 到 ${history_dates[history_dates.length-1]}`);
    } else {
      console.log(`[${indicator}] 警告: 没有历史数据返回!`);
      // 检查响应中是否存在history_dates字段
      console.log(`[${indicator}] 响应中是否有history_dates字段: ${response.data.hasOwnProperty('history_dates')}`);
      console.log(`[${indicator}] 完整响应数据:`, response.data);
    }

    // 标准化日期格式，确保都是YYYY-MM-DD
    const formatDates = (dates) => {
      return dates.map(date => {
        if (typeof date === 'string') {
          // 如果日期已经是字符串，确保格式为YYYY-MM-DD
          return date.split('T')[0];
        }
        return date;
      });
    };

    const formattedForecastDates = formatDates(forecast_dates || []);
    const formattedHistoryDates = formatDates(history_dates || []);

    // 构建结果对象
    const result = {
      indicator,
      forecast: {
        dates: formattedForecastDates,
        values: forecast_values || []
      },
      history: {
        dates: formattedHistoryDates,
        values: history_values || []
      }
    };

    console.log(`成功处理指标 ${indicator} 的预测数据: 
        ${result.forecast.dates.length} 条预测数据, 
        ${result.history.dates.length} 条历史数据`);

    return result;
  } catch (error) {
    console.error(`处理预测响应出错 (${indicator}):`, error);
    return null;
  }
}; 