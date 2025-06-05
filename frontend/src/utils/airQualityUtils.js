/**
 * 空气质量指标相关工具函数
 */

/**
 * 根据AQI值获取对应的颜色
 * @param {number} value - AQI值
 * @returns {string} 颜色值，格式为HEX或RGB
 */
export function getAqiColor(value) {
  if (value <= 50) return '#00e400'; // 优
  if (value <= 100) return '#ffff00'; // 良
  if (value <= 150) return '#ff7e00'; // 轻度污染
  if (value <= 200) return '#ff0000'; // 中度污染
  if (value <= 300) return '#99004c'; // 重度污染
  return '#7e0023'; // 严重污染
}

/**
 * 根据指标类型格式化数值
 * @param {string} indicator - 指标类型，如'AQI'、'PM2.5'等
 * @param {number} value - 数值
 * @returns {string} 格式化后的数值字符串
 */
export function formatValue(indicator, value) {
  if (value === undefined || value === null) return '—';
  
  // 确保value是数字
  const numValue = Number(value);
  if (isNaN(numValue)) return '—';
  
  // 根据不同指标进行格式化
  switch (indicator) {
    case 'AQI':
      return Math.round(numValue).toString();
    case 'PM2.5':
    case 'PM10':
    case 'SO2':
    case 'NO2':
    case 'O3':
      return Math.round(numValue) + ' μg/m³';
    case 'CO':
      return (Math.round(numValue * 10) / 10).toFixed(1) + ' mg/m³';
    case 'TEMP':
    case '温度':
      return Math.round(numValue) + ' °C';
    case '湿度':
    case 'HUMIDITY':
      return Math.round(numValue) + '%';
    default:
      return numValue.toString();
  }
}

/**
 * 获取指标对应的标签文本
 * @param {string} indicator - 指标代码
 * @returns {string} 对应的可读标签
 */
export function getIndicatorLabel(indicator) {
  const labels = {
    'AQI': '空气质量指数',
    'PM2.5': 'PM2.5',
    'PM10': 'PM10',
    'SO2': '二氧化硫',
    'NO2': '二氧化氮',
    'O3': '臭氧',
    'CO': '一氧化碳',
    'TEMP': '温度',
    'HUMIDITY': '湿度'
  };
  
  return labels[indicator] || indicator;
}

/**
 * 获取指标的单位
 * @param {string} indicator - 指标代码
 * @returns {string} 指标单位
 */
export function getIndicatorUnit(indicator) {
  const units = {
    'AQI': '',
    'PM2.5': 'μg/m³',
    'PM10': 'μg/m³',
    'SO2': 'μg/m³',
    'NO2': 'μg/m³',
    'O3': 'μg/m³',
    'CO': 'mg/m³',
    'TEMP': '°C',
    'HUMIDITY': '%'
  };
  
  return units[indicator] || '';
} 