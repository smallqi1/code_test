/**
 * API服务
 * 提供与后端API交互的方法
 */

import axios from 'axios'

// API基础URL配置
const BASE_URL = 'http://localhost:5000'
const REALTIME_URL = 'http://localhost:5001'
const FORECAST_URL = 'http://localhost:5002'

// 添加这行在顶部适当位置
const TREND_API_URL = 'http://localhost:5000/api/air-quality/trend-data';

// 创建axios实例
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false
})

// 创建历史数据API实例 (5000端口)
const historyApi = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false
})

// 创建实时数据API实例 (5001端口)
const realtimeApi = axios.create({
  baseURL: REALTIME_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false
})

// 创建预测API实例 (5002端口)
const forecastApi = axios.create({
  baseURL: FORECAST_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 在发送请求前做些什么
    console.log('Request:', config)
    return config
  },
  error => {
    // 对请求错误做些什么
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 对响应数据做些什么
    console.log('Response:', response)
    return response
  },
  error => {
    // 对响应错误做些什么
    console.error('Response error:', error)
    return Promise.reject(error)
  }
)

/**
 * 从API获取城市列表
 * @returns {Promise<Object>} 包含城市列表的响应对象
 */
export async function fetchCities() {
  try {
    console.log('🔍 请求城市列表...');
    const response = await fetch('/api/air-quality/cities');
    
    if (!response.ok) {
      console.error('获取城市列表失败:', response.status, response.statusText);
      return {
        status: 'error',
        message: `请求失败: ${response.status} ${response.statusText}`,
        data: getDefaultCities()
      };
    }
    
    const result = await response.json();
    console.log('📊 城市列表API返回原始响应:', result);
    
    // 规范化响应结构
    let normalizedResponse = {
      status: 'success',
      data: []
    };
    
    // 处理不同的返回格式
    if (result.status === 'success') {
      if (Array.isArray(result.data)) {
        normalizedResponse.data = result.data;
      } else if (typeof result.data === 'object' && result.data !== null) {
        // 检查是否有cities字段
        if (Array.isArray(result.data.cities)) {
          normalizedResponse.data = result.data.cities;
        } else {
          // 尝试查找第一个数组类型的字段
          const arrayField = Object.entries(result.data)
            .find(([key, value]) => Array.isArray(value));
          
          if (arrayField) {
            normalizedResponse.data = arrayField[1];
          } else {
            console.warn('无法从响应中提取城市数组');
            normalizedResponse.data = getDefaultCities();
          }
        }
      }
    } else {
      normalizedResponse = {
        status: 'error',
        message: result.message || '服务器未返回成功状态',
        data: getDefaultCities()
      };
    }
    
    console.log('✅ 规范化后的城市列表:', normalizedResponse);
    return normalizedResponse;
  } catch (error) {
    console.error('获取城市列表异常:', error);
    return {
      status: 'error',
      message: error.message || '获取城市列表时发生错误',
      data: getDefaultCities()
    };
  }
}

/**
 * 获取默认城市列表
 * @returns {Array} 默认城市列表
 */
function getDefaultCities() {
  return [
    '广州市', '深圳市', '珠海市', '汕头市', '佛山市',
    '韶关市', '湛江市', '肇庆市', '江门市', '茂名市',
    '惠州市', '梅州市', '汕尾市', '河源市', '阳江市',
    '清远市', '东莞市', '中山市', '潮州市', '揭阳市',
    '云浮市'
  ];
}

/**
 * 获取实时数据
 * @param {string} city 城市名称
 * @returns {Promise<Object>} 实时数据
 */
export async function fetchRealtimeData(city) {
  try {
    const response = await realtimeApi.get(`/api/realtime/${city}`)
    return response.data
  } catch (error) {
    console.error(`获取${city}实时数据失败:`, error)
    throw error
  }
}

/**
 * 获取全省实时数据
 * @returns {Promise<Array>} 全省实时数据
 */
export async function fetchProvinceData() {
  try {
    const response = await realtimeApi.get('/api/province')
    return response.data
  } catch (error) {
    console.error('获取全省数据失败:', error)
    throw error
  }
}

/**
 * 获取趋势分析数据
 * @param {Object} params 分析参数
 * @returns {Promise<Object>} 趋势数据
 */
export async function fetchTrendData(params) {
  try {
    console.log('🚀 请求趋势分析数据，参数:', JSON.stringify(params, null, 2));
    console.log('🔍 发送请求至：' + TREND_API_URL);
    
    const requestStart = performance.now();
    console.log('Request:', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        cities: params.cities,
        startYear: params.startYear,
        endYear: params.endYear,
        pollutant: params.pollutant,
        analysisType: params.analysisType
      })
    });
    
    // 使用 historyApi 实例处理跨域问题
    const response = await historyApi.post('/api/air-quality/trend-data', {
      cities: params.cities,
      startYear: params.startYear,
      endYear: params.endYear,
      pollutant: params.pollutant,
      analysisType: params.analysisType
    });
    
    const requestEnd = performance.now();
    console.log('Response:', response);
    console.log(`⏱️ 请求耗时: ${Math.round(requestEnd - requestStart)}ms`);
    
    if (response.status !== 200) {
      console.error('趋势数据请求失败:', response.status, response.statusText);
      return {
        status: 'error',
        message: `请求失败: ${response.status} ${response.statusText}`
      };
    }
    
    const result = response.data;
    console.log('📊 趋势分析API返回原始响应:', result);
    console.log('📊 响应状态码:', response.status);
    console.log('📊 响应数据类型:', typeof result.data);
    
    // 确保返回数据包含所有必要字段
    if (result.status === 'success' && result.data) {
      console.log('✅ 趋势分析数据处理成功:', result);
      
      // 预期的数据结构
      const expectedFields = [
        'annualData',
        'seasonalData',
        'monthlyData',
        'comparisonData',
        'correlationMatrix',
        'forecastData',
        'complianceData',
        'basicStats',
        'improvementStats',
        'summary'
      ];
      
      // 检查并记录数据字段是否存在
      expectedFields.forEach(field => {
        if (field in result.data) {
          const value = result.data[field];
          const dataType = Array.isArray(value) ? `数组[${value.length}项]` : 
                          (typeof value === 'object' && value !== null) ? 'object' : 
                          typeof value;
          console.log(`✅ 字段${field}存在，包含${dataType}数据`);
        } else {
          console.log(` ⚠️ 响应中缺少${field}字段，创建默认空结构`);
          
          // 创建默认值
          if (field === 'annualData' || field === 'seasonalData' || 
              field === 'monthlyData' || field === 'comparisonData' || 
              field === 'forecastData' || field === 'complianceData') {
            result.data[field] = [];
          } else if (field === 'correlationMatrix') {
            result.data[field] = {};
          } else if (field === 'basicStats') {
            result.data[field] = {};
          } else if (field === 'improvementStats') {
            result.data[field] = {};
          } else if (field === 'summary') {
            result.data[field] = {
              findings: [],
              suggestions: []
            };
          }
        }
      });
      
      // 输出最终数据结构
      const dataStructure = {};
      Object.keys(result.data).forEach(key => {
        const value = result.data[key];
        dataStructure[key] = Array.isArray(value) ? `数组[${value.length}项]` : 
                            (typeof value === 'object' && value !== null) ? 'object' : 
                            typeof value;
      });
      console.log('📊 响应数据结构:', dataStructure);
    } else {
      console.error('❌ 趋势分析数据处理失败:', result);
    }
    
    return result;
  } catch (error) {
    console.error('趋势数据请求异常:', error);
    return {
      status: 'error',
      message: error.message || '请求趋势数据时发生错误'
    };
  }
}

/**
 * 获取数据日期范围
 * @returns {Promise<Object>} 日期范围
 */
export async function fetchDateRange() {
  try {
    const response = await api.get('/api/air-quality/date-range')
    
    if (response.data && response.data.status === 'success') {
      return response.data.data
    } else {
      throw new Error('获取日期范围失败')
    }
  } catch (error) {
    console.error('获取日期范围失败:', error)
    throw error
  }
}

/**
 * 获取历史数据
 * @param {Object} params 请求参数
 * @returns {Promise<Array>} 历史数据
 */
export async function fetchHistoricalData(params) {
  try {
    // 使用historyApi实例进行请求
    const queryParams = new URLSearchParams();
    
    // 添加查询参数
    for (const key in params) {
      if (params[key] !== undefined && params[key] !== null) {
        queryParams.append(key, params[key]);
      }
    }
    
    console.log('历史数据请求参数:', Object.fromEntries(queryParams));
    
    const response = await historyApi.get('/api/air-quality/historical', {
      params: queryParams
    });
    
    console.log('历史数据响应:', response);
    
    if (response.data && response.data.status === 'success') {
      return response.data.data;
    } else {
      throw new Error(response.data?.message || '获取历史数据失败');
    }
  } catch (error) {
    console.error('获取历史数据失败:', error);
    throw error;
  }
}

// 导出API实例，以便在其他地方使用
export { api, realtimeApi }

/**
 * 导出历史空气质量数据为CSV
 * @param {Object} params - 查询参数
 * @param {string} params.city - 城市名称
 * @param {string} params.start_date - 开始日期 (YYYY-MM-DD)
 * @param {string} params.end_date - 结束日期 (YYYY-MM-DD)
 * @param {string} params.quality_level - 空气质量等级 (可选，默认 'all')
 */
export const exportHistoricalData = (params) => {
  // 构建完整的URL
  const queryParams = new URLSearchParams();
  
  // 添加参数
  Object.keys(params).forEach(key => {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      queryParams.append(key, params[key]);
    }
  });
  
  // 创建完整URL，添加/api前缀
  const url = `${BASE_URL}/api/air-quality/export?${queryParams.toString()}`;
  
  // 使用窗口打开下载链接
  window.open(url, '_blank');
};

export const getLatestDate = async () => {
  try {
    // 使用historyApi实例获取最新日期
    const response = await historyApi.get('/api/air-quality/latest-date');
    
    if (response.data && response.data.status === 'success') {
      return response.data.data.latest_date;
    }
    throw new Error(response.data?.message || '获取最新日期失败');
  } catch (error) {
    console.error('获取最新日期失败:', error);
    throw error;
  }
};

// 导出图表为图片
export const exportChart = async (chartType, chartData) => {
  try {
    const response = await api.post('/api/export/chart', {
      type: chartType,
      data: chartData
    })
    return response
  } catch (error) {
    console.error('导出图表失败:', error)
    throw error
  }
}

// 导出数据为CSV
export const exportData = async (data) => {
  try {
    const response = await api.post('/api/export/data', data, {
      responseType: 'blob'
    })
    return response
  } catch (error) {
    console.error('导出数据失败:', error)
    throw error
  }
} 