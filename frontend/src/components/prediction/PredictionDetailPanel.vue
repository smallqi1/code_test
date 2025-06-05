<template>
  <div class="prediction-detail-panel">
    <div class="panel-header">
      <div class="title">预测详情</div>
      <div class="actions">
        <el-button 
          v-if="!noData" 
          icon="Refresh" 
          size="small" 
          circle 
          @click="$emit('refresh')" 
          :loading="loading"
        />
      </div>
    </div>
      
    <div v-if="loading" class="loading-container">
      <el-skeleton animated :rows="6" />
    </div>
            
    <div v-else-if="noData" class="empty-state">
      <el-empty description="暂无预测数据">
        <template #description>
          <p class="empty-text">暂无预测数据</p>
          <p class="empty-subtext">请选择城市和指标，然后点击"开始预测"按钮</p>
        </template>
      </el-empty>
    </div>
            
    <div v-else class="panel-content">
      <!-- 关键指标展示区 -->
      <div class="key-indicators">
        <div class="section-title">关键指标</div>
        <div class="indicators-grid">
          <div 
            v-for="(item, idx) in keyIndicators" 
            :key="idx" 
            class="indicator-card"
            :class="{'highlight': item.name === selectedIndicatorLabel}"
            :style="{borderColor: item.color}"
          >
            <div class="indicator-name">{{ item.name }}</div>
            <div class="indicator-value" :style="{color: item.color}">
              {{ item.value }}
              <span class="indicator-unit">{{ item.unit }}</span>
            </div>
            <div v-if="item.qualityLevel" class="indicator-quality-level" :style="{background: item.color}">
              {{ item.qualityLevel }}
            </div>
            <div class="indicator-trend" v-if="item.trend">
              <span :class="[
                'trend-icon', 
                item.trend === 'up' ? 'trend-up' : 
                item.trend === 'down' ? 'trend-down' : 'trend-stable'
              ]">
                {{ item.trend === 'up' ? '↑' : item.trend === 'down' ? '↓' : '→' }}
              </span>
              <span class="trend-text">{{ item.trendValue }}</span>
            </div>
          </div>
        </div>
      </div>
              
      <!-- 健康影响评估区 -->
      <div class="health-impact" v-if="hasAqiData">
        <div class="section-title">健康影响评估</div>
        <div class="health-level" :style="{background: aqiLevelColor}">
          <span class="level-text">{{ aqiLevelText }}</span>
        </div>
        <div class="health-cards">
          <div class="health-card">
            <div class="card-title">
              <i class="el-icon-user"></i> 一般人群
            </div>
            <div class="card-content">{{ healthRecommendations.general }}</div>
          </div>
          <div class="health-card">
            <div class="card-title">
              <i class="el-icon-warning"></i> 敏感人群
            </div>
            <div class="card-content">{{ healthRecommendations.sensitive }}</div>
          </div>
          <div class="health-card">
            <div class="card-title">
              <i class="el-icon-position"></i> 户外活动建议
            </div>
            <div class="card-content">{{ healthRecommendations.outdoor }}</div>
          </div>
        </div>
      </div>
      
      <!-- 每日趋势分析 -->
      <div class="daily-trend">
        <div class="section-title">趋势分析</div>
        <div class="trend-stats">
          <div class="stat-item">
            <div class="stat-label">均值</div>
            <div class="stat-value">{{ statistics.average }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">最大值</div>
            <div class="stat-value">{{ statistics.max }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">最小值</div>
            <div class="stat-value">{{ statistics.min }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">标准差</div>
            <div class="stat-value">{{ statistics.standardDeviation }}</div>
          </div>
        </div>
        <div class="trend-visualization">
          <div class="trend-arrow" :class="trendClass">
            <i :class="trendIconClass"></i>
          </div>
          <div class="trend-percentage">{{ trendPercentage }}</div>
        </div>
        <div class="trend-description">
          <p v-if="noData || trendPercentage === '数据不足'">
            目前没有足够的数据来分析{{ selectedIndicatorLabel }}的趋势变化。
          </p>
          <template v-else>
            <p>在预测周期内，{{ selectedIndicatorLabel }}的均值为{{ statistics.average }}，波动范围为{{ statistics.min }} - {{ statistics.max }}。</p>
            <p v-if="statistics.trend === 'up'">
              总体呈<span class="trend-up">上升趋势</span>，这表明{{ selectedIndicatorLabel }}可能会逐渐增加。
            </p>
            <p v-else-if="statistics.trend === 'down'">
              总体呈<span class="trend-down">下降趋势</span>，这表明{{ selectedIndicatorLabel }}可能会逐渐降低。
            </p>
            <p v-else>
              总体保持<span class="trend-stable">稳定</span>，这表明{{ selectedIndicatorLabel }}变化不大。
            </p>
            <p v-if="props.selectedIndicator === 'AQI' || props.selectedIndicator === 'PM2.5'">
              空气质量指标的上升通常表示污染加重，下降则表示空气质量改善。
            </p>
          </template>
        </div>
      </div>
        
      <!-- 影响因素分析 -->
      <div class="influencing-factors">
        <div class="section-title">影响因素分析</div>
        <div class="factors-grid">
          <div 
            v-for="(factor, idx) in influencingFactors" 
            :key="idx"
            class="factor-card"
          >
            <div class="factor-header">
              <div class="factor-icon">
                <i :class="`icon-${factor.icon}`"></i>
              </div>
              <div class="factor-title">{{ factor.factor }}</div>
            </div>
            <div class="factor-content">
              <div class="factor-description">{{ factor.impact }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 预测建议 -->
      <div class="prediction-suggestions">
        <div class="section-title">预测建议</div>
        <el-card class="suggestion-card" shadow="hover">
          <template #header>
            <div class="suggestion-header">
              <i class="el-icon-info suggestion-icon"></i>
              <span class="suggestion-title">{{ suggestions.title }}</span>
            </div>
          </template>
          <div class="suggestion-content">{{ suggestions.content }}</div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { getIndicatorLabel, getIndicatorUnit, getAqiColor, formatValue } from '@/utils/airQualityUtils';
import { getHealthRecommendations, getInfluencingFactors, getPredictionSuggestions } from '@/utils/predictionUtils';
import { ElSkeleton, ElEmpty, ElCollapse, ElCollapseItem, ElCard, ElButton } from 'element-plus';

// 组件属性定义
const props = defineProps({
  forecastData: {
    type: Object,
    default: () => ({})
  },
  selectedIndicator: {
    type: String,
    default: 'AQI'
  },
  selectedCity: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// 定义事件
const emit = defineEmits(['refresh']);

// 数据可用性检查
const noData = computed(() => {
  // 简化调试输出，只在开发环境打印
  if (process.env.NODE_ENV === 'development') {
    // 避免打印整个数据对象
    console.log("检查预测数据可用性:", !!props.forecastData && !!props.forecastData.indicators);
  }
  
  // 松散检查：不同的数据结构都能处理
  if (!props.forecastData) return true;
  
  // 检查第一种可能的数据结构（indicators 属性，包含 forecast 子数组）
  if (props.forecastData.indicators && 
      props.forecastData.indicators[props.selectedIndicator] && 
      props.forecastData.indicators[props.selectedIndicator].forecast && 
      props.forecastData.indicators[props.selectedIndicator].forecast.length > 0) {
    return false;
  }
  
  // 检查第二种可能的数据结构（直接包含指标）
  if (props.forecastData[props.selectedIndicator] && 
      ((props.forecastData[props.selectedIndicator].forecast && 
        props.forecastData[props.selectedIndicator].forecast.length > 0) || 
       (props.forecastData[props.selectedIndicator].values && 
        props.forecastData[props.selectedIndicator].values.length > 0))) {
    return false;
  }
  
  return true;
});

// 获取当前选中指标的数据
const currentIndicatorData = computed(() => {
  if (noData.value) return { forecast: [], dates: [] };
  
  // 检查第一种数据结构 (indicators 属性，包含 forecast 子数组)
  if (props.forecastData.indicators && 
      props.forecastData.indicators[props.selectedIndicator]) {
    
    // 提取预测数据
    const forecastArray = props.forecastData.indicators[props.selectedIndicator].forecast || [];
    
    // 提取日期（如果预测数据中有日期字段）
    const dates = forecastArray.map(item => item.date || '');
    
    // 提取数值（如果是对象数组，则提取value字段）
    const forecast = forecastArray.map(item => 
      typeof item === 'object' && item !== null ? 
        parseFloat(item.value) : parseFloat(item)
    );
    
    return { forecast, dates };
  }
  
  // 检查第二种数据结构（直接包含指标）
  if (props.forecastData[props.selectedIndicator]) {
    const indicatorData = props.forecastData[props.selectedIndicator];
    
    let forecast = [];
    let dates = [];
    
    // 处理不同的数据格式
    if (indicatorData.forecast && indicatorData.forecast.length > 0) {
      forecast = indicatorData.forecast.map(item => 
        typeof item === 'object' && item !== null ? 
          parseFloat(item.value) : parseFloat(item)
      );
      dates = indicatorData.forecast.map(item => 
        typeof item === 'object' && item !== null && item.date ? 
          item.date : ''
      );
    } else if (indicatorData.values && indicatorData.values.length > 0) {
      forecast = indicatorData.values.map(v => parseFloat(v));
      dates = props.forecastData.dates || indicatorData.dates || [];
    }
    
    return { forecast, dates };
  }
  
  return { forecast: [], dates: [] };
});

// 检查是否有AQI数据
const hasAqiData = computed(() => {
  if (!props.forecastData) return false;
  
  // 检查第一种数据结构
  if (props.forecastData.indicators && 
      props.forecastData.indicators.AQI && 
      props.forecastData.indicators.AQI.forecast && 
      props.forecastData.indicators.AQI.forecast.length > 0) {
    return true;
  }
  
  // 检查第二种数据结构
  if (props.forecastData.AQI && 
      ((props.forecastData.AQI.forecast && props.forecastData.AQI.forecast.length > 0) ||
       (props.forecastData.AQI.values && props.forecastData.AQI.values.length > 0))) {
    return true;
  }
  
  return false;
});

// 当前AQI值
const currentAqi = computed(() => {
  if (!hasAqiData.value) return 0;
  
  // 检查第一种数据结构
  if (props.forecastData.indicators && props.forecastData.indicators.AQI) {
    // 从forecast数组获取第一个值，如果是对象则取value属性
    const firstItem = props.forecastData.indicators.AQI.forecast[0];
    return typeof firstItem === 'object' ? parseFloat(firstItem.value) : parseFloat(firstItem);
  }
  
  // 检查第二种数据结构
  if (props.forecastData.AQI) {
    if (props.forecastData.AQI.forecast && props.forecastData.AQI.forecast.length > 0) {
      const firstItem = props.forecastData.AQI.forecast[0];
      return typeof firstItem === 'object' ? parseFloat(firstItem.value) : parseFloat(firstItem);
    }
    
    if (props.forecastData.AQI.values && props.forecastData.AQI.values.length > 0) {
      return parseFloat(props.forecastData.AQI.values[0]);
    }
  }
  
  return 0;
});

// AQI等级和颜色
const aqiLevelColor = computed(() => getAqiColor(currentAqi.value));
const aqiLevelText = computed(() => {
  const aqi = currentAqi.value;
  if (aqi <= 50) return '优';
  if (aqi <= 100) return '良';
  if (aqi <= 150) return '轻度污染';
  if (aqi <= 200) return '中度污染';
  if (aqi <= 300) return '重度污染';
  return '严重污染';
});

// 获取健康建议
const healthRecommendations = computed(() => {
  return getHealthRecommendations(currentAqi.value);
});

// 关键指标展示
const keyIndicators = computed(() => {
  if (noData.value) return [];
  
  const indicators = ['AQI', 'PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'CO'];
  return indicators
    .filter(ind => {
      // 检查第一种数据结构
      if (props.forecastData.indicators && 
          props.forecastData.indicators[ind] && 
          props.forecastData.indicators[ind].forecast && 
          props.forecastData.indicators[ind].forecast.length > 0) {
        return true;
      }
      
      // 检查第二种数据结构
      if (props.forecastData[ind] && 
          ((props.forecastData[ind].forecast && props.forecastData[ind].forecast.length > 0) ||
           (props.forecastData[ind].values && props.forecastData[ind].values.length > 0))) {
        return true;
      }
      
      return false;
    })
    .map(ind => {
      // 获取值数组（确定数据结构）
      let forecastArray = [];
      if (props.forecastData.indicators && props.forecastData.indicators[ind]) {
        forecastArray = props.forecastData.indicators[ind].forecast || [];
      } else if (props.forecastData[ind]) {
        forecastArray = props.forecastData[ind].forecast || props.forecastData[ind].values || [];
      }
      
      // 提取数值（如果是对象数组，则提取value字段）
      const values = forecastArray.map(item => 
        typeof item === 'object' && item !== null ? parseFloat(item.value) : parseFloat(item)
      );
      
      // 确保值有效
      if (!values || values.length === 0 || isNaN(values[0])) {
        return { 
          name: getIndicatorLabel(ind),
          value: '—',
          unit: getIndicatorUnit(ind),
          color: '#909399',
          trend: 'stable',
          trendValue: '数据不足'
        };
      }
      
      const currentValue = values[0];
      
      let trend = 'stable';
      let trendValue = '';
      
      if (values.length > 1 && !isNaN(values[1])) {
        const nextDayValue = values[1];
        
        // 避免除以零
        if (currentValue === 0) {
          trend = nextDayValue > 0 ? 'up' : 'stable';
          trendValue = nextDayValue > 0 ? '有所增加' : '持平';
        } else {
          const change = ((nextDayValue - currentValue) / currentValue * 100);
          
          // 处理异常值
          if (isNaN(change) || !isFinite(change)) {
            trendValue = '持平';
          } else if (nextDayValue > currentValue * 1.02) {
            trend = 'up';
            trendValue = `+${change.toFixed(1)}%`;
          } else if (nextDayValue < currentValue * 0.98) {
            trend = 'down';
            trendValue = `${change.toFixed(1)}%`;
          } else {
            trendValue = '持平';
          }
        }
      } else {
        trendValue = '—';
      }
      
      // 为AQI和PM2.5等污染物指标添加质量评级
      let qualityLevel = '';
      if (ind === 'AQI') {
        if (currentValue <= 50) qualityLevel = '优';
        else if (currentValue <= 100) qualityLevel = '良';
        else if (currentValue <= 150) qualityLevel = '轻度污染';
        else if (currentValue <= 200) qualityLevel = '中度污染';
        else if (currentValue <= 300) qualityLevel = '重度污染';
        else qualityLevel = '严重污染';
      }
      
      return { 
        name: getIndicatorLabel(ind),
        value: formatValue(ind, currentValue),
        unit: getIndicatorUnit(ind),
        color: ind === 'AQI' ? getAqiColor(currentValue) : '#409EFF',
        trend,
        trendValue,
        qualityLevel
      };
    });
});

// 选中指标的标签
const selectedIndicatorLabel = computed(() => {
  return getIndicatorLabel(props.selectedIndicator);
});

// 统计计算
const statistics = computed(() => {
  if (noData.value) {
    return { 
      average: '0', 
      max: '0', 
      min: '0', 
      standardDeviation: '0',
      trend: 'stable'
    };
  }
  
  const values = currentIndicatorData.value.forecast;
  
  // 确保有有效数据
  if (!values || values.length === 0) {
    return { 
      average: '0', 
      max: '0', 
      min: '0', 
      standardDeviation: '0',
      trend: 'stable'
    };
  }
  
  // 过滤无效值
  const validValues = values.filter(val => !isNaN(val) && val !== null && val !== undefined);
  
  // 如果没有有效值，返回默认值
  if (validValues.length === 0) {
    return { 
      average: '0', 
      max: '0', 
      min: '0', 
      standardDeviation: '0',
      trend: 'stable'
    };
  }
  
  // 计算平均值
  const sum = validValues.reduce((acc, val) => acc + val, 0);
  const avg = sum / validValues.length;
  
  // 计算最大值和最小值
  const max = Math.max(...validValues);
  const min = Math.min(...validValues);
  
  // 计算标准差
  const squaredDifferences = validValues.map(val => Math.pow(val - avg, 2));
  const variance = squaredDifferences.reduce((acc, val) => acc + val, 0) / validValues.length;
  const stdDev = Math.sqrt(variance);
  
  // 判断趋势
  let trend = 'stable';
  if (validValues.length >= 2) {
    const firstHalf = validValues.slice(0, Math.floor(validValues.length / 2));
    const secondHalf = validValues.slice(Math.floor(validValues.length / 2));
    
    const firstHalfAvg = firstHalf.reduce((acc, val) => acc + val, 0) / firstHalf.length;
    const secondHalfAvg = secondHalf.reduce((acc, val) => acc + val, 0) / secondHalf.length;
    
    if (secondHalfAvg > firstHalfAvg * 1.05) {
      trend = 'up';
    } else if (secondHalfAvg < firstHalfAvg * 0.95) {
      trend = 'down';
    }
  }
  
  // 格式化返回值
  return {
    average: formatValue(props.selectedIndicator, avg),
    max: formatValue(props.selectedIndicator, max),
    min: formatValue(props.selectedIndicator, min),
    standardDeviation: stdDev.toFixed(2),
    trend
  };
});

// 趋势相关计算
const trendPercentage = computed(() => {
  if (noData.value) return '变化不大';
  
  const values = currentIndicatorData.value.forecast;
  
  // 确保有足够的数据来计算趋势
  if (!values || values.length < 2) return '数据不足';
  
  // 过滤无效值
  const validValues = values.filter(val => !isNaN(val) && val !== null && val !== undefined);
  
  // 如果有效值不足，返回默认值
  if (validValues.length < 2) return '数据不足';
  
  const firstHalf = validValues.slice(0, Math.floor(validValues.length / 2));
  const secondHalf = validValues.slice(Math.floor(validValues.length / 2));
  
  const firstHalfAvg = firstHalf.reduce((acc, val) => acc + val, 0) / firstHalf.length;
  const secondHalfAvg = secondHalf.reduce((acc, val) => acc + val, 0) / secondHalf.length;
  
  // 避免除以零
  if (firstHalfAvg === 0) return '基准值为零';
  
  const change = ((secondHalfAvg - firstHalfAvg) / firstHalfAvg * 100);
  
  // 处理NaN和非正常值
  if (isNaN(change) || !isFinite(change)) return '变化不大';
  
  if (Math.abs(change) < 2) return '变化不大';
  return change > 0 ? `上升 ${change.toFixed(1)}%` : `下降 ${Math.abs(change).toFixed(1)}%`;
});

const trendClass = computed(() => {
  return `trend-${statistics.value.trend}`;
});

const trendIconClass = computed(() => {
  if (statistics.value.trend === 'up') return 'el-icon-top';
  if (statistics.value.trend === 'down') return 'el-icon-bottom';
  return 'el-icon-right';
});

// 影响因素
const influencingFactors = computed(() => {
  return getInfluencingFactors(props.selectedIndicator);
});

// 预测建议
const suggestions = computed(() => {
  if (noData.value) {
    return {
      title: '暂无建议',
      content: '请先进行预测，获取数据后将提供相应建议'
    };
  }
  
  const currentValue = currentIndicatorData.value.forecast[0];
  return getPredictionSuggestions(props.selectedIndicator, currentValue, statistics.value);
});

// 监听数据变化，更新组件
watch(() => props.forecastData, (newData) => {
  if (newData && Object.keys(newData).length > 0) {
    // 仅在开发环境下打印简化的日志信息
    if (process.env.NODE_ENV === 'development') {
      // 避免打印大量数据，只打印结构信息
      const dataInfo = {
        hasData: true,
        structure: newData.indicators ? '嵌套indicators' : '直接指标',
        indicatorCount: newData.indicators ? Object.keys(newData.indicators).length : 0
      };
      console.log('预测详情数据已更新:', dataInfo);
    }
    
    // 检查数据是否为空 - 保留这个功能但不打印详细内容
    const hasData = newData.indicators ? 
      Object.values(newData.indicators).some(ind => ind.forecast && ind.forecast.length > 0) :
      Object.values(newData).some(ind => 
        (ind.forecast && ind.forecast.length > 0) || (ind.values && ind.values.length > 0)
      );
    
    // 只在数据无效时打印警告
    if (!hasData) {
      console.warn('预测数据无效或为空');
    }
  }
}, { deep: true });

</script>

<style scoped>
.prediction-detail-panel {
  width: 100%;
  height: 100%;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
}

.panel-header .title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.panel-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #606266;
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid #409EFF;
}

.loading-container, .empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.empty-image {
  width: 120px;
  height: 120px;
  opacity: 0.7;
}

.empty-text {
  font-size: 16px;
  color: #909399;
  margin: 8px 0;
}

.empty-subtext {
  font-size: 14px;
  color: #c0c4cc;
}

/* 关键指标样式 */
.indicators-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.indicator-card {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  border-left: 3px solid #409EFF;
  transition: all 0.3s ease;
}

.indicator-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.indicator-card.highlight {
  background: #ecf5ff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}

.indicator-name {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.indicator-value {
  font-size: 18px;
  font-weight: bold;
  color: #409EFF;
}

.indicator-unit {
  font-size: 12px;
  font-weight: normal;
  margin-left: 2px;
}

.indicator-quality-level {
  display: inline-block;
  padding: 2px 6px;
  margin-top: 6px;
  border-radius: 10px;
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.indicator-trend {
  margin-top: 6px;
  font-size: 12px;
  display: flex;
  align-items: center;
}

.trend-icon {
  margin-right: 4px;
}

.trend-up {
  color: #f56c6c;
}

.trend-down {
  color: #67c23a;
}

.trend-stable {
  color: #909399;
}

/* 健康影响评估样式 */
.health-impact {
  margin-bottom: 24px;
}

.health-level {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  color: white;
  font-weight: bold;
  margin-bottom: 12px;
}

.health-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.health-card {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  border-top: 3px solid #409EFF;
}

.card-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.card-title i {
  margin-right: 6px;
}

.card-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

/* 趋势分析样式 */
.daily-trend {
  margin-bottom: 24px;
}

.trend-stats {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.trend-visualization {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.trend-arrow {
  font-size: 24px;
  margin-right: 12px;
}

.trend-up {
  color: #f56c6c;
}

.trend-down {
  color: #67c23a;
}

.trend-stable {
  color: #909399;
}

.trend-percentage {
  font-size: 16px;
  font-weight: bold;
}

.trend-description {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

/* 影响因素分析样式 */
.influencing-factors {
  margin-bottom: 24px;
}

.factors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.factor-card {
  background: #f5f7fa;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: all 0.3s ease;
}

.factor-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.factor-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #ecf5ff;
  border-bottom: 1px solid #e0e6ed;
}

.factor-icon {
  width: 32px;
  height: 32px;
  margin-right: 12px;
  background: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.factor-title {
  font-weight: bold;
  font-size: 14px;
  color: #303133;
}

.factor-content {
  padding: 12px 16px;
}

.factor-description {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

/* 预测建议样式 */
.suggestion-card {
  border-radius: 8px;
  overflow: hidden;
}

.suggestion-header {
  display: flex;
  align-items: center;
}

.suggestion-icon {
  margin-right: 8px;
  color: #409EFF;
}

.suggestion-title {
  font-weight: bold;
  color: #303133;
}

.suggestion-content {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .indicators-grid, .health-cards, .trend-stats {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 480px) {
  .indicators-grid, .health-cards, .trend-stats {
    grid-template-columns: 1fr;
  }
}
</style> 