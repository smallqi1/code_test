<template>
  <div class="prediction-main-chart">
    <div class="main-chart-header">
      <!-- 删除了预测可视化标题 -->
      
      <!-- 增强的指标选择器 -->
      <div v-if="hasData" class="enhanced-indicator-selector">
        <div class="selector-header">
          <h3>指标选择</h3>
          <span class="selector-description">切换不同指标查看预测结果</span>
        </div>
        <div class="indicator-options">
          <div 
            v-for="indicator in availableIndicatorsWithInfo" 
            :key="indicator.value"
            class="indicator-option" 
            :class="{
              'active': selectedIndicator === indicator.value,
              'disabled': !isIndicatorAvailable(indicator.value) || chartSwitching
            }"
            @click="isIndicatorAvailable(indicator.value) && !chartSwitching && selectIndicator(indicator.value)"
            :title="
              chartSwitching ? '正在切换指标，请稍候' : 
              isIndicatorAvailable(indicator.value) ? indicator.description : '没有该指标的预测数据'
            "
          >
            <div class="indicator-icon">{{ indicator.icon }}</div>
            <div class="indicator-info">
              <div class="indicator-name">{{ indicator.label }}</div>
              <div class="indicator-desc">{{ indicator.shortDesc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 更改条件渲染逻辑，避免DOM重建 -->
    <div v-show="loading" class="chart-loading">
      <div class="loading-spinner"></div>
      <p>正在生成预测数据...</p>
    </div>
    
    <div v-show="error && !loading" class="chart-error">
      <div class="error-icon">⚠️</div>
      <p>{{ error }}</p>
    </div>
    
    <div v-show="!isIndicatorAvailable(selectedIndicator) && !loading && !error" class="chart-error">
      <div class="error-icon">ℹ️</div>
      <p>没有该指标的预测数据，请选择其他指标或重新预测</p>
    </div>
    
    <!-- 图表切换加载状态 -->
    <div v-show="chartSwitching && !loading && !error && isIndicatorAvailable(selectedIndicator)" class="chart-switching">
      <div class="switching-spinner"></div>
      <p>正在切换到 {{ getIndicatorLabel(selectedIndicator) }} 指标...</p>
    </div>
    
    <!-- 图表容器 - 始终保留在DOM中，通过v-show控制显示 -->
    <div v-show="hasData && !loading && !error && isIndicatorAvailable(selectedIndicator) && !chartSwitching" class="charts-container">
      <!-- 核心预测图表 -->
      <div class="chart-wrapper">
        <div class="chart-title">
          {{ chartTitle }}
          <span class="chart-subtitle">
            {{ startDate }} - {{ endDate }}
          </span>
        </div>
        <!-- 始终保持canvas在DOM中，通过样式控制显示/隐藏 -->
        <div class="chart-canvas-container" ref="chartContainer">
          <canvas ref="mainChart"></canvas>
        </div>
        
        <div class="chart-legend">
          <div class="legend-item">
            <span class="legend-color historical"></span>
            <span class="legend-label">历史数据</span>
          </div>
          <div class="legend-item">
            <span class="legend-color realtime"></span>
            <span class="legend-label">实时数据</span>
          </div>
          <div class="legend-item">
            <span class="legend-color forecast"></span>
            <span class="legend-label">预测数据</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 占位符内容 -->
    <div v-show="!hasData && !loading && !error" class="chart-placeholder">
      <div class="placeholder-content">
        <div class="placeholder-icon">📊</div>
        <h3>空气质量预测</h3>
        <p>选择城市和时间范围，然后点击"开始预测"查看预测结果</p>
        
        <div class="usage-guide">
          <h4>使用说明</h4>
          <ol>
            <li><strong>选择城市</strong>：点击城市选择框或搜索广东省内的特定城市</li>
            <li><strong>设置时间范围</strong>：选择需要预测的时间段
              <ul>
                <li>短期预测（高精度模式）：适合1-3天内预测，精度最高</li>
                <li>中期预测（平衡模式）：适合1周-1个月内预测，平衡精度和时间范围</li>
                <li>长期预测（趋势模式）：适合3个月-1年内预测，着重趋势判断</li>
              </ul>
            </li>
            <li><strong>选择预测模式</strong>：根据您的时间范围选择合适的预测模式</li>
            <li><strong>点击"开始预测"</strong>：获取空气质量预测结果</li>
          </ol>
          <div class="instruction-tip">
            提示：完成预测后，可以在顶部选择不同的污染物指标（AQI、PM2.5等）查看不同指标的预测结果
          </div>
        </div>
        
        <div class="steps-guide">
          <div class="step">
            <div class="step-number">1</div>
            <div class="step-text">在左侧面板选择城市</div>
          </div>
          <div class="step">
            <div class="step-number">2</div>
            <div class="step-text">选择预测时间范围</div>
          </div>
          <div class="step">
            <div class="step-number">3</div>
            <div class="step-text">选择预测模式</div>
          </div>
          <div class="step">
            <div class="step-number">4</div>
            <div class="step-text">点击"开始预测"按钮</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import Chart from 'chart.js/auto';
import { 
  LinearScale, 
  CategoryScale,
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  TimeScale 
} from 'chart.js';
import { format, addDays, parseISO } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import debounce from 'lodash/debounce';
import { getAqiLevel } from '@/utils/aqi';
// 导入Chart.js日期适配器
import 'chartjs-adapter-date-fns';

// 注册Chart.js组件
Chart.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// 核心图表状态
const chartInstance = ref(null);
const chartContainer = ref(null);
const mainChart = ref(null);
const chartSwitching = ref(false);
const isDarkMode = ref(false);

// Props定义
const props = defineProps({
  forecastData: {
    type: Object,
    default: () => null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  selectedTimePeriod: {
    type: Number,
    default: 1
  },
  selectedCity: {
    type: String,
    default: ''
  },
  selectedIndicator: {
    type: String,
    default: 'AQI'
  },
  startDate: {
    type: String,
    default: null
  },
  endDate: {
    type: String,
    default: null
  },
  periodTitle: {
    type: String,
    default: '预测'
  }
});

// 事件
const emit = defineEmits(['update:selected-indicator']);

// 计算属性
const hasData = computed(() => {
  return props.forecastData && 
         props.forecastData.indicators && 
         Object.keys(props.forecastData.indicators).length > 0;
});

// 获取当前指标的可用性
const isIndicatorAvailable = (indicator) => {
  if (!hasData.value) return false;
  
  const indicatorData = props.forecastData.indicators[indicator];
  return indicatorData && 
         indicatorData.forecast && 
         indicatorData.forecast.length > 0;
};

// 选择指标
const selectIndicator = (indicator) => {
  if (chartSwitching.value) return;
  
  if (indicator !== props.selectedIndicator) {
    chartSwitching.value = true;
    emit('update:selected-indicator', indicator);
  }
};

// 获取指标标签
const getIndicatorLabel = (indicatorKey) => {
  const mapping = {
    'PM25': 'PM2.5',
    'PM10': 'PM10',
    'O3': 'O3',
    'NO2': 'NO2',
    'SO2': 'SO2',
    'CO': 'CO',
    'AQI': 'AQI'
  };
  return mapping[indicatorKey] || indicatorKey;
};

// 图表标题
const chartTitle = computed(() => {
  const indicator = getIndicatorLabel(props.selectedIndicator);
  return `${props.selectedCity} ${indicator} ${props.periodTitle || '趋势预测'}`;
});

// 日期范围
const startDate = computed(() => {
  if (props.startDate) return props.startDate;
  
  if (hasData.value && props.selectedIndicator) {
    const data = props.forecastData.indicators[props.selectedIndicator];
    if (data && data.historical && data.historical.length > 0) {
      return format(new Date(data.historical[0].date), 'yyyy-MM-dd');
    }
  }
  return '未知日期';
});

const endDate = computed(() => {
  if (props.endDate) return props.endDate;
  
  if (hasData.value && props.selectedIndicator) {
    const data = props.forecastData.indicators[props.selectedIndicator];
    if (data && data.forecast && data.forecast.length > 0) {
      const lastItem = data.forecast[data.forecast.length - 1];
      return format(new Date(lastItem.date), 'yyyy-MM-dd');
    }
  }
  return '未知日期';
});

// 可用指标列表
const availableIndicatorsWithInfo = computed(() => {
  const indicatorInfo = [
    { value: 'AQI', label: 'AQI', icon: '🌍', shortDesc: '空气质量指数', description: '空气质量指数，综合评价各污染物的影响' },
    { value: 'PM25', label: 'PM2.5', icon: '🔬', shortDesc: '细颗粒物', description: '直径小于2.5微米的颗粒物，可深入肺部' },
    { value: 'PM10', label: 'PM10', icon: '💨', shortDesc: '可吸入颗粒物', description: '直径小于10微米的颗粒物，可吸入' },
    { value: 'O3', label: 'O3', icon: '☁️', shortDesc: '臭氧', description: '地面臭氧，强氧化性气体' },
    { value: 'NO2', label: 'NO2', icon: '🏭', shortDesc: '二氧化氮', description: '二氧化氮，刺激性气体' },
    { value: 'SO2', label: 'SO2', icon: '🌋', shortDesc: '二氧化硫', description: '二氧化硫，酸性气体' },
    { value: 'CO', label: 'CO', icon: '🚗', shortDesc: '一氧化碳', description: '一氧化碳，无色无味有毒气体' }
  ];
  
  // 自动根据可用性排序
  return indicatorInfo.sort((a, b) => {
    const aAvailable = isIndicatorAvailable(a.value);
    const bAvailable = isIndicatorAvailable(b.value);
    
    if (aAvailable && !bAvailable) return -1;
    if (!aAvailable && bAvailable) return 1;
    
    // 如果都可用或都不可用，保持原始顺序
    return 0;
  });
});

// 简化日志输出的辅助函数
const logDebug = (message, data = null) => {
  if (import.meta.env.DEV && import.meta.env.VITE_VERBOSE_LOGGING === 'true') {
    if (data) {
      console.log(message, data);
    } else {
      console.log(message);
    }
  }
};

// 图表创建和管理
const createChart = async () => {
  if (!hasData.value || !isIndicatorAvailable(props.selectedIndicator)) {
      return;
    }
    
  if (chartInstance.value) {
    chartInstance.value.destroy();
  }
  
  await nextTick();
  
  const ctx = mainChart.value.getContext('2d');
  if (!ctx) return;
  
  try {
    // 准备数据
    const currentData = props.forecastData.indicators[props.selectedIndicator];
    if (!currentData) return;
    
    const historicalData = currentData.historical || [];
    const forecastData = currentData.forecast || [];
    
    // 分离实时数据和历史数据
    const realTimeData = historicalData.filter(item => item.dataType === 'realtime');
    const pureHistoricalData = historicalData.filter(item => item.dataType === 'historical');
    
    // 合并所有数据用于计算图表范围
    const allData = [...pureHistoricalData, ...realTimeData, ...forecastData];
    
    if (allData.length === 0) return;
    
    // 确保实时数据点日期格式为当前系统日期
    if (realTimeData.length > 0) {
      const today = new Date();
      // 使用完整的日期表示，包含时区信息
      const todayStr = today.toISOString().split('T')[0];
      for (let item of realTimeData) {
        // 确保日期格式一致，使用完整的ISO日期格式
        item.date = todayStr;
        // 添加特殊标记，确保这是今天的数据点
        item.isToday = true;
      }
    }
    
    // 准备图表数据
    const chartLabels = allData.map(item => item.date);
    
    // 颜色配置
    const colors = {
      historical: isDarkMode.value ? 'rgba(87, 202, 132, 0.8)' : 'rgba(53, 162, 235, 0.8)',
      forecast: isDarkMode.value ? 'rgba(240, 173, 78, 0.8)' : 'rgba(255, 99, 132, 0.8)',
      grid: isDarkMode.value ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
    };
    
    // 用于标识不同数据类型的分段数据
    const datasets = [
      {
        label: '历史数据',
        data: pureHistoricalData
          .filter(item => item.date && item.value !== undefined && item.value !== null)
          .map(item => ({ x: item.date, y: item.value })),
        borderColor: colors.historical,
        backgroundColor: colors.historical.replace('0.8', '0.2'),
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: colors.historical,
        pointBorderColor: 'white',
        pointBorderWidth: 1,
        pointHoverRadius: 6,
        tension: 0.2,
        spanGaps: true
      },
      {
        label: '当天实时数据',
        data: realTimeData
          .filter(item => item.date && item.value !== undefined && item.value !== null)
          .map(item => {
            // 添加日志显示日期格式
            console.log('实时数据点日期:', item.date, '值:', item.value, '是否为今天:', item.isToday);
            
            // 确保日期已设置为今天
            const today = new Date();
            today.setHours(12, 0, 0, 0); // 设置为今天中午，避免时区问题
            
            // 使用当天的时间戳
            return { 
              x: today.toISOString().split('T')[0], 
              y: item.value,
              isToday: true 
            };
          }),
        borderColor: '#FF9800',
        backgroundColor: 'rgba(255, 152, 0, 0.1)',
        borderWidth: 3,
        pointRadius: 7,
        pointStyle: 'circle',
        pointBackgroundColor: '#FF9800',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointHoverRadius: 8,
        tension: 0.1,
        spanGaps: true,
        // 确保实时数据点位于最上层
        order: 0
      },
      {
        label: '预测数据',
        data: allData
          .filter(item => item.dataType === 'forecast' && item.date && item.value !== undefined && item.value !== null)
          .map(item => ({ x: item.date, y: item.value })),
        borderColor: colors.forecast,
        backgroundColor: colors.forecast.replace('0.8', '0.2'),
        borderWidth: 2,
        pointRadius: (context) => {
          const index = context.dataIndex;
          const dataPoint = context.dataset.data[index];
          if (!dataPoint) return 0;
          
          // 找到对应的原始数据项
          const originalItem = allData.find(item => 
            item.date === dataPoint.x && item.value === dataPoint.y);
            
          // 插值点显示为小圆点
          return originalItem && originalItem.interpolated ? 2 : 3;
        },
        pointBackgroundColor: colors.forecast,
        pointBorderColor: 'white',
        pointHoverRadius: 6,
        tension: 0.2,
        spanGaps: true
      }
    ];
    
    // AQI等级标识
    let aqiLevelAnnotations = {};
    if (props.selectedIndicator === 'AQI') {
      aqiLevelAnnotations = {
        annotationLines: [
          { value: 50, text: '优', color: 'rgba(0, 228, 0, 0.6)' },
          { value: 100, text: '良', color: 'rgba(255, 255, 0, 0.6)' },
          { value: 150, text: '轻度污染', color: 'rgba(255, 126, 0, 0.6)' },
          { value: 200, text: '中度污染', color: 'rgba(255, 0, 0, 0.6)' },
          { value: 300, text: '重度污染', color: 'rgba(153, 0, 76, 0.6)' }
        ]
      };
    }
    
    // 创建图表
    chartInstance.value = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartLabels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animations: {
          tension: {
            duration: 1000,
            easing: 'linear'
          }
        },
        elements: {
          point: {
            hitRadius: 10,  // 确保所有点都有hitRadius设置
            hoverRadius: 6
          },
          line: {
            tension: 0.2
          }
        },
        interaction: {
          intersect: false,  // 减少交叉点击需求
          mode: 'index'     // 索引模式更适合线图
        },
        scales: {
          x: {
            type: 'time',
            time: {
              unit: 'day',
              displayFormats: {
                day: 'MM-dd'
              },
              tooltipFormat: 'yyyy-MM-dd'
            },
            ticks: {
              maxRotation: 45,
              minRotation: 45,
              autoSkip: true,
              maxTicksLimit: 15,
              // 自定义日期显示
              callback: function(value, index, values) {
                // 确保日期正确显示
                const date = new Date(value);
                // 调试日期转换
                if (index === 0 || index === values.length - 1) {
                  console.log(`X轴刻度: 原始值=${value}, 转换后=${format(date, 'MM-dd')}, 时间戳=${date.getTime()}`);
                }
                return format(date, 'MM-dd', { locale: zhCN });
              }
            },
            // 确保日期正确解析
            parsing: false, // 禁用内置解析，使用我们自己的数据格式
            grid: {
              display: true,
              color: colors.grid
            },
            adapters: {
              date: {
                locale: zhCN
              }
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              precision: 0,
              callback: function(value) {
                return value.toFixed(0);
              }
            },
            grid: {
              display: true,
              color: colors.grid
            }
          }
        },
        plugins: {
          tooltip: {
            mode: 'index',
            intersect: false,
            callbacks: {
              title: function(tooltipItems) {
                if (!tooltipItems || !tooltipItems[0] || !tooltipItems[0].parsed || tooltipItems[0].parsed.x === undefined) {
                  return '未知日期';
                }
                const date = new Date(tooltipItems[0].parsed.x);
                return format(date, 'yyyy年MM月dd日', { locale: zhCN });
              },
              label: function(context) {
                if (!context || !context.dataset || context.parsed.y === null || context.parsed.y === undefined) {
                  return '';
                }
                
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                
                label += context.parsed.y.toFixed(1);
                
                // 为AQI添加等级说明
                if (props.selectedIndicator === 'AQI') {
                  const level = getAqiLevel(context.parsed.y);
                  if (level && level.name) {
                    label += ` (${level.name})`;
                  }
                }
                
                // 尝试找到对应的原始数据点
                if (context.datasetIndex !== undefined && context.dataIndex !== undefined) {
                  const datasetData = context.chart.data.datasets[context.datasetIndex].data;
                  if (datasetData && datasetData[context.dataIndex]) {
                    const dataPoint = datasetData[context.dataIndex];
                    // 找到对应的原始数据点
                    const originalPoint = allData.find(item => 
                      item.date === dataPoint.x && 
                      item.value === dataPoint.y);
                    
                    if (originalPoint) {
                      if (originalPoint.dataType === 'realtime') {
                        label += ' [实时数据]';
                      } else if (originalPoint.dataType === 'historical') {
                        label += ' [历史]';
                      } else if (originalPoint.interpolated) {
                        label += ' [插值]';
                      }
                    }
                  }
                }
                
                return label;
              }
            }
          },
          annotation: {
            annotations: {
              // 添加AQI等级线条
              ...aqiLevelAnnotations.annotationLines?.reduce((acc, line) => {
                acc[`line-${line.value}`] = {
                  type: 'line',
                  yMin: line.value,
                  yMax: line.value,
                  borderColor: line.color,
                  borderWidth: 1,
                  borderDash: [6, 2],
                  label: {
                    content: line.text,
                    enabled: true,
                    position: 'end',
                    backgroundColor: line.color
                  }
                };
                return acc;
              }, {})
            }
          }
        }
      }
    });
    
    // 重置切换状态
    chartSwitching.value = false;
  } catch (error) {
    console.error('创建图表失败:', error);
    chartSwitching.value = false;
  }
};

// 安全销毁和重建图表
const safeDestroyAndRebuildChart = debounce(async () => {
  try {
    // 销毁现有图表
    if (chartInstance.value) {
        chartInstance.value.destroy();
        chartInstance.value = null;
    }
    
    // 短延迟后重建
    await new Promise(resolve => setTimeout(resolve, 100));
    await createChart();
  } catch (error) {
    console.error('图表重建失败:', error);
  } finally {
    chartSwitching.value = false;
      }
    }, 300);

// 监听属性变化
watch(() => props.forecastData, (newVal) => {
  if (newVal) {
    safeDestroyAndRebuildChart();
  }
}, { deep: true });

watch(() => props.selectedIndicator, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    chartSwitching.value = true;
    safeDestroyAndRebuildChart();
  }
});

// 监听深色模式变化
const updateColorScheme = () => {
  // 检测深色模式
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  isDarkMode.value = prefersDark;
  
  // 如果图表已存在，重建以适应新颜色方案
  if (chartInstance.value) {
    safeDestroyAndRebuildChart();
  }
};

// 窗口大小变化处理
const handleResize = debounce(() => {
  if (chartInstance.value) {
    chartInstance.value.resize();
  }
}, 200);

// 生命周期钩子
onMounted(() => {
  // 设置颜色方案监听
  updateColorScheme();
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateColorScheme);
  
  // 设置窗口大小监听
  window.addEventListener('resize', handleResize);
  
  // 初始化图表 (如果有数据)
  if (hasData.value && isIndicatorAvailable(props.selectedIndicator)) {
    createChart();
  }
});

onBeforeUnmount(() => {
  // 移除事件监听器
  window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', updateColorScheme);
  window.removeEventListener('resize', handleResize);
  
  // 销毁图表
  if (chartInstance.value) {
    chartInstance.value.destroy();
    chartInstance.value = null;
  }
});
</script>

<style scoped>
.prediction-main-chart {
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  padding: 15px;
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.main-chart-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 10px;
}

.panel-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 600;
  color: #333;
  margin-right: auto;
}

/* 指标选择器的样式调整 */
.enhanced-indicator-selector {
  flex: 1;
  max-width: 100%;
}

.selector-header {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.selector-header h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  margin-right: 10px;
  color: #555;
}

.selector-description {
  font-size: 0.8rem;
  color: #888;
}

.indicator-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-start;
}

.indicator-option {
  display: flex;
  align-items: center;
  padding: 5px 10px;
  background-color: #f5f7fa;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  flex: 0 0 auto;
}

.indicator-option:hover {
  background-color: #e8f0fe;
  transform: translateY(-1px);
}

.indicator-option.active {
  background-color: #e1f0ff;
  border-color: #4389cf;
  box-shadow: 0 1px 4px rgba(67, 137, 207, 0.2);
}

.indicator-option.disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #f0f0f0;
  pointer-events: none;  /* 完全禁用点击 */
}

.indicator-option.disabled:hover {
  transform: none;
}

.indicator-icon {
  margin-right: 6px;
  font-size: 1.1rem;
}

.indicator-info {
  display: flex;
  flex-direction: column;
}

.indicator-name {
  font-weight: 600;
  font-size: 0.85rem;
  color: #333;
}

.indicator-desc {
  font-size: 0.7rem;
  color: #777;
}

/* 其余样式保持不变 */
.charts-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  height: 550px; /* 设置固定总高度 */
  flex-grow: 1;
  overflow: hidden;
}

/* 统一图表容器尺寸 */
.chart-wrapper {
  background: #fff;
  border-radius: 8px;
  padding: 10px;
  flex: 2;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.05);
  min-height: 350px; /* 增加最小高度，确保图表尺寸一致 */
  height: 350px; /* 添加固定高度 */
}

.chart-title {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-subtitle {
  font-size: 0.8rem;
  color: #666;
  font-weight: normal;
}

.chart-canvas-container {
  flex-grow: 1;
  position: relative;
  width: 100%;
  height: 280px; /* 固定画布高度 */
  min-height: 280px;
}

.chart-legend {
  display: flex;
  justify-content: center;
  margin-top: 10px;
  gap: 15px;
}

.legend-item {
  display: flex;
  align-items: center;
  font-size: 0.8rem;
  color: #666;
}

.legend-color {
  width: 12px;
  height: 12px;
  margin-right: 5px;
  border-radius: 2px;
}

.legend-color.historical {
  background-color: #1890ff;
}

.legend-color.realtime {
  background-color: #FF9800;
}

.legend-color.forecast {
  background-color: #52c41a;
}

/* 占位符内容样式 */
.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  flex-grow: 1;
}

.placeholder-content {
  text-align: center;
  max-width: 600px;
  color: #666;
}

.placeholder-icon {
  font-size: 3rem;
  margin-bottom: 20px;
  color: #ccc;
}

.placeholder-content h3 {
  font-size: 1.5rem;
  margin-bottom: 10px;
  color: #333;
}

.placeholder-content p {
  font-size: 1rem;
  margin-bottom: 20px;
}

/* 使用指南样式 */
.usage-guide {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  margin: 20px 0;
  text-align: left;
}

.usage-guide h4 {
  font-size: 1.1rem;
  margin-bottom: 10px;
  color: #333;
}

.usage-guide ol {
  padding-left: 20px;
  margin-bottom: 10px;
}

.usage-guide li {
  margin-bottom: 8px;
}

.usage-guide ul {
  padding-left: 20px;
  margin-top: 5px;
}

.usage-guide ul li {
  margin-bottom: 5px;
  font-size: 0.9rem;
  color: #555;
}

.steps-guide {
  display: flex;
  justify-content: space-around;
  margin-top: 20px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 150px;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: #4389cf;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 8px;
}

.step-text {
  text-align: center;
  font-size: 0.9rem;
  color: #555;
}

.instruction-tip {
  background-color: #fff9e3;
  border-left: 3px solid #ffd666;
  padding: 10px;
  margin-top: 15px;
  font-size: 0.85rem;
  color: #d48806;
}

/* 加载和错误状态 */
.chart-loading,
.chart-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  flex-grow: 1;
}

.loading-spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #4389cf;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.chart-loading p {
  color: #666;
}

.chart-error {
  color: #ff4d4f;
}

.error-icon {
  font-size: 2rem;
  margin-bottom: 10px;
}

.chart-error p {
  font-size: 1rem;
  max-width: 500px;
  text-align: center;
}

/* 添加图表切换加载样式 */
.chart-switching {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  flex-grow: 1;
  background-color: rgba(255, 255, 255, 0.9);
}

.switching-spinner {
  border: 4px solid rgba(67, 137, 207, 0.2);
  border-left-color: #4389cf;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

.chart-switching p {
  color: #4389cf;
  font-weight: 500;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style> 