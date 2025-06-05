// 数据可视化应用的主要视图组件
<template>
  <!-- 添加 LoadingOverlay 组件 -->
  <LoadingOverlay 
    :loading="loading" 
    :loadingTip="loadingTip" 
    :loadingProgress="loadingProgress"
    :loadingErrors="loadingErrors"
  />
  
  <!-- 修改：添加动态class以控制过渡效果 -->
  <div class="dashboard-container" :class="{ 'loading': loading }">
    <!-- 主要内容区域 -->
    <div class="dashboard-layout">
      <!-- 地图容器 - 独立一行 -->
      <div class="dashboard-row">
        <AirQualityMap
          :provinceData="dataStore.provinceData"
          :provinceError="dataStore.provinceError"
          :isProvinceLoading="dataStore.isProvinceLoading"
          @refresh-map="refreshMap"
          @reset-view="resetMapView"
          @zoom-map="zoomMap"
          @zoom-out-map="zoomOutMap"
          @map-type-change="handleMapTypeChange"
          @city-click="handleCityClick"
          ref="mapRef"
        />
      </div>
      
      <!-- 污染物分布 - 独立一行 -->
      <div class="dashboard-row">
        <PollutantChart
          :cityOptions="cityOptions"
          :initialCity="selectedCity"
          :cityData="dataStore.getCurrentData(selectedCity) || {}"
          :loading="loading"
          @city-change="handleCityChange"
          ref="pollutantChartRef"
        />
      </div>
      
      <!-- 城市排名和最新预警并列 -->
      <div class="dashboard-row dual-cards">
        <!-- 城市排名表格 -->
        <CityRanking
          :provinceData="dataStore.provinceData"
          :loading="loading"
          :isProvinceLoading="dataStore.isProvinceLoading"
        />
        
        <!-- 最新预警 -->
        <AlertsPanel
          :alerts="alertsToShow"
          :loading="loading"
          :alertsLoading="alerts.loading"
          @refresh-alerts="refreshAlerts"
          @show-all-alerts="showAllAlerts"
          ref="alertsPanelRef"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, onUnmounted, onActivated, reactive, nextTick } from 'vue'
import { useDataStore } from '@/store/dataStore'
import { useUserStore } from '@/store/userStore'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

// 导入组件
import LoadingOverlay from '@/components/LoadingOverlay.vue'
import AirQualityMap from '@/components/dashboard/AirQualityMap.vue'
import PollutantChart from '@/components/dashboard/PollutantChart.vue'
import CityRanking from '@/components/dashboard/CityRanking.vue'
import AlertsPanel from '@/components/dashboard/AlertsPanel.vue'

// Store
const dataStore = useDataStore()
const userStore = useUserStore()

// 添加全局变量
let refreshInterval = null // 自动刷新定时器
let mapUpdateTimer = null // 地图更新定时器
let isRerendering = false // 防止重复渲染的标志
let monitoringInterval = null // 监控定时器

// 页面加载状态
const loading = ref(true)
const loadingProgress = ref(0)
const loadingTip = ref('正在初始化页面...')
const loadingErrors = ref([])
const loadingAttempts = ref(0)
const loadTimestamp = ref(Date.now())

// 组件引用
const mapRef = ref(null)
const pollutantChartRef = ref(null)
const alertsPanelRef = ref(null)

// 状态
const selectedCity = ref('广州市')
const mapLoaded = ref(false)

// 最短数据更新间隔（毫秒）
const MIN_UPDATE_INTERVAL = 60 * 1000 // 1分钟

// 预警数据
const alerts = reactive({
  loading: false,
  error: null,
  items: [],
  lastUpdated: null
})

// 城市选项数据
const cityOptions = computed(() => {
  if (!dataStore.provinceData || dataStore.provinceData.length === 0) {
    return [{ label: '广州市', value: '广州市' }] // 默认城市
  }
  
  return dataStore.provinceData.map(city => ({
    label: city.name,
    value: city.name
  }))
})

// 限制显示的预警数量
const alertsToShow = computed(() => {
  // 显示最多10条预警信息
  const displayCount = Math.min(alerts.items.length, 10)
  return alerts.items.slice(0, displayCount)
})

// 加载广东省地图数据
const loadGdMap = async () => {
  try {
    // 全局变量记录地图加载状态，避免重复加载
    if (window.gdMapLoaded) {
      return true
    }
    
    // 检查是否已经加载
    if (echarts.getMap('guangdong')) {
      window.gdMapLoaded = true
      mapLoaded.value = true
      return true
    }
    
    // 仅加载一次地图数据
    try {
      const response = await fetch('/guangdong.json')
      if (!response.ok) {
        throw new Error(`HTTP错误: ${response.status}`)
      }
      
      const gdJson = await response.json()
      
      // 验证数据是否有效
      if (!gdJson || !gdJson.features || !gdJson.features.length) {
        throw new Error('地图数据格式不正确')
      }
      
      // 注册地图数据
      echarts.registerMap('guangdong', gdJson)
      
      // 标记为已加载
      window.gdMapLoaded = true
      mapLoaded.value = true
      
      return true
    } catch (error) {
      loadingErrors.value.push(`广东地图数据加载失败: ${error.message}`)
      return false
    }
  } catch (error) {
    return false
  }
}

// 方法
const fetchProvinceData = async () => {
  if (dataStore.isProvinceLoading) {
    console.log('省份数据正在加载中，跳过重复请求')
    return
  }
  
  try {
    console.log('正在获取省份数据...')
    
    await dataStore.fetchProvinceData()
    
    console.log('省份数据获取成功，数据条数:', dataStore.provinceData?.length)
  } catch (error) {
    console.error('获取省份数据失败:', error)
    ElMessage.error('获取省份数据失败: ' + (error.message || '未知错误'))
  }
}

const fetchRealTimeData = async (city) => {
  if (!city) {
    city = '广州市'
  }
  
  try {
    await dataStore.fetchRealTimeData(city)
    
    // 检查数据是否正确获取
    if (!dataStore.realTimeData.cityData[city]) {
      throw new Error(`未获取到${city}的实时数据`)
    }
    
    return dataStore.realTimeData.cityData[city]
  } catch (error) {
    console.error(`获取${city}实时数据失败:`, error)
    ElMessage.error(`获取${city}实时数据失败，请重试`)
    throw error
  }
}

// 获取预警数据
const fetchAlerts = async (limit = 10, forceRefresh = false) => {
  try {
    alerts.loading = true
    alerts.error = null
    
    // 使用数据仓库获取预警数据，强制刷新以获取最新数据
    const alertsData = await dataStore.fetchAlerts(forceRefresh)
    
    if (alertsData && alertsData.length > 0) {
      // 按照AQI值降序排序，显示污染最严重的城市预警
      const sortedAlerts = [...alertsData].sort((a, b) => b.aqi - a.aqi)
      // 取最新的几条预警
      alerts.items = sortedAlerts.slice(0, limit)
      alerts.lastUpdated = new Date().getTime()
    } else {
      alerts.items = []
    }
    
  } catch (error) {
    console.log("获取预警数据时出现错误，但不影响页面正常使用")
    alerts.error = null // 防止错误显示影响用户体验
    alerts.items = []
  } finally {
    alerts.loading = false
  }
}

// 安全调用污染物图表方法
const safeCallPollutantChart = (method, ...args) => {
  if (pollutantChartRef.value) {
    try {
      // 确保该方法存在
      if (typeof pollutantChartRef.value[method] === 'function') {
        return pollutantChartRef.value[method](...args)
      }
    } catch (error) {
      console.warn(`调用污染物图表${method}方法失败:`, error)
    }
  }
  return null
}

// 自动刷新数据函数
const startAutoRefresh = () => {
  // 清除可能存在的定时器
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  
  // 设置定时器，每5分钟刷新一次数据
  refreshInterval = setInterval(async () => {
    try {
      // 刷新省份数据
      await fetchProvinceData()
      
      // 刷新实时数据
      await fetchRealTimeData(selectedCity.value)
      
      // 刷新预警数据，强制刷新
      await fetchAlerts(10, true)
      
      // 安全刷新图表
      setTimeout(() => safeCallPollutantChart('renderChart'), 100)
      
    } catch (error) {
      // 自动刷新失败时静默处理
    }
  }, 5 * 60 * 1000) // 5分钟
}

// 处理城市变更
const handleCityChange = (city) => {
  if (!city) {
    console.warn('城市选择失败: 未提供有效的城市名')
    return
  }
  
  selectedCity.value = city
  
  fetchRealTimeData(city).then(() => {
    console.log(`已获取${city}的实时数据`)
    
    // 安全调用污染物图表渲染方法
    safeCallPollutantChart('renderChart')
  }).catch(error => {
    console.error(`获取${city}实时数据失败:`, error)
    ElMessage.error(`获取${city}数据失败，将显示最后可用数据`)
    
    // 即使获取数据失败，也尝试渲染图表（使用现有数据）
    safeCallPollutantChart('renderChart')
  })
}

// 处理地图点击
const handleCityClick = (city) => {
  if (!city) {
    console.warn('地图点击事件未提供有效城市名')
    return
  }
  
  selectedCity.value = city
  
  fetchRealTimeData(city).then(() => {
    console.log(`已获取${city}的实时数据`)
    
    safeCallPollutantChart('renderChart')
  }).catch(error => {
    console.error(`地图点击后获取${city}实时数据失败:`, error)
    
    // 即使获取数据失败，也尝试渲染图表
    safeCallPollutantChart('renderChart')
  })
}

// 地图相关操作
const refreshMap = async () => {
  try {
    dataStore.isProvinceLoading = true;
    
    // 刷新省份数据
    await dataStore.fetchProvinceData();
    
    // 刷新地图 - 简化调用过程
    if (mapRef.value && mapRef.value.renderMap) {
      mapRef.value.renderMap(dataStore.provinceData);
    }
    
    // 简短提示，减少视觉干扰
    ElMessage.success('数据已刷新');
  } catch (error) {
    ElMessage.error('刷新失败');
  } finally {
    dataStore.isProvinceLoading = false;
  }
}

const resetMapView = () => {
  // 使用地图组件的引用来重置视图
  if (mapRef.value && mapRef.value.chart) {
    try {
      // 获取地图实例
      const chartInstance = mapRef.value.chart;
      
      // 重置地图视图
      if (chartInstance.value) {
        chartInstance.value.dispatchAction({
          type: 'restore' // ECharts内置的重置视图操作
        });
        
        // 重新渲染地图确保显示正确
        mapRef.value.renderMap(dataStore.provinceData);
      }
      
      ElMessage({
        message: '已重置地图视图',
        type: 'success',
        duration: 1500
      });
    } catch (error) {
      console.error('重置地图视图失败:', error);
      ElMessage.warning('重置地图视图失败，请刷新页面');
    }
  } else {
  }
}

const zoomMap = () => {
  // 地图放大操作
  if (mapRef.value && mapRef.value.chart) {
    try {
      // 获取地图实例
      const chartInstance = mapRef.value.chart;
      
      // 放大地图
      if (chartInstance.value) {
        // 模拟鼠标滚轮放大效果
        chartInstance.value.dispatchAction({
          type: 'dataZoom',
          dataZoomIndex: 0,
          start: 20,
          end: 80,
          zoomScale: 1.2 // 放大比例
        });
        
        // 设置特定的缩放级别
        const currentOption = chartInstance.value.getOption();
        if (currentOption && currentOption.series && currentOption.series[0]) {
          const currentZoom = currentOption.series[0].zoom || 1;
          const newZoom = Math.min(currentZoom * 1.5, 3); // 最大放大到3倍
          
          chartInstance.value.setOption({
            series: [{
              zoom: newZoom
            }]
          }, false);
        }
      }
      
      ElMessage({
        message: '已放大地图视图',
        type: 'success',
        duration: 1500
      });
    } catch (error) {
      console.error('地图放大失败:', error);
      ElMessage.warning('地图放大失败，请尝试重置视图');
    }
  } else {
    ;
  }
}

const zoomOutMap = () => {
  // 地图缩小操作
  if (mapRef.value && mapRef.value.chart) {
    try {
      // 获取地图实例
      const chartInstance = mapRef.value.chart;
      
      // 缩小地图
      if (chartInstance.value) {
        // 模拟鼠标滚轮缩小效果
        chartInstance.value.dispatchAction({
          type: 'dataZoom',
          dataZoomIndex: 0,
          start: 20,
          end: 80,
          zoomScale: 0.8 // 缩小比例
        });
        
        // 设置特定的缩放级别
        const currentOption = chartInstance.value.getOption();
        if (currentOption && currentOption.series && currentOption.series[0]) {
          const currentZoom = currentOption.series[0].zoom || 1;
          const newZoom = Math.max(currentZoom * 0.7, 0.8); // 最小缩小到0.8倍
          
          chartInstance.value.setOption({
            series: [{
              zoom: newZoom
            }]
          }, false);
        }
      }
      
      ElMessage({
        message: '已缩小地图视图',
        type: 'success',
        duration: 1500
      });
    } catch (error) {
      console.error('地图缩小失败:', error);
      ElMessage.warning('地图缩小失败，请尝试重置视图');
    }
  } else {
    ;
  }
}

const handleMapTypeChange = (type) => {
    ElMessage({
      message: `已切换到${type === 'aqi' ? 'AQI指数' : type === 'pm25' ? 'PM2.5' : 'PM10'}地图`,
      type: 'success',
      duration: 1500
  })
  }

// 快速刷新数据
const quickRefreshData = async () => {
  try {
    // 避免频繁刷新，检查上次刷新时间
    const lastUpdateTime = dataStore.lastUpdateTime ? new Date(dataStore.lastUpdateTime).getTime() : 0
    const now = Date.now()
    
    if (now - lastUpdateTime < 30000) { // 30秒内不重复刷新
      ElMessage.info('数据已是最新')
      return
    }
    
    // 设置加载状态
    dataStore.isProvinceLoading = true
    
    // 并行刷新所有数据
    await Promise.all([
      dataStore.fetchProvinceData(),
      fetchRealTimeData(selectedCity.value),
      fetchAlerts(5, true) // 确保强制刷新预警数据
    ])
    
    // 安全刷新图表
    setTimeout(() => safeCallPollutantChart('renderChart'), 100)
    
    // 显示成功消息
    ElMessage({
      message: '数据已刷新',
      type: 'success',
      duration: 1500
    })
  } catch (error) {
    console.error('数据刷新失败:', error)
    ElMessage.error('数据刷新失败，请稍后重试')
  } finally {
    dataStore.isProvinceLoading = false
  }
}

// 刷新预警数据
const refreshAlerts = async () => {
  try {
    await fetchAlerts(10, true)
    
    // 显示成功消息
    ElMessage({
      message: '预警数据已刷新',
      type: 'success',
      duration: 1500
    })
  } catch (error) {
    console.error('刷新预警数据失败:', error)
    ElMessage.error('刷新预警数据失败，请稍后重试')
  }
}

// 显示全部预警
const showAllAlerts = async () => {
  try {
    await fetchAlerts(100, true) // 获取更多预警数据
    
    if (alertsPanelRef.value) {
      alertsPanelRef.value.setAllAlerts(alerts.items)
      alertsPanelRef.value.openAllAlertsDialog()
    }
  } catch (error) {
    console.error('获取全部预警数据失败:', error)
    ElMessage.error('获取全部预警数据失败，请稍后重试')
  }
}

// 重试加载
const retryLoading = async () => {
  loadingAttempts.value++
  loading.value = true
  loadingTip.value = '正在重新加载...'
  loadingProgress.value = 10
  loadingErrors.value = []
  
  try {
    // 初始化数据
    await initPageData()
  } catch (error) {
    console.error('重试加载失败:', error)
    loadingErrors.value.push(`重试失败: ${error.message || '未知错误'}`)
  }
}

// 初始化页面数据函数
const initPageData = async () => {
  try {
    loading.value = true
    loadingProgress.value = 10 // 开始加载
    
    loadingTip.value = '正在加载地图数据...'
    
    // 1. 首先确保地图数据已加载
    let mapLoadSuccess = false
    try {
      mapLoadSuccess = await loadGdMap()
      loadingProgress.value = 30
      
      if (!mapLoadSuccess) {
        loadingErrors.value.push('地图数据初始加载失败，稍后将重试')
      }
    } catch (error) {
      loadingErrors.value.push('地图数据加载失败，将使用备用数据')
    }
    
    loadingTip.value = '正在获取省份数据...'
    
    // 2. 获取各种数据
    try {
      // 获取省份数据
      await fetchProvinceData()
      loadingProgress.value = 50
      
      // 获取实时数据
      loadingTip.value = '正在获取实时数据...'
      await fetchRealTimeData(selectedCity.value)
      loadingProgress.value = 70
      
      // 获取预警数据
      loadingTip.value = '正在获取预警数据...'
      await fetchAlerts(10, true)
      loadingProgress.value = 90
    } catch (error) {
      loadingErrors.value.push('部分数据获取失败，将显示可用数据')
    }
    
    loadingProgress.value = 100
    loadingTip.value = '加载完成！'
    setTimeout(() => {
      loading.value = false
    }, 500)
    
    // 启动自动刷新
    startAutoRefresh()
  } catch (error) {
    loadingErrors.value.push('页面初始化失败: ' + error.message)
    loadingProgress.value = 100
    loading.value = false
  }
}

// 格式化日期时间
const formatDateTime = (timestamp) => {
  if (!timestamp) return '未知时间'
  
  try {
    // 处理字符串格式的时间戳
    let date;
    if (typeof timestamp === 'string') {
      // 尝试处理ISO格式的日期字符串
      if (timestamp.includes('T') || timestamp.includes('-')) {
        date = new Date(timestamp);
      } else {
        // 尝试处理数字字符串
        date = new Date(parseInt(timestamp, 10));
      }
    } else if (typeof timestamp === 'number') {
      date = new Date(timestamp);
    } else {
      date = new Date(timestamp);
    }
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return '刚刚更新';
    }
    
    // 格式化日期
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    console.error('日期格式化错误:', error, timestamp);
    return '刚刚更新';
  }
}

// 生命周期钩子
onMounted(async () => {
  console.log('[Dashboard] 组件挂载')
  
  try {
    // 初始化页面数据
    await initPageData()
  } catch (error) {
    console.error('[Dashboard] 初始化失败:', error)
    loadingErrors.value.push('初始化过程中出错:' + error.message)
    loading.value = false
  }
})

onUnmounted(() => {
  console.log('[Dashboard] 组件卸载，清理资源')
  
  // 清除数据刷新定时器
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
  
  // 清除地图更新定时器
  if (mapUpdateTimer) {
    clearInterval(mapUpdateTimer)
    mapUpdateTimer = null
  }
  
  // 清除监控定时器
  if (monitoringInterval) {
    clearInterval(monitoringInterval)
    monitoringInterval = null
  }
})

onActivated(() => {
  console.log('[Dashboard] 组件被激活')
  
  // 如果距离上次加载时间超过5分钟，则重新获取数据
  const timeElapsed = Date.now() - loadTimestamp.value
  if (timeElapsed > 5 * 60 * 1000) {
    console.log('[Dashboard] 距离上次加载已超过5分钟，重新获取数据')
    
    // 静默刷新数据，不显示加载界面
    quickRefreshData().catch(console.error)
    loadTimestamp.value = Date.now()
  } else {
    // 组件激活时给DOM一点时间再重新渲染图表
    setTimeout(() => {
      if (pollutantChartRef.value) {
        try {
          pollutantChartRef.value.renderChart()
          console.log('[Dashboard] 组件激活后重新渲染图表')
        } catch (error) {
          console.warn('[Dashboard] 图表重新渲染失败', error)
        }
      }
      
      // 如果地图也需要重新渲染
      if (mapRef.value && mapRef.value.renderMap) {
        try {
          mapRef.value.renderMap(dataStore.provinceData)
        } catch (error) {
          console.warn('[Dashboard] 地图重新渲染失败', error)
        }
      }
    }, 500)
  }
})
</script>

<style>
@import '../assets/styles/dashboard.css';
</style>