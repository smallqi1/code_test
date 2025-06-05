/**
 * 日期时间格式化工具函数
 */

/**
 * 格式化日期时间为本地字符串
 * @param {number|string|Date} timestamp - 时间戳或日期对象
 * @param {boolean} includeSeconds - 是否包含秒
 * @returns {string} 格式化后的日期时间字符串
 */
export const formatDateTime = (timestamp, includeSeconds = true) => {
  if (!timestamp) return '无数据';
  
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  
  const options = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  };
  
  if (includeSeconds) {
    options.second = '2-digit';
  }
  
  return date.toLocaleString('zh-CN', options);
};

/**
 * 格式化日期为YYYY-MM-DD格式
 * @param {number|string|Date} timestamp - 时间戳或日期对象
 * @returns {string} 格式化后的日期字符串
 */
export const formatDate = (timestamp) => {
  if (!timestamp) return '无数据';
  
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  return `${year}-${month}-${day}`;
};

/**
 * 格式化时间为HH:MM:SS格式
 * @param {number|string|Date} timestamp - 时间戳或日期对象
 * @returns {string} 格式化后的时间字符串
 */
export const formatTime = (timestamp) => {
  if (!timestamp) return '无数据';
  
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  return `${hours}:${minutes}:${seconds}`;
};

/**
 * 将日期格式化为相对时间（刚刚、x分钟前、x小时前等）
 * @param {number|string|Date} timestamp - 时间戳或日期对象
 * @returns {string} 相对时间字符串
 */
export const formatRelativeTime = (timestamp) => {
  if (!timestamp) return '无数据';
  
  const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  if (diffInSeconds < 60) {
    return '刚刚';
  }
  
  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes}分钟前`;
  }
  
  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours}小时前`;
  }
  
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 30) {
    return `${diffInDays}天前`;
  }
  
  // 超过30天，返回具体日期
  return formatDate(date);
}; 