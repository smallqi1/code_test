<template>
  <div class="app-container">
    <div v-if="isLoading" class="app-loading">
      <div class="app-loading-content">
        <div class="app-loading-spinner"></div>
        <div class="app-loading-text">{{ loadingText }}</div>
      </div>
    </div>
    <router-view v-slot="{ Component, route }" v-else>
      <keep-alive>
        <component :is="Component" :key="route.name" v-if="route.meta?.keepAlive" />
      </keep-alive>
      <component :is="Component" :key="route.name" v-if="!route.meta?.keepAlive" />
    </router-view>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useUserStore } from './store/userStore'

const userStore = useUserStore()
const isLoading = ref(false)
const loadingText = ref('加载中...')
const loadingTexts = ['准备数据...', '加载地图...', '初始化界面...']
let loadingInterval

// 循环显示不同的加载文本
const startLoadingTextAnimation = () => {
  if (loadingInterval) clearInterval(loadingInterval);
  
  let index = 0
  loadingInterval = setInterval(() => {
    loadingText.value = loadingTexts[index % loadingTexts.length]
    index++
  }, 1200)
}

// 停止加载动画
const stopLoadingAnimation = () => {
  if (loadingInterval) {
    clearInterval(loadingInterval)
    loadingInterval = null
  }
  
  // 最小加载时间缩短到500ms
  setTimeout(() => {
    isLoading.value = false
  }, 500)
}

// 监听应用就绪状态
const watchAppReady = () => {
  // 简化就绪状态检查
  if (window.appReady || (window.AppState && window.AppState.ready)) {
    stopLoadingAnimation();
    return;
  }
  
  // 监听统一的应用状态事件
  window.addEventListener('app:state', (event) => {
    if (event.detail && event.detail.ready) {
      stopLoadingAnimation();
    }
  });
  
  // 超时处理时间缩短到1.5秒
  setTimeout(stopLoadingAnimation, 1500);
}

onMounted(async () => {
  // 初始化应用
  await userStore.initializeSettings();
  
  // 简化加载状态逻辑
  if (window.AppState && window.AppState.ready) {
    // 应用已就绪
    isLoading.value = false;
  } else if (window.AppState && window.AppState.loading) {
    // HTML已经显示了加载器，默认不显示Vue加载器
    isLoading.value = false;
  } else {
    // 显示Vue加载器
    isLoading.value = true;
    startLoadingTextAnimation();
  }
  
  // 监听应用就绪状态
  watchAppReady();
  
  // 通知Vue应用已挂载
  window.dispatchEvent(new CustomEvent('app:state', { 
    detail: { vueAppMounted: true } 
  }));
})
</script>

<style>
/* 全局基础样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  width: 100%;
  margin: 0; /* 确保没有外边距 */
  padding: 0; /* 确保没有内边距 */
  overflow: hidden; /* 防止滚动条出现造成布局偏移 */
}

body {
  font-family: 'Avenir', 'Helvetica', 'Arial', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--text-color);
  background-color: var(--bg-color);
  transition: background-color 0.3s ease, color 0.3s ease;
}

#app {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* 应用容器 */
.app-container {
  height: 100%;
  width: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 加载动画 */
.app-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #f5f7fa;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.app-loading-content {
  text-align: center;
}

.app-loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e0e6ed;
  border-top: 4px solid #3b96ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

.app-loading-text {
  font-size: 16px;
  color: #606266;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style> 