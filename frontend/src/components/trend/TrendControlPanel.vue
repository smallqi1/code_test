<template>
  <div class="trend-control-panel">
    <el-card class="control-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <el-tooltip content="选择城市、污染物和分析类型，然后点击分析按钮来查看空气质量趋势" placement="top">
            <el-icon class="header-icon"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
      </template>
      
      <div class="control-form">
        <div class="form-row">
          <div class="form-item">
            <el-form-item label="城市选择">
              <el-select
                v-model="localSelectedCities"
                multiple
                filterable
                :collapse-tags="false"
                placeholder="选择城市(最多5个)"
                style="width: 100%"
                :disabled="loading"
                @visible-change="handleSelectVisibleChange"
              >
                <template #prefix>
                  <div class="city-limit-warning" v-if="localSelectedCities.length >= 5">
                    <el-icon><Warning /></el-icon> 已达上限
                  </div>
                </template>
                <template #tag="{ option }">
                  <el-tag
                    v-if="option && option.value"
                    closable
                    :disable-transitions="false"
                    :type="getCityTagType(option.value)"
                    effect="light"
                    size="small"
                    class="city-tag"
                    @close="removeCity(option.value)"
                  >
                    {{ option.label || option.value }}
                  </el-tag>
                </template>
                <el-option
                  v-for="city in cities"
                  :key="city.value"
                  :label="city.label"
                  :value="city.value"
                  :disabled="localSelectedCities.length >= 5 && !localSelectedCities.includes(city.value)"
                >
                  <div class="city-option">
                    <el-icon v-if="localSelectedCities.includes(city.value)"><Check /></el-icon>
                    <span>{{ city.label }}</span>
                  </div>
                </el-option>
              </el-select>
              <div class="city-selection-hint">
                <span v-if="localAnalysisType === 'comparison'">城市对比分析至少需要选择2个城市，最多选择5个城市</span>
                <span v-else>所有分析类型最多可选择5个城市</span>
                (已选择: {{ localSelectedCities.length }}/5)
              </div>
            </el-form-item>
          </div>
          
          <div class="form-item">
            <el-form-item label="污染物指标">
              <el-select
                v-model="localSelectedPollutant"
                placeholder="选择污染物指标"
                style="width: 100%"
                :disabled="loading"
              >
                <el-option label="AQI指数" value="aqi" />
                <el-option label="PM2.5浓度" value="pm25" />
                <el-option label="PM10浓度" value="pm10" />
                <el-option label="二氧化硫(SO₂)" value="so2" />
                <el-option label="二氧化氮(NO₂)" value="no2" />
                <el-option label="一氧化碳(CO)" value="co" />
                <el-option label="臭氧(O₃)" value="o3" />
              </el-select>
            </el-form-item>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-item">
            <el-form-item label="分析类型">
              <el-select
                v-model="localAnalysisType"
                placeholder="选择分析类型"
                style="width: 100%"
                :disabled="loading"
              >
                <el-option 
                  v-for="option in analysisTypeOptions" 
                  :key="option.value"
                  :label="option.label"
                  :value="option.value"
                >
                  <div class="analysis-option">
                    <span>{{ option.label }}</span>
                    <span class="option-description">{{ option.description }}</span>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>
          </div>
          
          <div class="form-item year-selection">
            <el-form-item label="年份范围">
              <div class="year-range-selector">
                <el-select
                  v-model="localStartYear"
                  placeholder="请选择起始年份"
                  @change="updateStartYear"
                  :disabled="loading"
                  class="year-select"
                >
                  <el-option
                    v-for="year in filteredStartYears"
                    :key="year"
                    :label="year + '年'"
                    :value="year"
                  />
                </el-select>
                
                <span class="year-range-separator">至</span>
                
                <el-select
                  v-model="localEndYear"
                  placeholder="请选择结束年份"
                  @change="updateEndYear"
                  :disabled="loading"
                  class="year-select"
                >
                  <el-option
                    v-for="year in filteredEndYears"
                    :key="year"
                    :label="year + '年'"
                    :value="year"
                  />
                </el-select>
              </div>
              <div class="selected-years-display" v-if="localStartYear && localEndYear">
                当前选择: {{ localStartYear }}年 至 {{ localEndYear }}年
              </div>
            </el-form-item>
          </div>
        </div>
        
        <div class="form-actions">
          <el-button
            type="primary"
            @click="handleAnalyze"
            :loading="loading"
            :disabled="!isFormValid"
            :icon="Histogram"
          >
            {{ loading ? '分析中...' : '开始分析' }}
          </el-button>
          
          <el-button
            @click="resetForm"
            :disabled="loading"
            :icon="RefreshRight"
          >
            重置
          </el-button>
          
          <el-popover
            placement="bottom"
            title="分析说明"
            :width="300"
            trigger="click"
          >
            <template #reference>
              <el-button
                text
                type="info"
                :icon="InfoFilled"
              >
                分析说明
              </el-button>
            </template>
            <div class="analysis-help">
              <p><strong>分析类型说明:</strong></p>
              <ul>
                <li><strong>年度分析:</strong> 统计每年的平均数值，分析长期变化趋势</li>
                <li><strong>季节分析:</strong> 按四季展示数据，分析季节变化规律</li>
                <li><strong>月度分析:</strong> 按月份展示数据，分析月度变化特点</li>
                <li><strong>城市对比:</strong> 对比不同城市的数据表现</li>
              </ul>
              <p><strong>污染物指标:</strong></p>
              <ul>
                <li><strong>AQI:</strong> 空气质量综合指数</li>
                <li><strong>PM2.5/PM10:</strong> 颗粒物浓度，影响呼吸系统</li>
                <li><strong>SO₂/NO₂:</strong> 气体污染物，主要来源于燃烧</li>
                <li><strong>CO:</strong> 一氧化碳，主要来源于车辆和燃烧</li>
                <li><strong>O₃:</strong> 臭氧，夏季高温易形成</li>
              </ul>
            </div>
          </el-popover>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { Histogram, RefreshRight, InfoFilled, QuestionFilled, Warning, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 定义props
const props = defineProps({
  selectedCities: {
    type: Array,
    default: () => ['广州市']
  },
  cities: {
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
  availableYears: {
    type: Array,
    default: () => []
  },
  selectedPollutant: {
    type: String,
    default: 'aqi'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// 定义事件
const emit = defineEmits([
  'update:selectedCities',
  'update:analysisType',
  'update:startYear',
  'update:endYear',
  'update:selectedPollutant',
  'analyze'
])

// 本地状态
const localSelectedCities = ref([...props.selectedCities])
const localSelectedPollutant = ref(props.selectedPollutant)
const localAnalysisType = ref(props.analysisType)
const localStartYear = ref(null)
const localEndYear = ref(null)
const isResetting = ref(false)

// 分析类型选项
const analysisTypeOptions = [
  { 
    value: 'annual', 
    label: '年度分析',
    description: '查看逐年变化趋势'
  },
  { 
    value: 'seasonal', 
    label: '季节分析',
    description: '分析季节性变化规律'
  },
  { 
    value: 'monthly', 
    label: '月度分析',
    description: '查看月度变化特征'
  },
  { 
    value: 'comparison', 
    label: '城市对比',
    description: '比较城市间差异'
  }
]

// 计算可选的年份范围
const filteredStartYears = computed(() => {
  return props.availableYears.filter(year => !localEndYear.value || year <= localEndYear.value)
})

const filteredEndYears = computed(() => {
  return props.availableYears.filter(year => !localStartYear.value || year >= localStartYear.value)
})

// 通知父组件年份选择变化
const updateStartYear = (newVal) => {
  emit('update:startYear', newVal)
}

const updateEndYear = (newVal) => {
  emit('update:endYear', newVal)
}

const isFormValid = computed(() => {
  // 验证表单是否有效
  return localSelectedCities.value.length > 0 && 
         localStartYear.value && 
         localEndYear.value && 
         localStartYear.value <= localEndYear.value
})

// 监听本地状态变化，更新父组件
watch(localSelectedCities, (newVal) => {
  // 如果正在重置，不触发更新
  if (isResetting.value) return
  
  // 限制最多选择5个城市
  if (newVal.length > 5) {
    ElMessage.warning('最多只能选择5个城市进行对比')
    localSelectedCities.value = newVal.slice(0, 5)
    return
  }
  emit('update:selectedCities', newVal)
})

watch(localAnalysisType, (newVal) => {
  if (isResetting.value) return
  console.log('[ControlPanel] localAnalysisType changed, emitting update:', newVal);
  
  // 对于城市对比分析，确保至少选择两个城市
  if (newVal === 'comparison' && localSelectedCities.value.length < 2) {
    ElMessage.info('城市对比分析需要至少选择两个城市')
  }
  
  // 对于所有分析类型，都限制最多选择5个城市
  if (localSelectedCities.value.length > 5) {
    ElMessage.warning('最多只能选择5个城市进行对比')
    localSelectedCities.value = localSelectedCities.value.slice(0, 5)
    emit('update:selectedCities', localSelectedCities.value)
  }
  
  emit('update:analysisType', newVal)
})

watch(localStartYear, (newVal) => {
  if (isResetting.value) return
  
  // 只有两个值都不为null时才进行比较
  if (newVal !== null && localEndYear.value !== null && newVal > localEndYear.value) {
    ElMessage.warning('起始年份不能大于结束年份')
    localEndYear.value = newVal
    emit('update:endYear', newVal)
  }
  emit('update:startYear', newVal)
})

watch(localEndYear, (newVal) => {
  if (isResetting.value) return
  
  // 只有两个值都不为null时才进行比较
  if (newVal !== null && localStartYear.value !== null && newVal < localStartYear.value) {
    ElMessage.warning('结束年份不能小于起始年份')
    localStartYear.value = newVal
    emit('update:startYear', newVal)
  }
  emit('update:endYear', newVal)
})

watch(localSelectedPollutant, (newVal) => {
  if (isResetting.value) return
  emit('update:selectedPollutant', newVal)
})

// 监听props变化，更新本地状态
watch(() => props.selectedCities, (newVal) => {
  if (isResetting.value) return
  if (JSON.stringify(localSelectedCities.value) === JSON.stringify(newVal)) return
  localSelectedCities.value = [...newVal]
})

watch(() => props.analysisType, (newVal) => {
  if (isResetting.value) return
  if (localAnalysisType.value === newVal) return
  localAnalysisType.value = newVal
})

watch(() => props.startYear, (newVal) => {
  if (isResetting.value) return
  if (localStartYear.value === newVal) return
  localStartYear.value = newVal
})

watch(() => props.endYear, (newVal) => {
  if (isResetting.value) return
  if (localEndYear.value === newVal) return
  localEndYear.value = newVal
})

watch(() => props.selectedPollutant, (newVal) => {
  if (isResetting.value) return
  if (localSelectedPollutant.value === newVal) return
  localSelectedPollutant.value = newVal
})

// 方法
const removeCity = (cityValue) => {
  localSelectedCities.value = localSelectedCities.value.filter(city => city !== cityValue)
  emit('update:selectedCities', localSelectedCities.value)
}

const handleAnalyze = () => {
  if (!isFormValid.value) {
    ElMessage.warning('请完善分析参数')
    return
  }
  
  // 校验城市数量
  if (localSelectedCities.value.length > 5) {
    ElMessage.warning('最多只能选择5个城市进行对比')
    localSelectedCities.value = localSelectedCities.value.slice(0, 5)
    emit('update:selectedCities', localSelectedCities.value)
    return
  }
  
  // 校验城市对比分析的城市数量
  if (localAnalysisType.value === 'comparison' && localSelectedCities.value.length < 2) {
    ElMessage.warning('城市对比分析至少需要选择2个城市')
    return
  }
  
  // 记录分析条件到控制台
  console.log('分析参数:', {
    cities: localSelectedCities.value,
    pollutant: localSelectedPollutant.value,
    analysisType: localAnalysisType.value,
    startYear: localStartYear.value,
    endYear: localEndYear.value
  })
  
  emit('analyze')
}

const resetForm = () => {
  // 设置重置标志，防止触发watch
  isResetting.value = true
  
  localSelectedCities.value = ['广州市']
  localAnalysisType.value = 'annual'
  localStartYear.value = null
  localEndYear.value = null
  localSelectedPollutant.value = 'aqi'
  
  // 一次性发送所有更新
  emit('update:selectedCities', localSelectedCities.value)
  emit('update:analysisType', localAnalysisType.value)
  emit('update:startYear', localStartYear.value)
  emit('update:endYear', localEndYear.value)
  emit('update:selectedPollutant', localSelectedPollutant.value)
  
  // 使用nextTick确保DOM更新后再重置标志
  nextTick(() => {
    isResetting.value = false
    ElMessage.success('已重置分析参数')
  })
}

// 生命周期钩子
onMounted(() => {
  console.log('趋势分析控制面板已加载，初始化年份值:', props.startYear, props.endYear)
  
  // 初始化本地年份值
  if (props.startYear) {
    localStartYear.value = props.startYear
    console.log('初始化起始年份:', localStartYear.value)
  }
  
  if (props.endYear) {
    localEndYear.value = props.endYear
    console.log('初始化结束年份:', localEndYear.value)
  }
  
  // 确保结束年份至少等于起始年份
  if (localStartYear.value && localEndYear.value && localEndYear.value < localStartYear.value) {
    localEndYear.value = localStartYear.value
    emit('update:endYear', localEndYear.value)
  }
  
  console.log('趋势分析控制面板已初始化完成，年份值:', localStartYear.value, localEndYear.value)
})

// 添加城市标签类型方法
const getCityTagType = (cityValue) => {
  if (!cityValue) return '';
  
  const cityIndex = localSelectedCities.value.indexOf(cityValue);
  if (cityIndex === -1) return '';
  
  // 对于城市对比分析，使用不同颜色区分城市
  if (localAnalysisType.value === 'comparison') {
    switch (cityIndex) {
      case 0: return 'primary';
      case 1: return 'success';
      case 2: return 'warning';
      case 3: return 'danger';
      case 4: return 'info';
      default: return '';
    }
  }
  
  // 对于其他分析类型，使用统一颜色
  return '';
}

// 监听分析类型变化，更新城市标签样式
watch(localAnalysisType, () => {
  // 触发视图更新，使标签样式根据分析类型变化
  if (localSelectedCities.value.length > 0) {
    const temp = [...localSelectedCities.value];
    localSelectedCities.value = [];
    nextTick(() => {
      localSelectedCities.value = temp;
    });
  }
});

// 添加处理Select显示状态变化的方法
const handleSelectVisibleChange = (visible) => {
  // 如果下拉框关闭且没有选择任何城市，自动选择第一个城市
  if (!visible && localSelectedCities.value.length === 0) {
    if (props.cities && props.cities.length > 0) {
      const firstCity = props.cities[0].value;
      if (firstCity) {
        localSelectedCities.value = [firstCity];
        emit('update:selectedCities', localSelectedCities.value);
      }
    }
  }
}
</script>

<style scoped>
.trend-control-panel {
  margin-bottom: 16px;
}

.control-card {
  border-radius: 8px;
  transition: all 0.25s;
  margin-bottom: 10px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.control-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 16px;
  background-color: #f8f9fa;
}

.header-icon {
  font-size: 16px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
}

.header-icon:hover {
  color: #409EFF;
  transform: scale(1.1);
}

.control-form {
  padding: 20px 16px;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 20px;
}

.form-item {
  flex: 1;
  min-width: 250px;
}

/* 城市选择相关样式 */
.city-option {
  display: flex;
  align-items: center;
  gap: 5px;
}

.city-option .el-icon {
  color: #409EFF;
  font-size: 14px;
}

.selected-city-icon {
  color: #409EFF;
  margin-right: 5px;
}

.el-select-dropdown__item.selected .city-option {
  color: #409EFF;
  font-weight: bold;
}

.analysis-option {
  display: flex;
  flex-direction: column;
}

.option-description {
  font-size: 12px;
  color: #909399;
}

.year-select {
  min-width: 140px;
}

.city-selection-hint {
  font-size: 12px;
  color: #606266;
  margin-top: 6px;
  line-height: 1.5;
  background-color: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
  border-left: 2px solid #409EFF;
}

.city-tag {
  margin-right: 6px;
  margin-bottom: 4px;
  font-size: 13px;
  border-radius: 4px;
  padding: 0 8px;
  height: 26px;
  line-height: 24px;
  border: 1px solid #e9e9eb;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  box-sizing: border-box;
  transition: all 0.2s;
}

.city-tag:hover {
  background-color: #ecf5ff;
  border-color: #d9ecff;
  color: #409eff;
}

.city-limit-warning {
  color: #E6A23C;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding-right: 8px;
}

/* 年份选择样式 */
.year-range-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}

.year-range-separator {
  color: #606266;
}

.selected-years-display {
  margin-top: 8px;
  font-size: 13px;
  color: #409EFF;
  font-weight: 500;
  background-color: #f0f9ff;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

/* 按钮区域样式 */
.form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
}

/* 分析说明样式 */
.analysis-help {
  font-size: 14px;
  line-height: 1.6;
}

.analysis-help ul {
  padding-left: 16px;
  margin: 8px 0;
}

.analysis-help li {
  margin-bottom: 6px;
}

.analysis-help p {
  margin: 10px 0 5px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
    gap: 16px;
  }
  
  .form-item {
    width: 100%;
  }
  
  .year-range-selector {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .year-range-separator {
    display: none;
  }
}
</style> 