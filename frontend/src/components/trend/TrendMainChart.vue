<template>
  <div class="trend-main-chart">
    <div v-if="!loading && !error && analysisComplete" class="chart-wrapper">
      <div v-if="analysisType === 'annual'" id="annual-trend-chart" ref="annualChart" class="chart-container" :key="'annual-' + chartKey"></div>
      <div v-else-if="analysisType === 'seasonal'" id="seasonal-trend-chart" ref="seasonalChart" class="chart-container" :key="'seasonal-' + chartKey"></div>
      <div v-else-if="analysisType === 'monthly'" id="monthly-trend-chart" ref="monthlyChart" class="chart-container" :key="'monthly-' + chartKey"></div>
      <div v-else-if="analysisType === 'comparison'" id="comparison-trend-chart" ref="comparisonChart" class="chart-container" :key="'comparison-' + chartKey"></div>
      <div class="chart-debug-info">
        <small>当前分析类型: {{ analysisType }} | 数据状态: {{ getDataStatusText() }}</small>
        <span class="chart-action-btn" @click="forceRender">重新加载图表</span>
      </div>
    </div>
    
    <div v-else-if="loading" class="chart-loading">
      <div class="loading-indicator"></div>
      <p>正在加载图表数据...</p>
    </div>
    
    <div v-else-if="error" class="chart-error">
      <el-alert :title="error" type="error" show-icon />
      <div class="error-actions">
        <el-button type="primary" size="small" @click="$emit('analyze')">
          重试
        </el-button>
      </div>
    </div>
    
    <div v-else class="chart-empty">
      <div class="empty-chart-container">
        <div v-if="analysisType === 'annual'" id="empty-annual-chart" class="empty-chart"></div>
        <div v-else-if="analysisType === 'seasonal'" id="empty-seasonal-chart" class="empty-chart"></div>
        <div v-else-if="analysisType === 'monthly'" id="empty-monthly-chart" class="empty-chart"></div>
        <div v-else-if="analysisType === 'comparison'" id="empty-comparison-chart" class="empty-chart"></div>
        <div class="empty-chart-overlay">
          <span class="chart-icon">📊</span>
          <p>请点击"开始分析"按钮生成趋势图表</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { ElMessage } from 'element-plus'

// 添加一个图表key，用于强制重新渲染容器
const chartKey = ref(0)

const props = defineProps({
    selectedCities: {
      type: Array,
      default: () => []
    },
    analysisType: {
      type: String,
      default: 'annual'
    },
    startYear: {
      type: Number,
      default: 2018
    },
    endYear: {
      type: Number,
      default: 2025
    },
    selectedPollutant: {
      type: String,
      default: 'aqi'
    },
    loading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: ''
    },
    analysisComplete: {
      type: Boolean,
      default: false
    },
    rawData: {
      type: Object,
    default: () => ({
      annualData: [],
      seasonalData: [],
      monthlyData: [],
      comparisonData: []
    })
    }
})

const emit = defineEmits(['analyze', 'export-chart'])
    
    // 图表实例
const chartInstances = ref({
  annual: null,
  seasonal: null,
  monthly: null,
  comparison: null
})

const chartContainerId = computed(() => `${props.analysisType}-trend-chart`)
    
    // 污染物名称映射
      const pollutantNames = {
        aqi: 'AQI指数',
  pm25: 'PM2.5浓度 (μg/m³)',
  pm10: 'PM10浓度 (μg/m³)',
  so2: 'SO₂浓度 (μg/m³)',
  no2: 'NO₂浓度 (μg/m³)',
  co: 'CO浓度 (mg/m³)',
  o3: 'O₃浓度 (μg/m³)'
}

const pollutantName = computed(() => {
  return pollutantNames[props.selectedPollutant] || props.selectedPollutant
})

// 根据分析类型获取相应的数据
const chartData = computed(() => {
  switch (props.analysisType) {
    case 'annual':
      return props.rawData.annualData || []
    case 'seasonal':
      return props.rawData.seasonalData || []
    case 'monthly':
      return props.rawData.monthlyData || []
    case 'comparison':
      return props.rawData.comparisonData || []
    default:
      return []
  }
})

// 图表容器refs
const annualChart = ref(null)
const seasonalChart = ref(null)
const monthlyChart = ref(null)
const comparisonChart = ref(null)

// 添加状态文本函数 - 移到前面，确保在模板中使用前定义
const getDataStatusText = () => {
  if (!props.rawData) return '无数据'
  
  const typeDataMap = {
    annual: props.rawData.annualData,
    seasonal: props.rawData.seasonalData,
    monthly: props.rawData.monthlyData,
    comparison: props.rawData.comparisonData
  }
  
  const currentTypeData = typeDataMap[props.analysisType]
  if (!currentTypeData || currentTypeData.length === 0) {
    return '当前类型无数据'
  }
  
  return `${currentTypeData.length}条记录`
}

// 添加forceRender方法 - 移到前面，确保在defineExpose前定义
const forceRender = () => {
  console.log('forceRender方法被调用，强制重新渲染图表');
  
  // 增加key触发容器重新渲染
  chartKey.value++;
  
  // 清理所有图表实例
  Object.keys(chartInstances.value).forEach(type => {
    if (chartInstances.value[type]) {
      try {
        chartInstances.value[type].dispose();
        console.log(`${type}图表实例已销毁`);
      } catch (error) {
        console.error(`销毁${type}图表实例失败:`, error);
      }
      chartInstances.value[type] = null;
    }
  });
  
  // 等待DOM更新后重新渲染
  nextTick(() => {
    setTimeout(() => {
      renderChartByType();
    }, 300);
  });
}

// 防抖函数，避免频繁触发resize
const debounce = (fn, delay) => {
  let timer = null
  return function() {
    const context = this
    const args = arguments
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      fn.apply(context, args)
    }, delay)
  }
}

// 标记变量，避免事件循环
const isResizing = ref(false)
const isRendering = ref(false)

// 基础图表渲染函数
const renderChart = (chartType, containerId, options) => {
  try {
    // 避免重复渲染
    if (isRendering.value) {
      console.log(`${chartType}图表正在渲染中，跳过重复渲染`)
      return null
    }
    
    isRendering.value = true
    console.log(`===== 渲染${chartType}图表 =====`)
    console.log(`容器ID: ${containerId}`)
    
    // 先检查容器是否存在
    const container = document.getElementById(containerId)
    if (!container) {
      console.error(`找不到图表容器：#${containerId}`)
      ElMessage.warning(`渲染${chartType}图表失败：找不到容器`)
      isRendering.value = false
      return null
    }
    
    console.log(`容器#${containerId}尺寸:`, {
      offsetWidth: container.offsetWidth,
      offsetHeight: container.offsetHeight,
      clientWidth: container.clientWidth,
      clientHeight: container.clientHeight,
      style: container.getAttribute('style') || '无样式'
    })
    
    // 确保容器尺寸正确
    container.style.width = '100%';
    container.style.height = '500px';
    container.style.minHeight = '500px';
    container.style.display = 'block';
    container.style.visibility = 'visible';
    container.style.opacity = '1';
    container.style.position = 'relative';
    container.style.zIndex = '1';
    
    // 强制DOM更新
    container.innerHTML = '';
    
    // 强制重新计算布局
    const rect = container.getBoundingClientRect();
    console.log(`强制布局后的容器尺寸:`, {
      width: rect.width,
      height: rect.height
    });
    
    // 检查是否已有ECharts实例并清理
    try {
      const existingChart = echarts.getInstanceByDom(container);
      if (existingChart) {
        console.log(`找到现有的${chartType}图表实例，将销毁重建`);
        existingChart.dispose();
      }
    } catch (err) {
      console.warn(`检查现有图表实例出错:`, err);
    }
    
    // 创建新的图表实例
    let chartInstance = null;
    try {
      console.log(`为${chartType}图表创建新实例`);
      
      // 获取容器的实际宽度
      const containerWidth = rect.width || container.clientWidth || container.offsetWidth;
      const containerHeight = rect.height || container.clientHeight || container.offsetHeight;
      
      console.log(`容器#${containerId}实际大小:`, {
        width: containerWidth,
        height: containerHeight
      });
      
      chartInstance = echarts.init(container, null, {
        renderer: 'canvas', // 强制使用canvas渲染器
        devicePixelRatio: window.devicePixelRatio, // 设置设备像素比
        width: containerWidth,
        height: containerHeight || 500
      });
      
      // 确保正确设置了宽高
      container.style.width = '100%';
      container.style.height = '500px';
    } catch (err) {
      console.error(`创建${chartType}图表实例失败:`, err);
      ElMessage.error(`创建图表实例失败: ${err.message || '未知错误'}`);
      isRendering.value = false
      return null;
    }
    
    if (!chartInstance) {
      console.error(`${chartType}图表实例为空，无法继续渲染`);
      ElMessage.error(`渲染${chartType}图表失败：无法创建图表实例`);
      isRendering.value = false
      return null;
    }
    
    console.log(`为${chartType}图表设置选项`);
    
    // 检查选项是否有效
    if (!options) {
      console.error(`${chartType}图表选项为空`);
      ElMessage.error(`渲染${chartType}图表失败：图表配置为空`);
      isRendering.value = false
      return null;
    }
    
    // 设置图表选项
    try {
      chartInstance.setOption(options, true);
      console.log(`${chartType}图表选项设置成功`);
    } catch (err) {
      console.error(`设置${chartType}图表选项失败:`, err);
      ElMessage.error(`设置图表选项失败: ${err.message || '未知错误'}`);
      isRendering.value = false
      return null;
    }
    
    // 确保图表正确渲染
    setTimeout(() => {
      if (chartInstance && !chartInstance.isDisposed()) {
        chartInstance.resize();
        console.log(`${chartType}图表延迟重绘完成`);
      }
    }, 100);
    
    // 记录图表实例
    chartInstances.value[chartType] = chartInstance;
    console.log(`${chartType}图表实例已记录到chartInstances中`);
    
    // 监听窗口大小变化，自动调整图表大小
    const handleResizeChart = debounce(() => {
      // 避免重复resize
      if (isResizing.value) return
      
      isResizing.value = true
      if (chartInstance && !chartInstance.isDisposed()) {
        console.log(`${chartType}图表大小调整开始`)
        chartInstance.resize()
        console.log(`${chartType}图表大小已调整`)
        
        // 重置标记
        setTimeout(() => {
          isResizing.value = false
        }, 200)
      }
    }, 300); // 300ms防抖
    
    // 记录resize处理函数，以便后续移除
    chartInstance._resizeHandler = handleResizeChart
    window.addEventListener('resize', handleResizeChart)
    
    // 添加点击事件
    chartInstance.on('click', (params) => {
      console.log(`${chartType}图表被点击:`, params);
    });
    
    // 监听图表渲染完成事件
    chartInstance.on('rendered', () => {
      // 避免频繁触发rendered事件引起的循环
      if (isResizing.value) return
      
      console.log(`${chartType}图表渲染完成事件触发`)
      
      // 额外处理: 确保只在需要时resize
      setTimeout(() => {
        // 重置渲染标记
        isRendering.value = false
      }, 200)
    });
    
    console.log(`${chartType}图表渲染成功`);
    
    // 重置渲染标记
    setTimeout(() => {
      isRendering.value = false
    }, 300)
    
    return chartInstance;
  } catch (error) {
    console.error(`渲染${chartType}图表时出错:`, error);
    ElMessage.error(`渲染图表失败: ${error.message || '未知错误'}`);
    isRendering.value = false
    return null;
  }
}

// 根据分析类型渲染不同的图表
const renderChartByType = async () => {
  try {
    console.log(`===== 尝试渲染${props.analysisType}图表 =====`)
    console.log('当前状态:', {
      loading: props.loading,
      analysisComplete: props.analysisComplete,
      error: props.error
    })
    
    if (props.loading || !props.analysisComplete) {
      console.warn('数据正在加载或分析未完成，暂不渲染图表')
      return
    }
    
    // 检查是否有原始数据
    if (!props.rawData) {
      console.warn('缺少原始数据，无法渲染图表')
      ElMessage.warning('无法获取分析数据，请重试')
      return
    }
    
    // 检查rawData的结构
    console.log('rawData结构:', Object.keys(props.rawData).join(', '))
    
    // 根据分析类型检查对应的数据是否存在
    const analysisType = props.analysisType
    
    // 详细记录数据状态
    const dataStatus = {
      annual: props.rawData.annualData ? `${props.rawData.annualData.length}项` : '无数据',
      seasonal: props.rawData.seasonalData ? `${props.rawData.seasonalData.length}项` : '无数据',
      monthly: props.rawData.monthlyData ? `${props.rawData.monthlyData.length}项` : '无数据',
      comparison: props.rawData.comparisonData ? `${props.rawData.comparisonData.length}项` : '无数据'
    }
    console.log('各类型数据状态:', dataStatus)
    
    // 等待DOM更新
    await nextTick()
    
    // 确保容器已准备好
    const containerId = `${analysisType}-trend-chart`
    let container = document.getElementById(containerId)
    
    if (!container) {
      console.warn(`找不到图表容器: #${containerId}，尝试强制创建`)
      
      // 检查父容器是否存在
      const chartWrapper = document.querySelector('.chart-wrapper')
      if (!chartWrapper) {
        console.error('找不到.chart-wrapper容器，DOM可能未正确渲染')
        
        // 检查根容器
        const rootContainer = document.querySelector('.trend-main-chart')
        if (!rootContainer) {
          console.error('找不到.trend-main-chart根容器，组件可能未正确挂载')
          ElMessage.error('图表容器渲染失败，请刷新页面重试')
          return
        }
        
        // 尝试强制清理并创建容器结构
        console.log('尝试重建图表容器结构')
        rootContainer.innerHTML = `
          <div class="chart-wrapper">
            <div id="${containerId}" class="chart-container" style="width:100%;height:500px;min-height:500px;display:block;position:relative;z-index:10;"></div>
            <div class="chart-debug-info">
              <small>当前分析类型: ${analysisType} | 数据状态: ${dataStatus[analysisType]}</small>
              <span class="chart-action-btn" onclick="document.dispatchEvent(new CustomEvent('force-render'))">重新加载图表</span>
            </div>
          </div>
        `
        
        // 重新获取容器
        container = document.getElementById(containerId)
        if (!container) {
          console.error('强制创建容器后仍找不到容器，放弃渲染')
          ElMessage.error('无法创建图表容器，请刷新页面重试')
          return
        }
        
        console.log('成功强制创建容器')
      } else {
        // 清空图表包装器并创建容器
        console.log('找到.chart-wrapper容器，尝试创建图表容器')
        chartWrapper.innerHTML = `
          <div id="${containerId}" class="chart-container" style="width:100%;height:500px;min-height:500px;display:block;position:relative;z-index:10;"></div>
          <div class="chart-debug-info">
            <small>当前分析类型: ${analysisType} | 数据状态: ${dataStatus[analysisType]}</small>
            <span class="chart-action-btn" onclick="document.dispatchEvent(new CustomEvent('force-render'))">重新加载图表</span>
          </div>
        `
        
        // 重新获取容器
        container = document.getElementById(containerId)
        if (!container) {
          console.error('创建容器后仍找不到容器，放弃渲染')
          ElMessage.error('无法创建图表容器，请刷新页面重试')
          return
        }
        console.log('成功创建所需容器')
      }
    }
    
    console.log(`容器#${containerId}已确认存在，尺寸:`, {
      width: container.clientWidth,
      height: container.clientHeight,
      offsetWidth: container.offsetWidth,
      offsetHeight: container.offsetHeight
    })
    
    // 让DOM更新
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // 强制重新计算尺寸
    const rect = container.getBoundingClientRect()
    console.log(`强制更新后的容器尺寸:`, {
      width: rect.width,
      height: rect.height
    })
    
    // 使用Vue ref来获取容器
    let chartRef = null
    switch (analysisType) {
      case 'annual':
        chartRef = annualChart.value
        break
      case 'seasonal':
        chartRef = seasonalChart.value
        break
      case 'monthly':
        chartRef = monthlyChart.value
        break
      case 'comparison':
        chartRef = comparisonChart.value
        break
    }
    
    console.log(`获取到容器ref: ${chartRef ? '成功' : '失败'}`)
    
    // 确保容器内部为空，防止干扰
    container.innerHTML = ''
    
    // 让DOM进一步更新
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // 确保所有现有实例被清理
    try {
      const existingInstance = chartInstances.value[analysisType]
      if (existingInstance) {
        existingInstance.dispose()
        chartInstances.value[analysisType] = null
        console.log(`已清理现有${analysisType}图表实例`)
      }
      
      // 额外检查DOM关联的实例
      const domInstance = echarts.getInstanceByDom(container)
      if (domInstance) {
        domInstance.dispose()
        console.log(`已清理DOM关联的${analysisType}图表实例`)
      }
    } catch (err) {
      console.warn(`清理图表实例出错:`, err)
    }
    
    // 设置一个较长的延迟确保DOM彻底准备好
    setTimeout(() => {
      try {
        let chartInstance = null;
        
        console.log(`开始渲染${analysisType}图表...`);
        
        // 检查当前类型的数据是否存在
        const typeDataMap = {
          annual: props.rawData.annualData || [],
          seasonal: props.rawData.seasonalData || [],
          monthly: props.rawData.monthlyData || [],
          comparison: props.rawData.comparisonData || []
        };
        
        const currentTypeData = typeDataMap[analysisType] || [];
        
        if (currentTypeData.length === 0) {
          console.warn(`${analysisType}类型的数据为空，尝试渲染空图表`);
          
          // 创建并显示无数据的图表
          if (analysisType === 'annual') {
            chartInstance = renderEmptyAnnualChart();
          } else if (analysisType === 'seasonal') {
            chartInstance = renderEmptySeasonalChart();
          } else if (analysisType === 'monthly') {
            chartInstance = renderEmptyMonthlyChart();
          } else if (analysisType === 'comparison') {
            chartInstance = renderEmptyComparisonChart();
          }
        } else {
          switch (analysisType) {
            case 'annual':
              chartInstance = renderAnnualChart();
              break;
            case 'seasonal':
              chartInstance = renderSeasonalChart();
              break;
            case 'monthly':
              chartInstance = renderMonthlyChart();
              break;
            case 'comparison':
              chartInstance = renderComparisonChart();
              break;
          }
        }
        
        // 检查图表是否成功渲染
        if (chartInstance) {
          // 存储图表实例
          chartInstances.value[analysisType] = chartInstance;
          
          // 强制图表更新和重绘
          setTimeout(() => {
            if (chartInstance && !chartInstance.isDisposed()) {
              // 获取容器的实际宽度和高度
              const containerRect = container.getBoundingClientRect();
              chartInstance.resize({
                width: containerRect.width,
                height: 500
              });
              console.log(`${analysisType}图表已强制重绘完成，设置尺寸:`, {
                width: containerRect.width,
                height: 500
              });
              
              // 添加窗口resize事件监听，以便在窗口大小变化时调整图表大小
              const resizeHandler = () => {
                if (chartInstance && !chartInstance.isDisposed()) {
                  const newRect = container.getBoundingClientRect();
                  chartInstance.resize({
                    width: newRect.width,
                    height: 500
                  });
                }
              };
              window.addEventListener('resize', resizeHandler);
              chartInstance._resizeHandler = resizeHandler;
            }
          }, 200);
        }
      } catch (innerError) {
        console.error(`渲染${analysisType}图表时内部错误:`, innerError);
        ElMessage.error(`渲染图表失败: ${innerError.message || '未知错误'}`);
      }
    }, 500); // 增加延迟时间，确保DOM完全渲染
  } catch (error) {
    console.error(`渲染${props.analysisType}图表时出错:`, error)
    ElMessage.error(`图表渲染流程失败: ${error.message || '未知错误'}`)
  }
}

// 渲染空的年度趋势图
const renderEmptyAnnualChart = () => {
  const options = {
    title: {
      text: `${pollutantName.value}年度变化趋势`,
      left: 'center',
      top: 0
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['暂无数据'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '60px',
      top: '60px',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: [],
      name: '年份',
      nameLocation: 'middle',
      nameGap: 35
    },
    yAxis: {
      type: 'value',
      name: pollutantName.value,
      nameLocation: 'middle',
      nameGap: 40
    },
    series: []
  }
  
  return renderChart('annual', 'annual-trend-chart', options)
}

// 渲染空的季节趋势图
const renderEmptySeasonalChart = () => {
  const options = {
    title: {
      text: `${pollutantName.value}季节变化趋势`,
      left: 'center',
      top: 0
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['暂无数据'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '60px',
      top: '60px',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['春季', '夏季', '秋季', '冬季'],
      name: '季节',
      nameLocation: 'middle',
      nameGap: 35
    },
    yAxis: {
      type: 'value',
      name: pollutantName.value,
      nameLocation: 'middle',
      nameGap: 40
    },
    series: []
  }
  
  return renderChart('seasonal', 'seasonal-trend-chart', options)
}

// 渲染空的月度趋势图
const renderEmptyMonthlyChart = () => {
  const options = {
    title: {
      text: `${pollutantName.value}月度变化趋势`,
      left: 'center',
      top: 0
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['暂无数据'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '60px',
      top: '60px',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
      name: '月份',
      nameLocation: 'middle',
      nameGap: 35
    },
    yAxis: {
      type: 'value',
      name: pollutantName.value,
      nameLocation: 'middle',
      nameGap: 40
    },
    series: []
  }
  
  return renderChart('monthly', 'monthly-trend-chart', options)
}

// 渲染空的城市对比图
const renderEmptyComparisonChart = () => {
  const options = {
    title: {
      text: `城市${pollutantName.value}对比分析`,
      left: 'center',
      top: 0
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['暂无数据'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '60px',
      top: '60px',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: [],
      name: '城市',
      nameLocation: 'middle',
      nameGap: 35
    },
    yAxis: {
      type: 'value',
      name: pollutantName.value,
      nameLocation: 'middle',
      nameGap: 40
    },
    series: []
  }
  
  return renderChart('comparison', 'comparison-trend-chart', options)
}

// 年度趋势图
const renderAnnualChart = () => {
  try {
    console.log('===== 开始渲染年度趋势图 =====')
    
    const data = props.rawData.annualData || []
    if (data.length === 0) {
      console.error('年度趋势数据为空')
      ElMessage.warning('没有年度趋势数据可显示')
      return null
    }
    
    console.log('年度数据:', data.length, '条记录')
    console.log('数据样本:', JSON.stringify(data[0]))
    
    // 检查数据格式是否符合预期
    const expectedFields = ['city', 'year', 'value']
    const hasValidFormat = data.every(item => {
      const hasFields = expectedFields.every(field => field in item)
      if (!hasFields) {
        console.warn('数据项缺少必要字段:', item)
      }
      return hasFields
    })
    
    if (!hasValidFormat) {
      console.error('部分数据格式不符合预期，可能导致图表渲染异常')
    }
    
    // 处理数据
    const cities = [...new Set(data.map(item => item.city))]
    const years = [...new Set(data.map(item => item.year))].sort((a, b) => a - b)
    
    console.log('解析后的城市列表:', cities)
    console.log('解析后的年份列表:', years)
    
    if (cities.length === 0) {
      console.error('未能从数据中提取城市信息')
      ElMessage.warning('无法解析城市数据')
      return null
    }
    
    if (years.length === 0) {
      console.error('未能从数据中提取年份信息')
      ElMessage.warning('无法解析年份数据')
      return null
    }
    
    // 构建系列数据，确保每个系列都有完整的数据结构
    const series = []
    
    cities.forEach(city => {
      const cityData = data.filter(item => item.city === city)
      console.log(`处理${city}的数据，共${cityData.length}条记录`)
      
      // 确保数据按年份排序
      const sortedData = years.map(year => {
        const yearData = cityData.find(item => item.year === year)
        return yearData ? yearData.value : null
      })
      
      console.log(`${city}的年度数据:`, sortedData)
      
      // 只有当排序后的数据存在且不全为null时才添加到系列中
      if (sortedData.some(val => val !== null)) {
        series.push({
          name: city,
          type: 'line',
          data: sortedData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
          }
        })
      } else {
        console.warn(`${city}的数据全为null，不添加到图表中`)
      }
    })
    
    // 如果没有有效的系列数据，退出
    if (series.length === 0) {
      console.error('未找到有效的系列数据，无法渲染图表')
      ElMessage.warning('处理后无有效数据，无法渲染图表')
      return null
    }
    
    console.log('已生成系列数据，准备渲染图表:', series.length, '个系列')
    
    // 检查DOM容器
    const container = document.getElementById('annual-trend-chart')
    if (!container) {
      console.error('找不到年度趋势图容器 #annual-trend-chart')
      ElMessage.error('渲染失败：找不到图表容器')
      return null
    }
    
    const options = {
      title: {
        text: `${pollutantName.value}年度变化趋势`,
        left: 'center',
        top: 0
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: (params) => {
          let result = `<div style="font-weight:bold">${params[0].axisValue}年</div>`
          params.forEach(param => {
            const item = data.find(d => d.city === param.seriesName && d.year === param.axisValue)
            if (item) {
              result += `<div style="margin-top:5px;display:flex;justify-content:space-between;min-width:150px">
                <span>${param.marker} ${param.seriesName}:</span>
                <span style="font-weight:bold">${param.value}</span>
              </div>`
              
              if (item.min !== undefined) {
                result += `<div style="margin-left:15px;font-size:12px;color:#888">
                  <span>最小值: ${item.min}</span>
                </div>`
              }
              
              if (item.max !== undefined) {
                result += `<div style="margin-left:15px;font-size:12px;color:#888">
                  <span>最大值: ${item.max}</span>
                </div>`
              }
            }
          })
          return result
        }
      },
      legend: {
        data: cities,
        type: 'scroll',
        bottom: 0
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '60px',
        top: '60px',
        containLabel: true
      },
      toolbox: {
        feature: {
          saveAsImage: {
            title: '保存为图片'
          }
        }
      },
      xAxis: {
        type: 'category',
        data: years,
        name: '年份',
        nameLocation: 'middle',
        nameGap: 35,
        axisLine: {
          lineStyle: {
            color: '#333'
          }
        },
        axisLabel: {
          formatter: '{value}年'
        }
      },
      yAxis: {
        type: 'value',
        name: pollutantName.value,
        nameLocation: 'middle',
        nameGap: 40,
        axisLine: {
          lineStyle: {
            color: '#333'
          }
        }
      },
      series: series
    }
    
    console.log('annual图表配置已生成，准备渲染')
    return renderChart('annual', 'annual-trend-chart', options)
  } catch (error) {
    console.error('渲染年度趋势图出错:', error)
    ElMessage.error(`渲染年度趋势图失败: ${error.message || '未知错误'}`)
    return null
  }
}

// 季节趋势图
const renderSeasonalChart = () => {
  const data = props.rawData.seasonalData || []
  if (data.length === 0) {
    ElMessage.warning('没有季节趋势数据可显示')
    return null
  }
  
  console.log('季节数据:', data.length, '条记录')
  
  // 处理数据
  const cities = [...new Set(data.map(item => item.city))]
  const seasons = ['春季', '夏季', '秋季', '冬季']
  const years = [...new Set(data.map(item => item.year))].sort((a, b) => a - b)
  
  // 构建系列数据
  const series = []
  
  cities.forEach(city => {
    const cityData = data.filter(item => item.city === city)
    
    years.forEach(year => {
      const yearData = cityData.filter(item => item.year === year)
      
      // 确保数据按季节排序
      const sortedData = seasons.map(season => {
        const seasonData = yearData.find(item => item.season === season)
        return seasonData ? seasonData.value : null
      })
      
      // 只有当排序后的数据存在且不全为null时才添加到系列中
      if (sortedData.some(val => val !== null)) {
        series.push({
          name: `${city} ${year}年`,
          type: 'bar',
          data: sortedData,
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
          }
        })
      }
    })
  })
  
  // 如果没有有效的系列数据，退出
  if (series.length === 0) {
    console.warn('未找到有效的季节数据，无法渲染图表')
    return null
  }
  
  const options = {
    title: {
      text: `${pollutantName.value}季节变化趋势`,
      left: 'center',
      top: 0
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      data: series.map(s => s.name)
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '80px',
      top: '60px',
      containLabel: true
    },
    toolbox: {
      feature: {
        saveAsImage: {
          title: '保存为图片'
        }
      }
    },
    xAxis: {
      type: 'category',
      data: seasons,
      name: '季节',
      nameLocation: 'middle',
      nameGap: 35,
      axisLine: {
        lineStyle: {
          color: '#333'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: pollutantName.value,
      nameLocation: 'middle',
      nameGap: 40,
      axisLine: {
        lineStyle: {
          color: '#333'
        }
      }
    },
    series: series
  }
  
  console.log('seasonal图表渲染完成')
  return renderChart('seasonal', 'seasonal-trend-chart', options)
}

// 月度趋势图
const renderMonthlyChart = () => {
  const data = props.rawData.monthlyData || []
  if (data.length === 0) {
    ElMessage.warning('没有月度趋势数据可显示')
    return null
  }
  
  console.log('月度数据:', data.length, '条记录')
  
  // 处理数据
  const cities = [...new Set(data.map(item => item.city))]
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
  const years = [...new Set(data.map(item => item.year))].sort((a, b) => a - b)
  
  // 构建系列数据
  const series = []
  
  cities.forEach(city => {
    const cityData = data.filter(item => item.city === city)
    
    years.forEach(year => {
      const yearData = cityData.filter(item => item.year === year)
      
      // 确保数据按月份排序
      const sortedData = months.map((_, index) => {
        const monthData = yearData.find(item => item.month === index + 1)
        return monthData ? monthData.value : null
      })
      
      // 只有当排序后的数据存在且不全为null时才添加到系列中
      if (sortedData.some(val => val !== null)) {
        series.push({
          name: `${city} ${year}年`,
          type: 'line',
          data: sortedData,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          emphasis: {
            itemStyle: {
              borderColor: '#fff',
              borderWidth: 2,
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
          }
        })
      }
    })
  })
  
  // 如果没有有效的系列数据，退出
  if (series.length === 0) {
    console.warn('未找到有效的月度数据，无法渲染图表')
    return null
  }
  
  const options = {
    title: {
      text: `${pollutantName.value}月度变化趋势`,
      left: 'center',
      top: 0
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      data: series.map(s => s.name)
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '80px',
      top: '60px',
      containLabel: true
    },
    toolbox: {
      feature: {
        saveAsImage: {
          title: '保存为图片'
        }
      }
    },
    xAxis: {
      type: 'category',
      data: months,
      name: '月份',
      nameLocation: 'middle',
      nameGap: 35,
      boundaryGap: false,
      axisLine: {
        lineStyle: {
          color: '#333'
        }
      }
    },
    yAxis: {
      type: 'value',
      name: pollutantName.value,
      nameLocation: 'middle',
      nameGap: 40,
      axisLine: {
        lineStyle: {
          color: '#333'
        }
      }
    },
    series: series
  }
  
  console.log('monthly图表渲染完成')
  return renderChart('monthly', 'monthly-trend-chart', options)
}

// 城市对比图
const renderComparisonChart = () => {
  const data = props.rawData.comparisonData || []
  if (data.length === 0) {
    ElMessage.warning('没有城市对比数据可显示')
    return
  }
  
  // 按照平均值排序
  const sortedData = [...data].sort((a, b) => a.mean - b.mean)
  
  const cities = sortedData.map(item => item.city)
  const means = sortedData.map(item => item.mean)
  const mins = sortedData.map(item => item.min)
  const maxs = sortedData.map(item => item.max)
  const improvements = sortedData.map(item => 
    item.improvement ? item.improvement : 0
  )
  
  // 定义改善率颜色
  const improvementColors = improvements.map(value => 
    value > 0 ? '#67c23a' : (value < 0 ? '#f56c6c' : '#909399')
  )
      
      // 创建图表配置
  const options = {
        title: {
      text: `城市${pollutantName.value}对比分析`,
      left: 'center',
      top: 0
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'shadow'
      },
      formatter: (params) => {
        const cityIndex = params[0].dataIndex
        const item = sortedData[cityIndex]
        
        if (!item) return ''
        
        let result = `<div style="font-weight:bold">${item.city}</div>`
        
        result += `<div style="margin-top:5px">
          <span>平均值: </span>
          <span style="font-weight:bold">${item.mean}</span>
        </div>`
        
        result += `<div>
          <span>最小值: </span>
          <span>${item.min}</span>
        </div>`
        
        result += `<div>
          <span>最大值: </span>
          <span>${item.max}</span>
        </div>`
        
        result += `<div>
          <span>标准差: </span>
          <span>${item.std}</span>
        </div>`
        
        if (item.improvement !== undefined) {
          result += `<div>
            <span>改善率: </span>
            <span style="color:${item.improvement > 0 ? '#67c23a' : '#f56c6c'}">
              ${item.improvement > 0 ? '+' : ''}${item.improvement.toFixed(2)}%
            </span>
          </div>`
        }
        
        return result
      }
    },
    legend: {
      data: ['平均值', '最小值', '最大值', '改善率'],
      bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
      bottom: '60px',
      top: '60px',
          containLabel: true
        },
    toolbox: {
      feature: {
        saveAsImage: {
          title: '保存为图片'
        }
      }
        },
        xAxis: {
          type: 'category',
      data: cities,
      name: '城市',
      nameLocation: 'middle',
      nameGap: 35,
      axisLabel: {
        interval: 0,
        rotate: 30
      },
      axisLine: {
        lineStyle: {
          color: '#333'
        }
      }
        },
    yAxis: [
      {
          type: 'value',
        name: pollutantName.value,
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#5470c6'
          }
        },
        axisLabel: {
          formatter: '{value}'
        }
      },
      {
        type: 'value',
        name: '改善率 (%)',
        position: 'right',
        axisLine: {
          lineStyle: {
            color: '#91cc75'
          }
        },
        axisLabel: {
          formatter: '{value}%'
        }
      }
    ],
    series: [
      {
        name: '平均值',
          type: 'bar',
        data: means,
        barMaxWidth: 30,
        emphasis: {
          focus: 'series'
        }
      },
      {
        name: '最小值',
        type: 'bar',
        data: mins,
        barMaxWidth: 30,
        emphasis: {
          focus: 'series'
        }
      },
      {
        name: '最大值',
        type: 'bar',
        data: maxs,
        barMaxWidth: 30,
        emphasis: {
          focus: 'series'
        }
      },
      {
        name: '改善率',
        type: 'bar',
        yAxisIndex: 1,
        data: improvements,
        barMaxWidth: 30,
        itemStyle: {
          color: (params) => improvementColors[params.dataIndex]
        },
        emphasis: {
          focus: 'series'
          }
        }
    ]
  }
  
  return renderChart('comparison', 'comparison-trend-chart', options)
}

// 导出图表为图片
const exportCurrentChart = () => {
  const type = props.analysisType
  if (!chartInstances.value[type]) {
    ElMessage.warning('图表未准备好，无法导出')
    return
  }
  
  try {
    const fileName = `${type}-trend-${props.selectedPollutant}`
    emit('export-chart', chartInstances.value[type], fileName)
  } catch (error) {
    console.error('导出图表失败:', error)
    ElMessage.error('导出图表失败: ' + error.message)
  }
}

// 获取ECharts实例
const getEchartsInstance = () => {
  const type = props.analysisType
  return chartInstances.value[type]
}

// 监听数据和分析类型变化
watch(() => props.rawData, (newData) => {
  console.log('rawData变更:', Object.keys(newData).length > 0 ? '有数据' : '无数据')
  if (props.analysisComplete && !props.loading) {
    console.log('检测到新数据，触发重新渲染')
    nextTick(() => {
      renderChartByType()
    })
  }
}, { deep: true })

watch(() => props.analysisType, (newType, oldType) => {
  console.log('[TrendMainChart] 分析类型变更:', newType);
  // 只记录变更，不再自动触发渲染
  // if (props.analysisComplete && !props.loading) {
  //   console.log('分析类型从', oldType, '变更为', newType, '，触发重新渲染')
  //   nextTick(() => {
  //     renderChartByType()
  //   })
  // }
})

watch(() => props.analysisComplete, (newVal) => {
  if (newVal) {
    console.log('分析完成状态变更为true，触发渲染')
    nextTick(() => {
      setTimeout(() => {
        renderChartByType()
      }, 200)
    })
  }
})

// 渲染初始空状态图表
const renderEmptyCharts = () => {
  if (!props.analysisComplete) {
    nextTick(() => {
      setTimeout(() => {
        const emptyContainers = {
          annual: document.getElementById('empty-annual-chart'),
          seasonal: document.getElementById('empty-seasonal-chart'),
          monthly: document.getElementById('empty-monthly-chart'),
          comparison: document.getElementById('empty-comparison-chart')
        }
        
        const currentContainer = emptyContainers[props.analysisType]
        if (currentContainer) {
          console.log(`找到空状态图表容器: #empty-${props.analysisType}-chart`)
          
          // 清理可能存在的旧实例
          try {
            const existingChart = echarts.getInstanceByDom(currentContainer)
            if (existingChart) {
              existingChart.dispose()
            }
          } catch (e) { /* 忽略错误 */ }
          
          // 创建空状态图表
          try {
            const emptyOptions = {
              grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '10%',
                containLabel: true
              },
              xAxis: {
                type: 'category',
                data: ['暂无数据'],
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { show: false }
              },
              yAxis: {
                type: 'value',
                axisLine: { show: false },
                axisTick: { show: false },
                axisLabel: { show: false },
                splitLine: { show: false }
              },
              series: []
            }
            
            const chart = echarts.init(currentContainer)
            chart.setOption(emptyOptions)
          } catch (e) {
            console.log('渲染空状态图表出错（可忽略）:', e)
          }
        }
      }, 200)
    })
  }
}

// 在组件挂载时初始化
onMounted(() => {
  console.log('TrendMainChart组件已挂载，当前分析类型:', props.analysisType)
  
  // 添加更多调试信息
  console.log('组件状态:', {
    analysisComplete: props.analysisComplete,
    loading: props.loading,
    error: props.error,
    hasData: props.rawData && Object.keys(props.rawData).length > 0
  })
  
  // 验证容器 - 仅在分析完成时验证
  if (props.analysisComplete) {
    setTimeout(() => {
      // 检查容器
      const containers = {
        annual: document.getElementById('annual-trend-chart'),
        seasonal: document.getElementById('seasonal-trend-chart'),
        monthly: document.getElementById('monthly-trend-chart'),
        comparison: document.getElementById('comparison-trend-chart')
      }
      
      console.log('挂载后验证图表容器状态:', {
        annual: containers.annual ? '存在' : '不存在',
        seasonal: containers.seasonal ? '存在' : '不存在',
        monthly: containers.monthly ? '存在' : '不存在',
        comparison: containers.comparison ? '存在' : '不存在'
      })
      
      // 仅当分析类型容器存在时才渲染
      if (containers[props.analysisType]) {
        console.log(`${props.analysisType}容器存在且已准备好渲染`)
      } else {
        console.warn(`${props.analysisType}容器不存在，尝试强制创建`)
        
        // 如果分析已完成但容器不存在，强制重渲染组件
        if (props.analysisComplete && !props.loading) {
          console.log('触发forceRender尝试修复容器问题')
          forceRender()
        }
      }
    }, 500)
  } else {
    console.log('分析未完成，等待分析完成后再验证容器')
  }
  
  // 添加窗口resize事件监听
  window.addEventListener('resize', handleResize)
  
  // 如果分析已完成，渲染图表
  if (props.analysisComplete && !props.loading) {
    console.log('组件挂载时分析已完成，执行初始渲染')
    // 延迟渲染确保DOM已准备好
    nextTick(() => {
      setTimeout(() => {
        try {
          renderChartByType()
        } catch (err) {
          console.error('挂载后渲染图表出错:', err)
          ElMessage.error(`渲染图表失败: ${err.message || '未知错误'}`)
        }
      }, 500)
    })
  }
  
  // 如果未开始分析，渲染空状态图表
  if (!props.analysisComplete) {
    renderEmptyCharts()
  }
  
  // 添加全局事件监听
  const handleForceRender = () => {
    console.log('接收到force-render事件，强制重新渲染图表')
    forceRender()
  }
  document.addEventListener('force-render', handleForceRender)
  
  // 保存回调引用以便清理
  window._handleForceRender = handleForceRender
})

// 暴露方法给父组件
defineExpose({
  getEchartsInstance,
  exportChart: exportCurrentChart,
  forceRender
})

// 在组件销毁前清理
onBeforeUnmount(() => {
  // 清理所有图表实例
  Object.keys(chartInstances.value).forEach(type => {
    const instance = chartInstances.value[type]
    if (instance) {
      try {
        // 清理resize事件
        if (instance._resizeHandler) {
          window.removeEventListener('resize', instance._resizeHandler)
        }
        
        // 销毁实例
        instance.dispose()
        console.log(`${type}图表实例已销毁`)
      } catch (error) {
        console.error(`销毁${type}图表实例出错:`, error)
      }
    }
  })
  
  // 清理全局事件
  window.removeEventListener('resize', handleResize)
  
  // 移除全局事件监听
  if (window._handleForceRender) {
    document.removeEventListener('force-render', window._handleForceRender)
    delete window._handleForceRender
  }
})

// 使用防抖处理的全局resize函数
const handleResize = debounce(() => {
  // 避免重复处理
  if (isResizing.value) return
  
  isResizing.value = true
  console.log('Window resize触发图表尺寸调整')
  
  try {
    const currentChartInstance = chartInstances.value[props.analysisType]
    if (currentChartInstance && !currentChartInstance.isDisposed()) {
      console.log(`${props.analysisType}图表resize开始`)
      
      // 获取当前容器的尺寸
      const container = document.getElementById(`${props.analysisType}-trend-chart`)
      if (container) {
        const containerRect = container.getBoundingClientRect()
        currentChartInstance.resize({
          width: containerRect.width,
          height: 500
        })
        console.log(`${props.analysisType}图表resize成功，新尺寸:`, {
          width: containerRect.width,
          height: 500
        })
      } else {
        // 如果找不到容器，使用默认resize
        currentChartInstance.resize()
        console.log(`${props.analysisType}图表resize成功（使用默认尺寸）`)
      }
    }
  } catch (err) {
    console.error('调整图表大小出错:', err)
  }
  
  // 重置标记
  setTimeout(() => {
    isResizing.value = false
  }, 200)
}, 300) // 300ms防抖
</script>

<style scoped>
.trend-main-chart {
  width: 100%;
  margin-bottom: 20px;
}

.chart-wrapper {
  width: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  height: 500px;
  min-height: 500px;
  background: #fafafa;
  border-radius: 8px;
  overflow: visible;
  margin-bottom: 10px;
  box-sizing: border-box;
}

.chart-debug-info {
  font-size: 12px;
  color: #999;
  text-align: right;
  padding: 5px 10px;
  margin-top: 5px;
}

.chart-loading,
.chart-error,
.chart-empty {
  width: 100%;
  height: 500px;
  min-height: 500px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #fafafa;
  border-radius: 8px;
}

.loading-indicator {
  width: 50px;
  height: 50px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #409eff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-chart-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.empty-chart {
  width: 100%;
  height: 100%;
}

.empty-chart-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: rgba(250, 250, 250, 0.8);
}

.chart-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.error-actions {
  margin-top: 20px;
}
</style> 