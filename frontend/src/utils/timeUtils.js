/**
 * 时间相关工具函数
 */

/**
 * 判断给定日期是否为今天
 * @param {Date} date - 要检查的日期对象
 * @returns {boolean} - 如果是今天返回true，否则返回false
 */
export function isToday(date) {
  if (!date || !(date instanceof Date) || isNaN(date.getTime())) {
    return false
  }
  
  const today = new Date()
  return date.getDate() === today.getDate() && 
         date.getMonth() === today.getMonth() && 
         date.getFullYear() === today.getFullYear()
}

/**
 * 格式化日期时间为友好格式
 * @param {string|number|Date} timestamp - 日期时间值
 * @returns {string} - 格式化后的日期时间字符串
 */
export function formatDateTime(timestamp) {
  if (!timestamp) return '未知'
  
  try {
    // 确保timestamp是一个有效的日期时间对象
    let date
    
    if (typeof timestamp === 'string') {
      // 尝试解析日期字符串
      date = new Date(timestamp)
    } else if (typeof timestamp === 'number') {
      // 如果是时间戳数字
      date = new Date(timestamp)
    } else {
      // 如果是Date对象
      date = timestamp
    }
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return '未知'
    }
    
    // 使用isToday函数判断是否是今天
    if (isToday(date)) {
      // 今天只显示时间
      return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
    } else {
      // 其他日期显示完整日期和时间
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).replace(/\//g, '-')
    }
  } catch (error) {
    console.error('日期格式化错误:', error, timestamp)
    return '未知'
  }
}

/**
 * 将日期时间转换为ISO格式字符串
 * @param {string|number|Date} timestamp - 日期时间值
 * @returns {string} - ISO格式的日期时间字符串
 */
export function toISOString(timestamp) {
  if (!timestamp) return new Date().toISOString()
  
  try {
    let date
    
    if (typeof timestamp === 'string') {
      date = new Date(timestamp)
    } else if (typeof timestamp === 'number') {
      date = new Date(timestamp)
    } else {
      date = timestamp
    }
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return new Date().toISOString()
    }
    
    return date.toISOString()
  } catch (error) {
    console.error('转换ISO日期错误:', error, timestamp)
    return new Date().toISOString()
  }
}

/**
 * 获取当前时间的ISO格式字符串
 * @returns {string} - 当前时间的ISO格式字符串
 */
export function getCurrentISOTime() {
  return new Date().toISOString()
} 