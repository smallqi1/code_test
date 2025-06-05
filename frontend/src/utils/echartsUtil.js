import * as echarts from 'echarts'

// 关闭ECharts非关键警告
echarts.init.mockDispose = true

/**
 * 创建安全的ECharts实例
 * @param {HTMLElement} dom - 图表容器DOM元素
 * @param {Object} theme - 主题，可选
 * @param {Object} opts - 初始化选项，可选
 * @returns {Object} - ECharts实例
 */
export const createChart = (element, options = {}) => {
  if (!element) return null;
  
  try {
    // 检查DOM元素尺寸
    if (element.clientWidth === 0 || element.clientHeight === 0) {
      console.warn('图表容器DOM元素尺寸为0，可能导致渲染问题');
    }
    
    // 检查是否已经有图表实例
    let existingInstance = echarts.getInstanceByDom(element);
    if (existingInstance) {
      // 如果已有实例，先销毁它
      existingInstance.dispose();
    }
    
    // 创建实例
    const chart = echarts.init(element, null, {
      renderer: 'canvas',
      useDirtyRect: true, // 优化渲染性能
      ...options
    });
    
    // 保存实例引用到DOM元素
    element.__chartInstance = chart;
    
    return chart;
  } catch (error) {
    console.error('创建图表实例失败:', error);
    return null;
  }
};

/**
 * 安全地销毁图表实例
 * @param {Object|HTMLElement} instance - 图表实例或DOM元素
 */
export const disposeChart = (chart) => {
  if (!chart) return false;
  
  try {
    if (typeof chart.dispose === 'function') {
      // 标记已处理，避免重复释放
      if (chart.__disposed) return true;
      
      // 移除DOM引用
      if (chart.getDom) {
        const dom = chart.getDom();
        if (dom && dom.__chartInstance) {
          delete dom.__chartInstance;
        }
      }
      
      // 销毁实例
      chart.dispose();
      chart.__disposed = true;
      return true;
    }
  } catch (e) {
    return false;
  }
  
  return false;
};

/**
 * 全局清理所有图表实例的辅助方法
 * 通常用于页面刷新或应用退出前
 */
export const disposeAllCharts = () => {
  try {
    // 获取所有实例
    let instances = [];
    
    // 尝试使用新API，如果不可用则回退到旧API
    try {
      instances = echarts.getInstanceByDom 
        ? Object.values(echarts.getInstanceByDom())
        : [];
    } catch (e) {
      // 无法获取实例，只能尝试通过DOM查找
      const chartDoms = document.querySelectorAll('[_echarts_instance_]');
      instances = Array.from(chartDoms).map(dom => {
        try {
          return echarts.getInstanceByDom(dom);
        } catch (_) {
          return null;
        }
      }).filter(Boolean);
    }
    
    // 确保是数组
    if (!Array.isArray(instances)) {
      instances = Object.values(instances);
    }
    
    // 释放每个实例
    instances.forEach(chart => {
      disposeChart(chart);
    });
    
    return true;
  } catch (error) {
    return false;
  }
};

export default {
  createChart,
  disposeChart,
  disposeAllCharts
} 