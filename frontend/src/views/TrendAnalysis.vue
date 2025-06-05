<template>
  <div class="trend-analysis-container">
    <!-- 控制面板 -->
    <TrendControlPanel
      :cities="availableCities"
      :selectedCities="selectedCities"
      :analysisType="analysisType"
      :startYear="startYear"
      :endYear="endYear"
      :selectedPollutant="selectedPollutant"
      :loading="loading"
      :availableYears="availableYears"
      @analyze="analyzeData"
      @update:analysisType="updateAnalysisType"
      @update:selectedCities="updateSelectedCities"
      @update:selectedPollutant="updateSelectedPollutant"
      @update:startYear="updateStartYear"
      @update:endYear="updateEndYear"
    />
    
    <!-- 加载中状态 -->
    <div v-if="loading" class="analysis-loading">
      <div class="loading-spinner"></div>
      <p>正在分析数据，请稍候...</p>
    </div>
    
    <!-- 错误状态 -->
    <div v-else-if="error" class="analysis-error">
      <el-alert :title="error" type="error" show-icon />
    </div>
    
    <!-- 分析结果区域 -->
    <div v-else-if="analysisComplete" class="analysis-results">
    <!-- 主图表 -->
    <TrendMainChart
        ref="mainChart"
      :selectedCities="selectedCities"
      :analysisType="analysisType"
      :startYear="startYear"
      :endYear="endYear"
      :selectedPollutant="selectedPollutant"
      :loading="loading"
      :error="error"
      :analysisComplete="analysisComplete"
      :rawData="rawData"
      @analyze="analyzeData"
      @export-chart="exportChart"
    />
    
      <!-- 数据表格区域 -->
      <div class="data-tables-section">
        <!-- 统计数据表格 -->
        <el-card class="stats-table-card">
          <template #header>
            <div class="card-header">
              <h3>{{ analysisType === 'annual' ? '年度' : analysisType === 'seasonal' ? '季节' : analysisType === 'monthly' ? '月度' : '对比' }}统计数据</h3>
              <el-button type="primary" size="small" @click="exportStatTable">
                <el-icon><Download /></el-icon> 导出数据
              </el-button>
            </div>
          </template>
          
          <!-- 统计摘要卡片 -->
          <div class="stats-summary-cards">
            <div v-for="city in selectedCities" :key="city" class="city-stat-card">
              <h4>{{ city }}统计摘要</h4>
              <div class="stat-grid" v-if="basicStats[city]">
                <div class="stat-item">
                  <span class="stat-label">平均值</span>
                  <span class="stat-value">{{ basicStats[city].mean?.toFixed(2) || 'N/A' }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">最大值</span>
                  <span class="stat-value">{{ basicStats[city].max?.toFixed(2) || 'N/A' }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">最小值</span>
                  <span class="stat-value">{{ basicStats[city].min?.toFixed(2) || 'N/A' }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">标准差</span>
                  <span class="stat-value">{{ basicStats[city].std?.toFixed(2) || 'N/A' }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">趋势</span>
                  <el-tag :type="getTrendTagType(basicStats[city].trend?.slope || 0)" size="small">
                    {{ basicStats[city].trend_direction || '无数据' }}
                  </el-tag>
                </div>
                <div class="stat-item">
                  <span class="stat-label">总改善率</span>
                  <span class="stat-value" :class="improvementStats[city]?.improvement_percentage > 0 ? 'positive' : 'negative'">
                    {{ improvementStats[city]?.improvement_percentage?.toFixed(2) || 0 }}%
                  </span>
                </div>
              </div>
              <div v-else class="empty-stats">
                <p>暂无统计数据</p>
              </div>
            </div>
          </div>
          
          <!-- 改善趋势表格 -->
          <div class="improvement-table-wrapper">
            <h4>空气质量改善情况</h4>
            <el-table :data="getImprovementTableData()" stripe style="width: 100%" :default-sort="{prop: 'totalRate', order: 'descending'}">
              <el-table-column prop="city" label="城市" width="120" />
              <el-table-column prop="firstYearValue" label="初始值" width="120">
                <template #default="scope">
                  {{ scope.row.firstYearValue?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="lastYearValue" label="最新值" width="120">
                <template #default="scope">
                  {{ scope.row.lastYearValue?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="totalRate" label="改善率(%)" sortable>
                <template #default="scope">
                  <span :class="scope.row.totalRate > 0 ? 'positive' : 'negative'">
                    {{ scope.row.totalRate?.toFixed(2) || 0 }}%
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="yearlyRate" label="年均改善率(%)" sortable>
                <template #default="scope">
                  <span :class="scope.row.yearlyRate > 0 ? 'positive' : 'negative'">
                    {{ scope.row.yearlyRate?.toFixed(2) || 0 }}%
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="trend" label="趋势">
                <template #default="scope">
                  <el-tag :type="getTrendTagType(scope.row.trend)">
                    {{ scope.row.trendDirection }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
        
        <!-- 详细数据表格 -->
        <el-card class="detail-table-card">
          <template #header v-if="analysisType !== 'comparison'">
            <div class="card-header">
              <h3>{{ analysisType === 'annual' ? '年度' : analysisType === 'seasonal' ? '季节' : analysisType === 'monthly' ? '月度' : '' }}详细数据</h3>
              <el-button type="primary" size="small" @click="exportDetailTable">
                <el-icon><Download /></el-icon> 导出数据
              </el-button>
            </div>
          </template>
          
          <!-- 年度数据表格 -->
          <div v-if="analysisType === 'annual'">
            <el-table :data="getAnnualTableData()" stripe style="width: 100%" height="400" :default-sort="{prop: 'year', order: 'ascending'}">
              <el-table-column prop="city" label="城市" width="120" />
              <el-table-column prop="year" label="年份" sortable width="100" />
              <el-table-column prop="value" label="值" sortable>
                <template #default="scope">
                  {{ scope.row.value?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="min" label="最小值" sortable>
                <template #default="scope">
                  {{ scope.row.min?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="max" label="最大值" sortable>
                <template #default="scope">
                  {{ scope.row.max?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="std" label="标准差">
                <template #default="scope">
                  {{ scope.row.std?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="count" label="数据量" width="100" />
            </el-table>
          </div>
          
          <!-- 季节数据表格 -->
          <div v-else-if="analysisType === 'seasonal'">
            <div class="seasonal-analysis-container">
              <div class="filter-container">
                <h3>季节筛选</h3>
                <div class="season-filter">
                  <el-radio-group v-model="seasonFilter" @change="handleSeasonFilterChange">
                    <el-radio :value="'all'">全部季节</el-radio>
                    <el-radio :value="'1'">春季</el-radio>
                    <el-radio :value="'2'">夏季</el-radio>
                    <el-radio :value="'3'">秋季</el-radio>
                    <el-radio :value="'4'">冬季</el-radio>
                  </el-radio-group>
                </div>
              </div>
              
              <div class="chart-container">
                <div id="season-chart" style="width: 100%; height: 400px;"></div>
              </div>
              
              <div class="table-container">
                <h3>季节数据表</h3>
                <el-table 
                  :data="getFilteredSeasonalTableData()" 
                  border 
                  style="width: 100%"
                  :row-class-name="getSeasonRowClass"
                >
                  <el-table-column prop="year" label="年份" width="100"></el-table-column>
                  <el-table-column prop="city" label="城市" width="120"></el-table-column>
                  <el-table-column prop="season" label="季节" width="120">
                    <template #default="scope">
                      <span :class="getSeasonClass(scope.row.season)">
                        {{ scope.row.season === 1 ? '春季' : 
                           scope.row.season === 2 ? '夏季' : 
                           scope.row.season === 3 ? '秋季' : 
                           scope.row.season === 4 ? '冬季' : '未知' }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column :label="pollutantNames[selectedPollutant] || selectedPollutant">
                    <template #default="scope">
                      <span :class="getValueClass(scope.row.value, selectedPollutant)">
                        {{ scope.row.value }}
                      </span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </div>
          
          <!-- 月度数据表格 -->
          <div v-else-if="analysisType === 'monthly'">
            <el-table :data="getMonthlyTableData()" stripe style="width: 100%" height="400" :default-sort="{prop: 'year', order: 'ascending'}">
              <el-table-column prop="city" label="城市" width="120" />
              <el-table-column prop="year" label="年份" sortable width="80" />
              <el-table-column prop="month" label="月份" sortable width="80" />
              <el-table-column prop="value" label="值" sortable>
                <template #default="scope">
                  {{ scope.row.value?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="min" label="最小值" sortable>
                <template #default="scope">
                  {{ scope.row.min?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
              <el-table-column prop="max" label="最大值" sortable>
                <template #default="scope">
                  {{ scope.row.max?.toFixed(2) || 'N/A' }}
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <!-- 城市对比数据表格 -->
          <div v-else-if="analysisType === 'comparison'" class="comparison-data-container">
            <div class="detail-top-container">
              <div class="detail-info-header">
                <h3>对比详细数据</h3>
                <div class="description-text">
                  <el-icon><InfoFilled /></el-icon>
                  <span>城市数据对比分析可以直观展示不同城市的污染物浓度差异和变化趋势</span>
                </div>
              </div>
              
              <div class="header-actions">
                <el-button type="primary" size="small" @click="exportDetailTable">
                  <el-icon><Download /></el-icon> 导出数据
                </el-button>
              </div>
            </div>
            
            <div class="comparison-info">
              <el-alert
                type="info"
                :closable="false"
                show-icon
              >
                <template #title>
                  <span>城市对比功能支持最多5个城市的数据对比分析</span>
                </template>
                已选择城市: {{ selectedCities.join('、') }}
              </el-alert>
            </div>
            
            <!-- 对比表格 -->
            <div class="comparison-table-container">
              <el-table 
                :data="getComparisonTableData()" 
                stripe 
                border
                style="width: 100%" 
                height="400" 
                :default-sort="{prop: 'value', order: 'ascending'}"
                :row-class-name="getCityRowClass"
              >
                <el-table-column prop="city" label="城市" width="140" fixed="left" />
                <el-table-column prop="value" label="平均值" sortable>
                  <template #default="scope">
                    <span class="value-cell">{{ scope.row.value?.toFixed(2) || 'N/A' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="min" label="最小值" sortable>
                  <template #default="scope">
                    <span class="value-cell">{{ scope.row.min?.toFixed(2) || 'N/A' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="max" label="最大值" sortable>
                  <template #default="scope">
                    <span class="value-cell">{{ scope.row.max?.toFixed(2) || 'N/A' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="count" label="数据量" width="100" />
                <el-table-column prop="improvementRate" label="改善率(%)" sortable width="150">
                  <template #default="scope">
                    <span :class="scope.row.improvementRate > 0 ? 'improvement-positive' : 'improvement-negative'">
                      <el-tag :type="scope.row.improvementRate > 0 ? 'success' : 'danger'" size="small">
                        {{ scope.row.improvementRate?.toFixed(2) || 0 }}%
                      </el-tag>
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="analysis-empty">
      <el-empty description="选择参数并点击分析按钮开始分析" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart, PieChart, ScatterChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent, ToolboxComponent, DataZoomComponent, MarkLineComponent, GeoComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { fetchTrendData, fetchCities } from '../services/api'
import TrendControlPanel from '../components/trend/TrendControlPanel.vue'
import TrendMainChart from '../components/trend/TrendMainChart.vue'
import TrendDetailPanel from '../components/trend/TrendDetailPanel.vue'
import { ElMessage, ElLoading } from 'element-plus'
import { Download, DataAnalysis, Refresh, InfoFilled } from '@element-plus/icons-vue'

// 注册echarts组件
echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  MarkLineComponent,
  GeoComponent,
  LineChart,
  BarChart,
  PieChart,
  ScatterChart,
  CanvasRenderer
])

// 状态变量
const selectedCities = ref(['广州市'])
const availableCities = ref([])
const analysisType = ref('annual')
const availableYears = ref([])
const startYear = ref(2015) // 设置默认起始年份
const endYear = ref(2025) // 设置默认结束年份
const selectedPollutant = ref('aqi')
const loading = ref(false)
const error = ref('')
const analysisComplete = ref(false)
const rawData = ref({
  annualData: [],
  seasonalData: [],
  monthlyData: [],
  comparisonData: [],
  correlationMatrix: {},
  forecastData: [],
  complianceData: [],
  basicStats: {},
  improvementStats: {},
  summary: {
  findings: [],
  suggestions: []
  }
})

// 污染物名称映射
const pollutantNames = {
  'pm25': 'PM2.5',
  'pm10': 'PM10',
  'so2': 'SO₂',
  'no2': 'NO₂',
  'o3': 'O₃',
  'co': 'CO',
  'aqi': 'AQI'
}

const selectedPollutantName = computed(() => {
  return pollutantNames[selectedPollutant.value] || selectedPollutant.value
})

// 基础统计和改善统计
const basicStats = computed(() => {
  return rawData.value.basicStats || {}
})

const improvementStats = computed(() => {
  return rawData.value.improvementStats || {}
})

// 分析总结
const analysisSummary = computed(() => {
  return {
    findings: rawData.value.summary?.findings || [],
    suggestions: rawData.value.summary?.suggestions || []
  }
})

// 处理子组件的更新事件
const updateSelectedCities = (newVal) => {
  if (JSON.stringify(selectedCities.value) === JSON.stringify(newVal)) return
  console.log('更新选中城市:', newVal)
  selectedCities.value = newVal
}

const updateAnalysisType = (newVal) => {
  if (analysisType.value === newVal) return
  console.log('[TrendAnalysis] Received update:analysisType event:', newVal);
  analysisType.value = newVal
  console.log('[TrendAnalysis] analysisType state updated to:', analysisType.value);
  // 不再自动触发分析，由用户点击"开始分析"按钮触发
}

const updateStartYear = (newVal) => {
  if (startYear.value === newVal) return
  console.log('更新起始年份:', newVal)
  startYear.value = newVal
  // 不再自动触发分析
}

const updateEndYear = (newVal) => {
  if (endYear.value === newVal) return
  console.log('更新结束年份:', newVal)
  endYear.value = newVal
  // 不再自动触发分析
}

const updateSelectedPollutant = (newVal) => {
  if (selectedPollutant.value === newVal) return
  console.log('更新污染物类型:', newVal)
  selectedPollutant.value = newVal
}

// 分析数据
const analyzeData = async () => {
  // 验证城市选择
  if (selectedCities.value.length === 0) {
    ElMessage.warning('请至少选择一个城市')
    return Promise.reject('未选择城市')
  }

  // 严格验证年份选择
  if (startYear.value === null || endYear.value === null) {
    ElMessage.warning('请选择完整的年份范围')
    return Promise.reject('年份不完整')
  }

  // 验证年份大小关系
  if (startYear.value > endYear.value) {
    ElMessage.warning('起始年份不能大于结束年份')
    return Promise.reject('年份范围无效')
  }

  console.log('===== [TrendAnalysis] analyzeData function started =====');
  console.log('[TrendAnalysis] Using analysisType for API call:', analysisType.value);
  console.log('[TrendAnalysis] Current parameters for analysis:', {
    cities: selectedCities.value,
    startYear: startYear.value,
    endYear: endYear.value,
    pollutant: selectedPollutant.value,
    analysisType: analysisType.value
  });
  
  error.value = ''
  loading.value = true
  analysisComplete.value = false
  
  console.log('加载状态已设置：', {loading: loading.value, analysisComplete: analysisComplete.value})
  
  const loadingInstance = ElLoading.service({
    lock: true,
    text: '正在分析数据，请稍候...',
    background: 'rgba(255, 255, 255, 0.7)'
  })

  try {
    console.log('[TrendAnalysis] Calling fetchTrendData with analysisType:', analysisType.value);
    const result = await fetchTrendData({
      cities: selectedCities.value,
      startYear: startYear.value,
      endYear: endYear.value,
      pollutant: selectedPollutant.value,
      analysisType: analysisType.value
    })
    
    console.log('API数据请求成功，响应状态:', result.status)
    console.log('API返回的原始数据结构:', Object.keys(result).join(', '))
    
    if (result.status === 'success') {
      console.log('API请求成功，开始处理数据...')
      
      if (!result.data) {
        console.error('API返回数据缺少data字段')
        error.value = '服务器返回数据格式错误'
        ElMessage.error(error.value)
        return Promise.reject('数据格式错误')
      }
      
      console.log('API返回的数据字段:', Object.keys(result.data).join(', '))
      
      // 直接使用API返回数据并确保所有必要字段都存在
      const {
        annualData = [],
        seasonalData = [],
        monthlyData = [],
        comparisonData = [],
        correlationMatrix = {},
        forecastData = [],
        complianceData = [],
        basicStats = null,
        improvementStats = null,
        summary = null
      } = result.data
      
      // 确保数据在控制台可见
      console.log('年度数据项数:', annualData?.length || 0)
      console.log('年度数据样本:', annualData?.[0] ? JSON.stringify(annualData[0]) : '无数据')
      console.log('季节数据项数:', seasonalData?.length || 0)
      console.log('月度数据项数:', monthlyData?.length || 0)
      console.log('对比数据项数:', comparisonData?.length || 0)
      console.log('改善统计数据:', JSON.stringify(improvementStats))
      
      // 检查数据结构是否符合图表渲染要求
      const hasValidData = (
        (analysisType.value === 'annual' && annualData?.length > 0) ||
        (analysisType.value === 'seasonal' && seasonalData?.length > 0) ||
        (analysisType.value === 'monthly' && monthlyData?.length > 0) ||
        (analysisType.value === 'comparison' && comparisonData?.length > 0)
      )
      
      if (!hasValidData) {
        console.warn(`当前分析类型 ${analysisType.value} 的数据为空，尝试生成测试数据`)
        
        // 根据分析类型生成测试数据
        if (analysisType.value === 'annual' && (!annualData || annualData.length === 0)) {
          console.log('使用真实数据分析，不生成模拟数据')
        }
      } else {
        console.log('数据验证通过，存在有效数据项，继续处理...')
      }
      
      // 确保基础统计信息存在
      if (!basicStats) {
        console.log('基础统计数据为空，初始化基础统计数据')
        const defaultStats = {}
        // 为每个城市创建默认统计
        selectedCities.value.forEach(city => {
          defaultStats[city] = {
            count: 0,
            mean: 0.0,
            median: 0.0,
            std: 0.0,
            min: 0.0,
            max: 0.0,
            percentile_25: 0.0,
            percentile_75: 0.0,
            trend: {
              slope: 0,
              r_value: 0,
              p_value: 0,
              yearly_means: [],
              years: []
            },
            trend_direction: '无数据'
          }
        })
        
        result.data.basicStats = defaultStats
      }
      
      // 确保改善统计信息存在
      if (!improvementStats) {
        console.log('改善统计数据为空，初始化改善统计数据')
        const defaultImprovement = {}
        // 为每个城市创建默认改善率
        selectedCities.value.forEach(city => {
          defaultImprovement[city] = {
            improvement_percentage: 0.0,
            first_year: startYear.value,
            last_year: endYear.value,
            first_year_value: 0.0,
            last_year_value: 0.0,
            yearly_rate: 0.0,
            yearlyRate: 0.0,
            totalRate: 0.0
          }
        })
        
        result.data.improvementStats = defaultImprovement
      }
      
      // 确保分析总结存在
      if (!summary) {
        console.log('分析总结数据为空，初始化分析总结')
        result.data.summary = {
          findings: ['数据分析完成，但未能生成详细分析发现。'],
          suggestions: ['建议收集更多数据进行深入分析。']
        }
      }
      
      // 确保各类数据都是数组
      if (!Array.isArray(result.data.annualData)) {
        console.warn('年度数据不是数组，已修正为空数组')
        result.data.annualData = []
      }
      if (!Array.isArray(result.data.seasonalData)) {
        console.warn('季节数据不是数组，已修正为空数组')
        result.data.seasonalData = []
      }
      if (!Array.isArray(result.data.monthlyData)) {
        console.warn('月度数据不是数组，已修正为空数组')
        result.data.monthlyData = []
      }
      if (!Array.isArray(result.data.comparisonData)) {
        console.warn('对比数据不是数组，已修正为空数组')
        result.data.comparisonData = []
      }
      
      console.log('数据预处理完成，更新组件状态...')
      
      // 更新数据
      rawData.value = result.data
      
      console.log('rawData已更新，设置分析完成状态...')
      
      // 设置分析完成状态（确保在数据设置后，以触发监听）
      // 使用nextTick和setTimeout以确保DOM有时间更新
      nextTick(() => {
        setTimeout(() => {
          analysisComplete.value = true
          console.log('分析完成状态已设置为true，此时应触发图表渲染')
          
          // 额外验证图表容器状态
          nextTick(() => {
            validateChartContainers()
          })
        }, 100)
      })
      
      ElMessage.success('数据分析完成')
      return Promise.resolve(result)
    } else {
      error.value = result.message || '分析数据失败'
      console.error('API返回失败:', error.value)
      ElMessage.error(error.value)
      return Promise.reject(error.value)
    }
  } catch (err) {
    console.error('分析数据出错:', err)
    error.value = err.message || '请求数据失败，请检查网络连接'
    ElMessage.error(error.value)
    return Promise.reject(err)
  } finally {
    loading.value = false
    loadingInstance.close()
    console.log('===== 趋势分析流程完成 =====')
  }
}

// 添加图表容器验证函数
const validateChartContainers = () => {
  console.log('验证图表容器状态...')
  // 只验证当前分析类型的容器
  const containerId = `${analysisType.value}-trend-chart`
    const container = document.getElementById(containerId)
    
    if (container) {
      console.log(`图表容器 ${containerId} 存在`, {
        offsetWidth: container.offsetWidth,
        offsetHeight: container.offsetHeight,
        clientWidth: container.clientWidth,
        clientHeight: container.clientHeight,
        style: container.getAttribute('style') || '无样式'
      })
    } else {
    console.warn(`图表容器 ${containerId} 不存在，这可能是因为当前处于其他分析类型的视图`)
    }
}

// 导出图表为图片
const exportChart = (chartRef, fileName) => {
  if (!chartRef) {
    ElMessage.warning('图表未准备好，无法导出')
    return
  }
  
  try {
    // 获取图表实例
    const chart = chartRef.getEchartsInstance()
    if (!chart) {
      ElMessage.warning('图表实例不存在')
      return
    }
    
    // 获取图表的数据URL
    const dataURL = chart.getDataURL({
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff'
    })
    
    // 创建下载链接
    const link = document.createElement('a')
    link.download = `${fileName || '趋势分析'}_${new Date().toISOString().split('T')[0]}.png`
    link.href = dataURL
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    ElMessage.success('图表已导出')
  } catch (err) {
    console.error('导出图表出错:', err)
    ElMessage.error('导出图表失败: ' + (err.message || '未知错误'))
  }
}

// 加载城市列表
const loadCityList = async () => {
  try {
    console.log('加载城市列表...')
    const response = await fetchCities()
    
    if (response.status === 'success' && response.data) {
      console.log('服务器返回城市数据:', response)
      
      // 根据实际返回的数据格式进行处理
      let cityList = []
      
      // 检查返回的数据格式
      if (Array.isArray(response.data)) {
        // 如果直接返回数组，则使用这个数组
        cityList = response.data
      } else if (response.data.cities && Array.isArray(response.data.cities)) {
        // 如果是 {cities: [...]} 格式
        cityList = response.data.cities
      } else {
        // 如果是其他格式，则尝试自动检测
        console.log('检测到非标准数据格式，尝试自动解析')
        for (const key in response.data) {
          if (Array.isArray(response.data[key])) {
            cityList = response.data[key]
            break
          }
        }
      }
      
      // 转换为select组件需要的格式
      if (cityList.length > 0) {
        // 检查第一个元素的格式，确定如何转换
        if (typeof cityList[0] === 'string') {
          // 如果是字符串数组
          availableCities.value = cityList.map(city => ({
            value: city,
            label: city
          }))
        } else if (typeof cityList[0] === 'object') {
          // 如果已经是对象数组，检查是否有name/value字段
          if (cityList[0].name) {
            availableCities.value = cityList.map(city => ({
              value: city.name,
              label: city.name
            }))
          } else if (cityList[0].value) {
            // 已经是合适的格式
            availableCities.value = cityList
          }
        }
      }
      
      console.log('处理后的城市列表:', availableCities.value)
      
      // 默认选择广州市，如果列表中有的话
      const hasGuangzhou = availableCities.value.some(city => city.value === '广州市')
      if (hasGuangzhou && selectedCities.value.length === 0) {
        selectedCities.value = ['广州市']
      }
    } else {
      console.error('城市列表数据获取失败:', response)
      // 使用默认城市列表
      useDefaultCityList()
    }
  } catch (err) {
    console.error('获取城市列表失败:', err)
    // 使用默认城市列表
    useDefaultCityList()
  }
}

// 使用默认城市列表
const useDefaultCityList = () => {
  console.log('使用默认城市列表');
  
  // 设置默认城市列表
  availableCities.value = [
    { value: '广州市', label: '广州市' },
    { value: '深圳市', label: '深圳市' },
    { value: '珠海市', label: '珠海市' },
    { value: '汕头市', label: '汕头市' },
    { value: '佛山市', label: '佛山市' },
    { value: '韶关市', label: '韶关市' },
    { value: '湛江市', label: '湛江市' },
    { value: '肇庆市', label: '肇庆市' },
    { value: '江门市', label: '江门市' },
    { value: '茂名市', label: '茂名市' },
    { value: '惠州市', label: '惠州市' },
    { value: '梅州市', label: '梅州市' },
    { value: '汕尾市', label: '汕尾市' },
    { value: '河源市', label: '河源市' },
    { value: '阳江市', label: '阳江市' },
    { value: '清远市', label: '清远市' },
    { value: '东莞市', label: '东莞市' },
    { value: '中山市', label: '中山市' },
    { value: '潮州市', label: '潮州市' },
    { value: '揭阳市', label: '揭阳市' },
    { value: '云浮市', label: '云浮市' }
  ]
  
  // 确保默认选择城市
  if (selectedCities.value.length === 0) {
    selectedCities.value = ['广州市']
    console.log('已设置默认城市为广州市')
  }
  
  // 检验城市列表是否有效
  if (availableCities.value.length === 0) {
    console.error('默认城市列表加载失败，提供紧急备用列表')
    availableCities.value = [
      { value: '广州市', label: '广州市' },
      { value: '深圳市', label: '深圳市' },
      { value: '北京市', label: '北京市' },
      { value: '上海市', label: '上海市' },
      { value: '重庆市', label: '重庆市' }
    ]
  }
  
  console.log('默认城市列表已加载:', availableCities.value.length, '个城市')
}

// 初始化可用年份范围
const initAvailableYears = () => {
  const currentYear = new Date().getFullYear()
  const years = []
  for (let year = 2015; year <= currentYear; year++) {
    years.push(year)
  }
  availableYears.value = years
  
  // 不再自动设置默认年份范围，让用户选择
  // startYear.value = currentYear - 3
  // endYear.value = currentYear
}

// 在页面挂载时初始化
onMounted(async () => {
  console.log('趋势分析页面已加载')
  
  // 初始化年份范围
  initAvailableYears()
  
  // 加载城市列表
  await loadCityList()
  
  // 确保默认城市有效
  if (selectedCities.value.length === 0 || !availableCities.value.some(city => city.value === selectedCities.value[0])) {
    if (availableCities.value.length > 0) {
      selectedCities.value = [availableCities.value[0].value];
      console.log('设置默认城市:', selectedCities.value);
    } else {
      console.error('没有可用的城市数据');
      // 设置默认城市
      useDefaultCityList();
      selectedCities.value = ['广州市'];
    }
  }

  // 页面加载时初始化
  if (analysisType.value === 'seasonal' && analysisComplete.value) {
    nextTick(() => {
      renderSeasonChart()
    })
  }
})

// 获取趋势标签类型
const getTrendTagType = (slope) => {
  if (!slope) return 'info'
  if (slope < -0.01) return 'success'
  if (slope > 0.01) return 'danger'
  return 'info'
}

// 渲染改善趋势图表
const renderImprovementChart = (chartContainer) => {
  if (!chartContainer || !improvementStats.value || Object.keys(improvementStats.value).length === 0) {
    console.log('无法渲染改善趋势图表：容器不存在或没有数据')
    return null
  }
  
  try {
    console.log('开始渲染改善趋势图表')
    // 确保容器被挂载
    if (!chartContainer.offsetWidth) {
      console.log('图表容器未挂载，宽度为0')
      chartContainer.style.width = '100%'
      chartContainer.style.height = '300px'
    }

    // 创建或获取图表实例
    let chartInstance
    try {
      chartInstance = echarts.getInstanceByDom(chartContainer)
      if (chartInstance) {
        console.log('使用现有echarts实例')
      } else {
        console.log('创建新的echarts实例')
        chartInstance = echarts.init(chartContainer)
      }
    } catch (err) {
      console.error('创建或获取echarts实例失败:', err)
      // 强制创建新实例
      try {
        console.log('尝试强制初始化新实例')
        chartInstance = echarts.init(chartContainer)
      } catch (secondErr) {
        console.error('强制初始化echarts实例失败:', secondErr)
        return null
      }
    }
    
    // 准备数据
    const cities = Object.keys(improvementStats.value)
    const improvementData = cities.map(city => {
      const data = improvementStats.value[city]
      return {
        name: city,
        value: data.totalRate || data.improvement_percentage || 0,
        firstYear: data.first_year,
        lastYear: data.last_year,
        firstValue: data.first_year_value,
        lastValue: data.last_year_value
      }
    })
    
    // 按改善率排序
    improvementData.sort((a, b) => b.value - a.value)
    
    const option = {
      title: {
        text: '空气质量改善趋势比较',
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        formatter: function(params) {
          const data = params[0].data
          return `<div style="font-weight:bold">${data.name}</div>
                 <div>改善率: ${data.value.toFixed(2)}%</div>
                 <div>${data.firstYear}年值: ${data.firstValue}</div>
                 <div>${data.lastYear}年值: ${data.lastValue}</div>`
        }
      },
      xAxis: {
        type: 'category',
        data: improvementData.map(item => item.name),
        axisLabel: {
          interval: 0,
          rotate: 30
        }
      },
      yAxis: {
        type: 'value',
        name: '改善百分比(%)'
      },
      series: [
        {
        type: 'bar',
          data: improvementData.map(item => ({
            ...item,
            itemStyle: {
              color: item.value > 0 ? '#67c23a' : '#f56c6c'
            }
          })),
          label: {
            show: true,
            position: 'top',
            formatter: '{c}%'
          }
        }
      ]
    }
    
    // 设置选项
    chartInstance.setOption(option, true)
    console.log('改善趋势图表渲染完成')
    
    // 窗口大小变化时调整图表大小
    window.addEventListener('resize', () => {
      chartInstance.resize()
    })
    
    return chartInstance
  } catch (error) {
    console.error('渲染改善趋势图表出错:', error)
    return null
  }
}

// 添加 echarts 图表引用
const mainChartRef = ref(null)

// 添加表格数据处理函数
const getAnnualTableData = () => {
  if (!rawData.value.annualData || rawData.value.annualData.length === 0) {
    return [];
  }
  return rawData.value.annualData.filter(item => selectedCities.value.includes(item.city));
}

const getSeasonalTableData = () => {
  if (!rawData.value.seasonalData || rawData.value.seasonalData.length === 0) {
    return [];
  }
  
  // 添加调试日志查看原始季节数据
  if (rawData.value.seasonalData.length > 0) {
    console.log('季节数据样本:', rawData.value.seasonalData.slice(0, 3));
    console.log('季节值示例:', rawData.value.seasonalData.map(item => item.season).slice(0, 10));
    
    // 分析季节值分布
    const seasonCounts = {1: 0, 2: 0, 3: 0, 4: 0, other: 0};
    const seasonValues = new Set();
    
    rawData.value.seasonalData.forEach(item => {
      const s = item.season;
      if (s === 1) seasonCounts[1]++;
      else if (s === 2) seasonCounts[2]++;
      else if (s === 3) seasonCounts[3]++;
      else if (s === 4) seasonCounts[4]++;
      else {
        seasonCounts.other++;
        seasonValues.add(s);
      }
    });
    
    console.log('季节值分布:', seasonCounts);
    if (seasonCounts.other > 0) {
      console.log('非标准季节值:', Array.from(seasonValues));
    }
  }
  
  // 过滤并处理季节数据，确保季节字段正确
  return rawData.value.seasonalData
    .filter(item => selectedCities.value.includes(item.city))
    .map(item => {
      // 添加季节处理逻辑，确保季节值是数字
      let seasonValue = item.season;
      
      // 如果季节是字符串，尝试转换为数字
      if (typeof seasonValue === 'string') {
        if (seasonValue.includes('春') || seasonValue.toLowerCase().includes('spring')) {
          seasonValue = 1;
        } else if (seasonValue.includes('夏') || seasonValue.toLowerCase().includes('summer')) {
          seasonValue = 2;
        } else if (seasonValue.includes('秋') || seasonValue.toLowerCase().includes('autumn') || seasonValue.toLowerCase().includes('fall')) {
          seasonValue = 3;
        } else if (seasonValue.includes('冬') || seasonValue.toLowerCase().includes('winter')) {
          seasonValue = 4;
        } else {
          // 尝试直接转换为数字
          const num = parseInt(seasonValue, 10);
          if (!isNaN(num) && num >= 1 && num <= 4) {
            seasonValue = num;
          }
        }
      }
      
      return {
        ...item,
        season: seasonValue
      };
    });
}

const getMonthlyTableData = () => {
  if (!rawData.value.monthlyData || rawData.value.monthlyData.length === 0) {
    return [];
  }
  return rawData.value.monthlyData.filter(item => selectedCities.value.includes(item.city));
}

const getComparisonTableData = () => {
  if (!rawData.value.comparisonData) {
    console.log('对比数据为null或undefined');
    return [];
  }
  
  if (rawData.value.comparisonData.length === 0) {
    console.log('对比数据数组为空');
    return [];
  }
  
  // 日志输出原始数据
  console.log('原始对比数据:', rawData.value.comparisonData.length, '条记录');
  console.log('选中的城市:', selectedCities.value);
  
  // 确保过滤出选中城市的数据，并做额外处理避免显示N/A
  const filteredData = rawData.value.comparisonData
    .filter(item => selectedCities.value.includes(item.city))
    .map(item => {
      // 处理可能的null或undefined值
      const cityImprovementStats = improvementStats.value[item.city] || {};
      const value = typeof item.value === 'number' ? item.value : 
               typeof item.mean === 'number' ? item.mean : 0;
      const min = typeof item.min === 'number' ? item.min : 0;
      const max = typeof item.max === 'number' ? item.max : 0;
      
      return {
        ...item,
        value: value,
        min: min,
        max: max,
        count: item.count || 0,
        improvementRate: cityImprovementStats ? 
          cityImprovementStats.improvement_percentage || cityImprovementStats.totalRate || 0 : 0
      };
    });
  
  console.log('过滤后的对比数据:', filteredData.length, '条记录');
  if (filteredData.length === 0) {
    console.log('警告：过滤后没有数据，请检查选中的城市是否在原始数据中');
  }
  
  return filteredData;
}

const getImprovementTableData = () => {
  if (!improvementStats.value || Object.keys(improvementStats.value).length === 0) {
    return [];
  }
  
  return selectedCities.value.map(city => {
    const stats = improvementStats.value[city] || {};
    const cityBasicStats = basicStats.value[city] || {};
    
    return {
      city,
      firstYear: stats.first_year || startYear.value,
      lastYear: stats.last_year || endYear.value,
      firstYearValue: stats.first_year_value || 0,
      lastYearValue: stats.last_year_value || 0,
      totalRate: stats.improvement_percentage || stats.totalRate || 0,
      yearlyRate: stats.yearly_rate || stats.yearlyRate || 0,
      trend: cityBasicStats.trend?.slope || 0,
      trendDirection: cityBasicStats.trend_direction || '无变化'
    };
  });
}

// 表格导出函数
const exportStatTable = () => {
  try {
    // 创建一个新的CSV数据
    let csvContent = "data:text/csv;charset=utf-8,";
    
    // 添加表头
    csvContent += "城市,初始年份,最终年份,初始值,最终值,总改善率(%),年均改善率(%),趋势\n";
    
    // 添加每一行数据
    getImprovementTableData().forEach(row => {
      csvContent += `${row.city},${row.firstYear},${row.lastYear},${row.firstYearValue?.toFixed(2) || 0},${row.lastYearValue?.toFixed(2) || 0},${row.totalRate?.toFixed(2) || 0},${row.yearlyRate?.toFixed(2) || 0},${row.trendDirection}\n`;
    });
    
    // 创建下载链接
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${selectedPollutantName.value}_统计数据_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success('统计数据导出成功');
  } catch (error) {
    console.error('导出统计数据出错:', error);
    ElMessage.error('导出统计数据失败: ' + (error.message || '未知错误'));
  }
}

const exportDetailTable = () => {
  try {
    // 创建一个新的CSV数据
    let csvContent = "data:text/csv;charset=utf-8,";
    let tableData = [];
    let headers = [];
    
    // 根据当前分析类型获取不同的数据和表头
    if (analysisType.value === 'annual') {
      headers = ["城市", "年份", "值", "最小值", "最大值", "标准差", "数据量"];
      tableData = getAnnualTableData().map(row => [
        row.city,
        row.year,
        row.value?.toFixed(2) || 0,
        row.min?.toFixed(2) || 0,
        row.max?.toFixed(2) || 0,
        row.std?.toFixed(2) || 0,
        row.count || 0
      ]);
    } else if (analysisType.value === 'seasonal') {
      headers = ["城市", "年份", "季节", "值", "最小值", "最大值"];
      tableData = getSeasonalTableData().map(row => [
        row.city,
        row.year,
        row.season === 1 ? '春季' : row.season === 2 ? '夏季' : row.season === 3 ? '秋季' : '冬季',
        row.value?.toFixed(2) || 0,
        row.min?.toFixed(2) || 0,
        row.max?.toFixed(2) || 0
      ]);
    } else if (analysisType.value === 'monthly') {
      headers = ["城市", "年份", "月份", "值", "最小值", "最大值"];
      tableData = getMonthlyTableData().map(row => [
        row.city,
        row.year,
        row.month,
        row.value?.toFixed(2) || 0,
        row.min?.toFixed(2) || 0,
        row.max?.toFixed(2) || 0
      ]);
    } else if (analysisType.value === 'comparison') {
      headers = ["城市", "平均值", "最小值", "最大值", "数据量", "改善率(%)"];
      tableData = getComparisonTableData().map(row => [
        row.city,
        row.value?.toFixed(2) || 0,
        row.min?.toFixed(2) || 0,
        row.max?.toFixed(2) || 0,
        row.count || 0,
        row.improvementRate?.toFixed(2) || 0
      ]);
    }
    
    // 添加表头
    csvContent += headers.join(",") + "\n";
    
    // 添加每一行数据
    tableData.forEach(row => {
      csvContent += row.join(",") + "\n";
    });
    
    // 创建下载链接
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${selectedPollutantName.value}_${analysisType.value === 'annual' ? '年度' : analysisType.value === 'seasonal' ? '季节' : analysisType.value === 'monthly' ? '月度' : '对比'}_详细数据_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success('详细数据导出成功');
  } catch (error) {
    console.error('导出详细数据出错:', error);
    ElMessage.error('导出详细数据失败: ' + (error.message || '未知错误'));
  }
}

// 新增季节筛选和分组逻辑
const seasonFilter = ref('all')

const handleSeasonFilterChange = () => {
  // 触发季节图表更新
  nextTick(() => {
    renderSeasonChart()
  })
}

const getFilteredSeasonalTableData = () => {
  const data = getSeasonalTableData()
  if (seasonFilter.value === 'all') {
    return data
  }
  // 筛选特定季节
  return data.filter(item => {
    const season = parseInt(seasonFilter.value, 10)
    return item.season === season
  })
}

const getSeasonRowClass = (row) => {
  // 根据季节设置行样式
  const season = row.row.season
  if (season === 1) return 'season-spring'
  if (season === 2) return 'season-summer'
  if (season === 3) return 'season-autumn'
  if (season === 4) return 'season-winter'
  return ''
}

const getSeasonClass = (season) => {
  // 根据季节返回样式类名
  if (season === 1) return 'season-label spring'
  if (season === 2) return 'season-label summer'
  if (season === 3) return 'season-label autumn'
  if (season === 4) return 'season-label winter'
  return 'season-label'
}

const getValueClass = (value, pollutant) => {
  // 根据AQI值范围设置不同的样式
  if (pollutant !== 'aqi' || value === undefined || value === null) return ''
  
  if (value <= 50) return 'value-excellent'
  if (value <= 100) return 'value-good'
  if (value <= 150) return 'value-moderate'
  if (value <= 200) return 'value-unhealthy'
  if (value <= 300) return 'value-very-unhealthy'
  return 'value-hazardous'
}

// 渲染季节趋势图表
const renderSeasonChart = () => {
  nextTick(() => {
    // 确保DOM元素已加载
    const chartContainer = document.getElementById('season-chart')
    if (!chartContainer) return
    
    // 获取筛选后的季节数据
    const data = getFilteredSeasonalTableData()
    if (data.length === 0) return
    
    // 清除已有图表实例
    let chartInstance = echarts.getInstanceByDom(chartContainer)
    if (chartInstance) {
      chartInstance.dispose()
    }
    
    // 初始化图表
    chartInstance = echarts.init(chartContainer)
    
    // 处理数据
    const years = [...new Set(data.map(item => item.year))].sort((a, b) => a - b)
    const cities = [...new Set(data.map(item => item.city))]
    const seasons = seasonFilter.value === 'all' 
      ? [1, 2, 3, 4] 
      : [parseInt(seasonFilter.value, 10)]
    
    const seasonNames = {
      1: '春季',
      2: '夏季',
      3: '秋季',
      4: '冬季'
    }
    
    // 根据筛选模式构建图表配置
    if (seasonFilter.value === 'all') {
      // 多季节对比模式
      const series = []
      
      cities.forEach(city => {
        seasons.forEach(season => {
          const seasonData = data.filter(item => item.city === city && item.season === season)
          const values = []
          
          years.forEach(year => {
            const item = seasonData.find(d => d.year === year)
            values.push(item ? item.value : null)
          })
          
          series.push({
            name: `${city}-${seasonNames[season]}`,
            type: 'line',
            data: values,
            smooth: true
          })
        })
      })
      
      const option = {
        title: {
          text: '季节趋势对比',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          type: 'scroll',
          bottom: 0,
          data: series.map(s => s.name)
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: years,
          name: '年份'
        },
        yAxis: {
          type: 'value',
          name: pollutantNames[selectedPollutant.value] || selectedPollutant.value
        },
        series: series
      }
      
      chartInstance.setOption(option)
    } else {
      // 单季节模式
      const season = parseInt(seasonFilter.value, 10)
      const series = []
      
      cities.forEach(city => {
        const seasonData = data.filter(item => item.city === city)
        const values = []
        
        years.forEach(year => {
          const item = seasonData.find(d => d.year === year)
          values.push(item ? item.value : null)
        })
        
        series.push({
          name: city,
          type: 'line',
          data: values,
          smooth: true
        })
      })
      
      const option = {
        title: {
          text: `${seasonNames[season]}趋势分析`,
          left: 'center'
        },
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          type: 'scroll',
          bottom: 0,
          data: cities
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: years,
          name: '年份'
        },
        yAxis: {
          type: 'value',
          name: pollutantNames[selectedPollutant.value] || selectedPollutant.value
        },
        series: series
      }
      
      chartInstance.setOption(option)
    }
    
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      chartInstance.resize()
    })
  })
}

// 监听季节数据和筛选器变化，更新图表
watch([() => rawData.value.seasonalData, seasonFilter], () => {
  if (analysisType.value === 'seasonal' && analysisComplete.value) {
    renderSeasonChart()
  }
})

// 当分析完成时，确保图表渲染
watch(() => analysisComplete.value, (newVal) => {
  if (newVal && analysisType.value === 'seasonal') {
    nextTick(() => {
      renderSeasonChart()
    })
  }
})

// 获取城市行样式类
const getCityRowClass = (row) => {
  // 根据城市设置不同的行样式
  const cityIndex = selectedCities.value.indexOf(row.row.city);
  if (cityIndex === 0) return 'city-primary';
  if (cityIndex === 1) return 'city-success';
  if (cityIndex === 2) return 'city-warning';
  if (cityIndex === 3) return 'city-danger';
  if (cityIndex === 4) return 'city-info';
  return '';
}

// 监听城市对比模式的选择变化，绘制对比图表
watch([() => analysisType.value, () => rawData.value.comparisonData, () => selectedCities.value], () => {
  // 如果是城市对比模式且数据已加载完毕，绘制对比图表
  if (analysisType.value === 'comparison' && rawData.value.comparisonData && rawData.value.comparisonData.length > 0) {
    nextTick(() => {
      renderComparisonChart();
    });
  }
}, { deep: true });

// 渲染城市对比图表
const renderComparisonChart = () => {
  nextTick(() => {
    const chartContainer = document.getElementById('comparison-chart');
    if (!chartContainer) return;
    
    // 获取筛选后的城市对比数据
    const data = getComparisonTableData();
    if (data.length === 0) {
      console.log('没有城市对比数据可显示');
      return; // 没有数据时不继续执行图表渲染
    }
    
    // 清除已有图表实例
    let chartInstance = echarts.getInstanceByDom(chartContainer);
    if (chartInstance) {
      chartInstance.dispose();
    }
    
    // 初始化图表
    chartInstance = echarts.init(chartContainer);
    
    // 按照平均值排序
    const sortedData = [...data].sort((a, b) => a.value - b.value);
    
    const cities = sortedData.map(item => item.city);
    const means = sortedData.map(item => item.value);
    const mins = sortedData.map(item => item.min);
    const maxs = sortedData.map(item => item.max);
    const improvements = sortedData.map(item => 
      item.improvementRate ? item.improvementRate : 0
    );
    
    // 定义改善率颜色
    const improvementColors = improvements.map(value => 
      value > 0 ? '#67c23a' : (value < 0 ? '#f56c6c' : '#909399')
    );
    
    // 创建图表配置
    const option = {
      title: {
        text: `城市${selectedPollutantName.value}对比分析`,
        left: 'center'
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function(params) {
          // 获取多个系列的数据
          const city = params[0].name;
          let html = `<div style="font-weight:bold;margin-bottom:5px">${city}</div>`;
          
          params.forEach(param => {
            let value = param.value;
            let color = param.color;
            let seriesName = param.seriesName;
            
            if (seriesName === '改善率') {
              html += `<div style="display:flex;justify-content:space-between">
                <span style="margin-right:10px">${seriesName}:</span>
                <span style="color:${value > 0 ? '#67c23a' : '#f56c6c'}">${value.toFixed(2)}%</span>
              </div>`;
            } else {
              html += `<div style="display:flex;justify-content:space-between">
                <span style="margin-right:10px">${seriesName}:</span>
                <span>${value.toFixed(2)}</span>
              </div>`;
            }
          });
          
          return html;
        }
      },
      legend: {
        data: ['平均值', '最小值', '最大值', '改善率'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: cities,
        axisLabel: {
          interval: 0,
          rotate: 30
        }
      },
      yAxis: [
        {
          type: 'value',
          name: selectedPollutantName.value,
          position: 'left'
        },
        {
          type: 'value',
          name: '改善率(%)',
          position: 'right',
          axisLine: {
            show: true,
            lineStyle: {
              color: '#5470C6'
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
          barWidth: '25%',
          itemStyle: {
            color: '#5470C6'
          }
        },
        {
          name: '最小值',
          type: 'bar',
          data: mins,
          barWidth: '25%',
          itemStyle: {
            color: '#91CC75'
          }
        },
        {
          name: '最大值',
          type: 'bar',
          data: maxs,
          barWidth: '25%',
          itemStyle: {
            color: '#FAC858'
          }
        },
        {
          name: '改善率',
          type: 'line',
          yAxisIndex: 1,
          data: improvements,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: function(params) {
              return improvementColors[params.dataIndex];
            }
          }
        }
      ]
    };
    
    // 设置图表选项
    chartInstance.setOption(option);
    
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      chartInstance.resize();
    });
  });
}

</script>

<style scoped>
.trend-analysis-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.page-description {
  color: #606266;
  font-size: 14px;
}

.analysis-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background-color: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid #eee;
  border-top-color: #409EFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.analysis-error {
  margin: 40px 0;
}

.analysis-results {
  margin-top: 24px;
  width: 100%;
}

.summary-card {
  margin-bottom: 24px;
  border-radius: 8px;
  transition: all 0.3s;
}

.summary-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.summary-content {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.findings-section, .suggestions-section {
  flex: 1;
  min-width: 300px;
}

.findings-section h4, .suggestions-section h4 {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.findings-list, .suggestions-list {
  padding-left: 20px;
  margin: 0;
}

.findings-list li, .suggestions-list li {
  margin-bottom: 8px;
  line-height: 1.5;
}

.chart-container {
  margin-bottom: 24px;
  width: 100%;
}

.chart-card {
  margin-bottom: 24px;
  border-radius: 8px;
  transition: all 0.3s;
  width: 100%;
}

.chart-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.chart-area {
  height: 500px;
  width: 100%;
}

.active-chart {
  display: block;
  width: 100%;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.stats-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.stats-card {
  border-radius: 8px;
  transition: all 0.3s;
}

.stats-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stats-content {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}

.stat-item {
  flex: 0 0 calc(50% - 12px);
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.stat-label {
  color: #606266;
}

.stat-value {
  font-weight: 500;
  color: #303133;
}

.improvement-info {
  width: 100%;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ebeef5;
}

.improvement-header {
  margin-bottom: 12px;
}

.improvement-header h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.improvement-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}

.improvement-item {
  flex: 0 0 calc(33.33% - 8px);
  display: flex;
  flex-direction: column;
}

.improvement-label {
  font-size: 12px;
  color: #909399;
}

.improvement-value {
  font-weight: 500;
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}

.analysis-empty {
  padding: 60px 0;
  text-align: center;
}

/* 新增样式 - 确保图表容器能够充分利用可用空间 */
.el-row {
  width: 100%;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

.el-col {
  padding-left: 0 !important;
  padding-right: 0 !important;
}

@media (max-width: 768px) {
  .summary-content {
    flex-direction: column;
    gap: 16px;
  }
  
  .stats-container {
    grid-template-columns: 1fr;
  }
  
  .improvement-item {
    flex: 0 0 100%;
  }
  
  .stat-item {
    flex: 0 0 100%;
  }
  
  .chart-area {
    height: 400px;
  }
}

.annual-chart-area,
.seasonal-chart-area,
.monthly-chart-area,
.comparison-chart-area {
  width: 100%;
  height: 500px;
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 30px;
  width: 100%;
  min-height: 550px;
}

.chart-area {
  height: 500px;
  width: 100%;
  overflow: visible;
}

/* 数据表格区域样式 */
.data-tables-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 20px;
}

.stats-table-card,
.detail-table-card {
  margin-bottom: 20px;
  width: 100%;
}

.stats-summary-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.city-stat-card {
  flex: 1;
  min-width: 300px;
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.city-stat-card h4 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 16px;
  color: #303133;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 8px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.empty-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100px;
  color: #909399;
  font-style: italic;
}

.improvement-table-wrapper {
  margin-top: 16px;
}

.improvement-table-wrapper h4 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 16px;
  color: #303133;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .data-tables-section {
    flex-direction: column;
  }
  
  .city-stat-card {
    width: 100%;
  }
  
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.seasonal-analysis-container {
  margin-top: 20px;
}

.filter-container {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.season-filter {
  margin-top: 10px;
}

.chart-container {
  margin-bottom: 30px;
  background-color: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.table-container {
  margin-bottom: 30px;
}

/* 季节标签样式 */
.season-label {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
}

.spring {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.summer {
  background-color: #fff8e1;
  color: #ff8f00;
}

.autumn {
  background-color: #fff3e0;
  color: #e65100;
}

.winter {
  background-color: #e3f2fd;
  color: #1565c0;
}

/* 行样式 */
.season-spring {
  background-color: rgba(232, 245, 233, 0.3);
}

.season-summer {
  background-color: rgba(255, 248, 225, 0.3);
}

.season-autumn {
  background-color: rgba(255, 243, 224, 0.3);
}

.season-winter {
  background-color: rgba(227, 242, 253, 0.3);
}

/* 值样式 */
.value-excellent {
  color: #00e400;
  font-weight: bold;
}

.value-good {
  color: #92d050;
  font-weight: bold;
}

.value-moderate {
  color: #ffff00;
  font-weight: bold;
  text-shadow: 0px 0px 1px rgba(0,0,0,0.5);
}

.value-unhealthy {
  color: #ff7e00;
  font-weight: bold;
}

.value-very-unhealthy {
  color: #ff0000;
  font-weight: bold;
}

.value-hazardous {
  color: #99004c;
  font-weight: bold;
}

.comparison-info {
  margin-bottom: 20px;
}

.comparison-chart-container {
  margin-top: 24px;
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 3px solid #409EFF;
}

/* 城市对比相关样式 */
.value-cell {
  font-weight: 500;
}

/* 城市行样式 */
:deep(.city-primary) {
  background-color: rgba(64, 158, 255, 0.1);
}

:deep(.city-success) {
  background-color: rgba(103, 194, 58, 0.1);
}

:deep(.city-warning) {
  background-color: rgba(230, 162, 60, 0.1);
}

:deep(.city-danger) {
  background-color: rgba(245, 108, 108, 0.1);
}

:deep(.city-info) {
  background-color: rgba(144, 147, 153, 0.1);
}

.improvement-positive {
  color: #67c23a;
  font-weight: bold;
}

.improvement-negative {
  color: #f56c6c;
  font-weight: bold;
}

.comparison-data-container {
  margin-top: 20px;
}

.comparison-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.comparison-info {
  margin-bottom: 16px;
}

.comparison-chart-container {
  margin-top: 24px;
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-top: 0;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 3px solid #409EFF;
}

/* 城市行样式 */
:deep(.city-primary) td {
  background-color: rgba(64, 158, 255, 0.1);
}

:deep(.city-success) td {
  background-color: rgba(103, 194, 58, 0.1);
}

:deep(.city-warning) td {
  background-color: rgba(230, 162, 60, 0.1);
}

:deep(.city-danger) td {
  background-color: rgba(245, 108, 108, 0.1);
}

:deep(.city-info) td {
  background-color: rgba(144, 147, 153, 0.1);
}

.value-cell {
  font-weight: 500;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.improvement-positive {
  color: #67c23a;
}

.improvement-negative {
  color: #f56c6c;
}

/* 介绍卡片样式优化 */
.card-header {
  padding: 12px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
  background-color: #f8f9fa;
}

.detail-table-card, .stats-table-card {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  margin-bottom: 24px;
}

/* 确保表格的美观性 */
:deep(.el-table) {
  border-radius: 4px;
  overflow: hidden;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table--border) {
  border: 1px solid #ebeef5;
}

/* 控制空白区域比例 */
.analysis-results {
  padding: 20px 0;
}

.data-tables-section {
  display: grid;
  grid-gap: 24px;
  padding: 0 12px;
}

.detail-info-header {
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-info-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.description-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #606266;
  background-color: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid #409EFF;
}

.description-text .el-icon {
  color: #409EFF;
  font-size: 16px;
}

/* 城市对比详细数据样式 */
.detail-top-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.detail-info-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 10px;
  margin-top: auto;
}

.comparison-table-container {
  margin-bottom: 24px;
}

.description-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #606266;
  background-color: #f8f9fa;
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid #409EFF;
}

.empty-chart-tip {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
  position: absolute;
  top: 50px;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(248, 249, 250, 0.8);
  border-radius: 8px;
  z-index: 5;
}

.empty-chart-tip p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #606266;
}
</style> 