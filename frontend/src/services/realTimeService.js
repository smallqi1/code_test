/**
 * 实时数据服务
 * 
 * 提供获取当天实时空气质量数据的API接口
 */

import * as apiClient from './apiClient';

// 使用环境变量中定义的实时API接口URL
const REALTIME_API_BASE_URL = import.meta.env.VITE_REALTIME_API_BASE_URL || 'http://localhost:5001';

// 在初始化时设置基础URL
apiClient.setBaseURL(REALTIME_API_BASE_URL);

/**
 * 获取指定城市的实时空气质量数据
 * 
 * @param {string} cityName - 城市名称
 * @returns {Promise<Object>} 实时数据
 */
export async function getRealTimeData(cityName) {
  try {
    console.log(`获取城市 "${cityName}" 的实时数据`);
    
    // 尝试新的API路径格式
    const response = await apiClient.get(`/api/realtime/${encodeURIComponent(cityName)}`);
    if (response && response.data) {
      console.log('成功获取实时数据:', response.data);
      return response.data;
    } else {
      console.error('API响应格式不正确');
      return null;
    }
  } catch (error) {
    console.error('获取实时数据失败:', error);
    // 返回一个默认值而不是抛出错误，这样即使API失败也不会影响预测功能
    return null;
  }
}

/**
 * 获取所有支持实时数据的城市列表
 * 
 * @returns {Promise<Array<string>>} 城市名称列表
 */
export async function getSupportedCities() {
  try {
    // 修改为可能正确的API路径
    const response = await apiClient.get('/api/cities');
    if (response && response.data && Array.isArray(response.data)) {
      console.log('成功获取支持城市列表:', response.data);
      return response.data;
    } else if (response && response.data && response.data.cities && Array.isArray(response.data.cities)) {
      console.log('成功获取支持城市列表:', response.data.cities);
      return response.data.cities;
    } else {
      console.error('API响应格式不正确');
      return [];
    }
  } catch (error) {
    console.error('获取支持城市列表失败:', error);
    return [];
  }
} 