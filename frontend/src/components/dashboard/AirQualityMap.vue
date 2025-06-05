<template>
  <el-card class="map-container" shadow="hover">
    <template #header>
      <div class="card-header map-header">
        <div class="header-left">
          <span><i class="header-icon">🗺️</i> 空气质量分布</span>
        </div>
        <div class="header-controls">
          <!-- 地图类型切换 -->
          <el-dropdown trigger="click" @command="handleMapTypeChange" class="map-type-dropdown">
            <el-button size="default" type="primary" class="map-btn aqi-btn">
              {{ mapTypeLabel }} <el-icon><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="aqi">AQI 指数</el-dropdown-item>
                <el-dropdown-item command="pm25">PM2.5</el-dropdown-item>
                <el-dropdown-item command="pm10">PM10</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <!-- 水平排列的控制按钮组 -->
          <div class="map-control-group">
            <el-button-group>
              <el-tooltip content="放大" placement="top">
                <el-button @click="zoomMap" size="default" type="default" class="map-btn control-btn">
                  <el-icon><ZoomIn /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="缩小" placement="top">
                <el-button @click="zoomOutMap" size="default" type="default" class="map-btn control-btn">
                  <el-icon><ZoomOut /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="重置视图" placement="top">
                <el-button @click="resetMapView" size="default" type="default" class="map-btn control-btn">
                  <el-icon><Position /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="刷新数据" placement="top">
                <el-button @click="refreshMap" size="default" type="default" class="map-btn control-btn">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </el-tooltip>
            </el-button-group>
          </div>
        </div>
      </div>
    </template>
    
    <!-- 添加占位背景地图，解决初始闪烁问题 -->
    <div class="placeholder-map" v-if="showPlaceholder">
      <!-- 使用静态背景图作为占位，确保广州显示预定义颜色 -->
      <div class="placeholder-text">加载中...</div>
    </div>
    
    <div id="gdMap" class="map-chart" :style="{ visibility: showPlaceholder ? 'hidden' : 'visible' }"></div>
    
    <div v-if="provinceError" class="error-message">
      {{ provinceError }}
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, onBeforeUnmount, defineProps, defineEmits, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Refresh, ZoomIn, ZoomOut, ArrowDown, Position } from '@element-plus/icons-vue'
import { createChart, disposeChart } from '@/utils/echartsUtil'

const props = defineProps({
  provinceData: {
    type: Array,
    required: true
  },
  provinceError: {
    type: String,
    default: ''
  },
  isProvinceLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh-map', 'reset-view', 'zoom-map', 'zoom-out-map', 'map-type-change', 'city-click'])

// 图表实例
const chart = ref(null)
const mapLoaded = ref(false)
const currentMapType = ref('aqi')
const showPlaceholder = ref(true) // 默认显示占位图

// 计算属性 - 将当前地图类型转换为显示标签
const mapTypeLabel = computed(() => {
  const labels = {
    'aqi': 'AQI 指数',
    'pm25': 'PM2.5',
    'pm10': 'PM10'
  };
  return labels[currentMapType.value] || 'AQI 指数';
});

// 组件状态标记
const isComponentMounted = ref(false)
const isComponentBeingDestroyed = ref(false)
const isInitialRenderComplete = ref(false)
let initialRenderTimer = null

// 为地图组件设置缩放当前比例
let currentZoomLevel = 1.2; // 默认稍微放大一点，以便更好地展示地图

// 预处理数据，确保不会有空白点
const preProcessData = (data) => {
  if (!data || data.length === 0) return [];
  
  return data.map(city => {
    // 基础数据
    const result = {
      name: city.name,
      value: city.aqi || 0,
      aqi: city.aqi || 0,
      pm25: city.pm25 || city.pm2_5 || 0,
      pm10: city.pm10 || 0,
      level: city.level || '优'
    };
    
    // 确保每个城市都有合理的默认值
    if (result.aqi === 0 || result.aqi === null || result.aqi === undefined) {
      result.aqi = 30; // 默认良好
      result.value = 30;
    }
    
    if (result.pm25 === 0 || result.pm25 === null || result.pm25 === undefined) {
      result.pm25 = 15;
    }
    
    if (result.pm10 === 0 || result.pm10 === null || result.pm10 === undefined) {
      result.pm10 = 25;
    }
    
    // 广州市特殊处理，确保始终有值
    if (city.name === '广州市') {
      result.value = Math.max(30, result.value); // 确保至少为30
      result.aqi = Math.max(30, result.aqi);
      result.pm25 = Math.max(15, result.pm25);
      result.pm10 = Math.max(25, result.pm10);
    }
    
    return result;
  });
};

// 更高效的预渲染方法 - 大幅简化
const preRenderMap = () => {
  const mapElement = document.getElementById('gdMap');
  if (!mapElement) return;
  
  try {
    // 创建实例并保存
    chart.value = createChart(mapElement);
    
    // 立即隐藏加载指示器
    showPlaceholder.value = false;
  } catch (e) {}
};

// 监听数据变化，更新地图
watch(() => props.provinceData, (newData) => {
  if (newData && newData.length > 0) {
    nextTick(() => renderMap(newData))
  }
}, { deep: true })

// 确保标签始终显示的帮助函数
const ensureLabelsShown = () => {
  if (!chart.value) return;
  
  try {
    chart.value.setOption({
      series: [{
        label: {
          show: true,
          color: '#333',
          fontSize: 10
        }
      }]
    }, false);
  } catch (e) {}
}

// 高效地更新地图数据
const updateMapData = (mapData) => {
  if (!chart.value) return;
  
  // 只更新数据部分
  chart.value.setOption({
    series: [{
      data: mapData
    }]
  });
}

// 刷新地图数据
const refreshMap = () => {
  emit('refresh-map');
  
  if (!chart.value || !props.provinceData?.length) return;
  
  // 预处理数据
  const mapData = preProcessData(props.provinceData);
  
  // 根据当前类型设置值
  if (currentMapType.value !== 'aqi') {
    const valueField = currentMapType.value === 'pm25' ? 'pm25' : 'pm10';
    mapData.forEach(item => {
      item.value = item[valueField] || 0;
    });
  }
  
  // 更新地图数据
  updateMapData(mapData);
}

// 检查实例是否有效
const isChartValid = () => {
  return chart.value && 
         typeof chart.value.setOption === 'function' && 
         !chart.value.isDisposed?.();
}

// 渲染地图前的安全检查
const ensureChartInstance = () => {
  const mapElement = document.getElementById('gdMap')
  if (!mapElement) return false
  
  if (!isChartValid()) {
    try {
      chart.value = createChart(mapElement)
      return isChartValid()
    } catch (e) {
      return false
    }
  }
  
  return true
}

// 安全地应用设置
const safeSetOption = (partialOption, notMerge = false) => {
  if (!isChartValid()) {
    if (!ensureChartInstance()) {
      return false;
    }
  }
  
  try {
    chart.value.setOption(partialOption, notMerge);
    return true;
  } catch (e) {
    return false;
  }
}

// 直接修改zoom值的高性能函数
const updateZoom = (newZoom) => {
  if (!chart.value) return;
  currentZoomLevel = newZoom;
  
  try {
    // 完整更新缩放配置
    chart.value.setOption({
      series: [{
        zoom: newZoom,
        center: null // 清除中心点限制，允许自由缩放
      }]
    });
    
    // 确保标签在缩放后仍然可见
    setTimeout(() => ensureLabelsShown(), 100);
  } catch (e) {
    console.error('地图缩放失败:', e);
  }
}

const resetMapView = () => {
  emit('reset-view');
  // 重置视图时完全重新渲染地图
  if (props.provinceData?.length) {
    currentZoomLevel = 1.2; // 重置到默认缩放级别
    renderMap(props.provinceData, false);
  }
}

const zoomMap = () => {
  emit('zoom-map');
  const newZoom = Math.min(currentZoomLevel + 0.3, 3);
  updateZoom(newZoom);
}

const zoomOutMap = () => {
  emit('zoom-out-map');
  const newZoom = Math.max(currentZoomLevel - 0.3, 0.7);
  updateZoom(newZoom);
}

// 处理地图类型切换
const handleMapTypeChange = (type) => {
  if (type === currentMapType.value) return;
  
  currentMapType.value = type;
  emit('map-type-change', type);
  
  // 如果没有数据则不处理
  if (!props.provinceData?.length) return;
  
  // 更新数据
  const mapData = preProcessData(props.provinceData);
  
  // 根据类型设置值字段
  if (type !== 'aqi') {
    const valueField = type === 'pm25' ? 'pm25' : 'pm10';
    mapData.forEach(item => {
      item.value = item[valueField] || 0;
    });
  }
  
  // 更新地图数据
  updateMapData(mapData);
}

// 渲染地图的方法 - 高度优化版本
const renderMap = (data, firstRender = false) => {
  if (!data?.length || !isComponentMounted.value) return;
  
  try {
    // 获取地图DOM元素
    const mapElement = document.getElementById('gdMap');
    if (!mapElement) return;
    
    // 检查DOM元素尺寸
    if (mapElement.clientWidth === 0 || mapElement.clientHeight === 0) {
      console.warn('地图容器尺寸不可用，延迟渲染');
      setTimeout(() => renderMap(data, firstRender), 200);
      return;
    }
    
    // 确保旧实例被清理
    if (chart.value) {
      chart.value.dispose();
      chart.value = null;
    }
    
    // 创建新的图表实例
    chart.value = createChart(mapElement);
    if (!chart.value) return;
    
    // 预处理数据
    const mapData = preProcessData(data);
    
    // 根据类型设置值
    if (currentMapType.value !== 'aqi') {
      const valueField = currentMapType.value === 'pm25' ? 'pm25' : 'pm10';
      mapData.forEach(item => item.value = item[valueField] || 0);
    }
    
    // 构建选项对象
    const option = {
      backgroundColor: 'transparent',
      title: {
        text: '广东省空气质量实时监测',
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          if (!params.data) return '无数据';
          return `${params.name}<br/>
                 AQI: ${params.data.aqi}<br/>
                 PM2.5: ${params.data.pm25} μg/m³<br/>
                 PM10: ${params.data.pm10} μg/m³<br/>
                 空气质量: ${params.data.level}`;
        }
      },
      visualMap: {
        type: 'piecewise',
        pieces: [
          {min: 0, max: 50, label: '优', color: '#1e9e40'},
          {min: 51, max: 100, label: '良', color: '#95cd56'},
          {min: 101, max: 150, label: '轻度', color: '#ffde33'},
          {min: 151, max: 200, label: '中度', color: '#ff9933'}, 
          {min: 201, max: 300, label: '重度', color: '#cc0033'},
          {min: 301, max: 500, label: '严重', color: '#660099'}
        ],
        realtime: false,
        textStyle: {color: '#333'},
        left: 'left',
        top: 'bottom'
      },
      series: [{
        name: '广东省空气质量',
        type: 'map',
        map: 'guangdong',
        roam: true, // 启用地图拖动和缩放
        zoom: currentZoomLevel,
        scaleLimit: {min: 0.7, max: 3},
        label: {
          show: true,
          formatter: '{b}',
          fontSize: 10,
          color: '#333'
        },
        emphasis: {
          label: {show: true, fontSize: 12, fontWeight: 'bold'},
          itemStyle: {areaColor: '#5ccfe6'}
        },
        itemStyle: {
          areaColor: '#e0f3f8',
          borderColor: '#acbbcd',
          borderWidth: 1
        },
        data: mapData
      }]
    };
    
    // 设置选项
    chart.value.setOption(option);
    
    // 隐藏占位图
    showPlaceholder.value = false;
    isInitialRenderComplete.value = true;
    
    // 仅在首次渲染时设置点击事件
    if (firstRender) {
      chart.value.off('click');
      chart.value.on('click', (params) => {
        if (params.name) emit('city-click', params.name);
      });
    }
  } catch (error) {
    showPlaceholder.value = false;
  }
}

// 窗口大小调整处理 - 使用节流函数
const handleResize = () => {
  if (!chart.value) return;
  
  try {
    // 先执行resize
    chart.value.resize();
    
    // 如果地图已经加载过数据，则在resize后重新应用数据，确保颜色正确显示
    if (props.provinceData?.length) {
      // 短暂延迟重新渲染，确保DOM已经更新
      setTimeout(() => {
        // 完全重新渲染，确保正确显示
        renderMap(props.provinceData, false);
      }, 100);
    }
  } catch (error) {
    console.error('地图重绘出错:', error);
  }
}

// 创建节流版本的resize处理函数
const throttledResize = (() => {
  let timer = null;
  
  return () => {
    if (timer) clearTimeout(timer);
    
    timer = setTimeout(() => {
      handleResize();
      timer = null;
    }, 150); // 增加到150ms延迟，避免频繁重绘
  };
})();

// 组件挂载时简化处理
onMounted(() => {
  isComponentMounted.value = true;
  
  // 创建图表实例
  preRenderMap();
  
  // 立即渲染数据
  if (props.provinceData?.length) {
    renderMap(props.provinceData, true);
  }
  
  // 添加resize事件监听，使用节流版本
  window.addEventListener('resize', throttledResize);
  
  // 添加orientationchange事件监听，针对移动设备旋转
  window.addEventListener('orientationchange', () => {
    setTimeout(throttledResize, 200); // 在方向变化后延迟处理
  });
})

// 组件卸载前处理
onBeforeUnmount(() => {
  isComponentBeingDestroyed.value = true;
  
  // 移除事件监听
  window.removeEventListener('resize', throttledResize);
  window.removeEventListener('orientationchange', throttledResize);
  
  // 清理图表实例
  if (chart.value) {
    chart.value.dispose();
    chart.value = null;
  }
})

// 设置图表实例，由父组件调用
const setChartInstance = (instance) => {
  chart.value = instance
}

// 暴露方法给父组件
defineExpose({
  refreshMap,
  resetMapView,
  zoomMap,
  zoomOutMap,
  handleMapTypeChange,
  setChartInstance
})
</script>

<style>
/* 全局修复Element Plus按钮中图标和文字不居中的问题 */
.el-button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.el-button .el-icon {
  vertical-align: middle !important;
}
</style>

<style scoped>
.map-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  padding: 0 !important;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 52px;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  height: 100%;
  font-size: 16px;
  font-weight: 500;
}

.header-icon {
  margin-right: 8px;
}

.map-btn {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 14px !important;
}

.aqi-btn {
  padding: 8px 16px !important;
  height: 38px !important;
  font-weight: 500 !important;
}

.map-type-dropdown {
  margin-right: 12px;
}

.map-control-group {
  display: flex;
  align-items: center;
  height: 100%;
}

.map-control-group :deep(.el-button) {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 38px;
  width: 38px;
  padding: 0;
  line-height: 0;
}

.map-control-group :deep(.el-icon) {
  margin: 0;
  vertical-align: middle;
  line-height: 0;
  font-size: 18px;
}

.control-btn {
  border-width: 1px !important;
}

.map-chart {
  flex: 1;
  min-height: 280px;
  width: 100%;
}

.placeholder-map {
  position: absolute;
  top: 60px;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
  z-index: 2;
}

.placeholder-text {
  font-size: 16px;
  color: #909399;
}

.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #f56c6c;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.8);
  padding: 10px 15px;
  border-radius: 4px;
  z-index: 10;
}

/* 确保地图在调整大小时保持比例 */
@media (max-width: 768px) {
  .map-chart {
    min-height: 220px;
  }
}
</style> 