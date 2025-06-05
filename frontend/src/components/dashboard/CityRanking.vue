<template>
  <el-card class="ranking-table" shadow="hover">
    <template #header>
      <div class="card-header">
        <span><i class="header-icon">🏆</i> 城市排名</span>
        <div class="header-actions">
          <el-select v-model="rankMetric" size="small" placeholder="排序指标" style="margin-right: 6px;">
            <el-option label="AQI" value="aqi"></el-option>
            <el-option label="PM2.5" value="pm25"></el-option>
            <el-option label="PM10" value="pm10"></el-option>
            <el-option label="SO2" value="so2"></el-option>
            <el-option label="NO2" value="no2"></el-option>
            <el-option label="O3" value="o3"></el-option>
            <el-option label="CO" value="co"></el-option>
          </el-select>
          <el-radio-group v-model="rankOrder" size="small" :disabled="loading">
            <el-radio-button :value="'asc'">升序</el-radio-button>
            <el-radio-button :value="'desc'">降序</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </template>
    
    <div v-if="loading" class="table-skeleton">
      <div class="skeleton-row header-row">
        <div class="skeleton-cell" v-for="i in 5" :key="i"></div>
      </div>
      <div class="skeleton-row" v-for="i in 5" :key="i">
        <div class="skeleton-cell" v-for="j in 5" :key="j"></div>
      </div>
    </div>
    
    <el-table 
      v-else
      :data="sortedCities" 
      style="width: 100%"
      :empty-text="isProvinceLoading ? '加载中...' : '暂无数据'"
      v-loading="isProvinceLoading"
      stripe
      border
      size="small"
      :row-class-name="tableRowClassName"
    >
      <el-table-column type="index" label="排名" width="60" align="center" />
      <el-table-column prop="city_name" label="城市" align="center" />
      <el-table-column :prop="rankMetric" :label="getMetricLabel(rankMetric)" sortable align="center">
        <template #default="scope">
          <span>{{ scope.row[rankMetric] }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="level" label="等级" align="center">
        <template #default="scope">
          <el-tag :type="getLevelType(scope.row.level)" size="small" v-if="rankMetric === 'aqi'">{{ scope.row.level }}</el-tag>
          <el-tag :type="getLevelTagType(getPollutantLevel(rankMetric, scope.row[rankMetric]))" size="small" v-else>
            {{ getPollutantLevel(rankMetric, scope.row[rankMetric]) }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { ref, computed, defineProps, watch } from 'vue'
import { getPollutantLevel, getLevelTagType } from '@/utils/aqi'

// 接收属性
const props = defineProps({
  provinceData: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  isProvinceLoading: {
    type: Boolean,
    default: false
  }
})

// 内部状态
const rankMetric = ref('aqi')
const rankOrder = ref('asc')

// 计算属性
const sortedCities = computed(() => {
  if (!props.provinceData || props.provinceData.length === 0) {
    return []
  }
  
  const cities = [...props.provinceData]
  return cities.sort((a, b) => {
    // 获取排序字段的值
    let valueA = a[rankMetric.value]
    let valueB = b[rankMetric.value]
    
    // 确保值为数字
    valueA = Number(valueA) || 0
    valueB = Number(valueB) || 0
    
    return rankOrder.value === 'asc' 
      ? valueA - valueB 
      : valueB - valueA
  }).map(city => ({
    ...city,
    city_name: city.name // 添加city_name字段以兼容表格展示
  }))
})

// 方法
const tableRowClassName = ({ row, rowIndex }) => {
  if (rowIndex === 0) return 'top-rank-row'
  if (rowIndex === 1) return 'second-rank-row'
  if (rowIndex === 2) return 'third-rank-row'
  return ''
}

const getMetricLabel = (metric) => {
  const labels = {
    'aqi': 'AQI',
    'pm25': 'PM2.5',
    'pm10': 'PM10',
    'so2': 'SO2',
    'no2': 'NO2',
    'o3': 'O3',
    'co': 'CO'
  }
  return labels[metric] || metric
}

const getLevelType = (level) => {
  if (level === '优') return 'success'
  if (level === '良') return 'warning'
  if (level === '轻度污染') return 'danger'
  if (level === '中度污染') return 'danger'
  if (level === '重度污染') return 'danger'
  return 'danger'
}

// 根据污染物类型和值获取对应的CSS类 - 删除颜色样式
const getPollutantClass = (pollutantType, value) => {
  // 所有指标都统一返回空字符串，显示默认黑色
  return ''
}

const getAqiClass = (aqi) => {
  // 返回空字符串，使用默认黑色
  return ''
}
</script>

<style scoped>
/* 自定义组件样式 */
:deep(.el-table td) {
  color: #333; /* 确保表格内所有文字都是黑色 */
  padding: 4px 0; /* 减少单元格内边距 */
}

:deep(.el-table th) {
  padding: 6px 0; /* 减少表头内边距 */
}

:deep(.el-card__header) {
  padding: 10px 15px; /* 减少卡片头部内边距 */
}

:deep(.el-card__body) {
  padding: 8px; /* 减少卡片内容内边距 */
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 调整标签样式 */
:deep(.el-tag) {
  padding: 0 6px;
  height: 20px;
  line-height: 20px;
}
</style> 