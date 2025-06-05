<template>
  <div class="prediction-control-panel">
    <div class="control-panel-card">
      <div class="panel-content-grid">
        <!-- 城市选择模块 -->
        <div class="control-module city-module">
          <div class="module-header">
            <div class="header-icon">📍</div>
            <h3>城市选择</h3>
          </div>
          <div class="city-selector">
            <div class="selector-display" @click="toggleCityDropdown">
              <span class="city-name">{{ selectedCity }}</span>
              <span class="selector-icon">{{ showCityDropdown ? '▲' : '▼' }}</span>
            </div>
            <input 
              type="text" 
              class="search-input" 
              placeholder="搜索城市..." 
              v-model="citySearchText"
              @focus="showCityDropdown = true"
              @input="onCitySearch"
            />
            
            <div v-if="showCityDropdown" class="dropdown-panel">
              <div class="dropdown-header">
                <span>广东省城市</span>
                <button class="close-btn" @click="showCityDropdown = false">×</button>
              </div>
              <div v-if="filteredCities.length === 0" class="empty-message">
                未找到匹配的城市
              </div>
              <div v-else class="dropdown-options">
                <div
                  v-for="city in filteredCities"
                  :key="city"
                  class="option-item"
                  :class="{ active: city === selectedCity }"
                  @click="selectCity(city)"
                >
                  {{ city }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 时间预测范围模块 -->
        <div class="control-module time-module">
          <div class="module-header">
            <div class="header-icon">🕒</div>
            <h3>时间预测范围</h3>
          </div>
          
          <div class="time-range-groups">
            <!-- 短期预测 -->
            <div class="time-group">
              <div class="group-label">
                短期预测
                <span class="tag high-tag">高精度</span>
              </div>
              <div class="range-buttons">
                <button 
                  v-for="period in shortTermPeriods" 
                  :key="period.value"
                  class="range-btn short"
                  :class="{ active: selectedTimePeriod === period.value }"
                  @click="onlySelectTimePeriod(period.value)"
                >
                  {{ period.label }}
                </button>
              </div>
            </div>
            
            <!-- 中期预测 -->
            <div class="time-group">
              <div class="group-label">
                中期预测
                <span class="tag medium-tag">平衡型</span>
              </div>
              <div class="range-buttons">
                <button 
                  v-for="period in mediumTermPeriods" 
                  :key="period.value"
                  class="range-btn medium"
                  :class="{ active: selectedTimePeriod === period.value }"
                  @click="onlySelectTimePeriod(period.value)"
                >
                  {{ period.label }}
                </button>
              </div>
            </div>
            
            <!-- 长期预测 -->
            <div class="time-group">
              <div class="group-label">
                长期预测
                <span class="tag long-tag">趋势型</span>
              </div>
              <div class="range-buttons">
                <button 
                  v-for="period in longTermPeriods" 
                  :key="period.value"
                  class="range-btn long"
                  :class="{ active: selectedTimePeriod === period.value }"
                  @click="onlySelectTimePeriod(period.value)"
                >
                  {{ period.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 预测模式选择模块 -->
        <div class="control-module mode-module">
          <div class="module-header">
            <div class="header-icon">⚙️</div>
            <h3>预测模式</h3>
          </div>
          
          <div class="mode-options">
            <div 
              class="mode-option"
              :class="{ active: selectedMode === 'high_precision' }"
              @click="selectMode('high_precision')"
            >
              <div class="option-check">
                <div class="check-indicator"></div>
              </div>
              <div class="option-content">
                <div class="option-title">高精度模式</div>
                <div class="option-desc">适用于短期预测（1-3天），精度最高</div>
              </div>
            </div>
            
            <div 
              class="mode-option"
              :class="{ active: selectedMode === 'balanced' }"
              @click="selectMode('balanced')"
            >
              <div class="option-check">
                <div class="check-indicator"></div>
              </div>
              <div class="option-content">
                <div class="option-title">平衡模式</div>
                <div class="option-desc">适用于中期预测（1周-1个月），平衡精度与范围</div>
              </div>
            </div>
            
            <div 
              class="mode-option"
              :class="{ active: selectedMode === 'trend' }"
              @click="selectMode('trend')"
            >
              <div class="option-check">
                <div class="check-indicator"></div>
              </div>
              <div class="option-content">
                <div class="option-title">趋势模式</div>
                <div class="option-desc">适用于长期预测（3个月-1年），关注整体趋势</div>
                <div class="option-warning">仅供参考，实际误差可能超过30%</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 预测控制区域 -->
      <div class="prediction-action-area">
        <!-- 预测进度条 -->
        <div class="prediction-progress" v-if="loading">
          <div class="progress-info">
            <div class="progress-step">{{ predictionStepText }}</div>
            <div class="progress-percentage">{{ Math.round(predictionProgress) }}%</div>
          </div>
          <div class="progress-bar-container">
            <div 
              class="progress-bar" 
              :style="{ width: `${predictionProgress}%` }"
              :class="{ 
                'preparing': predictionProgress < 20,
                'loading': predictionProgress >= 20 && predictionProgress < 40,
                'predicting': predictionProgress >= 40 && predictionProgress < 60,
                'processing': predictionProgress >= 60 && predictionProgress < 80,
                'finishing': predictionProgress >= 80 && predictionProgress < 100,
                'completed': predictionProgress >= 100
              }"
            ></div>
          </div>
          <div class="status-message" :class="statusType">{{ statusMessage }}</div>
        </div>
        
        <!-- 预测按钮 -->
        <button 
          class="predict-button" 
          :class="{ 'loading': loading }"
          @click="startPrediction"
          :disabled="loading"
        >
          <span class="button-icon">{{ loading ? '⏳' : '🚀' }}</span>
          <span class="button-text">{{ loading ? '预测中...' : '开始预测' }}</span>
        </button>
      </div>

      <!-- 状态消息 -->
      <div v-if="statusMessage" class="status-message" :class="statusType">
        <div class="status-icon">
          <span v-if="statusType === 'error'">⚠️</span>
          <span v-else-if="statusType === 'success'">✅</span>
          <span v-else>ℹ️</span>
        </div>
        <div class="status-text">{{ statusMessage }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';

// 定义props
const props = defineProps({
  cities: {
    type: Array,
    default: () => []
  },
  selectedCity: {
    type: String,
    default: '广州'
  },
  selectedTimePeriod: {
    type: Number,
    default: 7
  },
  selectedMode: {
    type: String,
    default: 'balanced'
  },
  loading: {
    type: Boolean,
    default: false
  },
  predictionProgress: {
    type: Number,
    default: 0
  },
  predictionStepText: {
    type: String,
    default: ''
  },
  statusMessage: {
    type: String,
    default: ''
  },
  statusType: {
    type: String,
    default: 'info'
  }
});

// 定义事件
const emit = defineEmits([
  'update:selectedCity', 
  'update:selectedTimePeriod', 
  'update:selectedMode',
  'update:timePeriodType',
  'startPrediction'
]);

// 城市选择相关
const showCityDropdown = ref(false);
const citySearchText = ref('');

const filteredCities = computed(() => {
  if (!citySearchText.value) {
    return props.cities;
  }
  
  const searchText = citySearchText.value.toLowerCase();
  return props.cities.filter(city => 
    city.toLowerCase().includes(searchText)
  );
});

function toggleCityDropdown() {
  showCityDropdown.value = !showCityDropdown.value;
}

function onCitySearch() {
  showCityDropdown.value = true;
}

function selectCity(city) {
  emit('update:selectedCity', city);
  showCityDropdown.value = false;
  citySearchText.value = '';
}

// 预测时间范围相关
const shortTermPeriods = [
  { value: 1, label: '1天' },
  { value: 2, label: '2天' },
  { value: 3, label: '3天' }
];

const mediumTermPeriods = [
  { value: 7, label: '7天' },
  { value: 14, label: '14天' },
  { value: 30, label: '30天' }
];

const longTermPeriods = [
  { value: 90, label: '3个月' },
  { value: 180, label: '6个月' },
  { value: 365, label: '1年' }
];

function onlySelectTimePeriod(days) {
  if (days === props.selectedTimePeriod) return;
  
  emit('update:selectedTimePeriod', days);
  
  // 更新时间周期类型
  if (days <= 3) {
    emit('update:timePeriodType', 'short');
  } else if (days <= 30) {
    emit('update:timePeriodType', 'medium');
  } else {
    emit('update:timePeriodType', 'long');
  }
  
  // 推荐预测模式
  if (days <= 3 && props.selectedMode !== 'high_precision') {
    emit('update:selectedMode', 'high_precision');
  } else if (days <= 30 && days > 3 && props.selectedMode !== 'balanced') {
    emit('update:selectedMode', 'balanced');
  } else if (days > 30 && props.selectedMode !== 'trend') {
    emit('update:selectedMode', 'trend');
  }
}

// 预测模式选择
function selectMode(mode) {
  if (mode === props.selectedMode) return;
  emit('update:selectedMode', mode);
}

// 开始预测
function startPrediction() {
  if (props.loading) return;
  emit('startPrediction');
}

// 点击面板外部关闭下拉菜单
function closeDropdownOnOutsideClick(event) {
  if (showCityDropdown.value) {
    const dropdown = document.querySelector('.city-selector');
    if (dropdown && !dropdown.contains(event.target)) {
      showCityDropdown.value = false;
    }
  }
}

// 添加和移除事件监听器
onMounted(() => {
  document.addEventListener('click', closeDropdownOnOutsideClick);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', closeDropdownOnOutsideClick);
});

// 初始化时间周期类型
onMounted(() => {
  // 根据初始天数设置时间周期类型
  if (props.selectedTimePeriod <= 3) {
    emit('update:timePeriodType', 'short');
  } else if (props.selectedTimePeriod <= 30) {
    emit('update:timePeriodType', 'medium');
  } else {
    emit('update:timePeriodType', 'long');
  }
});
</script>

<style scoped>
.prediction-control-panel {
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.control-panel-card {
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.06);
  padding: 20px;
  transition: all 0.3s ease;
}

/* 网格布局 */
.panel-content-grid {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

/* 模块通用样式 */
.control-module {
  background-color: #f8f9fa;
  border-radius: 10px;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.module-header {
  display: flex;
  align-items: center;
  margin-bottom: 14px;
}

.header-icon {
  font-size: 16px;
  margin-right: 8px;
}

.module-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

/* 城市选择模块 */
.city-selector {
  position: relative;
}

.selector-display {
  background-color: #ffffff;
  border: 1px solid #e0e4e8;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  margin-bottom: 10px;
  transition: all 0.2s;
}

.selector-display:hover {
  border-color: #c0c6cc;
}

.city-name {
  font-weight: 500;
  color: #333;
}

.selector-icon {
  color: #888;
  font-size: 12px;
}

.search-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e0e4e8;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
}

.search-input:focus {
  border-color: #4389cf;
  outline: none;
  box-shadow: 0 0 0 2px rgba(67, 137, 207, 0.1);
}

.dropdown-panel {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e0e4e8;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  margin-top: 5px;
  overflow: hidden;
}

.dropdown-header {
  padding: 10px 12px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e0e4e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #555;
}

.empty-message {
  padding: 12px;
  text-align: center;
  color: #888;
  font-size: 14px;
}

.dropdown-options {
  max-height: 200px;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 5px;
  padding: 10px;
}

.option-item {
  padding: 8px 12px;
  text-align: center;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.option-item:hover {
  background-color: #f0f7ff;
}

.option-item.active {
  background-color: #e1f0ff;
  color: #1890ff;
  font-weight: 500;
}

/* 时间预测范围样式 */
.time-range-groups {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.time-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.group-label {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  display: flex;
  align-items: center;
}

.tag {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 12px;
  margin-left: 8px;
  font-weight: normal;
}

.high-tag {
  background-color: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}

.medium-tag {
  background-color: rgba(250, 173, 20, 0.1);
  color: #faad14;
}

.long-tag {
  background-color: rgba(245, 34, 45, 0.1);
  color: #f5222d;
}

.range-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.range-btn {
  padding: 8px 0;
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 14px;
  font-weight: normal;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  background-color: #fff;
}

.range-btn:hover {
  transform: translateY(-1px);
}

.range-btn.short {
  border-color: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.range-btn.medium {
  border-color: rgba(250, 173, 20, 0.2);
  color: #faad14;
}

.range-btn.long {
  border-color: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.range-btn.active {
  font-weight: 500;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.range-btn.short.active {
  background-color: #52c41a;
  border-color: #52c41a;
  color: white;
}

.range-btn.medium.active {
  background-color: #faad14;
  border-color: #faad14;
  color: white;
}

.range-btn.long.active {
  background-color: #f5222d;
  border-color: #f5222d;
  color: white;
}

/* 预测模式模块 */
.mode-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mode-option {
  display: flex;
  align-items: flex-start;
  padding: 12px;
  border-radius: 8px;
  background-color: #fff;
  transition: all 0.2s;
  cursor: pointer;
  border: 1px solid #e0e4e8;
}

.mode-option:hover {
  background-color: #f5f7fa;
}

.mode-option.active {
  border-color: #1890ff;
  background-color: #e6f7ff;
}

.option-check {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #d9d9d9;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  margin-top: 2px;
  flex-shrink: 0;
}

.mode-option.active .option-check {
  border-color: #1890ff;
}

.check-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: transparent;
  transition: all 0.2s;
}

.mode-option.active .check-indicator {
  background-color: #1890ff;
}

.option-content {
  flex-grow: 1;
}

.option-title {
  font-weight: 500;
  margin-bottom: 4px;
  color: #333;
  font-size: 14px;
}

.option-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.option-warning {
  font-size: 12px;
  color: #f5222d;
  margin-top: 4px;
}

/* 预测控制区域 */
.prediction-action-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 16px;
}

.predict-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1890ff;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0 28px;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.3);
  position: relative;
  overflow: hidden;
  margin-top: 16px;
  width: 180px;
}

.predict-button:hover {
  background-color: #40a9ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.4);
}

.predict-button:active {
  background-color: #096dd9;
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.predict-button:disabled {
  background-color: #d9d9d9;
  color: rgba(0, 0, 0, 0.25);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.predict-button.loading {
  background-color: #1890ff;
  opacity: 0.8;
  cursor: default;
}

.predict-button.loading::after {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg, 
    rgba(255, 255, 255, 0) 0%, 
    rgba(255, 255, 255, 0.2) 50%, 
    rgba(255, 255, 255, 0) 100%
  );
  animation: loading-shine 1.5s infinite;
}

@keyframes loading-shine {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.button-icon {
  margin-right: 10px;
  font-size: 18px;
}

/* 状态消息 */
.status-message {
  margin-top: 8px;
  font-size: 14px;
  color: #595959;
  text-align: center;
}

.status-message.success {
  color: #52c41a;
}

.status-message.error {
  color: #f5222d;
}

.status-message.warning {
  color: #faad14;
}

.status-message.info {
  color: #1890ff;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .panel-content-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .mode-module {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .panel-content-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .mode-module {
    grid-column: span 1;
  }
  
  .control-panel-card {
    padding: 16px;
  }
}

/* 进度条样式 */
.prediction-progress {
  margin-top: 16px;
  margin-bottom: 10px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.progress-step {
  font-weight: 500;
  color: #1890ff;
}

.progress-percentage {
  color: #595959;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background-color: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  height: 100%;
  background-color: #1890ff;
  border-radius: 4px;
  transition: width 0.3s ease-in-out;
  position: relative;
  overflow: hidden;
}

.progress-bar::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  right: 0;
  background-image: linear-gradient(
    -45deg,
    rgba(255, 255, 255, 0.2) 25%,
    transparent 25%,
    transparent 50%,
    rgba(255, 255, 255, 0.2) 50%,
    rgba(255, 255, 255, 0.2) 75%,
    transparent 75%,
    transparent
  );
  background-size: 30px 30px;
  animation: progress-animation 2s linear infinite;
  z-index: 1;
}

@keyframes progress-animation {
  0% {
    background-position: 0 0;
  }
  100% {
    background-position: 30px 0;
  }
}

/* 不同阶段颜色 */
.progress-bar.preparing {
  background-color: #faad14;
}

.progress-bar.loading {
  background-color: #1890ff;
}

.progress-bar.predicting {
  background-color: #722ed1;
}

.progress-bar.processing {
  background-color: #13c2c2;
}

.progress-bar.finishing, 
.progress-bar.completed {
  background-color: #52c41a;
}
</style> 