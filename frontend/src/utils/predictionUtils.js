/**
 * 预测相关的工具函数和常量
 */

// 定义AQI等级常量
const airQualityLevels = {
  excellent: { min: 0, max: 50, color: '#00e400' },
  good: { min: 51, max: 100, color: '#ffff00' },
  moderate: { min: 101, max: 150, color: '#ff7e00' },
  'unhealthy-sensitive': { min: 151, max: 200, color: '#ff0000' },
  unhealthy: { min: 201, max: 300, color: '#99004c' },
  'very-unhealthy': { min: 301, max: 500, color: '#7e0023' },
  hazardous: { min: 501, max: Infinity, color: '#7e0023' }
};

/**
 * 获取基于AQI等级的健康建议
 * @param {number} aqi - AQI值
 * @returns {Object} 不同人群的健康建议
 */
export function getHealthRecommendations(aqi) {
  if (aqi <= 50) {
    return {
      general: '空气质量令人满意，基本无空气污染',
      sensitive: '空气质量令人满意，基本无空气污染',
      outdoor: '各类人群可正常活动',
    };
  } else if (aqi <= 100) {
    return {
      general: '可以正常进行室外活动',
      sensitive: '极少数异常敏感人群应减少户外活动',
      outdoor: '除少数对污染物特别敏感的人群外，其他人群可以正常活动',
    };
  } else if (aqi <= 150) {
    return {
      general: '建议一般人群减少户外运动',
      sensitive: '儿童、老人及心脏病、呼吸系统疾病患者应避免长时间、高强度的户外锻炼',
      outdoor: '适当减少户外活动',
    };
  } else if (aqi <= 200) {
    return {
      general: '建议一般人群减少户外运动',
      sensitive: '儿童、老人及心脏病、呼吸系统疾病患者避免长时间、高强度的户外锻炼，一般人群适量减少户外运动',
      outdoor: '尽量减少户外活动',
    };
  } else if (aqi <= 300) {
    return {
      general: '建议一般人群减少户外运动',
      sensitive: '儿童、老人及心脏病、呼吸系统疾病患者应停留在室内，避免户外活动，一般人群尽量减少户外活动',
      outdoor: '停止户外活动，匆匆往返于户外',
    };
  } else {
    return {
      general: '建议一般人群停止户外运动',
      sensitive: '儿童、老人及心脏病、呼吸系统疾病患者应停留在室内，避免户外活动，一般人群避免户外活动',
      outdoor: '停止户外活动，匆匆往返于户外',
    };
  }
}

/**
 * 获取各个指标的影响因素
 * @param {string} indicator - 指标名称
 * @returns {Array} 影响因素列表
 */
export function getInfluencingFactors(indicator) {
  const factors = {
    AQI: [
      { icon: 'car', factor: '交通排放', impact: '汽车尾气中的颗粒物和氮氧化物是城市空气污染的主要来源之一' },
      { icon: 'factory', factor: '工业活动', impact: '工厂排放的废气中含有多种污染物，包括二氧化硫、氮氧化物和挥发性有机物' },
      { icon: 'weather', factor: '气象条件', impact: '风速、降水和大气稳定性等气象条件会影响污染物的扩散和积累' },
    ],
    PM25: [
      { icon: 'smoke', factor: '燃烧活动', impact: '化石燃料燃烧和生物质燃烧是PM2.5的主要来源' },
      { icon: 'factory', factor: '工业排放', impact: '工业生产过程中排放的细颗粒物' },
      { icon: 'car', factor: '交通排放', impact: '机动车尾气排放的颗粒物及其前体物' },
    ],
    PM10: [
      { icon: 'dust', factor: '扬尘', impact: '建筑施工、道路扬尘和自然风尘是PM10的主要来源' },
      { icon: 'car', factor: '交通排放', impact: '机动车排放的颗粒物' },
      { icon: 'factory', factor: '工业排放', impact: '工业生产过程中产生的粗颗粒物' },
    ],
    SO2: [
      { icon: 'factory', factor: '工业排放', impact: '煤炭和石油等含硫燃料的燃烧过程' },
      { icon: 'power-plant', factor: '发电厂', impact: '火力发电厂燃烧煤炭产生的二氧化硫' },
      { icon: 'heating', factor: '冬季供暖', impact: '冬季燃煤供暖会导致二氧化硫浓度升高' },
    ],
    NO2: [
      { icon: 'car', factor: '交通排放', impact: '机动车尾气是城市NO2的主要来源' },
      { icon: 'factory', factor: '工业活动', impact: '高温燃烧过程中产生的氮氧化物' },
      { icon: 'power-plant', factor: '发电厂', impact: '火力发电厂燃烧过程中产生的氮氧化物' },
    ],
    O3: [
      { icon: 'sun', factor: '阳光照射', impact: '强烈的阳光照射会促进臭氧的生成' },
      { icon: 'car', factor: '前体物排放', impact: '氮氧化物和挥发性有机物在阳光下发生光化学反应生成臭氧' },
      { icon: 'temperature', factor: '高温天气', impact: '高温天气有利于臭氧的生成和累积' },
    ],
    CO: [
      { icon: 'car', factor: '交通排放', impact: '机动车尾气中的一氧化碳' },
      { icon: 'fire', factor: '不完全燃烧', impact: '燃料不完全燃烧产生的一氧化碳' },
      { icon: 'indoor', factor: '室内污染', impact: '室内燃烧和取暖设备可能产生一氧化碳' },
    ],
    TEMP: [
      { icon: 'sun', factor: '日照强度', impact: '阳光照射是温度变化的主要因素' },
      { icon: 'cloud', factor: '云层覆盖', impact: '云层会影响太阳辐射到达地面的量，从而影响温度' },
      { icon: 'wind', factor: '气流活动', impact: '空气流动会带来温度变化' },
    ],
    HUMID: [
      { icon: 'water', factor: '水体蒸发', impact: '附近水体的蒸发会增加空气湿度' },
      { icon: 'rain', factor: '降水', impact: '降水前后空气湿度通常较高' },
      { icon: 'plant', factor: '植被蒸腾', impact: '植物的蒸腾作用会向空气中释放水分' },
    ],
    WIND: [
      { icon: 'pressure', factor: '气压差', impact: '不同区域的气压差是风形成的主要原因' },
      { icon: 'terrain', factor: '地形影响', impact: '山谷、峡谷等地形会影响风的速度和方向' },
      { icon: 'building', factor: '城市建筑', impact: '高大建筑会改变局部风向和风速' },
    ],
  };

  return factors[indicator] || [
    { icon: 'info', factor: '暂无数据', impact: '暂无该指标的影响因素数据' },
  ];
}

/**
 * 获取基于指标和数据的预测建议
 * @param {string} indicator - 指标名称
 * @param {number} value - 当前值
 * @param {Object} statistics - 统计数据，包含平均值
 * @returns {Object} 包含建议标题和内容的对象
 */
export function getPredictionSuggestions(indicator, value, statistics) {
  const average = statistics?.average || value;
  
  if (indicator === 'AQI') {
    // AQI建议
    const level = getAqiLevel(value);
    
    if (level === 'excellent' || level === 'good') {
      return {
        title: '空气质量良好',
        content: '当前空气质量状况良好，适合户外活动，可以正常安排户外活动和体育锻炼。',
      };
    } else if (level === 'moderate') {
      return {
        title: '空气质量中等',
        content: '空气质量可接受，但某些污染物可能对极少数异常敏感人群健康有较弱影响，请敏感人群减少户外活动。',
      };
    } else if (level === 'unhealthy-sensitive') {
      return {
        title: '对敏感人群不健康',
        content: '空气质量较差，敏感人群（老人、儿童和呼吸系统疾病患者）应当减少户外活动，一般人群适量减少户外运动。',
      };
    } else if (level === 'unhealthy') {
      return {
        title: '空气不健康',
        content: '空气污染严重，敏感人群应避免户外活动，一般人群应减少户外活动，外出时建议佩戴口罩。',
      };
    } else if (level === 'very-unhealthy') {
      return {
        title: '空气非常不健康',
        content: '空气污染严重，建议尽量留在室内，减少开窗时间，外出务必佩戴防护口罩。',
      };
    } else {
      return {
        title: '危险空气质量',
        content: '空气污染极为严重，所有人群应避免户外活动，外出时必须采取防护措施。',
      };
    }
  } else if (indicator === 'PM25') {
    // PM2.5建议
    if (value <= 35) {
      return {
        title: 'PM2.5浓度低',
        content: '当前PM2.5浓度较低，空气较为清新，适合各类户外活动。',
      };
    } else if (value <= 75) {
      return {
        title: 'PM2.5浓度中等',
        content: '当前PM2.5浓度中等，敏感人群应减少长时间户外活动，普通人群可正常活动。',
      };
    } else {
      return {
        title: 'PM2.5浓度高',
        content: '当前PM2.5浓度较高，建议减少户外活动，外出时佩戴口罩，避免剧烈运动。',
      };
    }
  } else if (indicator === 'PM10') {
    // PM10建议
    if (value <= 50) {
      return {
        title: 'PM10浓度低',
        content: '当前PM10浓度较低，空气较为清新，适合各类户外活动。',
      };
    } else if (value <= 150) {
      return {
        title: 'PM10浓度中等',
        content: '当前PM10浓度中等，敏感人群应适当减少户外活动，普通人群可正常活动。',
      };
    } else {
      return {
        title: 'PM10浓度高',
        content: '当前PM10浓度较高，建议减少户外活动，外出时佩戴口罩，避免在灰尘大的环境中长时间停留。',
      };
    }
  } else if (indicator === 'TEMP') {
    // 温度建议
    if (value < 10) {
      return {
        title: '温度较低',
        content: '当前温度较低，外出需注意保暖，穿着厚实的衣物，避免受凉感冒。',
      };
    } else if (value < 20) {
      return {
        title: '温度适宜',
        content: '当前温度舒适，适合户外活动，但早晚温差可能较大，建议适当增减衣物。',
      };
    } else if (value < 30) {
      return {
        title: '温度温暖',
        content: '当前温度温暖，适合户外活动，注意补充水分，避免长时间暴露在阳光下。',
      };
    } else {
      return {
        title: '温度较高',
        content: '当前温度较高，建议减少户外活动，避免午间高温时段出行，注意防暑降温和补充水分。',
      };
    }
  } else if (indicator === 'HUMID') {
    // 湿度建议
    if (value < 30) {
      return {
        title: '湿度偏低',
        content: '当前湿度较低，空气干燥，建议增加室内湿度，多补充水分，注意皮肤保湿。',
      };
    } else if (value < 60) {
      return {
        title: '湿度适宜',
        content: '当前湿度适中，空气舒适，适合各类户外活动。',
      };
    } else {
      return {
        title: '湿度偏高',
        content: '当前湿度较高，可能感到闷热，注意保持室内通风，防止物品发霉，减少剧烈运动。',
      };
    }
  } else {
    // 其他指标的通用建议
    if (value < average * 0.8) {
      return {
        title: `${indicator}浓度较低`,
        content: `当前${indicator}浓度低于平均水平，空气质量状况良好。`,
      };
    } else if (value < average * 1.2) {
      return {
        title: `${indicator}浓度一般`,
        content: `当前${indicator}浓度接近平均水平，空气质量状况一般。`,
      };
    } else {
      return {
        title: `${indicator}浓度较高`,
        content: `当前${indicator}浓度高于平均水平，建议关注空气质量变化。`,
      };
    }
  }
}

/**
 * 获取AQI等级
 * @param {number} value - AQI值
 * @returns {string} AQI等级
 */
function getAqiLevel(value) {
  if (value <= 50) return 'excellent';
  if (value <= 100) return 'good';
  if (value <= 150) return 'moderate';
  if (value <= 200) return 'unhealthy-sensitive';
  if (value <= 300) return 'unhealthy';
  if (value <= 500) return 'very-unhealthy';
  return 'hazardous';
} 