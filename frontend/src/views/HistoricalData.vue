<template>
  <div class="historical-data-page">
    <div class="filter-bar card">
      <div class="filter-group">
        <label>选择城市:</label>
        <el-select v-model="selectedCity" class="city-select" filterable placeholder="请选择城市">
          <el-option
            v-for="city in cities"
            :key="city"
            :label="city"
            :value="city">
          </el-option>
        </el-select>
      </div>
      
      <div class="filter-group">
        <label>时间范围:</label>
        <div class="date-range-container">
          <div class="date-range-preset">
            <select v-model="selectedDateRange" class="date-range-select" @change="applyDateRange">
              <option value="custom">自定义</option>
              <option value="last7days">最近7天</option>
              <option value="last30days">最近30天</option>
              <option value="last90days">最近90天</option>
              <option value="thisYear">今年</option>
              <option value="lastYear">去年</option>
              <option value="last5Years">近5年</option>
              <option value="all">全部数据</option>
            </select>
          </div>
          <div class="date-range">
            <div class="date-input-container">
              <input id="startDateDisplay" type="text" :value="formatDateForDisplay(startDate)" readonly class="date-input" @click="openStartDatePicker" />
              <i class="date-icon">📅</i>
              <div v-if="showStartDatePicker" class="date-picker-overlay" @click.self="showStartDatePicker = false">
                <div class="date-picker-container">
                  <div class="date-picker-header">
                    <button id="startMonthPrev" class="date-nav-btn" @click.prevent="changeMonth(-1)">&lt;</button>
                    <span class="date-header-text">{{ currentMonthYear }}</span>
                    <button id="startMonthNext" class="date-nav-btn" @click.prevent="changeMonth(1)">&gt;</button>
                  </div>
                  <input id="startDatePicker" type="date" 
                    v-model="startDate" 
                    class="date-picker-input" 
                    @change="onStartDateChange"
                    :min="earliestDate"
                    :max="getTodayDate()" />
                </div>
              </div>
            </div>
            <span class="date-separator">至</span>
            <div class="date-input-container">
              <input id="endDateDisplay" type="text" :value="formatDateForDisplay(endDate)" readonly class="date-input" @click="openEndDatePicker" />
              <i class="date-icon">📅</i>
              <div v-if="showEndDatePicker" class="date-picker-overlay" @click.self="showEndDatePicker = false">
                <div class="date-picker-container">
                  <div class="date-picker-header">
                    <button id="endMonthPrev" class="date-nav-btn" @click.prevent="changeEndMonth(-1)">&lt;</button>
                    <span class="date-header-text">{{ currentEndMonthYear }}</span>
                    <button id="endMonthNext" class="date-nav-btn" @click.prevent="changeEndMonth(1)">&gt;</button>
                  </div>
                  <input id="endDatePicker" type="date" 
                    v-model="endDate" 
                    class="date-picker-input" 
                    @change="onEndDateChange"
                    :min="startDate || earliestDate"
                    :max="getTodayDate()" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="filter-group">
        <label for="dataTypeSelect">数据类型:</label>
        <select id="dataTypeSelect" v-model="selectedDataType" class="filter-select" name="dataType">
          <option value="all">全部指标</option>
          <option value="aqi">AQI</option>
          <option value="pm25">PM2.5</option>
          <option value="pm10">PM10</option>
          <option value="so2">SO2</option>
          <option value="no2">NO2</option>
          <option value="o3">O3</option>
          <option value="co">CO</option>
        </select>
      </div>
      
      <div class="filter-group">
        <label for="qualityLevelSelect">空气质量等级:</label>
        <select id="qualityLevelSelect" v-model="selectedQualityLevel" class="filter-select" name="qualityLevel">
          <option value="all">所有等级</option>
          <option value="优">优</option>
          <option value="良">良</option>
          <option value="轻度污染">轻度污染</option>
          <option value="中度污染">中度污染</option>
          <option value="重度污染">重度污染</option>
          <option value="严重污染">严重污染</option>
        </select>
      </div>
      
      <button id="queryBtn" class="btn btn-primary" @click="queryData">查询</button>
      <button id="refreshBtn" class="btn btn-refresh" @click="refreshData" :disabled="refreshing">
        <span v-if="refreshing">刷新中...</span>
        <span v-else>刷新数据</span>
      </button>
    </div>
    
    <div class="data-container card">
      <div class="card-header">
        <h2 class="card-title">查询结果</h2>
        <div class="card-actions">
          <button 
            class="btn-outline" 
            @click="exportData" 
            :disabled="!hasData || exporting"
          >
            <span v-if="exporting">导出中...</span>
            <span v-else>导出数据</span>
          </button>
        </div>
      </div>
      
      <div class="card-body">
        <div v-if="loading" class="loading-container">
          <div class="spinner"></div>
          <p>加载中...</p>
        </div>
        
        <div v-else-if="error" class="error-message">
          {{ error }}
          <button class="retry-button" @click="queryData">重试</button>
        </div>
        
        <div v-else-if="!hasData" class="placeholder-text">
          请选择查询条件并点击查询按钮来查看历史数据...
        </div>
        
        <div v-else>
          <div class="data-summary">
            <p>查询结果: 共 <strong>{{ historicalData.length }}</strong> 条记录</p>
            <p>查询时间范围: <strong>{{ formatDateForDisplay(startDate) }}</strong> 至 <strong>{{ formatDateForDisplay(endDate) }}</strong></p>
            <p>查询城市: <strong>{{ selectedCity }}</strong></p>
          </div>
          
          <div class="data-content">
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>城市</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'aqi'">AQI</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'aqi'">空气质量等级</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'aqi'"></th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'pm25'">PM2.5 (μg/m³)</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'pm10'">PM10 (μg/m³)</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'so2'">SO2 (μg/m³)</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'no2'">NO2 (μg/m³)</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'co'">CO (mg/m³)</th>
                    <th v-if="selectedDataType === 'all' || selectedDataType === 'o3'">O3 (μg/m³)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in paginatedData" :key="index">
                    <td>{{ formatDate(item.date || item.record_date) }}</td>
                    <td>{{ item.city }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'aqi'" :class="getAqiClass(item.aqi || item.aqi_index)">{{ item.aqi || item.aqi_index }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'aqi'" :class="getAqiClass(item.aqi || item.aqi_index)">{{ item.quality_level }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'aqi'"></td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'pm25'">{{ item.pm25 || item.pm25_avg }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'pm10'">{{ item.pm10 || item.pm10_avg }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'so2'">{{ item.so2 || item.so2_avg }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'no2'">{{ item.no2 || item.no2_avg }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'co'">{{ item.co || item.co_avg }}</td>
                    <td v-if="selectedDataType === 'all' || selectedDataType === 'o3'">{{ item.o3 || item.o3_avg }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <div class="pagination-wrapper">
              <div class="pagination">
                <div class="pagination-controls">
                  <button class="btn-outline btn-sm" @click="prevPage" :disabled="currentPage === 1">上一页</button>
                  <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
                  <button class="btn-outline btn-sm" @click="nextPage" :disabled="currentPage === totalPages">下一页</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 新增Toast通知组件 -->
    <div class="toast-container" v-if="showToast">
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
import { ref, computed, onMounted } from 'vue'
import { fetchHistoricalData, fetchCities, exportHistoricalData } from '../services/api'
import { ElSelect, ElOption, ElMessage } from 'element-plus'

// 初始化状态
const selectedCity = ref('广州市')
const startDate = ref('')
const endDate = ref('')
const selectedDateRange = ref('last7days')  // 默认改为最近7天
const showStartDatePicker = ref(false)
const showEndDatePicker = ref(false)
const currentPickerMonth = ref(new Date())
const currentEndPickerMonth = ref(new Date())
const selectedDataType = ref('all')
const selectedQualityLevel = ref('all')
const loading = ref(false)
const exporting = ref(false)
const refreshing = ref(false)
const error = ref('')
const historicalData = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const latestDate = ref(null)
const earliestDate = ref(null)

// 城市列表
const cities = ref([])

// 获取城市列表
const fetchCityList = async () => {
  try {
    const response = await fetchCities()
    console.log('城市列表API响应:', response)
    
    // 处理不同格式的API响应
    if (response.status === 'success' && response.data) {
      // 如果response.data是数组，直接使用
      if (Array.isArray(response.data)) {
        cities.value = response.data
      } 
      // 如果response.data是对象且包含cities数组
      else if (response.data.cities && Array.isArray(response.data.cities)) {
        cities.value = response.data.cities
      }
      // 其他情况，尝试找出第一个数组属性
      else if (typeof response.data === 'object') {
        const firstArrayProp = Object.values(response.data).find(val => Array.isArray(val))
        if (firstArrayProp) {
          cities.value = firstArrayProp
        }
      }
    } else {
      // 使用默认城市列表
      cities.value = getDefaultCities()
    }
    
    // 确保城市列表不为空
    if (!cities.value || cities.value.length === 0) {
      cities.value = getDefaultCities()
    }
    
    console.log('处理后的城市列表:', cities.value)
    
    // 如果当前选择的城市不在列表中，设置为第一个城市
    if (cities.value.length > 0 && !cities.value.includes(selectedCity.value)) {
      selectedCity.value = cities.value[0]
    }
  } catch (err) {
    console.error('获取城市列表失败:', err)
    cities.value = getDefaultCities()
    
    // 如果当前选择的城市不在列表中，设置为第一个城市
    if (cities.value.length > 0 && !cities.value.includes(selectedCity.value)) {
      selectedCity.value = cities.value[0]
    }
  }
}

// 默认城市列表
const getDefaultCities = () => {
  return [
    '广州市', '深圳市', '珠海市', '汕头市', '佛山市', '韶关市', 
    '湛江市', '肇庆市', '江门市', '茂名市', '惠州市', '梅州市', 
    '汕尾市', '河源市', '阳江市', '清远市', '东莞市', '中山市', 
    '潮州市', '揭阳市', '云浮市'
  ]
}

// 在组件挂载时获取城市列表
onMounted(() => {
  fetchCityList()
  fetchDateRange()  // 获取日期范围
  initializeDates() // 初始化默认日期
})

// 计算属性
const hasData = computed(() => historicalData.value.length > 0)

const totalPages = computed(() => {
  return Math.ceil(historicalData.value.length / pageSize.value)
})

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = Math.min(start + pageSize.value, historicalData.value.length)
  return historicalData.value.slice(start, end)
})

const currentMonthYear = computed(() => {
  const month = currentPickerMonth.value.getMonth()
  const year = currentPickerMonth.value.getFullYear()
  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
  return `${monthNames[month]} ${year}`
})

const currentEndMonthYear = computed(() => {
  const month = currentEndPickerMonth.value.getMonth()
  const year = currentEndPickerMonth.value.getFullYear()
  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
  return `${monthNames[month]} ${year}`
})

// Toast通知状态
const showToast = ref(false)
const toastMessage = ref('')
const toastType = ref('success') // success, error, info

// 显示Toast通知
const showToastMessage = (message, type = 'success', duration = 3000) => {
  toastMessage.value = message
  toastType.value = type
  showToast.value = true
  
  // 自动关闭
  setTimeout(() => {
    showToast.value = false
  }, duration)
}

// 方法
const queryData = async () => {
  // 验证日期输入
  if (!startDate.value || !endDate.value) {
    error.value = '请选择开始和结束日期'
    return
  }
  
  // 确保日期不是未来日期
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  let start = new Date(startDate.value);
  let end = new Date(endDate.value);
  
  if (start > today || end > today) {
    const todayStr = formatDateForInput(today);
    if (start > today) {
      startDate.value = todayStr;
      start = today;
    }
    if (end > today) {
      endDate.value = todayStr;
      end = today;
    }
  }
  
  console.log(`查询参数: 城市=${selectedCity.value}, 开始日期=${startDate.value}, 结束日期=${endDate.value}`)
  
  loading.value = true
  error.value = ''
  
  try {
    const params = {
      city: selectedCity.value,
      start_date: startDate.value,
      end_date: endDate.value,
      data_type: selectedDataType.value,
      quality_level: selectedQualityLevel.value
    }
    
    // 使用services/api.js中的方法
    const data = await fetchHistoricalData(params)
    historicalData.value = data
    currentPage.value = 1
  } catch (err) {
    console.error('Failed to fetch historical data:', err)
    error.value = err.message || '获取数据失败，请稍后重试'
    historicalData.value = []
  } finally {
    loading.value = false
  }
}

const exportData = async () => {
  if (!hasData.value || exporting.value) return
  
  exporting.value = true
  
  try {
    const params = {
      city: selectedCity.value,
      start_date: startDate.value,
      end_date: endDate.value,
      quality_level: selectedQualityLevel.value !== 'all' ? selectedQualityLevel.value : ''
    }
    
    await exportHistoricalData(params)
    showToastMessage('数据导出成功！')
    
    // 导出成功后，3秒重置按钮状态
    setTimeout(() => {
      exporting.value = false
    }, 3000)
  } catch (err) {
    console.error('Failed to export data:', err)
    showToastMessage('导出数据失败，请稍后重试', 'error')
    exporting.value = false
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    // 滚动到表格顶部
    document.querySelector('.table-container')?.scrollIntoView({ behavior: 'smooth' })
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    // 滚动到表格顶部
    document.querySelector('.table-container')?.scrollIntoView({ behavior: 'smooth' })
  }
}

// 日期操作函数
const changeMonth = (diff) => {
  const newDate = new Date(currentPickerMonth.value)
  newDate.setMonth(newDate.getMonth() + diff)
  
  // 检查是否超出范围
  const earliestAllowed = earliestDate.value ? new Date(earliestDate.value) : new Date('2018-01-01')
  const today = new Date() // 使用当前日期作为最新日期
  
  if (newDate < earliestAllowed) {
    currentPickerMonth.value = earliestAllowed
  } else if (newDate > today) {
    currentPickerMonth.value = today
  } else {
    currentPickerMonth.value = newDate
  }
}

const changeEndMonth = (diff) => {
  const newDate = new Date(currentEndPickerMonth.value)
  newDate.setMonth(newDate.getMonth() + diff)
  
  // 检查是否超出范围
  const earliestAllowed = startDate.value ? new Date(startDate.value) : (earliestDate.value ? new Date(earliestDate.value) : new Date('2018-01-01'))
  const today = new Date() // 使用当前日期作为最新日期
  
  if (newDate < earliestAllowed) {
    currentEndPickerMonth.value = earliestAllowed
  } else if (newDate > today) {
    currentEndPickerMonth.value = today
  } else {
    currentEndPickerMonth.value = newDate
  }
}

const onStartDateChange = () => {
  const selectedStart = new Date(startDate.value)
  const earliestAllowed = earliestDate.value ? new Date(earliestDate.value) : new Date('2018-01-01')
  const todayDate = new Date()
  todayDate.setHours(0, 0, 0, 0) // 设置时间为当天0点，便于比较
  
  // 确保日期在允许范围内（不早于最早数据，不晚于今天）
  if (selectedStart < earliestAllowed) {
    startDate.value = formatDateForInput(earliestAllowed)
  } else if (selectedStart > todayDate) {
    startDate.value = formatDateForInput(todayDate)
  }
  
  // 如果开始日期晚于结束日期，更新结束日期
  if (new Date(startDate.value) > new Date(endDate.value)) {
    endDate.value = startDate.value
  }
  
  selectedDateRange.value = 'custom'
  showStartDatePicker.value = false
}

const onEndDateChange = () => {
  const selectedEnd = new Date(endDate.value)
  const todayDate = new Date()
  todayDate.setHours(0, 0, 0, 0) // 设置时间为当天0点，便于比较
  const earliestAllowed = new Date(startDate.value)
  
  // 确保结束日期在允许范围内（不早于开始日期，不晚于今天）
  if (selectedEnd > todayDate) {
    endDate.value = formatDateForInput(todayDate)
  } else if (selectedEnd < earliestAllowed) {
    endDate.value = formatDateForInput(earliestAllowed)
  }
  
  selectedDateRange.value = 'custom'
  showEndDatePicker.value = false
}

const applyDateRange = () => {
  if (!earliestDate.value) {
    earliestDate.value = '2018-01-01'
  }
  
  // 使用当前日期作为最新日期
  const today = new Date();
  today.setHours(0, 0, 0, 0); // 设置为当天0点
  
  let start = new Date(today);
  let end = new Date(today);
  
  switch (selectedDateRange.value) {
    case 'last7days':
      start.setDate(today.getDate() - 6) // 减6天得到最近7天
      break;
    case 'last30days':
      start.setDate(today.getDate() - 29) // 减29天得到最近30天
      break
    case 'last90days':
      start.setDate(today.getDate() - 89) // 减89天得到最近90天
      break
    case 'thisYear':
      start = new Date(today.getFullYear(), 0, 1) // 本年1月1日
      break
    case 'lastYear':
      start = new Date(today.getFullYear() - 1, 0, 1) // 去年1月1日
      end = new Date(today.getFullYear() - 1, 11, 31) // 去年12月31日
      break
    case 'last5Years':
      start = new Date(today.getFullYear() - 4, 0, 1) // 5年前1月1日
      break
    case 'all':
      start = new Date(earliestDate.value)
      break
    case 'custom':
      // 自定义范围不改变当前选择
      return
  }
  
  // 确保开始日期不早于数据最早日期
  const earliestAllowed = new Date(earliestDate.value)
  if (start < earliestAllowed) {
    start = new Date(earliestAllowed)
  }
  
  // 更新日期选择
  startDate.value = formatDateForInput(start)
  endDate.value = formatDateForInput(end)
  
  // 更新日期选择器月份
  currentPickerMonth.value = new Date(startDate.value)
  currentEndPickerMonth.value = new Date(endDate.value)
}

// 辅助函数
const formatDate = (date) => {
  if (!date) return '无日期'
  
  // 如果是字符串格式，转换为Date对象
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    
    return dateObj.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  } catch (e) {
    console.error('日期格式化错误:', e, date)
    return '格式错误'
  }
}

const formatDateForInput = (date) => {
  const d = new Date(date)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const formatDateForDisplay = (dateString) => {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const day = String(date.getDate()).padStart(2, '0')
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const year = date.getFullYear()
  
  return `${day}/${month}/${year}`
}

const getAqiClass = (aqi) => {
  if (!aqi) return ''
  
  aqi = Number(aqi)
  if (isNaN(aqi)) return ''
  
  if (aqi <= 50) return 'quality-excellent'
  if (aqi <= 100) return 'quality-good'
  if (aqi <= 150) return 'quality-moderate'
  if (aqi <= 200) return 'quality-unhealthy'
  if (aqi <= 300) return 'quality-very-unhealthy'
  return 'quality-hazardous'
}

// 获取数据库中的日期范围
const fetchDateRange = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/air-quality/date-range')
    const data = await response.json()
    if (data.status === 'success' && data.data) {
      earliestDate.value = data.data.startDate
      
      // 始终使用当前日期作为最新日期
      latestDate.value = formatDateForInput(new Date())
    } else {
      // 设置默认值，以防API失败
      earliestDate.value = '2018-01-01'
      latestDate.value = formatDateForInput(new Date())
    }
  } catch (err) {
    console.error('获取日期范围失败:', err)
    // 设置默认值
    earliestDate.value = '2018-01-01'
    latestDate.value = formatDateForInput(new Date())
  }
}

// 添加getTodayDate函数
const getTodayDate = () => {
  const today = new Date();
  return formatDateForInput(today);
}

// 刷新数据 - 运行后端脚本
const refreshData = async () => {
  if (refreshing.value) return
  
  refreshing.value = true
  error.value = ''
  
  try {
    // 调用后端API触发脚本执行
    const response = await fetch('http://localhost:5000/api/air-quality/refresh-data', {
      method: 'POST'
    })
    
    const result = await response.json()
    
    if (result.status === 'success') {
      // 显示数据正在后台刷新的通知
      showToastMessage(result.message || '数据刷新已开始，系统将在后台处理数据。', 'info', 6000)
      
      // 创建一个定时器，每30秒自动刷新一次查询结果
      const autoRefreshInterval = 30000 // 30秒
      const maxRefreshCount = 10 // 最多自动刷新10次
      let refreshCount = 0
      
      const autoRefresh = () => {
        if (refreshCount >= maxRefreshCount) {
          // 达到最大刷新次数后，显示提醒
          showToastMessage('自动刷新已完成，如需查看最新数据请手动查询', 'info')
          return
        }
        
        refreshCount++
        // 如果当前有查询结果，自动刷新查询
        if (historicalData.value.length > 0) {
          queryData()
            .then(() => {
              // 成功刷新后显示通知
              if (refreshCount === 1) { // 只在第一次成功刷新时显示
                showToastMessage('数据已更新！后台处理可能仍在继续，系统将定期自动刷新。', 'success')
              }
            })
            .catch(err => {
              console.error('自动刷新查询失败:', err)
            })
        }
        
        // 继续等待下一次刷新
        setTimeout(autoRefresh, autoRefreshInterval)
      }
      
      // 首次刷新等待稍长时间，给后台处理一些时间
      setTimeout(autoRefresh, 60000) // 首次等待60秒后刷新
    } else {
      throw new Error(result.message || '数据刷新启动失败')
    }
  } catch (err) {
    console.error('数据刷新启动失败:', err)
    error.value = err.message || '数据刷新启动失败，请稍后重试'
    showToastMessage(error.value, 'error')
  } finally {
    // 由于是异步处理，在API响应后就将按钮恢复可用状态
    setTimeout(() => {
      refreshing.value = false
    }, 3000) // 等待3秒再恢复按钮，避免用户频繁点击
  }
}

// 添加初始化日期函数
const initializeDates = () => {
  // 设置默认日期为最近7天
  const today = new Date()
  endDate.value = formatDateForInput(today)
  
  const weekAgo = new Date()
  weekAgo.setDate(today.getDate() - 6) // 7天包括今天
  startDate.value = formatDateForInput(weekAgo)
  
  // 确保日期选择器月份正确
  currentPickerMonth.value = new Date(startDate.value)
  currentEndPickerMonth.value = new Date(endDate.value)
}

// 添加日期选择器的打开函数，确保月份正确
const openStartDatePicker = () => {
  // 确保月份选择器显示的是开始日期对应的月份
  if (startDate.value) {
    currentPickerMonth.value = new Date(startDate.value);
  } else {
    // 如果还没有开始日期，显示当前月份
    currentPickerMonth.value = new Date();
  }
  showStartDatePicker.value = !showStartDatePicker.value;
}

const openEndDatePicker = () => {
  // 确保月份选择器显示的是结束日期对应的月份
  if (endDate.value) {
    currentEndPickerMonth.value = new Date(endDate.value);
  } else {
    // 如果还没有结束日期，显示当前月份
    currentEndPickerMonth.value = new Date();
  }
  showEndDatePicker.value = !showEndDatePicker.value;
}

</script>

<style scoped>
/* 确保下拉选项文字完整显示 */
.date-range-select option,
.filter-select option {
  white-space: normal; /* 允许换行 */
  padding: 8px 12px; /* 调整padding */
  font-size: 14px;
  line-height: 1.5; /* 调整行高 */
}

.historical-data-page {
  padding: 20px;
  color: #333;
  max-width: 1290px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 25px;
  align-items: center; /* 改为居中对齐 */
  padding: 25px;
  margin-bottom: 30px;
  background-color: #fff;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
  border-top: 3px solid #2196f3;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 240px;
}

.filter-group label {
  font-weight: 600;
  color: #424242;
  font-size: 15px;
  white-space: nowrap;
  margin-bottom: 4px; /* 增加标签和选择框间距 */
}

.filter-select,
.date-input {
  padding: 0 10px; /* 移除垂直padding，让line-height控制 */
  border: 1px solid #bdbdbd;
  border-radius: 4px;
  background-color: #fff;
  color: #333;
  min-width: 180px;
  height: 40px; /* 进一步增加高度 */
  line-height: 40px; /* 使line-height等于height */
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
  text-overflow: ellipsis;
  white-space: nowrap;
  overflow: hidden;
  vertical-align: middle; /* 尝试对齐 */
}

.city-select {
  width: 240px !important;
  min-width: 240px !important;
  height: 40px; /* 保持一致 */
  line-height: 40px; /* 保持一致 */
}

.date-range-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 320px;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.date-input-container {
  position: relative;
  flex: 1;
}

.date-range-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #fff;
  color: #333;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.date-separator {
  white-space: nowrap;
}

.btn {
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  align-self: flex-end;
  margin-top: auto;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.btn-primary {
  background-color: #1890ff;
  color: white;
  min-width: 80px; /* 确保按钮有最小宽度 */
}

.btn-refresh {
  background-color: #52c41a;
  color: white;
  margin-left: 10px;
  min-width: 100px; /* 确保按钮有最小宽度 */
}

/* 响应式优化 */
@media (max-width: 1200px) {
  .filter-bar {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .filter-group {
    width: 100%;
    min-width: unset;
  }
  
  .date-range-container,
  .city-select {
    width: 100%;
    min-width: unset;
  }
  
  .btn {
    align-self: flex-start;
    margin-top: 10px;
  }
}

.data-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  overflow: auto;
  border-top: 3px solid #2196f3;
  max-height: calc(100vh - 220px); /* 限制最大高度为视口高度减去过滤栏和边距的高度 */
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  border-top: 3px solid #2196f3;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
}

.card-body {
  padding: 20px;
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
}

.placeholder-text {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: var(--text-secondary);
}

.spinner {
  border: 3px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  border-top: 3px solid var(--primary-color);
  width: 24px;
  height: 24px;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  text-align: center;
  color: var(--error-color);
  padding: 20px;
}

.retry-button {
  background: none;
  border: none;
  color: var(--primary-color);
  text-decoration: underline;
  cursor: pointer;
  margin-left: 8px;
}

.data-summary {
  margin-bottom: 15px;
  color: var(--text-secondary);
  font-size: 0.9em;
}

.data-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  margin-top: 15px;
}

.table-container {
  overflow-x: auto;
  overflow-y: auto;
  flex: 1;
  min-height: 200px;
  max-height: calc(100vh - 400px);
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 20px;
  background-color: #fff;
}

.pagination-wrapper {
  margin-top: 10px;
  padding-top: 10px;
  background-color: #fff;
  border-top: 1px solid #f0f0f0;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px 0;
  background-color: #fff;
  z-index: 10;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 15px;
}

.page-info {
  font-weight: 500;
  color: #333;
  min-width: 60px;
  text-align: center;
}

.btn-sm {
  padding: 5px 10px;
  font-size: 0.85em;
}

.btn-outline {
  background-color: transparent;
  color: #2196f3;
  border: 1px solid #2196f3;
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}

.btn-outline:hover:not(:disabled) {
  background-color: #e3f2fd;
}

.btn-outline:disabled {
  color: #bdbdbd;
  border-color: #bdbdbd;
  cursor: not-allowed;
}

/* 空气质量等级颜色 */
.quality-excellent {
  color: #00AA00;
  font-weight: 600;
}

.quality-good {
  color: #AAAA00;
  font-weight: 600;
}

.quality-moderate {
  color: #FF6600;
  font-weight: 600;
}

.quality-unhealthy {
  color: #CC0000;
  font-weight: 600;
}

.quality-very-unhealthy {
  color: #660033;
  font-weight: 600;
}

.quality-hazardous {
  color: #660000;
  font-weight: 600;
}

/* 增加对暗色背景下的数据可见性 */
@media (prefers-color-scheme: dark) {
  .data-table th {
    background-color: #333;
    color: #fff;
  }
  
  .data-table td {
    color: #f0f0f0;
  }
}

/* Toast通知样式 */
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  max-width: 350px;
  transition: all 0.3s ease;
  animation: slideInRight 0.3s forwards;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast {
  display: flex;
  align-items: center;
  background-color: white;
  border-radius: 4px;
  padding: 12px 20px;
  margin-bottom: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-left: 4px solid #4CAF50;
}

.toast.success {
  border-left-color: #4CAF50;
}

.toast.error {
  border-left-color: #F44336;
}

.toast.info {
  border-left-color: #2196F3;
}

.toast-icon {
  margin-right: 12px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 14px;
}

.toast.success .toast-icon {
  background-color: #4CAF50;
  color: white;
}

.toast.error .toast-icon {
  background-color: #F44336;
  color: white;
}

.toast.info .toast-icon {
  background-color: #2196F3;
  color: white;
}

.toast-content {
  flex: 1;
}

.toast-message {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.filter-select {
  width: 240px;
  height: 40px; /* 保持一致 */
  font-size: 14px;
  line-height: 40px; /* 保持一致 */
  padding-right: 30px;
}

/* 修复Element Plus选择器样式 */
.filter-group .el-select {
  width: 240px;
  height: 40px; /* 保持一致 */
  line-height: 40px; /* 保持一致 */
}

.el-select .el-input__wrapper {
  height: 40px !important;
  line-height: 40px !important;
  border-radius: 4px;
  box-shadow: 0 0 0 1px #bdbdbd inset !important;
  padding: 0 10px !important; /* 确保padding生效 */
  display: flex !important; /* 使用flex布局 */
  align-items: center !important; /* 垂直居中 */
}

.el-input__inner {
  height: auto !important; /* 让高度自适应 */
  line-height: normal !important; /* 使用正常行高 */
  padding: 0 !important; /* 移除内部padding */
  flex: 1 !important; /* 占据剩余空间 */
  align-self: center; /* 确保在 flex 容器中居中 */
}

.el-select-dropdown__item {
  padding: 0 12px !important; /* 调整选项padding */
  white-space: normal !important;
  line-height: normal !important; /* 使用正常行高，让flex控制 */
  min-height: 40px !important; /* 确保选项有足够高度 */
  display: flex !important; /* 使用flex布局 */
  align-items: center !important; /* 垂直居中 */
  min-width: 240px !important;
}

.filter-select option {
  padding: 10px 12px;
  white-space: normal;
  width: 100%;
  box-sizing: border-box;
  font-size: 14px;
  line-height: 1.6;
  min-height: 40px; /* 增加最小高度 */
  display: flex; /* 使用flex对齐 */
  align-items: center; /* 垂直居中 */
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95em;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  overflow: hidden;
  table-layout: fixed; /* 固定表格布局 */
}

.data-table th {
  background-color: #f5f5f5;
  color: #424242;
  text-align: left;
  padding: 14px 15px;
  font-weight: 600;
  border-bottom: 2px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 5;
}

.data-table td {
  padding: 12px 15px;
  border-bottom: 1px solid #eeeeee;
  color: #424242;
}

.data-table tr:hover {
  background-color: #f9f9f9;
}

.data-table tr:nth-child(even) {
  background-color: #fafafa;
}
</style> 