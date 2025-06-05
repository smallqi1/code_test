<template>
  <div class="smart-prediction-page">
    <!-- API状态指示器已隐藏 -->
    
    <!-- API连接警告已隐藏 -->
    
    <div class="prediction-layout">
      <!-- 控制面板 -->
      <PredictionControlPanel
        :cities="cities"
        :selected-city="selectedCity"
        :selected-time-period="selectedTimePeriod"
        :selected-mode="selectedMode"
        :loading="loading"
        :prediction-progress="predictionProgress"
        :prediction-step-text="predictionStepText"
        :status-message="statusMessage"
        :status-type="statusType"
        @update:selectedCity="selectedCity = $event"
        @update:selectedTimePeriod="selectedTimePeriod = $event"
        @update:selectedMode="selectedMode = $event"
        @update:timePeriodType="handleTimePeriodTypeUpdate"
        @startPrediction="startPrediction"
      />
      
      <!-- 图表区域 -->
      <PredictionMainChart
        :forecast-data="forecastData"
        :loading="loading"
        :error="error"
        :selected-indicator="selectedIndicator"
        :selected-time-period="selectedTimePeriod"
        :selected-city="selectedCity"
        @update:selected-indicator="handleIndicatorChange"
      />
      
      <!-- 详情面板 -->
      <PredictionDetailPanel
        :forecast-data="forecastData"
        :selected-city="selectedCity"
        :selected-indicator="selectedIndicator"
        @refresh="refreshPredictionData"
      />
    </div>
    
    <!-- 移动设备适配：标签页切换 -->
    <div class="mobile-tabs">
      <button 
        :class="['tab-btn', { active: mobileActiveTab === 'control' }]"
        @click="mobileActiveTab = 'control'"
      >
        控制面板
      </button>
      <button 
        :class="['tab-btn', { active: mobileActiveTab === 'chart' }]"
        @click="mobileActiveTab = 'chart'"
      >
        预测图表
      </button>
      <button 
        :class="['tab-btn', { active: mobileActiveTab === 'detail' }]"
        @click="mobileActiveTab = 'detail'"
      >
        详细分析
      </button>
    </div>
    
    <!-- Toast通知组件 -->
    <div class="toast-container" v-if="showToastNotification">
      <div class="toast" :class="toastType">
        <div class="toast-icon">
          <span v-if="toastType === 'success'">✓</span>
          <span v-else-if="toastType === 'error'">✗</span>
          <span v-else>!</span>
        </div>
        <div class="toast-content">
          <div class="toast-message">{{ toastMessage }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, onUnmounted, onActivated } from 'vue';
import PredictionControlPanel from '../components/prediction/PredictionControlPanel.vue';
import PredictionMainChart from '../components/prediction/PredictionMainChart.vue';
import PredictionDetailPanel from '../components/prediction/PredictionDetailPanel.vue';
import * as forecastService from '@/services/forecastService';
import * as realTimeService from '@/services/realTimeService';

// 核心状态变量
const forecastData = ref(null);
const realTimeData = ref(null);
const selectedCity = ref('广州');
const selectedCityId = ref(null);
const selectedTimePeriod = ref(7);
const selectedIndicator = ref('AQI');
const selectedMode = ref('balanced');
const loading = ref(false);
const error = ref('');
const mobileActiveTab = ref('chart');
const apiConnected = ref(false);
const apiStatusMessage = ref('正在连接预测服务...');
const showApiConnectionAlert = ref(false);
const singleIndicatorMode = ref(false);
const predictionMetadata = ref(null);
const timePeriodType = ref('short');
const progressInterval = ref(null);

// Toast通知状态
const showToastNotification = ref(false);
const toastMessage = ref('');
const toastType = ref('success');

// 预测进度变量
const predictionProgress = ref(0);
const predictionSteps = ['准备数据', '加载模型', '执行预测', '处理结果', '生成图表'];
const currentStep = ref(0);
const predictionStepText = computed(() => predictionSteps[currentStep.value] || '');

// 预测阶段配置
const predictionPhases = {
  preparing: { max: 20, step: 0 },
  loading: { max: 50, step: 1 },
  predicting: { max: 80, step: 2 },
  processing: { max: 95, step: 3 },
  finishing: { max: 100, step: 4 }
};
const currentPhase = ref('preparing');

// 状态信息
const statusMessage = ref('');
const statusType = ref('info');

// API连接重试相关
const apiRetryCount = ref(0);
const MAX_API_RETRIES = 3;
const apiRetryInterval = ref(null);

// 计算属性：是否有数据
const hasData = computed(() => {
  if (!forecastData.value?.indicators) return false;
  
  for (const key in forecastData.value.indicators) {
    if (forecastData.value.indicators[key].forecast?.length > 0) {
      return true;
    }
  }
  return false;
});

// 显示空状态
const showEmptyState = computed(() => !loading.value && !hasData.value);

// 显示Toast通知
function showToast(message, type = 'info', duration = 3000) {
  toastMessage.value = message;
  toastType.value = type;
  showToastNotification.value = true;
  
  setTimeout(() => {
    showToastNotification.value = false;
  }, duration);
}

// 城市列表
const cities = ref([
  '广州', '深圳', '佛山', '东莞', '珠海', '惠州', '江门', '肇庆', 
  '汕头', '潮州', '揭阳', '汕尾', '梅州', '河源', '清远', '韶关', 
  '云浮', '阳江', '茂名', '湛江', '中山'
]);

// 可用指标列表
const availableIndicators = computed(() => {
  // 指标映射
  const indicatorMapping = {
    'PM25': { label: 'PM2.5', description: '细颗粒物，粒径2.5微米及以下' },
    'PM10': { label: 'PM10', description: '可吸入颗粒物，粒径10微米及以下' },
    'O3': { label: 'O3', description: '臭氧，氧气的同素异形体' },
    'NO2': { label: 'NO2', description: '二氧化氮，棕红色气体' },
    'SO2': { label: 'SO2', description: '二氧化硫，无色气体，有刺激性气味' },
    'CO': { label: 'CO', description: '一氧化碳，无色无味气体' },
    'AQI': { label: 'AQI', description: '空气质量指数，综合评价' }
  };
  
  // 没有预测数据时返回默认列表
  if (!forecastData.value?.indicators) {
    return Object.keys(indicatorMapping).map(key => ({
      value: key,
      label: indicatorMapping[key].label,
      description: indicatorMapping[key].description
    }));
  }
  
  // 返回可用指标
  const availableKeys = Object.keys(forecastData.value.indicators);
  return availableKeys.map(key => {
    const info = indicatorMapping[key] || { label: key, description: '空气质量指标' };
    return {
      value: key,
      label: info.label,
      description: info.description
    };
  });
});

// 统一处理事件回调
function handleIndicatorChange(indicator) {
  selectedIndicator.value = indicator;
}

function handleTimePeriodTypeUpdate(newType) {
  timePeriodType.value = newType;
}

/**
 * 开始预测过程
 */
async function startPrediction() {
  // 避免重复预测
  if (loading.value) return;
  
  // 初始化状态
  loading.value = true;
  error.value = '';
  predictionProgress.value = 10; // 开始状态
  statusMessage.value = '准备预测数据...';
  statusType.value = 'info';
  currentStep.value = 0;
  
  try {
    // 参数准备
    const cityName = selectedCity.value;
    let cityId = selectedCityId.value;
    const predictionDays = selectedTimePeriod.value;
    const periodType = timePeriodType.value;
    const apiOptions = { mode: selectedMode.value };
    
    // 更新进度为20%
    predictionProgress.value = 20;
    statusMessage.value = '获取实时数据...';
    currentStep.value = 0;
    
    // 并行获取实时数据
    const realTimePromise = realTimeService.getRealTimeData(cityName)
      .then(data => { realTimeData.value = data; })
      .catch(err => console.error('获取实时数据失败:', err));
    
    // 获取城市ID（如果需要）
    if (!cityId) {
      try {
        cityId = await forecastService.getCityIdByName(cityName);
        selectedCityId.value = cityId;
      } catch (error) {
        throw new Error(`无法获取城市 ${cityName} 的ID，请选择其他城市`);
      }
    }
    
    // 更新进度为40%
    predictionProgress.value = 40;
    statusMessage.value = '执行预测...';
    currentStep.value = 2;
    
    // 执行预测
    let result;
    if (selectedIndicator.value && singleIndicatorMode.value) {
      // 单指标预测
      result = await forecastService.getForecast(
        cityId, 
        selectedIndicator.value.toLowerCase(),
        predictionDays,
        periodType,
        apiOptions
      );
    } else {
      // 全指标预测
      result = await forecastService.getAllIndicatorsForecast(
        cityId,
        predictionDays,
        periodType,
        apiOptions
      );
    }
    
    // 更新进度为80%
    predictionProgress.value = 80;
    statusMessage.value = '处理预测结果...';
    currentStep.value = 3;
    
    // 处理结果
    handlePredictionResult(result, cityName, predictionDays);
    
    // 等待实时数据
    await realTimePromise;
    
  } catch (error) {
    handlePredictionError(error);
  } finally {
    predictionProgress.value = 100;
    loading.value = false;
  }
}

/**
 * 处理预测结果
 */
function handlePredictionResult(result, cityName, predictionDays) {
  // 完成进度
  currentPhase.value = 'finishing';
  currentStep.value = 4;
  predictionProgress.value = 100;
  loading.value = false;
  
  if (result.status === 'success' || result.status === 'partial') {
    // 处理部分成功
    let successMessage = '';
    if (result.status === 'partial') {
      const successfulIndicators = [];
      const failedIndicators = [];
      
      if (result.data?.indicators) {
        Object.entries(result.data.indicators).forEach(([indicator, data]) => {
          if (data.forecast?.length > 0) {
            successfulIndicators.push(indicator);
          } else {
            failedIndicators.push(indicator);
          }
        });
      }
      
      if (successfulIndicators.length > 0) {
        successMessage = `成功获取指标: ${successfulIndicators.join(', ')}`;
        console.warn(`获取失败指标: ${failedIndicators.join(', ')}`);
      } else {
        handlePredictionError(new Error('所有指标预测都失败了'));
        return;
      }
    }
    
    // 处理预测数据
    const processedData = processAllIndicatorsData(result.data);
    
    // 检查数据有效性
    let hasValidData = false;
    for (const key in processedData.indicators) {
      if (processedData.indicators[key].forecast?.length > 0) {
        hasValidData = true;
        break;
      }
    }
    
    if (!hasValidData) {
      handlePredictionError(new Error('预测结果中没有有效数据'));
      return;
    }
    
    // 更新数据
    forecastData.value = processedData;
    
    // 选择合适的指标
    if (processedData.indicators['AQI']?.forecast?.length > 0) {
      selectedIndicator.value = 'AQI';
    } else {
      // 找到第一个有数据的指标
      const firstAvailable = Object.keys(processedData.indicators).find(key => 
        processedData.indicators[key].forecast?.length > 0
      );
      selectedIndicator.value = firstAvailable || 'AQI';
    }
    
    // 更新元数据
    predictionMetadata.value = {
      city: cityName,
      date: new Date().toISOString().split('T')[0],
      days: predictionDays,
      result: 'success',
      indicators: Object.keys(processedData.indicators).length,
      message: successMessage || '预测成功'
    };
    
    // 更新状态
    statusMessage.value = '预测数据已加载';
    statusType.value = 'success';
  } else {
    handlePredictionError(new Error(result.message || '预测API返回错误'));
  }
}

/**
 * 处理预测错误
 */
function handlePredictionError(error) {
  // 清理资源
  if (progressInterval.value) {
    clearInterval(progressInterval.value);
    progressInterval.value = null;
  }
  
  // 更新状态
  loading.value = false;
  predictionProgress.value = 0;
  
  // 检查错误类型
  const errorMessage = error.message || '未知错误';
  
  if (errorMessage.includes('Failed to fetch') || 
      errorMessage.includes('ERR_CONNECTION_RESET') || 
      errorMessage.includes('Network Error')) {
    // 设置API连接状态为断开
    apiConnected.value = false;
    
    // 记录一次错误日志，避免重复
    console.error('无法连接到预测服务器，请检查后端服务是否正常运行');
    
    // 更新状态信息
    statusMessage.value = '无法连接到预测服务器，请检查后端服务是否正常运行';
    statusType.value = 'error';
    
    // 尝试重新连接，但不显示UI警告
    retryConnection();
    return;
  }
  
  // 显示预测错误
  statusMessage.value = `预测失败: ${errorMessage}`;
  statusType.value = 'error';
  showToast(`预测失败: ${errorMessage}`, 'error');
}

/**
 * 处理多指标预测数据 - 简化数据处理逻辑
 */
function processAllIndicatorsData(data) {
  // 标准化指标键名
  const standardizeKey = (key) => {
    if (!key) return 'AQI';
    const mapping = {
      'pm25': 'PM25', 'pm10': 'PM10', 'so2': 'SO2', 
      'no2': 'NO2', 'o3': 'O3', 'co': 'CO', 'aqi': 'AQI'
    };
    return mapping[key.toLowerCase()] || key.toUpperCase();
  };
  
  // 初始化标准化数据结构
  const allSupportedIndicators = ['AQI', 'PM25', 'PM10', 'SO2', 'NO2', 'CO', 'O3'];
  const processedIndicators = {};
  
  // 初始化所有指标
  allSupportedIndicators.forEach(indicator => {
    processedIndicators[indicator] = {
      forecast: [],
      historical: []
    };
  });
  
  // 检查数据有效性
  if (!data) {
    return {
      city_name: '',
      indicators: processedIndicators,
      currentIndicator: 'AQI'
    };
  }
  
  // 处理多指标数据
  if (data.indicators) {
    const cityName = data.city_name || '';
    const today = new Date().toISOString().split('T')[0];
    
    Object.entries(data.indicators).forEach(([key, indicatorData]) => {
      const standardKey = standardizeKey(key);
      
      if (!indicatorData?.historical || !indicatorData?.forecast) return;
      
      // 获取并排序数据
      const historicalData = sortDataByDate([...indicatorData.historical])
        .map(item => ({ ...item, dataType: 'historical' }));
      
      const forecastData = sortDataByDate([...indicatorData.forecast])
        .map(item => ({ 
          ...item, 
          dataType: 'forecast',
          interpolated: item.isInterpolated || false
        }));
      
      // 添加实时数据点（如果可用）
      if (realTimeData.value?.[standardKey.toLowerCase()] !== undefined) {
        const todayValue = realTimeData.value[standardKey.toLowerCase()];
        // 创建当前日期对象并格式化为ISO字符串的日期部分
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];
        console.log(`为指标 ${standardKey} 添加当天实时数据: ${todayValue}，日期: ${todayStr}，原始时间戳: ${today.getTime()}`);
        const realtimePoint = {
          date: todayStr,
          value: todayValue,
          dataType: 'realtime',
          isToday: true, // 明确标记为今天的数据
          time_updated: new Date().toISOString() // 添加时间戳确保是最新数据
        };
        historicalData.push(realtimePoint);
      } else {
        // 如果没有实时数据，检查预测数据中是否有今天的数据
        // 创建当前日期对象并格式化
        const today = new Date();
        const todayStr = today.toISOString().split('T')[0];
        console.log(`搜索今天的预测数据，当前日期: ${todayStr}，时间戳: ${today.getTime()}`);
        
        // 输出预测数据的日期用于调试
        forecastData.forEach((item, index) => {
          console.log(`预测数据[${index}]: 日期=${item.date}, 值=${item.value}`);
        });
        
        const todayForecastPoint = forecastData.find(item => item.date === todayStr);
        if (todayForecastPoint) {
          console.log(`为指标 ${standardKey} 使用今天的预测数据作为实时点: ${todayForecastPoint.value}，日期: ${todayStr}`);
          // 从预测中移除今天的数据点
          const index = forecastData.indexOf(todayForecastPoint);
          if (index !== -1) {
            forecastData.splice(index, 1);
          }
          // 添加到历史数据作为实时点
          historicalData.push({
            date: todayStr,
            value: todayForecastPoint.value,
            dataType: 'realtime',
            isToday: true, // 明确标记为今天的数据
            time_updated: new Date().toISOString() // 添加时间戳确保是最新数据
          });
        } else {
          // 如果没有实时数据也没有今天的预测数据，则使用最后一个历史数据点的值作为今天的值
          // 确保使用当前系统日期
          const today = new Date();
          const todayStr = today.toISOString().split('T')[0];
          if (historicalData.length > 0) {
            const lastHistorical = historicalData[historicalData.length - 1];
            console.log(`为指标 ${standardKey} 使用最后历史数据点作为今天实时点: ${lastHistorical.value}，日期: ${todayStr}`);
            historicalData.push({
              date: todayStr,
              value: lastHistorical.value,
              dataType: 'realtime',
              isToday: true, // 明确标记为今天的数据
              time_updated: new Date().toISOString() // 添加时间戳确保是最新数据
            });
          } else if (forecastData.length > 0) {
            // 如果没有历史数据，则使用第一个预测数据点的值
            const firstForecast = forecastData[0];
            console.log(`为指标 ${standardKey} 使用第一个预测数据点作为今天实时点: ${firstForecast.value}，日期: ${todayStr}`);
            historicalData.push({
              date: todayStr,
              value: firstForecast.value,
              dataType: 'realtime',
              isToday: true, // 明确标记为今天的数据
              time_updated: new Date().toISOString() // 添加时间戳确保是最新数据
            });
          } else {
            // 万不得已，创建一个默认值的实时点
            const defaultValue = standardKey === 'AQI' ? 37 : 
                               standardKey === 'PM25' ? 15 : 
                               standardKey === 'PM10' ? 35 : 
                               standardKey === 'SO2' ? 5 : 
                               standardKey === 'NO2' ? 15 : 
                               standardKey === 'CO' ? 0.8 : 
                               standardKey === 'O3' ? 40 : 37;
            console.log(`为指标 ${standardKey} 创建默认实时点: ${defaultValue}，日期: ${todayStr}`);
            historicalData.push({
              date: todayStr,
              value: defaultValue,
              dataType: 'realtime',
              isToday: true, // 明确标记为今天的数据
              time_updated: new Date().toISOString() // 添加时间戳确保是最新数据
            });
          }
        }
      }
      
      // 保存处理后的数据
      processedIndicators[standardKey] = {
        historical: historicalData,
        forecast: forecastData,
        metadata: data.metadata || {}
      };
    });
    
    return {
      city_name: cityName,
      indicators: processedIndicators,
      currentIndicator: 'AQI'
    };
  }
  
  // 处理单指标数据
  if (data.historical && data.forecast) {
    const standardKey = standardizeKey(data.indicator || 'AQI');
    const cityName = data.city_name || '';
    
    const historicalData = sortDataByDate([...data.historical])
      .map(item => ({ ...item, dataType: 'historical' }));
    
    const forecastData = sortDataByDate([...data.forecast])
      .map(item => ({
        ...item,
        dataType: 'forecast',
        interpolated: item.isInterpolated || false
      }));
    
    processedIndicators[standardKey] = {
      historical: historicalData,
      forecast: forecastData,
      metadata: data.metadata || {}
    };
    
    return {
      city_name: cityName,
      indicators: processedIndicators,
      currentIndicator: standardKey
    };
  }
  
  // 返回空结果
  return {
    city_name: '',
    indicators: processedIndicators,
    currentIndicator: 'AQI'
  };
}

// 辅助函数：按日期排序数据
function sortDataByDate(dataArray) {
  if (!dataArray || !Array.isArray(dataArray)) return [];
  return dataArray.sort((a, b) => new Date(a.date) - new Date(b.date));
}

/**
 * 检查API连接状态
 */
async function checkApiConnection(showError = false) {
  try {
    // 使用健康检查检查API连接状态
    const result = await forecastService.checkHealth();
    
    // 更新连接状态 - 注意这里使用success而不是status
    apiConnected.value = result.success === true;
    
    if (apiConnected.value) {
      apiStatusMessage.value = '预测服务已连接';
      console.log('预测服务已连接: 预测服务正常运行中');
      showApiConnectionAlert.value = false;
    } else {
      // 只在API真正不可用时才记录警告
      apiStatusMessage.value = '预测服务未连接: ' + (result.message || '未知错误');
      console.warn('预测服务未连接: ' + (result.message || '未知错误'));
    }
    
    return apiConnected.value;
  } catch (error) {
    console.error('API连接检查失败:', error);
    apiConnected.value = false;
    apiStatusMessage.value = '预测服务未连接，无法访问API';
    
    return false;
  }
}

/**
 * 重试连接预测服务
 */
function retryConnection() {
  // 更新状态信息
  apiStatusMessage.value = '正在尝试重新连接...';
  console.log('正在尝试重新连接预测服务...');
  
  // 清除已有的重试定时器
  if (apiRetryInterval.value) {
    clearInterval(apiRetryInterval.value);
    apiRetryInterval.value = null;
  }
  
  // 增加重试计数
  apiRetryCount.value++;
  
  // 尝试连接
  checkApiConnection(false).then(connected => {
    if (connected) {
      // 连接成功，清理资源
      if (apiRetryInterval.value) {
        clearInterval(apiRetryInterval.value);
        apiRetryInterval.value = null;
      }
      // 不需要额外日志，checkApiConnection已经记录了成功信息
    } else if (apiRetryCount.value < MAX_API_RETRIES) {
      // 连接失败但未达到最大重试次数
      console.log(`将在5秒后重试连接 (${apiRetryCount.value}/${MAX_API_RETRIES})`);
      
      // 设置下一次重试
      apiRetryInterval.value = setTimeout(() => {
        retryConnection();
      }, 5000);
    } else {
      // 达到最大重试次数
      console.error(`预测服务连接失败，已达到最大重试次数 (${apiRetryCount.value}/${MAX_API_RETRIES})`);
    }
  });
}

// 刷新预测数据
function refreshPredictionData() {
  if (!loading.value) {
    startPrediction();
  }
}

// 生命周期钩子
onMounted(async () => {
  // 初始化
  checkApiConnection();
  
  // 获取实时数据
  try {
    const data = await realTimeService.getRealTimeData(selectedCity.value);
    realTimeData.value = data;
  } catch (error) {
    console.error('获取实时数据失败:', error);
  }
});

onUnmounted(() => {
  // 清理资源
  if (progressInterval.value) {
    clearInterval(progressInterval.value);
    progressInterval.value = null;
  }
  
  if (apiRetryInterval.value) {
    clearInterval(apiRetryInterval.value);
    apiRetryInterval.value = null;
  }
});

onActivated(() => {
  // 页面重新激活时检查API状态
  checkApiConnection();
});

// 监听城市变化，更新实时数据
watch(selectedCity, async (newCity) => {
  if (newCity) {
    try {
      const data = await realTimeService.getRealTimeData(newCity);
      realTimeData.value = data;
      selectedCityId.value = null; // 重置城市ID，下次预测时重新获取
    } catch (error) {
      console.error(`获取城市 ${newCity} 实时数据失败:`, error);
    }
  }
});

// 监听预测时间变化，自动调整预测模式
watch(selectedTimePeriod, (newValue) => {
  // 根据时间周期自动调整预测模式
  if (newValue <= 3) {
    selectedMode.value = 'high_precision';
  } else if (newValue <= 30) {
    selectedMode.value = 'balanced';
  } else {
    selectedMode.value = 'trend';
  }
});
</script>

<script>
export default {
  name: 'SmartPrediction',
  watch: {
    // 监听移动设备标签页的变化
    mobileActiveTab(newTab) {
      // 设置data属性以便CSS可以相应地显示/隐藏面板
      document.querySelector('.smart-prediction-page').setAttribute('data-active-tab', newTab);
    }
  },
  
  mounted() {
    // 初始化移动设备标签页状态
    document.querySelector('.smart-prediction-page').setAttribute('data-active-tab', this.mobileActiveTab);
  }
}
</script>

<style scoped>
.smart-prediction-page {
  padding: 16px;
  max-width: 1680px;
  margin: 0 auto;
  background-color: #f0f2f5;
  min-height: calc(100vh - 64px);
}

.prediction-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}

/* API状态指示器样式优化 */
.api-status {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  margin-bottom: 16px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.api-status.connected {
  background-color: rgba(82, 196, 26, 0.1);
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.2);
}

.api-status.disconnected {
  background-color: rgba(245, 34, 45, 0.1);
  color: #f5222d;
  border: 1px solid rgba(245, 34, 45, 0.2);
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.connected .status-dot {
  background-color: #52c41a;
  box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.2);
}

.disconnected .status-dot {
  background-color: #f5222d;
  box-shadow: 0 0 0 2px rgba(245, 34, 45, 0.2);
}

.reconnect-btn {
  background-color: transparent;
  border: 1px solid currentColor;
  color: inherit;
  border-radius: 4px;
  font-size: 0.75rem;
  padding: 2px 8px;
  margin-left: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.reconnect-btn:hover {
  background-color: rgba(245, 34, 45, 0.15);
}

/* API连接警告优化 */
.api-connection-alert {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  max-width: 400px;
  width: calc(100% - 40px);
  background-color: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  animation: slide-down 0.3s ease;
}

@keyframes slide-down {
  0% { transform: translateX(-50%) translateY(-20px); opacity: 0; }
  100% { transform: translateX(-50%) translateY(0); opacity: 1; }
}

.alert-content {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
}

.alert-content i {
  margin-right: 12px;
  color: #f5222d;
  font-size: 20px;
}

.alert-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.retry-btn {
  padding: 6px 16px;
  border: none;
  border-radius: 4px;
  background-color: #1890ff;
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.retry-btn:hover {
  background-color: #40a9ff;
}

.close-btn {
  padding: 6px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: white;
  color: rgba(0, 0, 0, 0.65);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.close-btn:hover {
  background-color: #f5f5f5;
  border-color: #d9d9d9;
}

/* 移动设备标签页优化 */
.mobile-tabs {
  display: none;
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.tab-btn {
  flex: 1;
  padding: 12px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 14px;
  color: #595959;
  cursor: pointer;
  transition: all 0.3s;
}

.tab-btn.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
  font-weight: 500;
}

/* Toast通知优化 */
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  max-width: 350px;
  animation: slide-in 0.3s ease;
}

@keyframes slide-in {
  0% { transform: translateX(100%); opacity: 0; }
  100% { transform: translateX(0); opacity: 1; }
}

.toast {
  display: flex;
  padding: 12px 16px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.15);
  margin-bottom: 12px;
  overflow: hidden;
}

.toast.success {
  border-left: 4px solid #52c41a;
}

.toast.error {
  border-left: 4px solid #f5222d;
}

.toast.info {
  border-left: 4px solid #1890ff;
}

.toast-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-right: 12px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
}

.toast.success .toast-icon {
  background-color: #f6ffed;
  color: #52c41a;
}

.toast.error .toast-icon {
  background-color: #fff2f0;
  color: #f5222d;
}

.toast.info .toast-icon {
  background-color: #e6f7ff;
  color: #1890ff;
}

.toast-content {
  flex: 1;
}

.toast-message {
  font-size: 14px;
  color: #262626;
  line-height: 1.4;
}

/* 响应式布局调整 */
@media (max-width: 768px) {
  .smart-prediction-page {
    padding: 12px;
  }
  
  .prediction-layout {
    gap: 12px;
  }
  
  .mobile-tabs {
    display: flex;
  }
  
  .prediction-layout > * {
    display: none;
  }
  
  .prediction-layout > *:nth-child(1) {
    display: block;
  }
  
  .smart-prediction-page[data-active-tab="control"] .prediction-layout > :nth-child(1),
  .smart-prediction-page[data-active-tab="chart"] .prediction-layout > :nth-child(2),
  .smart-prediction-page[data-active-tab="detail"] .prediction-layout > :nth-child(3) {
    display: block;
  }
}

@media (max-width: 480px) {
  .toast-container {
    left: 20px;
    right: 20px;
    max-width: none;
  }
}
</style> 