<template>
  <div v-if="loading" class="loading-overlay">
    <div class="loading-container">
      <div class="loading-spinner">
        <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      </div>
      <div class="loading-text">{{ loadingTip || '加载中...' }}</div>
      
      <!-- 错误提示 -->
      <div v-if="loadingErrors && loadingErrors.length > 0" class="loading-errors">
        <div v-for="(error, index) in loadingErrors" :key="index" class="error-item">
          <el-alert type="warning" :title="error" :closable="false" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue';

defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  loadingTip: {
    type: String,
    default: '加载中...'
  },
  loadingProgress: {
    type: Number,
    default: 0
  },
  loadingErrors: {
    type: Array,
    default: () => []
  }
});
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: transparent !important; /* 确保背景完全透明 */
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.loading-container {
  background-color: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  text-align: center;
  max-width: 80%;
  min-width: 300px;
}

.loading-spinner {
  margin-bottom: 15px;
  display: flex;
  justify-content: center;
}

.loading-spinner .el-icon {
  color: #409EFF;
  font-size: 40px;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-text {
  font-size: 16px;
  color: #333;
  margin-bottom: 20px;
}

/* 隐藏进度条相关样式 
.progress-container {
  height: 6px;
  background-color: #eee;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 5px;
}

.progress-bar {
  height: 100%;
  background-color: #409EFF;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 14px;
  color: #666;
  margin-bottom: 15px;
}
*/

.loading-errors {
  margin-top: 20px;
  text-align: left;
}

.error-item {
  margin-bottom: 8px;
}
</style> 