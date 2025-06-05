/**
 * AQI（空气质量指数）相关工具函数
 */

/**
 * 根据AQI值获取空气质量等级描述
 * @param {number} aqi - 空气质量指数值
 * @returns {string} 空气质量等级描述
 */
export function getAqiLevelName(aqi) {
  if (aqi <= 50) return '优';
  if (aqi <= 100) return '良';
  if (aqi <= 150) return '轻度污染';
  if (aqi <= 200) return '中度污染';
  if (aqi <= 300) return '重度污染';
  return '严重污染';
}

/**
 * 根据AQI值获取空气质量等级类名
 * @param {number} aqi - 空气质量指数值
 * @returns {string} 空气质量等级对应的CSS类名
 */
export function getAqiLevelClass(aqi) {
  if (aqi <= 50) return 'level-good';
  if (aqi <= 100) return 'level-moderate';
  if (aqi <= 150) return 'level-unhealthy-sensitive';
  if (aqi <= 200) return 'level-unhealthy';
  if (aqi <= 300) return 'level-very-unhealthy';
  return 'level-hazardous';
}

/**
 * 根据AQI值获取空气质量等级信息（完整版）
 * @param {number} aqi - 空气质量指数值
 * @returns {Object} 包含等级名称和CSS类名的对象
 */
export function getAqiLevel(aqi) {
  return {
    name: getAqiLevelName(aqi),
    className: getAqiLevelClass(aqi)
  };
}

/**
 * 获取AQI值对应的健康建议
 * @param {number} aqi - 空气质量指数值
 * @returns {string} 健康建议文本
 */
export function getHealthTips(aqi) {
  if (aqi <= 50) {
    return '空气质量令人满意，基本无空气污染，各类人群可正常活动。';
  } else if (aqi <= 100) {
    return '空气质量可接受，但某些污染物可能对极少数异常敏感人群健康有较弱影响。';
  } else if (aqi <= 150) {
    return '轻度污染，敏感人群症状有轻度加剧，健康人群出现刺激症状。建议儿童、老年人及心脏病、呼吸系统疾病患者减少长时间、高强度的户外锻炼。';
  } else if (aqi <= 200) {
    return '中度污染，进一步加剧敏感人群症状，可能对健康人群心脏、呼吸系统有影响。建议疾病患者避免长时间、高强度的户外锻练，一般人群适量减少户外运动。';
  } else if (aqi <= 300) {
    return '重度污染，心脏病和肺病患者症状显著加剧，运动耐受力降低，健康人群普遍出现症状。建议儿童、老年人和心脏病、肺病患者应停留在室内，停止户外运动，一般人群减少户外运动。';
  } else {
    return '严重污染，健康人群运动耐受力降低，有明显强烈症状，提前出现某些疾病。建议儿童、老年人和病人应当留在室内，避免体力消耗，一般人群应避免户外活动。';
  }
}

/**
 * 根据PM2.5浓度获取等级描述
 * @param {number} value - PM2.5浓度值 (μg/m³)
 * @returns {string} 等级描述
 */
export function getPM25Level(value) {
  if (value <= 35) return 'I级';
  if (value <= 75) return 'II级';
  if (value <= 115) return 'III级';
  if (value <= 150) return 'IV级';
  if (value <= 250) return 'V级';
  return 'VI级';
}

/**
 * 根据PM10浓度获取等级描述
 * @param {number} value - PM10浓度值 (μg/m³)
 * @returns {string} 等级描述
 */
export function getPM10Level(value) {
  if (value <= 50) return 'I级';
  if (value <= 150) return 'II级';
  if (value <= 250) return 'III级';
  if (value <= 350) return 'IV级';
  if (value <= 420) return 'V级';
  return 'VI级';
}

/**
 * 根据SO2浓度获取等级描述
 * @param {number} value - SO2浓度值 (μg/m³)
 * @returns {string} 等级描述
 */
export function getSO2Level(value) {
  if (value <= 50) return 'I级';
  if (value <= 150) return 'II级';
  if (value <= 475) return 'III级';
  if (value <= 800) return 'IV级';
  if (value <= 1600) return 'V级';
  return 'VI级';
}

/**
 * 根据NO2浓度获取等级描述
 * @param {number} value - NO2浓度值 (μg/m³)
 * @returns {string} 等级描述
 */
export function getNO2Level(value) {
  if (value <= 40) return 'I级';
  if (value <= 80) return 'II级';
  if (value <= 180) return 'III级';
  if (value <= 280) return 'IV级';
  if (value <= 565) return 'V级';
  return 'VI级';
}

/**
 * 根据O3浓度获取等级描述
 * @param {number} value - O3浓度值 (μg/m³)
 * @returns {string} 等级描述
 */
export function getO3Level(value) {
  if (value <= 100) return 'I级';
  if (value <= 160) return 'II级';
  if (value <= 215) return 'III级';
  if (value <= 265) return 'IV级';
  if (value <= 800) return 'V级';
  return 'VI级';
}

/**
 * 根据CO浓度获取等级描述
 * @param {number} value - CO浓度值 (mg/m³)
 * @returns {string} 等级描述
 */
export function getCOLevel(value) {
  if (value <= 2) return 'I级';
  if (value <= 4) return 'II级';
  if (value <= 14) return 'III级';
  if (value <= 24) return 'IV级';
  if (value <= 36) return 'V级';
  return 'VI级';
}

/**
 * 根据污染物类型和值获取对应的等级
 * @param {string} pollutantType - 污染物类型 (aqi, pm25, pm10, so2, no2, o3, co)
 * @param {number} value - 污染物浓度值
 * @returns {string} 等级描述
 */
export function getPollutantLevel(pollutantType, value) {
  switch (pollutantType) {
    case 'aqi':
      return getAqiLevel(value);
    case 'pm25':
    case 'pm2_5':
      return getPM25Level(value);
    case 'pm10':
      return getPM10Level(value);
    case 'so2':
      return getSO2Level(value);
    case 'no2':
      return getNO2Level(value);
    case 'o3':
      return getO3Level(value);
    case 'co':
      return getCOLevel(value);
    default:
      return '未知';
  }
}

/**
 * 获取污染物等级对应的颜色类型
 * @param {string} level - 污染物等级
 * @returns {string} element-ui 标签颜色类型
 */
export function getLevelTagType(level) {
  if (level.includes('I级')) return 'success';
  if (level.includes('II级')) return 'success';
  if (level.includes('III级')) return 'warning';
  if (level.includes('IV级')) return 'warning';
  if (level.includes('V级')) return 'danger';
  if (level.includes('VI级')) return 'danger';
  
  // AQI等级
  if (level === '优') return 'success';
  if (level === '良') return 'success';
  if (level.includes('轻度')) return 'warning';
  if (level.includes('中度')) return 'warning';
  if (level.includes('重度')) return 'danger';
  if (level.includes('严重')) return 'danger';
  
  return 'info';
} 