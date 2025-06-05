/**
 * Vuetify配置文件
 * 负责初始化Vuetify，配置主题和图标
 */

import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// 显式导入相关样式文件
import 'vuetify/styles'

/**
 * 尝试预加载Material Design Icons
 * 如果service-worker无法加载，提供备用方案
 */
function ensureMaterialDesignIcons() {
  const mdiUrl = 'https://cdn.jsdelivr.net/npm/@mdi/font@latest/css/materialdesignicons.min.css';
  const unpkgUrl = 'https://unpkg.com/@mdi/font@latest/css/materialdesignicons.min.css';
  
  // 检查是否已经存在MDI样式
  if (document.querySelector('link[href*="materialdesignicons"]')) {
    console.log('MDI图标已加载，跳过初始化');
    return Promise.resolve();
  }
  
  return new Promise((resolve) => {
    // 创建并添加样式链接
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = mdiUrl;
    
    // 成功处理
    link.onload = () => {
      console.log('成功加载MDI图标 (jsdelivr)');
      resolve();
    };
    
    // 错误处理 - 尝试备用CDN
    link.onerror = () => {
      console.warn('从jsdelivr加载MDI图标失败，尝试备用CDN');
      link.href = unpkgUrl;
      
      // 备用CDN成功处理
      link.onload = () => {
        console.log('成功加载MDI图标 (unpkg)');
        resolve();
      };
      
      // 备用CDN错误处理
      link.onerror = () => {
        console.error('所有CDN加载MDI图标失败');
        resolve(); // 仍然解析promise，让应用继续
      };
    };
    
    document.head.appendChild(link);
  });
}

// 主题配置
const lightTheme = {
  dark: false,
  colors: {
    primary: '#2196F3',
    secondary: '#03A9F4',
    accent: '#9C27B0',
    error: '#F44336',
    warning: '#FF9800', 
    info: '#00BCD4',
    success: '#4CAF50'
  }
}

const darkTheme = {
  dark: true,
  colors: {
    primary: '#2196F3',
    secondary: '#03A9F4',
    accent: '#9C27B0',
    error: '#F44336',
    warning: '#FF9800',
    info: '#00BCD4',
    success: '#4CAF50'
  }
}

// 创建Vuetify实例
const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: lightTheme,
      dark: darkTheme
    }
  },
  icons: {
    defaultSet: 'mdi'
  }
})

/**
 * 初始化Vuetify，确保图标库和主题正确加载
 * @param {Object} app - Vue应用实例
 * @returns {Promise} - 初始化完成的Promise
 */
export function initVuetify(app) {
  // 使用Vuetify
  app.use(vuetify);
  
  // 将vuetify实例存储在全局window对象中，方便在其他地方访问
  window.vuetifyInstance = vuetify;
  
  // 加载所需图标
  return ensureMaterialDesignIcons();
}

// 导出Vuetify实例
export default vuetify; 