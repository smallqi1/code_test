/**
 * 浏览器兼容性补丁文件
 * 用于处理不同浏览器之间的兼容性问题
 */

/**
 * 修复fetch请求头兼容性问题
 * - 确保Content-Type设置为utf-8
 * - 确保application/json的媒体类型正确
 */
export function applyFetchPatches() {
  // 避免重复修补
  if (window.__fetchPatched) return;
  window.__fetchPatched = true;
  
  // 保存原始的fetch函数
  const originalFetch = window.fetch;
  
  // 重写fetch函数
  window.fetch = function(url, options = {}) {
    // 如果headers不存在，则创建
    options.headers = options.headers || {};
    
    // 确保Content-Type的charset为utf-8
    if (options.headers['Content-Type'] && 
        options.headers['Content-Type'].includes('application/json')) {
      options.headers['Content-Type'] = 'application/json; charset=utf-8';
    }
    
    // 调用原始fetch
    return originalFetch.call(this, url, options);
  };
}

/**
 * 为axios设置默认标头，解决Content-Type问题
 * @param {Object} axiosInstance - Axios实例
 */
export function setupAxiosDefaults(axiosInstance) {
  // 设置请求拦截器来确保内容类型正确
  axiosInstance.interceptors.request.use(
    config => {
      // 确保Content-Type的charset为utf-8
      if (config.headers['Content-Type'] && 
          config.headers['Content-Type'].includes('application/json')) {
        config.headers['Content-Type'] = 'application/json; charset=utf-8';
      }
      return config;
    },
    error => Promise.reject(error)
  );
}

/**
 * 初始化所有兼容性补丁
 * @param {Object} app - Vue应用实例
 * @param {Object} options - 补丁选项
 */
export function initCompatibilityPatches(app, options = {}) {
  // 应用fetch补丁
  applyFetchPatches();
  
  // 如果提供了axios实例，设置默认值
  if (options.axios) {
    setupAxiosDefaults(options.axios);
  }
  
  console.log('✅ 浏览器兼容性补丁已应用');
}

export default {
  initCompatibilityPatches
}; 