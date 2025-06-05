<template>
  <div class="trend-details" v-if="analysisComplete">
    <!-- 统计分析卡片 -->
    <div class="stats-grid">
      <!-- 基本统计信息 -->
      <div class="card stats-card">
        <div class="card-header">
          <h2 class="card-title">基本统计信息</h2>
        </div>
        <div class="card-body">
          <div v-if="Object.keys(basicStats).length > 0" class="stats-table">
            <table>
              <thead>
                <tr>
                  <th>城市</th>
                  <th>平均值</th>
                  <th>最大值</th>
                  <th>最小值</th>
                  <th>标准差</th>
                  <th>中位数</th>
                  <th>变异系数</th>
                  <th>超标率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="city in selectedCities" :key="city">
                  <td>{{ city }}</td>
                  <td>{{ formatValue(basicStats[city]?.mean) }}</td>
                  <td>{{ formatValue(basicStats[city]?.max) }}</td>
                  <td>{{ formatValue(basicStats[city]?.min) }}</td>
                  <td>{{ formatValue(basicStats[city]?.std) }}</td>
                  <td>{{ formatValue(basicStats[city]?.median) }}</td>
                  <td>{{ formatValue(basicStats[city]?.cv) }}%</td>
                  <td>{{ formatValue(basicStats[city]?.exceedRate) }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-data-message">
            暂无统计数据
          </div>
          
          <!-- 质量达标率图表，确保容器一直存在并显示 -->
          <div class="quality-rate-chart-container">
            <h3 class="section-title">空气质量达标率</h3>
            <div id="quality-rate-chart" class="chart-container"></div>
          </div>
        </div>
      </div>
      
      <!-- 改善情况分析 -->
      <div class="card improvement-card">
        <div class="card-header">
          <h2 class="card-title">空气质量改善情况</h2>
          <div class="card-actions">
            <button class="btn-outline btn-sm improvement-toggle-btn" @click="toggleImprovementView">
              {{ improvementViewMode === 'cards' ? '切换为列表视图' : '切换为卡片视图' }}
            </button>
          </div>
        </div>
        <div class="card-body">
          <!-- 卡片视图 -->
          <div v-if="Object.keys(improvementStats).length > 0 && improvementViewMode === 'cards'" class="improvement-grid">
            <div v-for="city in selectedCities" :key="city" class="improvement-item">
              <div class="city-name">{{ city }}</div>
              <div class="improvement-stats">
                <div class="stat">
                  <div class="stat-label">年均改善率</div>
                  <div class="stat-value" :class="getImprovementClass(improvementStats[city]?.yearlyRate)">
                    {{ formatValue(improvementStats[city]?.yearlyRate) }}%
                  </div>
                </div>
                <div class="stat">
                  <div class="stat-label">总体改善率</div>
                  <div class="stat-value" :class="getImprovementClass(improvementStats[city]?.totalRate)">
                    {{ formatValue(improvementStats[city]?.totalRate) }}%
                  </div>
                </div>
                <div class="improvement-trend">
                  <div class="trend-icon" :class="getTrendClass(improvementStats[city]?.totalRate)">
                    <i v-if="improvementStats[city]?.totalRate < 0" class="trend-arrow-down">▼</i>
                    <i v-else-if="improvementStats[city]?.totalRate > 0" class="trend-arrow-up">▲</i>
                    <i v-else class="trend-neutral">●</i>
                  </div>
                  <div class="trend-text">{{ getTrendText(improvementStats[city]?.totalRate) }}</div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 列表视图 -->
          <div v-else-if="Object.keys(improvementStats).length > 0 && improvementViewMode === 'list'" class="improvement-list">
            <table class="improvement-table">
              <thead>
                <tr>
                  <th>城市</th>
                  <th>年均改善率</th>
                  <th>总体改善率</th>
                  <th>改善趋势</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="city in selectedCities" :key="city">
                  <td>{{ city }}</td>
                  <td :class="getImprovementClass(improvementStats[city]?.yearlyRate)">
                    {{ formatValue(improvementStats[city]?.yearlyRate) }}%
                  </td>
                  <td :class="getImprovementClass(improvementStats[city]?.totalRate)">
                    {{ formatValue(improvementStats[city]?.totalRate) }}%
                  </td>
                  <td>
                    <div class="trend-indicator">
                      <span class="trend-dot" :class="getTrendClass(improvementStats[city]?.totalRate)"></span>
                      {{ getTrendText(improvementStats[city]?.totalRate) }}
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- 改善情况图表，只在图表模式下显示 -->
          <div v-else-if="improvementViewMode === 'chart'" class="improvement-chart-container">
            <div id="improvement-chart" class="chart-container"></div>
          </div>
          
          <div v-if="Object.keys(improvementStats).length === 0" class="empty-data-message">
            暂无改善情况数据
          </div>
          
          <!-- 视图切换按钮组 -->
          <div class="view-toggles">
            <button 
              class="view-toggle-btn" 
              :class="{ active: improvementViewMode === 'cards' }" 
              @click="improvementViewMode = 'cards'"
            >
              卡片视图
            </button>
            <button 
              class="view-toggle-btn" 
              :class="{ active: improvementViewMode === 'list' }" 
              @click="improvementViewMode = 'list'"
            >
              列表视图
            </button>
            <button 
              class="view-toggle-btn" 
              :class="{ active: improvementViewMode === 'chart' }" 
              @click="setChartViewMode"
            >
              图表视图
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 添加一个新的两列网格以容纳达标天数分析和季节性变化分析 -->
    <div class="stats-grid">
      <!-- 达标天数分析 -->
      <div class="card compliance-card">
        <div class="card-header">
          <h2 class="card-title">空气质量达标天数分析</h2>
          <div class="card-actions">
            <button class="btn-outline btn-sm" @click="$emit('export-chart', 'compliance')">导出图表</button>
          </div>
        </div>
        <div class="card-body">
          <div id="compliance-chart" class="chart-container">
            <!-- 图表内容由父组件渲染 -->
          </div>
        </div>
      </div>
      
      <!-- 新增的季节性变化分析卡片 -->
      <div class="card seasonal-pattern-card">
        <div class="card-header">
          <h2 class="card-title">季节性变化分析</h2>
          <div class="card-actions">
            <button class="btn-outline btn-sm" @click="$emit('export-chart', 'seasonalPattern')">导出图表</button>
          </div>
        </div>
        <div class="card-body">
          <div id="seasonal-pattern-chart" class="chart-container">
            <!-- 图表内容由父组件渲染 -->
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分析结果摘要 -->
    <div class="card summary-card">
      <div class="card-header">
        <h2 class="card-title">趋势分析摘要</h2>
      </div>
      <div class="card-body">
        <div v-if="analysisSummary.findings.length > 0 || analysisSummary.suggestions.length > 0" class="summary-content">
          <div class="summary-section">
            <h3 class="section-title">主要发现</h3>
            <ul v-if="analysisSummary.findings.length > 0" class="findings-list">
              <li v-for="(finding, index) in analysisSummary.findings" :key="index" class="finding-item">
                <span class="finding-icon">📊</span>
                <span class="finding-text">{{ finding }}</span>
              </li>
            </ul>
            <p v-else class="empty-list-message">暂无分析发现</p>
          </div>
          <div class="summary-section">
            <h3 class="section-title">改善建议</h3>
            <ul v-if="analysisSummary.suggestions.length > 0" class="suggestions-list">
              <li v-for="(suggestion, index) in analysisSummary.suggestions" :key="index" class="suggestion-item">
                <span class="suggestion-icon">💡</span>
                <span class="suggestion-text">{{ suggestion }}</span>
              </li>
            </ul>
            <p v-else class="empty-list-message">暂无改善建议</p>
          </div>
        </div>
        <div v-else class="empty-data-message">
          <div class="placeholder-icon">📝</div>
          <p class="placeholder-text">暂无足够数据生成分析摘要</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  selectedCities: {
    type: Array,
    required: true
  },
  basicStats: {
    type: Object,
    default: () => ({})
  },
  improvementStats: {
    type: Object,
    default: () => ({})
  },
  analysisSummary: {
    type: Object,
    default: () => ({ findings: [], suggestions: [] })
  },
  analysisComplete: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['export-chart']);

// 改善率视图模式
const improvementViewMode = ref('cards');

// 数值格式化
const formatValue = (value) => {
  if (value === undefined || value === null || isNaN(value)) {
    return '--';
  }
  return Number(value).toFixed(1);
};

// 设置为图表视图模式
const setChartViewMode = () => {
  improvementViewMode.value = 'chart';
  emit('render-improvement-chart');
};

// 切换改善率视图模式
const toggleImprovementView = () => {
  improvementViewMode.value = improvementViewMode.value === 'cards' ? 'list' : 'cards';
};

// 获取改善率文字描述
const getTrendText = (rate) => {
  if (!rate || isNaN(rate)) return '数据不足';
  if (rate <= -10) return '显著改善';
  if (rate < 0) return '有所改善';
  if (rate === 0) return '持平';
  if (rate <= 10) return '轻微恶化';
  return '明显恶化';
};

// 获取改善率CSS类
const getTrendClass = (rate) => {
  if (!rate || isNaN(rate)) return 'trend-neutral';
  if (rate < 0) return 'trend-good';
  if (rate > 0) return 'trend-bad';
  return 'trend-neutral';
};

// 获取改善率CSS类
const getImprovementClass = (value) => {
  if (value === undefined || value === null || isNaN(value)) {
    return '';
  }
  if (value < 0) return 'improvement-good';
  if (value > 0) return 'improvement-bad';
  return '';
};
</script>

<style scoped>
.trend-details {
  margin-bottom: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(580px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
  overflow: hidden;
}

.card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  border-bottom: 1px solid #f0f0f0;
}

.card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 500;
  color: #333;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.card-body {
  padding: 12px 15px;
}

/* 基本统计信息表格 */
.stats-table {
  width: 100%;
  overflow-x: auto;
}

.stats-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.stats-table th {
  background-color: #f5f7fa;
  padding: 8px 10px;
  text-align: left;
  font-weight: 500;
  color: #666;
  white-space: nowrap;
}

.stats-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
}

.stats-table tr:last-child td {
  border-bottom: none;
}

.quality-rate-chart-container {
  margin-top: 20px;
  border-top: 1px solid #f0f0f0;
  padding-top: 15px;
}

.quality-rate-chart {
  height: 300px !important;
  width: 100% !important;
  min-height: 250px !important;
  position: relative;
  background-color: #fff;
  overflow: hidden;
  border: 1px solid #f0f0f0;
  margin-top: 10px;
}

/* 改善情况分析 */
.improvement-card .card-body {
  padding-bottom: 8px;
}

.improvement-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.improvement-item {
  background-color: #f5f7fa;
  border-radius: 6px;
  padding: 10px;
  transition: all 0.2s;
}

.improvement-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.city-name {
  font-weight: 500;
  font-size: 14px;
  padding-bottom: 6px;
  margin-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.improvement-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  color: #666;
}

.stat-value {
  font-size: 14px;
  font-weight: 500;
}

.improvement-trend {
  display: flex;
  align-items: center;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #eee;
}

.trend-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  margin-right: 8px;
  font-size: 12px;
}

.trend-text {
  font-size: 12px;
}

.improvement-good, .trend-good {
  color: #52c41a;
}

.improvement-bad, .trend-bad {
  color: #f5222d;
}

.trend-neutral {
  color: #faad14;
}

/* 列表视图 */
.improvement-list {
  margin-bottom: 10px;
}

.improvement-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.improvement-table th {
  background-color: #f5f7fa;
  padding: 8px 10px;
  text-align: left;
  font-weight: 500;
  color: #666;
}

.improvement-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
}

.trend-indicator {
  display: flex;
  align-items: center;
}

.trend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}

.trend-dot.trend-good {
  background-color: #52c41a;
}

.trend-dot.trend-bad {
  background-color: #f5222d;
}

.trend-dot.trend-neutral {
  background-color: #faad14;
}

/* 图表视图 */
.improvement-chart-container {
  margin-top: 15px;
  display: block;
}

.improvement-chart {
  height: 300px !important;
  width: 100% !important;
  min-height: 250px !important;
  position: relative;
  background-color: #fff;
  overflow: hidden;
  border: 1px solid #f0f0f0;
  margin-top: 10px;
}

.view-toggles {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 15px;
}

.view-toggle-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background-color: white;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.view-toggle-btn:hover {
  color: #1890ff;
  border-color: #1890ff;
}

.view-toggle-btn.active {
  background-color: #1890ff;
  color: white;
  border-color: #1890ff;
}

/* 达标天数和季节性分析 */
.chart-container, .quality-rate-chart, .improvement-chart {
  height: 300px !important;
  width: 100% !important;
  min-height: 300px !important;
  border: 1px solid #e0e0e0 !important;
  margin-top: 10px;
  box-sizing: border-box;
  position: relative;
  background-color: #fff;
  overflow: hidden;
  padding: 2px;
}

/* 分析结果摘要 */
.summary-card {
  margin-bottom: 0;
}

.summary-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 12px;
  color: #333;
  border-left: 3px solid #1890ff;
  padding-left: 8px;
}

.findings-list, .suggestions-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.finding-item, .suggestion-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.finding-icon, .suggestion-icon {
  margin-right: 8px;
  font-size: 14px;
  flex-shrink: 0;
}

.empty-list-message, .empty-data-message {
  color: #999;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

.placeholder-icon {
  font-size: 24px;
  margin-bottom: 10px;
  opacity: 0.5;
}

.placeholder-text {
  font-size: 14px;
}

.improvement-toggle-btn {
  font-size: 12px;
}

.btn-outline {
  padding: 4px 8px;
  background-color: transparent;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  color: #666;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  color: #1890ff;
  border-color: #1890ff;
}

.btn-sm {
  padding: 3px 8px;
  font-size: 12px;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .summary-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .improvement-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .chart-container {
    height: 250px;
  }
}
</style> 