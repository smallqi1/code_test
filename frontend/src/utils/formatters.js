/**
 * 格式化数值，保留2位小数
 * @param {number} value - 要格式化的值
 * @returns {string} 格式化后的值
 */
export const formatValue = (value) => {
  if (value === undefined || value === null || isNaN(value)) return '—'
  return parseFloat(value).toFixed(2)
}

/**
 * 获取改善率的CSS类
 * @param {number} rate - 改善率值
 * @returns {string} CSS类名
 */
export const getImprovementClass = (rate) => {
  if (rate === undefined || rate === null || isNaN(rate)) return ''
  if (rate < 0) return 'improvement-good' // 负值意味着污染物减少，是好事
  if (rate > 0) return 'improvement-bad'  // 正值意味着污染物增加，是坏事
  return ''
}

/**
 * 格式化日期
 * @param {string} date - 日期字符串
 * @returns {string} 格式化后的日期
 */
export const formatDate = (date) => {
  if (/^\d{4}$/.test(date)) {
    return date + '年'
  }
  return date
} 