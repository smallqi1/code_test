<template>
  <div class="chart-container" ref="chartContainer" :style="{height: height, width: width}">
    <div v-if="loading" class="chart-loading">
      <div class="spinner"></div>
      <span>{{ loadingText }}</span>
    </div>
    
    <div v-else-if="error" class="chart-error">
      <div class="error-icon">!</div>
      <div class="error-message">{{ error }}</div>
      <button v-if="onRetry" class="retry-button" @click="onRetry">重试</button>
    </div>
    
    <div 
      v-else 
      ref="chartRef" 
      class="chart-element"
      :style="{ height: height, width: width }"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { echarts, getChartTheme } from '@/plugins/echarts'
import { useUserStore } from '@/store/userStore'

const props = defineProps({
  // 图表配置项
  options: {
    type: Object,
    required: true
  },
  // 图表高度
  height: {
    type: String,
    default: '300px'
  },
  // 图表宽度
  width: {
    type: String,
    default: '100%'
  },
  // 是否自动调整大小
  autoResize: {
    type: Boolean,
    default: true
  },
  // 加载状态
  loading: {
    type: Boolean,
    default: false
  },
  // 加载文本
  loadingText: {
    type: String,
    default: '加载中...'
  },
  // 错误信息
  error: {
    type: String,
    default: ''
  },
  // 重试回调
  onRetry: {
    type: Function,
    default: null
  }
})

const emits = defineEmits(['chartInit', 'chartClick', 'chartDblclick', 'legendSelectChanged'])

// 引用和状态
const chartRef = ref(null)
const chartContainer = ref(null)
const chartInstance = ref(null)
const userStore = useUserStore()

// 添加空气质量等级颜色配置
const AQI_COLORS = {
  'excellent': '#00e400',  // 优
  'good': '#ffff00',       // 良
  'moderate': '#ff7e00',   // 轻度污染
  'unhealthy': '#ff0000',  // 中度污染
  'very-unhealthy': '#99004c', // 重度污染
  'hazardous': '#7e0023'   // 严重污染
}

// 创建空气质量指数渐变函数
const createAqiGradient = () => {
  return new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: AQI_COLORS.excellent },
    { offset: 0.3, color: AQI_COLORS.good },
    { offset: 0.5, color: AQI_COLORS.moderate },
    { offset: 0.7, color: AQI_COLORS.unhealthy },
    { offset: 0.9, color: AQI_COLORS.very_unhealthy },
    { offset: 1, color: AQI_COLORS.hazardous }
  ])
}

// 获取AQI等级颜色
const getAqiColor = (aqi) => {
  if (aqi <= 50) return AQI_COLORS.excellent
  if (aqi <= 100) return AQI_COLORS.good
  if (aqi <= 150) return AQI_COLORS.moderate
  if (aqi <= 200) return AQI_COLORS.unhealthy
  if (aqi <= 300) return AQI_COLORS.very_unhealthy
  return AQI_COLORS.hazardous
}

// 创建空气质量趋势图配置
const createAirQualityTrendOptions = (data, params = {}) => {
  const { 
    title = '空气质量趋势', 
    subtext = '',
    type = 'line',
    metric = 'aqi',
    xField = 'date',
    cities = [],
    showLegend = true
  } = params
  
  // 提取指标名称
  const metricName = {
    'aqi': 'AQI指数',
    'pm25': 'PM2.5 (μg/m³)',
    'pm10': 'PM10 (μg/m³)',
    'so2': 'SO2 (μg/m³)',
    'no2': 'NO2 (μg/m³)',
    'co': 'CO (mg/m³)',
    'o3': 'O3 (μg/m³)'
  }[metric] || metric
  
  // 格式化数据为echarts系列
  const series = []
  
  // 处理多城市数据
  if (cities.length > 0 && Array.isArray(data)) {
    // 多城市对比图
    cities.forEach(city => {
      const cityData = data.filter(item => item.city === city)
      series.push({
        name: city,
        type,
        data: cityData.map(item => item[metric]),
        // 为不同城市分配不同颜色
        itemStyle: {
          color: city.includes('广州') ? '#ff6b81' : 
                 city.includes('深圳') ? '#0abde3' :
                 city.includes('佛山') ? '#1dd1a1' :
                 city.includes('东莞') ? '#feca57' :
                 city.includes('中山') ? '#5f27cd' : '#c8d6e5'
        }
      })
    })
  } else if (typeof data === 'object' && !Array.isArray(data)) {
    // 时间序列数据（按年/季度/月）
    Object.entries(data).forEach(([key, value]) => {
      series.push({
        name: key,
        type,
        data: Array.isArray(value) ? value.map(item => item[metric]) : value[metric],
        emphasis: {
          focus: 'series'
        }
      })
    })
  } else {
    // 标准时间序列数据
    series.push({
      name: metricName,
      type,
      data: data.map(item => item[metric]),
      // 为AQI指数设置渐变色
      itemStyle: metric === 'aqi' ? {
        color: (params) => {
          return getAqiColor(params.value)
        }
      } : null,
      emphasis: {
        focus: 'series'
      }
    })
  }
  
  // 计算数据范围，设置Y轴最小值为0
  let minVal = 0
  let maxVal = 0
  if (Array.isArray(data)) {
    maxVal = Math.max(...data.map(item => item[metric] || 0)) * 1.1
  } else if (typeof data === 'object') {
    const allValues = []
    Object.values(data).forEach(value => {
      if (Array.isArray(value)) {
        allValues.push(...value.map(item => item[metric] || 0))
      } else if (typeof value === 'object') {
        allValues.push(value[metric] || 0)
      }
    })
    maxVal = Math.max(...allValues) * 1.1
  }
  
  // 设置X轴数据
  let xAxisData = []
  if (Array.isArray(data)) {
    xAxisData = data.map(item => item[xField])
  } else if (typeof data === 'object') {
    xAxisData = Object.keys(data)
  }
  
  // 创建空气质量等级标记线
  const markLines = []
  if (metric === 'aqi') {
    markLines.push(
      { yAxis: 50, lineStyle: { color: AQI_COLORS.excellent }, label: { formatter: '优' } },
      { yAxis: 100, lineStyle: { color: AQI_COLORS.good }, label: { formatter: '良' } },
      { yAxis: 150, lineStyle: { color: AQI_COLORS.moderate }, label: { formatter: '轻度污染' } },
      { yAxis: 200, lineStyle: { color: AQI_COLORS.unhealthy }, label: { formatter: '中度污染' } },
      { yAxis: 300, lineStyle: { color: AQI_COLORS.very_unhealthy }, label: { formatter: '重度污染' } }
    )
  } else if (metric === 'pm25') {
    markLines.push(
      { yAxis: 35, lineStyle: { color: AQI_COLORS.good }, label: { formatter: 'WHO指导值' } },
      { yAxis: 75, lineStyle: { color: AQI_COLORS.moderate }, label: { formatter: '国家标准' } }
    )
  } else if (metric === 'pm10') {
    markLines.push(
      { yAxis: 50, lineStyle: { color: AQI_COLORS.good }, label: { formatter: 'WHO指导值' } },
      { yAxis: 150, lineStyle: { color: AQI_COLORS.moderate }, label: { formatter: '国家标准' } }
    )
  }
  
  return {
    title: {
      text: title,
      subtext,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let result = `${params[0].axisValue}<br/>`
        params.forEach(param => {
          if (metric === 'aqi') {
            const level = param.value <= 50 ? '优' :
                         param.value <= 100 ? '良' :
                         param.value <= 150 ? '轻度污染' :
                         param.value <= 200 ? '中度污染' :
                         param.value <= 300 ? '重度污染' : '严重污染'
            result += `${param.marker} ${param.seriesName}: ${param.value} (${level})<br/>`
          } else {
            result += `${param.marker} ${param.seriesName}: ${param.value}<br/>`
          }
        })
        return result
      }
    },
    legend: {
      data: series.map(s => s.name),
      show: showLegend,
      bottom: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: showLegend ? '15%' : '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLabel: {
        rotate: xAxisData.length > 12 ? 45 : 0,
        interval: 'auto'
      }
    },
    yAxis: {
      type: 'value',
      min: minVal,
      max: maxVal > 0 ? maxVal : null,
      name: metricName,
      nameLocation: 'middle',
      nameGap: 50,
      nameTextStyle: {
        fontWeight: 'bold'
      },
      splitLine: {
        lineStyle: {
          type: 'dashed'
        }
      }
    },
    series: series.map(s => {
      if (metric === 'aqi' && markLines.length > 0) {
        return {
          ...s,
          markLine: {
            symbol: 'none',
            silent: true,
            lineStyle: {
              type: 'dashed'
            },
            data: markLines
          }
        }
      }
      return s
    })
  }
}

// 初始化图表
const initChart = async () => {
  if (!chartRef.value) {
    console.warn('图表DOM元素未准备好，初始化延迟');
    // 延迟尝试初始化
    setTimeout(() => {
      if (chartRef.value && !chartInstance.value) {
        initChart();
      }
    }, 200);
    return;
  }
  
  // 销毁旧的图表实例
  if (chartInstance.value) {
    try {
      chartInstance.value.dispose();
    } catch (e) {
      console.warn('销毁旧图表实例时出错', e);
    }
    chartInstance.value = null;
  }
  
  try {
    // 创建新的ECharts实例
    chartInstance.value = echarts.init(chartRef.value, getChartTheme(userStore.preferences.darkMode));
    
    // 为地图组件提供刷新回调
    window.__chartRefreshCallback = () => {
      if (chartInstance.value) {
        // 重新设置配置
        chartInstance.value.setOption(props.options, true);
      }
    };
    
    // 设置图表选项
    chartInstance.value.setOption(props.options);
    
    // 注册事件
    chartInstance.value.on('click', (params) => {
      emits('chartClick', params);
    });
    
    chartInstance.value.on('dblclick', (params) => {
      emits('chartDblclick', params);
    });
    
    chartInstance.value.on('legendselectchanged', (params) => {
      emits('legendSelectChanged', params);
    });
    
    // 检查是否是地图类型
    const hasMapseries = props.options.series && props.options.series.some(
      s => s.type === 'map'
    );
    
    if (hasMapseries) {
      const mapType = props.options.series?.find(s => s.type === 'map')?.map || 'guangdong';
      
      // 确保广东地图已注册
      if (mapType === 'guangdong' && !echarts.getMap('guangdong')) {
        console.warn('广东地图未注册，使用备用简化地图');
        
        // 构建简化的广东地图
        const simplifiedMap = {
          "type": "FeatureCollection",
          "features": []
        };
        
        try {
          // 注册新地图 - 无需先尝试取消注册
          // 直接覆盖注册即可
          echarts.registerMap('guangdong', simplifiedMap);
          console.log('已在BaseChart中注册备用广东地图');
        } catch (e) {
          console.error('注册备用广东地图失败:', e);
        }
      }
    }
    
    // 安全地设置配置项
    try {
      // 创建副本避免修改原始选项
      const safeOptions = JSON.parse(JSON.stringify(props.options));
      
      // 检查地图系列
      if (safeOptions.series && Array.isArray(safeOptions.series)) {
        safeOptions.series.forEach(series => {
          if (series.type === 'map') {
            // 确保地图已注册
            if (!echarts.getMap(series.map)) {
              console.warn(`地图 ${series.map} 未注册，尝试注册...`);
              // 这里可以添加地图注册逻辑
            }
          }
        });
      }
      
      // 设置配置项
      chartInstance.value.setOption(safeOptions);
      console.log('图表选项设置成功');
    } catch (error) {
      console.error('设置图表选项失败:', error);
      // 尝试使用简化配置
      try {
        const simpleOptions = {
          title: { text: '图表加载失败', left: 'center' },
          series: [{ type: 'pie', data: [{name: '错误', value: 100}] }]
        };
        chartInstance.value.setOption(simpleOptions);
      } catch (simpleError) {
        console.error('设置简化配置也失败:', simpleError);
      }
    }
    
    // 发送初始化成功事件
    emits('chartInit', chartInstance.value);
  } catch (error) {
    console.error('初始化图表失败:', error);
    
    // 记录错误细节便于调试
    console.error('错误细节:', {
      chartRefExists: !!chartRef.value,
      chartRefDimensions: chartRef.value ? {
        width: chartRef.value.clientWidth,
        height: chartRef.value.clientHeight
      } : null,
      options: props.options
    });
    
    // 最后尝试
    setTimeout(() => {
      try {
        if (chartRef.value && !chartInstance.value) {
          const isDarkTheme = userStore.themePreference === 'dark';
          chartInstance.value = echarts.init(chartRef.value, getChartTheme(isDarkTheme));
          
          // 使用最简单的配置
          const fallbackOptions = {
            title: { text: '图表加载失败', left: 'center', top: 'center' },
            series: [{ type: 'line', data: [1, 2, 3] }]
          };
          
          chartInstance.value.setOption(fallbackOptions);
          emits('chartInit', chartInstance.value);
        }
      } catch (retryError) {
        console.error('重试初始化图表失败:', retryError);
      }
    }, 500);
  }
};

// 重置图表大小
const resizeChart = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

// 监听窗口大小变化
let resizeObserver = null
const setupResizeListener = () => {
  if (props.autoResize && chartContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      resizeChart()
    })
    resizeObserver.observe(chartContainer.value)
  }
}

// 监听选项变化
watch(() => props.options, (newOptions) => {
  if (chartInstance.value && newOptions) {
    // 使用notMerge:false保留用户操作的状态（如图例选择）
    chartInstance.value.setOption(newOptions, { notMerge: false })
  }
}, { deep: true })

// 监听主题变化
watch(() => userStore.themePreference, () => {
  initChart()
})

// 监听加载和错误状态
watch([() => props.loading, () => props.error], ([loading, error]) => {
  if (!loading && !error && chartRef.value) {
    // 当从加载或错误状态恢复后，确保图表正确初始化
    initChart()
  }
})

// 生命周期钩子
onMounted(() => {
  // 延迟初始化确保DOM已渲染
  setTimeout(() => {
    if (!props.loading && !props.error) {
      initChart();
    }
    setupResizeListener();
  }, 100);
});

onBeforeUnmount(() => {
  // 清理资源
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
  
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

// 暴露给父组件的方法
defineExpose({
  getChartInstance: () => chartInstance.value,
  resize: resizeChart,
  createAirQualityTrendOptions,
  getAqiColor,
  AQI_COLORS
})
</script>

<style scoped>
.chart-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: inherit;
}

.chart-element {
  width: 100% !important;
  height: 100% !important;
  min-height: 300px !important;
  visibility: visible !important;
  z-index: 5;
}

.chart-loading,
.chart-error {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.8);
}

.spinner {
  width: 36px;
  height: 36px;
  border: 4px solid rgba(24, 144, 255, 0.2);
  border-radius: 50%;
  border-top-color: #1890ff;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #ff4d4f;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
}

.error-message {
  color: #333;
  margin-bottom: 16px;
  text-align: center;
  max-width: 80%;
}

.retry-button {
  padding: 6px 16px;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.retry-button:hover {
  background-color: #40a9ff;
}

/* 暗色主题适配 */
:deep(body.dark-theme) .chart-loading,
:deep(body.dark-theme) .chart-error {
  background-color: rgba(30, 30, 30, 0.8);
}

:deep(body.dark-theme) .error-message {
  color: #e0e0e0;
}
</style>