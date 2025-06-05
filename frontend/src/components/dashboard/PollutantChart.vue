<template>
  <el-card class="pollution-chart">
    <template #header>
      <div class="card-header">
        <span>污染物分布</span>
        <el-select 
          v-model="selectedCity" 
          placeholder="选择城市" 
          size="small"
          :disabled="loading" 
          aria-label="选择城市"
          @change="cityChanged"
        >
          <el-option
            v-for="item in cityOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </div>
    </template>
    
    <div v-if="loading" class="chart-skeleton">
      <div class="skeleton-chart">
        <div class="skeleton-bars">
          <div class="skeleton-bar" v-for="i in 6" :key="i" :style="{ width: 20 + (i*10) + '%' }"></div>
        </div>
        <div class="skeleton-axis"></div>
      </div>
    </div>
    
    <!-- 污染物图表容器部分 - 使用ref直接引用DOM -->
    <div class="chart-container" v-loading="pollutantLoading">
      <!-- 直接使用ref绑定DOM -->
      <div ref="chartDom" style="height: 380px; width: 100%;"></div>
      <div v-if="pollutantError" class="error-message">{{ pollutantError }}</div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, onUnmounted, defineProps, defineEmits, computed, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { createChart, disposeChart } from '@/utils/echartsUtil'

// 接收父组件传递的数据
const props = defineProps({
  cityOptions: {
    type: Array,
    required: true
  },
  initialCity: {
    type: String,
    default: '广州市'
  },
  cityData: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['city-change'])

// 本地状态
const selectedCity = ref(props.initialCity)
const pollutantLoading = ref(false)
const pollutantError = ref('')
// 防抖定时器
let debounceTimer = null
// 标记组件状态
const isComponentMounted = ref(false)
const isComponentBeingDestroyed = ref(false)

// DOM引用 - 直接通过ref访问DOM元素
const chartDom = ref(null)
// 图表实例引用
let chartInstance = null
// 窗口resize处理函数
const handleResize = () => {
  if (chartInstance && isComponentMounted.value && !isComponentBeingDestroyed.value) {
    chartInstance.resize()
  }
}

// 安全地创建或获取图表实例
const getChartInstance = () => {
  // 如果组件正在销毁或未挂载，不创建实例
  if (isComponentBeingDestroyed.value || !isComponentMounted.value) {
    return null
  }
  
  // 确保DOM元素存在
  if (!chartDom.value) {
    console.warn('图表DOM元素不存在')
    return null
  }
  
  try {
    // 使用工具类创建安全的图表实例
    return createChart(chartDom.value, null, { 
      renderer: 'canvas',
      useDirtyRect: true
    })
  } catch (error) {
    console.error('创建图表实例失败:', error)
    return null
  }
}

// 安全地销毁图表实例
const disposeChartInstance = () => {
  try {
    // 使用工具类安全地销毁图表实例
    if (chartDom.value) {
      disposeChart(chartDom.value)
    }
    
    if (chartInstance) {
      disposeChart(chartInstance)
      chartInstance = null
    }
  } catch (error) {
    console.error('销毁图表实例失败:', error)
  }
}

// 监听城市变化
watch(selectedCity, (newCity) => {
  cityChanged(newCity)
})

// 监听cityData变化，带防抖
watch(() => props.cityData, (newData, oldData) => {
  // 如果组件未挂载或正在销毁，不处理
  if (!isComponentMounted.value || isComponentBeingDestroyed.value) {
    return
  }
  
  // 如果数据为空，不处理
  if (!newData) {
    return
  }
  
  // 防抖处理
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    if (isComponentMounted.value && !isComponentBeingDestroyed.value) {
      renderChart()
    }
  }, 300)
}, { deep: true })

// 计算污染物图表选项
const getChartOptions = (cityData) => {
  if (!cityData) {
    return {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center'
      }
    }
  }

  // 处理数据
  const pm25Value = Number(cityData.pm25 || cityData.pm2_5 || 0)
  const pm10Value = Number(cityData.pm10 || 0)
  const so2Value = Number(cityData.so2 || 0)
  const no2Value = Number(cityData.no2 || 0)
  const o3Value = Number(cityData.o3 || 0)
  const coValue = parseFloat(cityData.co || 0)
  
  return {
    grid: {
      top: 60,
      right: 100,
      bottom: 30,
      left: 120,
      containLabel: true
    },
    title: {
      text: `${selectedCity.value}空气污染物浓度`,
      left: 'center'
    },
    tooltip: {},
    xAxis: {
      type: 'value'
    },
    yAxis: {
      type: 'category',
      data: ['PM2.5', 'PM10', 'SO2', 'NO2', 'O3', 'CO']
    },
    series: [{
      type: 'bar',
      data: [
        pm25Value,
        pm10Value,
        so2Value,
        no2Value,
        o3Value,
        coValue
      ],
      label: {
        show: true,
        position: 'right',
        formatter: function(params) {
          const units = ['μg/m³', 'μg/m³', 'μg/m³', 'μg/m³', 'μg/m³', 'mg/m³']
          return `${params.value} ${units[params.dataIndex]}`
        }
      }
    }]
  }
}

// 根据污染物值和阈值获取颜色
const getColorByValue = (value, threshold) => {
  // 如果值为0，可能是数据缺失，使用灰色
  if (value === 0) {
    return '#909399';
  }
  
  // 计算污染指数（值与阈值的比率）
  const ratio = value / threshold;
  
  if (ratio <= 0.5) {
    // 优：绿色
    return '#67C23A';
  } else if (ratio <= 1) {
    // 良：浅绿色
    return '#95D475';
  } else if (ratio <= 1.5) {
    // 轻度污染：黄色
    return '#E6A23C';
  } else if (ratio <= 2) {
    // 中度污染：橙色
    return '#F56C6C';
  } else {
    // 重度污染：红色
    return '#F56C6C';
  }
};

// 方法
const cityChanged = (newCity) => {
  emit('city-change', newCity)
}

// 重置图表
const resetChart = () => {
  // 销毁当前图表实例
  disposeChartInstance()
  
  // 确保组件挂载且未销毁
  if (isComponentMounted.value && !isComponentBeingDestroyed.value) {
    // 等待下一个DOM更新周期
    nextTick(() => {
      renderChart()
    })
  }
}

// 渲染空图表
const renderEmptyChart = () => {
  try {
    // 如果已经有图表实例，则直接使用
    if (!chartInstance && chartDom.value) {
      chartInstance = createChart(chartDom.value);
    }
    
    if (chartInstance) {
      // 设置空图表的配置
      chartInstance.setOption({
        title: {
          text: '暂无污染物数据',
          left: 'center',
          top: 'center',
          textStyle: {
            fontSize: 14,
            color: '#909399'
          }
        },
        grid: {
          left: 0,
          right: 0,
          bottom: 0,
          top: 0
        },
        xAxis: { show: false },
        yAxis: { show: false },
        series: []
      });
    }
  } catch (error) {
    console.error('渲染空图表失败:', error);
    pollutantError.value = '图表渲染失败';
  }
};

// 渲染图表
const renderChart = () => {
  if (!chartDom || !chartDom.value || isComponentBeingDestroyed.value) return;
  
  try {
    // 先销毁已有实例，防止重复初始化警告
    if (chartInstance) {
      chartInstance.dispose();
      chartInstance = null;
    }
    
    // 如果没有数据，则渲染一个空的图表
    if (!props.cityData || 
        !Object.keys(props.cityData).length || 
        !props.cityData.aqi) {
      renderEmptyChart();
      return;
    }
    
    // 确保DOM元素已经有合适的尺寸
    if (chartDom.value.clientWidth === 0 || chartDom.value.clientHeight === 0) {
      console.log('图表容器尺寸不可用，延迟渲染');
      setTimeout(renderChart, 200);
      return;
    }
    
    // 创建图表实例
    chartInstance = createChart(chartDom.value);
    
    // 准备数据
    const data = props.cityData;
    
    // 按照顺序排列污染物
    const pollutants = [
      {name: 'PM2.5', value: data.pm25 || data.pm2_5 || 0, unit: 'μg/m³', threshold: 35},
      {name: 'PM10', value: data.pm10 || 0, unit: 'μg/m³', threshold: 50},
      {name: 'NO₂', value: data.no2 || 0, unit: 'μg/m³', threshold: 40},
      {name: 'SO₂', value: data.so2 || 0, unit: 'μg/m³', threshold: 50},
      {name: 'CO', value: data.co || 0, unit: 'mg/m³', threshold: 4},
      {name: 'O₃', value: data.o3 || 0, unit: 'μg/m³', threshold: 160}
    ];
    
    // 设置图表选项
    const option = {
      title: {
        text: `${selectedCity.value || '城市'} 污染物浓度`,
        left: 'center',
        top: 0,
        textStyle: {
          fontSize: 16,
          fontWeight: 'normal'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function(params) {
          const item = params[0];
          const pollutant = pollutants[item.dataIndex];
          return `${pollutant.name}: ${pollutant.value} ${pollutant.unit}`;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '80px',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: pollutants.map(p => p.name),
        axisLabel: {
          interval: 0,
          fontSize: 12
        },
        axisTick: {
          alignWithLabel: true
        }
      },
      yAxis: {
        type: 'value',
        name: '浓度',
        nameTextStyle: {
          fontSize: 12,
          padding: [0, 0, 5, 0]
        },
        axisLabel: {
          fontSize: 12
        }
      },
      series: [
        {
          name: '污染物浓度',
          type: 'bar',
          barWidth: '60%',
          data: pollutants.map(p => ({
            value: p.value,
            itemStyle: {
              color: getColorByValue(p.value, p.threshold)
            }
          })),
          label: {
            show: true,
            position: 'top',
            formatter: function(params) {
              const index = params.dataIndex;
              return `${pollutants[index].value} ${pollutants[index].unit}`;
            }
          }
        }
      ],
      toolbox: {
        feature: {
          dataView: { show: false },
          saveAsImage: { show: true }
        },
        right: 20,
        top: 15
      }
    };
    
    // 应用选项到图表
    chartInstance.setOption(option);
    
    // 设置点击事件
    chartInstance.off('click');
  } catch (error) {
    renderEmptyChart();
  }
};

// 清理资源
onBeforeUnmount(() => {
  isComponentBeingDestroyed.value = true;
  
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
  
  if (chartDom.value && chartDom.value.__chartInstance) {
    delete chartDom.value.__chartInstance;
  }
  
  // 移除窗口resize监听
  window.removeEventListener('resize', handleResize);
  
  // 安全销毁图表
  if (chartInstance) {
    try {
      chartInstance.dispose();
      chartInstance = null;
    } catch (e) {
      // 静默处理
    }
  }
});

// 生命周期钩子
onMounted(() => {
  console.log('污染物图表组件开始挂载')
  
  // 标记组件已挂载
  isComponentMounted.value = true
  
  // 等待DOM更新完成后渲染图表
  nextTick(() => {
    // 延迟渲染以确保DOM完全就绪
    setTimeout(() => {
      if (isComponentMounted.value && !isComponentBeingDestroyed.value) {
        renderChart()
      }
    }, 300)
  })
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
  
  // 存储事件处理函数以便在卸载时移除
  window._pollutantChartResizeHandler = handleResize
})

// 在组件销毁后清理
onUnmounted(() => {
  console.log('污染物图表组件已卸载，清理图表实例')
  
  // 确保图表实例被销毁
  disposeChartInstance()
  
  // 解除引用
  chartDom.value = null
  chartInstance = null
})

// 暴露方法给父组件
defineExpose({
  renderChart,
  resetChart,
  getSelectedCity: () => selectedCity.value
})
</script> 