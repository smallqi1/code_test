<template>
  <div>
    <!-- 最新预警面板 -->
    <div class="latest-alerts card">
      <div class="card-header">
        <span>最新预警</span>
        <div class="card-actions">
          <el-button type="primary" size="small" :loading="loading" :disabled="loading" @click="refreshAlerts">刷新</el-button>
        </div>
      </div>
      
      <div v-if="loading" class="alert-skeleton">
        <div class="skeleton-alert-item" v-for="i in 3" :key="i">
          <div class="skeleton-alert-icon"></div>
          <div class="skeleton-alert-content">
            <div class="skeleton-alert-title"></div>
            <div class="skeleton-alert-message"></div>
            <div class="skeleton-alert-meta">
              <div class="skeleton-alert-city"></div>
              <div class="skeleton-alert-time"></div>
            </div>
          </div>
        </div>
      </div>
      
      <div v-else-if="alerts.length === 0" class="empty-data">
        <el-empty description="暂无预警信息"></el-empty>
      </div>
      
      <div v-else class="alert-list">
        <div v-for="(alert, index) in alerts" :key="index" 
             :class="['alert-item', {'unread': alert.isNew, ['alert-' + alert.level]: true}]">
          <div :class="['alert-icon', {'alert-warning': alert.level === 'warning', 'alert-critical': alert.level === 'critical'}]">
            <i v-if="alert.level === 'info'" class="el-icon-info"></i>
            <i v-else-if="alert.level === 'warning'" class="el-icon-warning"></i>
            <i v-else class="el-icon-error"></i>
          </div>
          <div class="alert-content">
            <div class="alert-title">{{ alert.title }}</div>
            <div class="alert-message">{{ alert.message }}</div>
            <div class="alert-meta">
              <span>{{ alert.city }}</span>
              <span>{{ formatDateTime(alert.time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 全部预警对话框 -->
    <el-dialog
      title="全部预警信息"
      v-model="alertsDialogVisible"
      width="80%"
      :before-close="handleDialogClose"
      :destroy-on-close="true"
    >
      <el-table 
        :data="allAlerts" 
        style="width: 100%"
        v-loading="alertsLoading"
      >
        <el-table-column prop="city" label="城市" width="120" />
        <el-table-column prop="title" label="预警标题" min-width="180" />
        <el-table-column prop="aqi" label="AQI" width="80" />
        <el-table-column label="级别" width="120">
          <template #default="scope">
            <el-tag
              :type="getAlertLevelType(scope.row.level)"
            >
              {{ getAlertLevelText(scope.row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.time) }}
          </template>
        </el-table-column>
        <el-table-column label="详情" width="100">
          <template #default="scope">
            <el-button @click="showAlertDetail(scope.row)" link size="small">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 预警详情对话框 -->
    <el-dialog
      title="预警详情"
      v-model="alertDetailVisible"
      width="60%"
      :before-close="() => alertDetailVisible = false"
      :destroy-on-close="true"
    >
      <div v-if="selectedAlert" class="alert-detail">
        <h3>{{ selectedAlert.title }}</h3>
        <div class="alert-meta">
          <p><strong>城市:</strong> {{ selectedAlert.city }}</p>
          <p><strong>AQI:</strong> {{ selectedAlert.aqi }}</p>
          <p><strong>级别:</strong> {{ getAlertLevelText(selectedAlert.level) }}</p>
          <p><strong>时间:</strong> {{ formatDateTime(selectedAlert.time) }}</p>
        </div>
        <div class="alert-content">
          <p>{{ selectedAlert.message }}</p>
        </div>
        <div class="alert-measures" v-if="selectedAlert.measures && selectedAlert.measures.length">
          <h4>建议措施:</h4>
          <ul>
            <li v-for="(measure, index) in selectedAlert.measures" :key="index">{{ measure }}</li>
          </ul>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  alerts: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  alertsLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['refresh-alerts', 'show-all-alerts'])

// 内部状态
const alertsDialogVisible = ref(false)
const alertDetailVisible = ref(false)
const selectedAlert = ref(null)
const allAlerts = ref([])

// 方法
const refreshAlerts = () => {
  emit('refresh-alerts')
}

const showAllAlerts = () => {
  alertsDialogVisible.value = true
}

const handleDialogClose = () => {
  alertsDialogVisible.value = false
}

const showAlertDetail = (alert) => {
  selectedAlert.value = alert
  alertDetailVisible.value = true
}

// 根据预警级别获取标签类型
const getAlertLevelType = (level) => {
  switch (level) {
    case 'critical':
      return 'danger'
    case 'warning':
      return 'warning'
    case 'info':
      return 'info'
    default:
      return 'info'
  }
}

// 根据预警级别获取文本
const getAlertLevelText = (level) => {
  switch (level) {
    case 'critical':
      return '严重'
    case 'warning':
      return '警告'
    case 'info':
      return '提示'
    default:
      return '未知'
  }
}

// 格式化日期时间
const formatDateTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 暴露方法给父组件
defineExpose({
  setAllAlerts: (alerts) => {
    allAlerts.value = alerts
  },
  openAllAlertsDialog: () => {
    alertsDialogVisible.value = true
  }
})
</script>

<style scoped>
.alert-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 4px;
  background-color: #f9f9f9;
  transition: all 0.3s;
}

.alert-item:hover {
  background-color: #f0f0f0;
  transform: translateX(5px);
}

.alert-item.unread {
  border-left: 3px solid #409EFF;
}

.alert-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: #e1f3d8;
  color: #67C23A;
  flex-shrink: 0;
}

.alert-warning {
  background-color: #fdf6ec;
  color: #E6A23C;
}

.alert-critical {
  background-color: #fef0f0;
  color: #F56C6C;
}

.alert-content {
  flex: 1;
  min-width: 0; /* 防止内容溢出 */
}

.alert-title {
  font-weight: bold;
  margin-bottom: 4px;
  color: #303133;
}

.alert-message {
  color: #606266;
  font-size: 13px;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.alert-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.alert-detail {
  padding: 10px;
}

.alert-detail h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
  font-size: 18px;
}

.alert-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 15px;
  background-color: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
}

.alert-meta p {
  margin: 0;
}

.alert-content {
  margin-bottom: 15px;
  line-height: 1.5;
}

.alert-measures h4 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 16px;
}

.alert-measures ul {
  margin: 0;
  padding-left: 20px;
}

.alert-measures li {
  margin-bottom: 5px;
}

.empty-data {
  padding: 30px 0;
}

.alert-loading {
  padding: 20px;
}

.latest-alerts {
  background-color: white;
  border-radius: 10px;
  padding: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.card-actions {
  display: flex;
  gap: 8px;
}
</style> 