import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/main.scss'
import './assets/styles/base.css'
import './assets/styles/fixes.css'
import './assets/styles/performance-fixes.css'
import './assets/report-styles.css'
import { echarts, loadGuangdongMap, isMapRegistered } from './plugins/echarts'
import { disposeAllCharts } from './utils/echartsUtil'
import { initCompatibilityPatches } from './plugins/compatibility-patch'
import { initCacheConfig } from './plugins/cache-config'
import { initVuetify } from './plugins/vuetify'
import axios from 'axios'

// 向window添加应用就绪状态标志
window.appReady = false;

// 如果未初始化，创建全局应用状态对象
if (!window.AppState) {
  window.AppState = {
    preloadedResources: new Set(), // 使用Set代替Array，避免重复检查
    loading: true,
    ready: false,
    currentRoute: null,
    registerPreloadedResource(url) {
      if (!this.preloadedResources.has(url)) {
        this.preloadedResources.add(url);
        return true;
      }
      return false;
    },
    isResourcePreloaded(url) {
      return this.preloadedResources.has(url);
    },
    areResourcesPreloaded(urls) {
      if (!urls || !urls.length) return true;
      return urls.every(url => this.isResourcePreloaded(url));
    },
    setReady() {
      this.ready = true;
      this.loading = false;
      window.appReady = true;
      // 统一使用一个事件通知就绪状态
      window.dispatchEvent(new CustomEvent('app:state', { 
        detail: { ready: true, loading: false }
      }));
    }
  };
}

// 设置ECharts全局配置，禁用非关键警告
echarts.init.mockDispose = true

// 在页面卸载前清理所有ECharts实例
window.addEventListener('beforeunload', () => {
  disposeAllCharts()
})

// 导入日期格式化工具函数
import * as dateFormat from './utils/dateFormat'

// 导入Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

// 日志系统配置
const LOG_LEVELS = {
  NONE: 0,
  ERROR: 1,
  WARN: 2,
  INFO: 3,
  DEBUG: 4,
  VERBOSE: 5
};

// 创建全局日志管理器 - 生产环境默认只显示错误
const currentLogLevel = process.env.NODE_ENV === 'production' ? LOG_LEVELS.ERROR : LOG_LEVELS.WARN;

// 创建全局日志对象
window.AppLog = {
  level: currentLogLevel,
  
  // 日志方法
  error: (message, ...args) => {
    console.error(message, ...args);
  },
  
  warn: (message, ...args) => {
    if (window.AppLog.level >= LOG_LEVELS.WARN) {
      console.warn(message, ...args);
    }
  },
  
  info: (message, ...args) => {
    if (window.AppLog.level >= LOG_LEVELS.INFO) {
      console.info(message, ...args);
    }
  },
  
  debug: (message, ...args) => {
    if (window.AppLog.level >= LOG_LEVELS.DEBUG) {
      console.log('[DEBUG]', message, ...args);
    }
  },
  
  verbose: (message, ...args) => {
    if (window.AppLog.level >= LOG_LEVELS.VERBOSE) {
      console.log('[VERBOSE]', message, ...args);
    }
  },
  
  // 设置日志级别
  setLevel: (level) => {
    window.AppLog.level = level;
  }
};

// 在生产环境禁用大部分日志
if (process.env.NODE_ENV === 'production') {
  // 保留错误日志，但禁用其他所有日志
  console.log = () => {};
  console.info = () => {};
  console.debug = () => {};
}

// 全局状态记录，用于排除重复初始化
const globalState = {
  mapInitialized: false
}

// 应用兼容性补丁
initCompatibilityPatches(null, { axios });

// 初始化缓存配置
initCacheConfig({
  enableServiceWorker: true,
  enableFetchCache: true
});

// 确保广东地图正确加载
const ensureGuangdongMapLoaded = async () => {
  if (globalState.mapInitialized) {
    return true;
  }
  
  try {
    // 检查地图是否已经注册
    if (!isMapRegistered('guangdong')) {
      // 加载广东地图数据
      const result = await loadGuangdongMap();
      globalState.mapInitialized = result;
      return result;
    } else {
      globalState.mapInitialized = true;
      return true;
    }
  } catch (error) {
    console.error('加载广东地图时出错:', error);
    return false;
  }
};

// 创建应用实例
const app = createApp(App);

// 全局注册日期格式化工具函数
app.config.globalProperties.formatDateTime = dateFormat.formatDateTime;
app.config.globalProperties.formatDate = dateFormat.formatDate;
app.config.globalProperties.formatTime = dateFormat.formatTime;
app.config.globalProperties.formatRelativeTime = dateFormat.formatRelativeTime;

// 配置全局异常处理
app.config.errorHandler = (err, vm, info) => {
  // 过滤掉重复的格式化相关错误
  if (err.message && err.message.includes('formatDateTime is not a function')) {
    return;
  }
  
  // 其他错误正常处理
  console.error('全局错误:', err);
  
  // 地图相关错误处理
  if (err.message) {
    if (err.message.includes('Map guangdong not exists')) {
      ensureGuangdongMapLoaded();
    }
  }
};

// 配置Pinia
const pinia = createPinia();

// 注册插件
app.use(pinia);
app.use(router);
app.use(ElementPlus, {
  locale: zhCn
});

// 初始化Vuetify
initVuetify(app);

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

// 添加资源加载计数
let resourcesLoaded = 0;
const totalResources = 1; // 只依赖地图数据作为关键资源

// 标记资源已加载
const markResourceLoaded = () => {
  resourcesLoaded++;
  if (resourcesLoaded >= totalResources) {
    // 所有资源都已加载，使用统一方法设置就绪状态
    if (window.AppState && typeof window.AppState.setReady === 'function') {
      window.AppState.setReady();
    } else {
      // 降级处理 - 如果setReady方法不存在，直接设置状态
      if (window.AppState) {
        window.AppState.ready = true;
        window.AppState.loading = false;
      }
      window.appReady = true;
      window.dispatchEvent(new CustomEvent('app:state', { 
        detail: { ready: true, loading: false }
      }));
    }
  }
};

// 监听全局应用状态事件
window.addEventListener('app:state', (event) => {
  if (event.detail) {
    // 更新AppState的对应属性
    Object.entries(event.detail).forEach(([key, value]) => {
      if (window.AppState.hasOwnProperty(key)) {
        window.AppState[key] = value;
      }
    });
    
    // 特殊处理route变更
    if (event.detail.route) {
      window.AppState.currentRoute = event.detail.route;
    }
  }
});

// 在应用挂载前预热ECharts
(async () => {
  // 创建一个预热任务的Promise
  const warmupTasks = [
    ensureGuangdongMapLoaded().catch(() => {})
      .then(() => markResourceLoaded())
  ];
  
  // 初始化结束后挂载应用，不等待地图加载完成
  app.mount('#app');
  
  // 等待预热任务完成
  await Promise.all(warmupTasks).catch(error => {
    console.error('预热任务执行出错，但应用已挂载:', error);
  });
  
  // 如果地图没有初始化，再尝试一次
  if (!globalState.mapInitialized) {
    ensureGuangdongMapLoaded();
  }
})(); 