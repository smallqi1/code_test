/**
 * API客户端
 * 提供与后端API交互的通用方法
 */

import axios from 'axios';

// 创建默认的axios实例
const api = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 在发送请求前做些什么
    console.log('API Client Request:', config);
    return config;
  },
  error => {
    // 对请求错误做些什么
    console.error('API Client Request error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 对响应数据做些什么
    return response;
  },
  error => {
    // 对响应错误做些什么
    console.error('API Client Response error:', error);
    return Promise.reject(error);
  }
);

/**
 * 发送GET请求
 * @param {string} url - 请求URL
 * @param {Object} params - URL参数
 * @param {Object} config - axios配置
 * @returns {Promise<Object>} 响应对象
 */
export function get(url, params = {}, config = {}) {
  return api.get(url, { params, ...config });
}

/**
 * 发送POST请求
 * @param {string} url - 请求URL
 * @param {Object} data - 请求体数据
 * @param {Object} config - axios配置
 * @returns {Promise<Object>} 响应对象
 */
export function post(url, data = {}, config = {}) {
  return api.post(url, data, config);
}

/**
 * 发送PUT请求
 * @param {string} url - 请求URL
 * @param {Object} data - 请求体数据
 * @param {Object} config - axios配置
 * @returns {Promise<Object>} 响应对象
 */
export function put(url, data = {}, config = {}) {
  return api.put(url, data, config);
}

/**
 * 发送DELETE请求
 * @param {string} url - 请求URL
 * @param {Object} config - axios配置
 * @returns {Promise<Object>} 响应对象
 */
export function del(url, config = {}) {
  return api.delete(url, config);
}

/**
 * 设置API基础URL
 * @param {string} baseURL - 基础URL
 */
export function setBaseURL(baseURL) {
  api.defaults.baseURL = baseURL;
} 