<template>
  <div class="report-generation-page">
    <h1 class="page-title">报告生成</h1>
    
    <!-- 全局错误提示 -->
    <div v-if="globalError" class="global-error-message">
      <span class="error-icon">⚠️</span> {{ globalError }}
      <button class="close-btn" @click="globalError = ''">×</button>
    </div>
    
    <div class="report-layout">
      <div class="report-settings card">
        <div class="card-header">
          <h2 class="card-title">报告设置</h2>
        </div>
        <div class="card-body">
          <form class="report-form" @submit.prevent="generateReport">
            <div class="form-group">
              <label>报告类型</label>
              <select class="form-control" v-model="reportSettings.type">
                <option value="daily">日报</option>
                <option value="weekly">周报</option>
                <option value="monthly">月报</option>
                <option value="quarterly">季度报告</option>
                <option value="yearly">年度报告</option>
                <option value="custom">自定义报告</option>
              </select>
            </div>
            
            <div class="form-group">
              <label>时间范围</label>
              <div class="date-range">
                <input type="date" class="form-control" v-model="reportSettings.startDate" />
                <span class="date-separator">至</span>
                <input type="date" class="form-control" v-model="reportSettings.endDate" />
              </div>
            </div>
            
            <div class="form-group">
              <label>地区选择</label>
              <select class="form-control" v-model="reportSettings.region">
                <option value="all">全省</option>
                <option value="guangzhou">广州</option>
                <option value="shenzhen">深圳</option>
                <option value="pearl_delta">珠三角</option>
                <option value="east">粤东地区</option>
                <option value="west">粤西地区</option>
                <option value="north">粤北地区</option>
              </select>
            </div>
            
            <div class="form-group">
              <label>报告内容</label>
              <div class="checkbox-group">
                <label class="checkbox-item">
                  <input type="checkbox" v-model="reportSettings.content.overview" /> 空气质量概览
                </label>
                <label class="checkbox-item">
                  <input type="checkbox" v-model="reportSettings.content.pollution" /> 污染物分析
                </label>
                <label class="checkbox-item">
                  <input type="checkbox" v-model="reportSettings.content.trend" /> 趋势变化
                </label>
                <label class="checkbox-item">
                  <input type="checkbox" v-model="reportSettings.content.warning" /> 预警信息
                </label>
                <label class="checkbox-item">
                  <input type="checkbox" v-model="reportSettings.content.policy" /> 政策建议
                </label>
              </div>
            </div>
            
            <div class="form-group">
              <label>报告格式</label>
              <div class="format-options">
                <label class="format-item">
                  <input type="radio" name="format" value="pdf" v-model="reportSettings.format" /> PDF
                </label>
                <label class="format-item">
                  <input type="radio" name="format" value="word" v-model="reportSettings.format" /> Word
                </label>
                <label class="format-item">
                  <input type="radio" name="format" value="excel" v-model="reportSettings.format" /> Excel
                </label>
                <label class="format-item">
                  <input type="radio" name="format" value="html" v-model="reportSettings.format" /> HTML
                </label>
              </div>
            </div>
            
            <div class="form-actions">
              <button type="submit" class="btn btn-primary" :disabled="isGenerating">
                {{ isGenerating ? '生成中...' : '生成报告' }}
              </button>
              <button type="button" class="btn-outline" @click="resetForm">重置</button>
            </div>
          </form>
        </div>
      </div>
      
      <div class="report-preview card">
        <div class="card-header">
          <h2 class="card-title">报告预览</h2>
          <div class="card-actions" v-if="currentReport">
            <button class="btn-outline btn-sm" @click="downloadReport" :disabled="isDownloading">
              <span v-if="!isDownloading">下载</span>
              <span v-else>下载中 ({{ downloadProgress }}%)</span>
            </button>
            <button class="btn-outline btn-sm" @click="printReport">打印</button>
            <button class="btn-outline btn-sm" @click="shareReport">分享</button>
          </div>
        </div>
        <div class="card-body">
          <!-- 下载进度和错误消息 -->
          <div v-if="isDownloading || downloadError" class="download-status">
            <div v-if="isDownloading" class="progress-container">
              <div class="progress-bar" :style="{ width: `${downloadProgress}%` }"></div>
              <div class="progress-text">下载中: {{ downloadProgress }}%</div>
            </div>
            <div v-if="downloadError" class="error-message">
              <span class="error-icon">⚠️</span> {{ downloadError }}
              <button v-if="currentDownloadingId" class="retry-btn" @click="retryDownload">重试</button>
            </div>
          </div>
          
          <div class="preview-content" v-if="currentReport && currentReport.content">
            <div class="report-content-wrapper" v-html="currentReport.content"></div>
          </div>
          <div class="preview-content" v-else-if="currentReport && !currentReport.content">
            <div class="placeholder-text">
              报告已生成，但只能在下载后查看完整内容。<br>
              <button class="btn btn-sm" @click="downloadReport" :disabled="isDownloading">
                <span v-if="!isDownloading">下载报告</span>
                <span v-else>下载中...</span>
              </button>
            </div>
          </div>
          <div class="preview-content" v-else>
            <div class="placeholder-text">
              配置报告参数并点击"生成报告"按钮来预览报告内容...
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="card report-history">
      <div class="card-header">
        <h2 class="card-title">报告历史</h2>
        <div class="card-actions">
          <input type="text" class="search-input" v-model="searchQuery" placeholder="搜索报告..." />
        </div>
      </div>
      <div class="card-body">
        <div v-if="isLoading" class="loading-indicator">加载中...</div>
        <table class="history-table" v-else-if="filteredReports.length > 0">
          <thead>
            <tr>
              <th>报告名称</th>
              <th>类型</th>
              <th>生成时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="report in filteredReports" :key="report.id">
              <td>{{ report.name }}</td>
              <td>{{ getReportTypeName(report.type) }}</td>
              <td>{{ formatDate(report.createdAt) }}</td>
              <td><span :class="getStatusClass(report.status)">{{ getStatusText(report.status) }}</span></td>
              <td>
                <button class="action-btn" @click="viewReport(report)">查看</button>
                <button class="action-btn" 
                  @click="downloadReportFile(report.id, report.format)"
                  :disabled="isDownloading && currentDownloadingId === report.id">
                  <span v-if="!(isDownloading && currentDownloadingId === report.id)">下载</span>
                  <span v-else>下载中</span>
                </button>
                <button class="action-btn action-btn-danger" @click="confirmDelete(report)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          暂无报告记录
        </div>
      </div>
    </div>
    
    <!-- 删除确认对话框 -->
    <div v-if="deleteConfirmVisible" class="confirm-dialog">
      <div class="confirm-dialog-content">
        <h3 class="confirm-dialog-title">确认删除</h3>
        <p class="confirm-dialog-message">
          确定要删除报告 "{{ reportToDelete?.name || '未命名报告' }}" 吗？<br>
          <span class="confirm-dialog-warning">此操作无法撤销！</span>
        </p>
        <div class="confirm-dialog-actions">
          <button class="btn btn-outline" @click="deleteConfirmVisible = false">取消</button>
          <button class="btn btn-danger" @click="executeDelete" :disabled="isDeleting">
            {{ isDeleting ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { fetchReportHistory, generateReportRequest, downloadReportFile as downloadFile, getReportDetails, deleteReport } from '@/api/reports'

// 报告设置表单数据
const reportSettings = reactive({
  type: 'daily',
  startDate: new Date().toISOString().split('T')[0], // 今天
  endDate: new Date().toISOString().split('T')[0],  // 今天
  region: 'all',
  content: {
    overview: true,
    pollution: true,
    trend: true,
    warning: true,
    policy: false
  },
  format: 'pdf'
})

// 状态变量
const isGenerating = ref(false)
const isLoading = ref(false)
const reportHistory = ref([])
const currentReport = ref(null)
const searchQuery = ref('')
const isDownloading = ref(false)
const downloadError = ref('')
const downloadProgress = ref(0)
const currentDownloadingId = ref(null)
const lastDownloadFormat = ref('')
const globalError = ref('') // 全局错误消息
const deleteConfirmVisible = ref(false) // 控制删除确认对话框显示
const reportToDelete = ref(null) // 要删除的报告
const isDeleting = ref(false) // 删除中状态

// 计算属性：过滤后的报告列表
const filteredReports = computed(() => {
  if (!searchQuery.value) return reportHistory.value
  
  const query = searchQuery.value.toLowerCase()
  return reportHistory.value.filter(report => 
    report.name.toLowerCase().includes(query) || 
    getReportTypeName(report.type).toLowerCase().includes(query)
  )
})

// 生命周期钩子
onMounted(async () => {
  console.log('ReportGeneration view mounted')
  await loadReportHistory()
})

// 方法
async function loadReportHistory() {
  isLoading.value = true
  globalError.value = '' // 清除全局错误
  try {
    const data = await fetchReportHistory()
    reportHistory.value = data || []
    if (reportHistory.value.length === 0) {
      console.log('没有找到报告历史记录或服务器未返回数据')
    }
  } catch (error) {
    console.error('Failed to load report history:', error)
    globalError.value = '加载报告历史记录失败，请刷新页面重试'
  } finally {
    isLoading.value = false
  }
}

async function generateReport() {
  if (isGenerating.value) return
  
  isGenerating.value = true
  downloadError.value = '' // 清除之前的错误信息
  globalError.value = '' // 清除全局错误
  
  try {
    const reportData = {
      ...reportSettings,
      name: generateReportName(reportSettings)
    }
    
    console.log('生成报告请求参数:', JSON.stringify(reportData))
    const result = await generateReportRequest(reportData)
    currentReport.value = result
    
    // 添加到历史记录
    await loadReportHistory()
  } catch (error) {
    console.error('Failed to generate report:', error)
    // 获取具体的错误消息
    let errorMessage = '报告生成失败'
    
    if (error.message) {
      errorMessage = error.message
      console.log('错误信息:', errorMessage)
    }
    
    // 使用error-message显示错误
    downloadError.value = errorMessage
    
    // 同时设置全局错误，使其更醒目
    globalError.value = `报告生成失败: ${errorMessage}`
    
    // 如果错误消息提示没有数据，给出更明确的提示
    if (errorMessage.includes('没有可用的空气质量数据') || 
        errorMessage.includes('未找到空气质量数据') ||
        errorMessage.includes('没有数据')) {
      globalError.value = `所选时间段(${reportSettings.startDate}至${reportSettings.endDate})的数据存在问题。请尝试：
        1. 选择其他日期范围
        2. 选择不同的地区范围
        3. 确认系统中有该时间段的数据`;
    }
  } finally {
    isGenerating.value = false
  }
}

function resetForm() {
  Object.assign(reportSettings, {
    type: 'daily',
    startDate: new Date().toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    region: 'all',
    content: {
      overview: true,
      pollution: true,
      trend: true,
      warning: true,
      policy: false
    },
    format: 'pdf'
  })
}

async function viewReport(report) {
  try {
    // 重置错误状态
    downloadError.value = ''
    
    // 如果报告是HTML格式，获取详细信息以显示内容
    if (report.format === 'html') {
      const reportDetails = await getReportDetails(report.id)
      currentReport.value = reportDetails
    } else {
      // 非HTML格式，尝试获取预览版本
      try {
        currentReport.value = report  // 先设置基本信息
        
        // 请求报告预览内容
        const previewResponse = await fetch(`${import.meta.env.VITE_REPORTS_API_BASE_URL || 'http://localhost:5003'}/api/reports/preview/${report.id}`)
        
        if (previewResponse.ok) {
          // 获取预览HTML内容
          const previewContent = await previewResponse.text()
          
          // 更新报告内容为预览内容
          currentReport.value = {
            ...report,
            content: previewContent,
            isPreview: true  // 标记这是预览版本
          }
        } else {
          // 如果无法获取预览，只显示基本信息
          console.warn(`无法获取报告预览: ${previewResponse.status}`)
          if (previewResponse.status === 404) {
            downloadError.value = '找不到报告预览，请尝试下载查看完整报告'
          } else {
            downloadError.value = `无法加载预览(${previewResponse.status})，请尝试下载查看完整报告`
          }
        }
      } catch (previewError) {
        console.error('获取报告预览失败:', previewError)
        // 发生错误时只显示基本信息
        downloadError.value = '无法连接预览服务器，请尝试下载查看完整报告'
      }
    }
  } catch (error) {
    console.error('Failed to view report:', error)
    downloadError.value = error.message || '获取报告详情失败'
    currentReport.value = null
  }
}

async function downloadReport() {
  if (!currentReport.value || isDownloading.value) return
  
  isDownloading.value = true
  downloadProgress.value = 0
  downloadError.value = ''
  currentDownloadingId.value = currentReport.value.id
  lastDownloadFormat.value = currentReport.value.format
  
  try {
    console.log(`开始下载报告: ${currentReport.value.id}, 格式: ${currentReport.value.format}`)
    
    // 添加下载进度回调
    const progressCallback = (progressEvent) => {
      if (progressEvent.lengthComputable) {
        downloadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      } else {
        // 如果无法计算进度，使用一个模拟的进度
        downloadProgress.value = Math.min(downloadProgress.value + 5, 95)
      }
    }
    
    // 增加超时时间和重试次数
    const result = await downloadFile(
      currentReport.value.id, 
      currentReport.value.format,
      {
        onDownloadProgress: progressCallback,
        timeout: 180000,  // 3分钟超时
        retry: 3,
        retryDelay: 2000
      }
    )
    
    // 完成下载
    downloadProgress.value = 100
    console.log('报告下载成功:', result)
    
    // 延迟一点关闭下载状态，让用户看到100%
    setTimeout(() => {
      isDownloading.value = false
      currentDownloadingId.value = null
    }, 500)
    
  } catch (error) {
    console.error('报告下载失败:', error)
    downloadError.value = error.message || '下载失败，请重试'
    downloadProgress.value = 0
    isDownloading.value = false
    
    // 保留当前下载ID以便重试
  }
}

// 重试下载
async function retryDownload() {
  if (!currentDownloadingId.value) return
  
  const reportId = currentDownloadingId.value
  const format = lastDownloadFormat.value
  
  // 重置状态
  downloadError.value = ''
  isDownloading.value = true
  downloadProgress.value = 0
  
  try {
    console.log(`重试下载报告: ${reportId}, 格式: ${format}`)
    
    // 添加下载进度回调
    const progressCallback = (progressEvent) => {
      if (progressEvent.lengthComputable) {
        downloadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      } else {
        downloadProgress.value = Math.min(downloadProgress.value + 5, 95)
      }
    }
    
    // 增加超时时间和重试次数
    const result = await downloadFile(
      reportId, 
      format,
      {
        onDownloadProgress: progressCallback,
        timeout: 180000,  // 3分钟超时
        retry: 3,
        retryDelay: 2000
      }
    )
    
    // 完成下载
    downloadProgress.value = 100
    console.log('报告下载成功:', result)
    
    setTimeout(() => {
      isDownloading.value = false
      currentDownloadingId.value = null
      downloadError.value = ''
    }, 500)
    
  } catch (error) {
    console.error('报告重试下载失败:', error)
    downloadError.value = error.message || '下载失败，请检查网络连接'
    downloadProgress.value = 0
    isDownloading.value = false
  }
}

function printReport() {
  if (currentReport.value && currentReport.value.content) {
    // 创建一个新窗口用于打印
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      // 构建包含完整HTML结构和CSS样式的内容
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>${currentReport.value.name || '空气质量报告'}</title>
          <meta charset="utf-8">
          <style>
            body {
              font-family: "Microsoft YaHei", Arial, sans-serif;
              line-height: 1.6;
              color: #333;
              padding: 20px;
            }
            table {
              border-collapse: collapse;
              width: 100%;
              margin-bottom: 15px;
              page-break-inside: avoid;
              table-layout: fixed;
            }
            th, td {
              border: 1px solid #000;
              padding: 8px;
              text-align: left;
              word-wrap: break-word;
              overflow-wrap: break-word;
            }
            th {
              background-color: #f2f2f2;
              font-weight: bold;
            }
            h1, h2, h3 {
              margin-top: 20px;
              margin-bottom: 10px;
              line-height: 1.4;
            }
            p, div, span {
              line-height: 1.6;
              margin-bottom: 10px;
            }
            .pollutant-grid {
              display: grid;
              grid-template-columns: repeat(3, 1fr);
              gap: 15px;
              margin-top: 20px;
            }
            .stats-card, .pollutant-card {
              background-color: #f8f9fa;
              border-radius: 5px;
              padding: 15px;
              text-align: center;
              box-shadow: 0 2px 5px rgba(0,0,0,0.1);
              margin-bottom: 15px;
            }
            @media print {
              body {
                font-size: 12pt;
              }
              .container {
                width: 100%;
                max-width: none;
              }
            }
          </style>
        </head>
        <body>
          ${currentReport.value.content}
        </body>
        </html>
      `)
      printWindow.document.close()
      printWindow.onload = function() {
        printWindow.focus()
        printWindow.print()
      }
    } else {
      alert('请允许打开弹出窗口以打印报告')
    }
  } else if (currentReport.value) {
    alert('此格式的报告不支持直接打印，请先下载后再打印')
  }
}

function shareReport() {
  if (currentReport.value) {
    alert('分享功能正在开发中')
  }
}

// 辅助函数
function generateReportName(settings) {
  const regionNames = {
    all: '广东省',
    guangzhou: '广州市',
    shenzhen: '深圳市',
    pearl_delta: '珠三角',
    east: '粤东地区',
    west: '粤西地区',
    north: '粤北地区'
  }
  
  const typeNames = {
    daily: '日报',
    weekly: '周报',
    monthly: '月报',
    quarterly: '季度报告',
    yearly: '年度报告',
    custom: '自定义报告'
  }
  
  const region = regionNames[settings.region] || '广东省'
  const type = typeNames[settings.type] || '报告'
  
  const now = new Date()
  const dateStr = now.toISOString().split('T')[0].replace(/-/g, '')
  const timeStr = `${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
  
  return `${region}空气质量${type} - ${dateStr}_${timeStr}`
}

function getReportTypeName(type) {
  const typeMap = {
    daily: '日报',
    weekly: '周报',
    monthly: '月报',
    quarterly: '季度报告',
    yearly: '年度报告',
    custom: '自定义报告'
  }
  return typeMap[type] || type
}

function formatDate(dateString) {
  if (!dateString) return ''
  const date = new Date(dateString)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:${String(date.getSeconds()).padStart(2, '0')}`
}

function getStatusClass(status) {
  return {
    completed: 'status-complete',
    pending: 'status-pending',
    error: 'status-error'
  }[status] || 'status-default'
}

function getStatusText(status) {
  return {
    completed: '已完成',
    pending: '处理中',
    error: '失败'
  }[status] || status
}

function confirmDelete(report) {
  reportToDelete.value = report
  deleteConfirmVisible.value = true
}

async function executeDelete() {
  if (!reportToDelete.value || isDeleting.value) return
  
  isDeleting.value = true
  
  try {
    await deleteReport(reportToDelete.value.id)
    
    // 从列表中移除已删除的报告
    reportHistory.value = reportHistory.value.filter(report => report.id !== reportToDelete.value.id)
    
    // 如果当前预览的报告被删除，清空当前报告
    if (currentReport.value && currentReport.value.id === reportToDelete.value.id) {
      currentReport.value = null
    }
    
    // 显示成功消息
    globalError.value = ''
    
    // 关闭对话框
    deleteConfirmVisible.value = false
    reportToDelete.value = null
  } catch (error) {
    console.error('删除报告失败:', error)
    globalError.value = error.message || '删除报告失败，请重试'
  } finally {
    isDeleting.value = false
  }
}

async function downloadReportFile(reportId, format) {
  if (!reportId || isDownloading.value) return
  
  isDownloading.value = true
  downloadProgress.value = 0
  downloadError.value = ''
  currentDownloadingId.value = reportId
  lastDownloadFormat.value = format
  
  try {
    console.log(`开始下载报告: ${reportId}, 格式: ${format}`)
    
    // 添加下载进度回调
    const progressCallback = (progressEvent) => {
      if (progressEvent.lengthComputable) {
        downloadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      } else {
        downloadProgress.value = Math.min(downloadProgress.value + 5, 95)
      }
    }
    
    // 确保报告ID有效
    if (!reportId) {
      throw new Error('下载失败：缺少报告ID')
    }
    
    // 增加超时时间和重试次数
    const result = await downloadFile(
      reportId, 
      format,
      {
        onDownloadProgress: progressCallback,
        timeout: 180000,  // 3分钟超时
        retry: 3,
        retryDelay: 2000
      }
    )
    
    // 完成下载
    downloadProgress.value = 100
    console.log('报告下载成功:', result)
    
    // 延迟一点关闭下载状态，让用户看到100%
    setTimeout(() => {
      isDownloading.value = false
      currentDownloadingId.value = null
      downloadError.value = '' // 清除错误信息
    }, 500)
    
  } catch (error) {
    console.error('报告下载失败:', error)
    downloadError.value = error.message || '下载失败，请重试'
    downloadProgress.value = 0
    isDownloading.value = false
  }
}
</script>

<style scoped>
.report-generation-page {
  padding: 20px;
}

.page-title {
  margin-bottom: 20px;
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 600;
}

.report-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.card {
  background-color: var(--card-bg);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 15px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.card-body {
  padding: 20px;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.report-settings, .report-preview {
  height: 100%;
}

.report-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-weight: 600;
  color: var(--text-primary);
}

.form-control {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--input-bg, #fff);
  color: var(--text-primary);
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-separator {
  color: var(--text-secondary);
}

.checkbox-group, .format-options {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.checkbox-item, .format-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-secondary);
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary {
  background-color: var(--primary-color, #1890ff);
  color: white;
}

.btn-primary:hover {
  background-color: var(--primary-hover, #40a9ff);
}

.btn-primary:disabled {
  background-color: var(--disabled-color, #d9d9d9);
  cursor: not-allowed;
}

.btn-outline {
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.btn-outline:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.preview-content {
  min-height: 400px;
  border: 1px dashed var(--border-color);
  border-radius: 4px;
  padding: 20px;
  overflow: auto;
  display: block;
}

.preview-content > div {
  width: 100%;
}

.preview-content table {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 15px;
}

.preview-content th,
.preview-content td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

.preview-content th {
  background-color: #f2f2f2;
  font-weight: bold;
}

.report-content-wrapper {
  font-family: Arial, sans-serif;
  line-height: 1.6;
  color: #333;
}

.report-content-wrapper h1,
.report-content-wrapper h2,
.report-content-wrapper h3 {
  margin-top: 20px;
  margin-bottom: 10px;
  line-height: 1.4;
}

.report-content-wrapper p {
  margin-bottom: 10px;
}

.placeholder-text {
  color: var(--text-secondary);
  text-align: center;
}

.search-input {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--input-bg, #fff);
  color: var(--text-primary);
  width: 200px;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table th, .history-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.history-table th {
  font-weight: 600;
  color: var(--text-secondary);
  background-color: rgba(0, 0, 0, 0.02);
}

.history-table tbody tr:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.status-complete {
  color: var(--success-color, #52c41a);
  font-weight: 500;
}

.status-pending {
  color: var(--warning-color, #faad14);
  font-weight: 500;
}

.status-error {
  color: var(--danger-color, #f5222d);
  font-weight: 500;
}

.status-default {
  color: var(--text-secondary);
}

.action-btn {
  padding: 4px 8px;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  cursor: pointer;
  margin-right: 5px;
  transition: all 0.2s;
}

.action-btn:hover {
  background-color: var(--primary-light, #e6f7ff);
  border-color: var(--primary-color, #1890ff);
  color: var(--primary-color, #1890ff);
}

.loading-indicator {
  display: flex;
  justify-content: center;
  padding: 20px;
  color: var(--text-secondary);
}

.empty-state {
  display: flex;
  justify-content: center;
  padding: 30px;
  color: var(--text-secondary);
  font-style: italic;
}

.download-status {
  margin-bottom: 15px;
  border-radius: 4px;
  overflow: hidden;
}

.progress-container {
  background-color: #f0f0f0;
  height: 24px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-bar {
  background-color: #4caf50;
  height: 100%;
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #333;
}

.error-message {
  background-color: #ffebee;
  color: #d32f2f;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
  font-size: 14px;
  display: flex;
  align-items: center;
}

.error-icon {
  margin-right: 8px;
  font-size: 16px;
}

.retry-btn {
  margin-left: auto;
  padding: 4px 8px;
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #333;
}

.retry-btn:hover {
  background-color: #e0e0e0;
}

@media (max-width: 992px) {
  .report-layout {
    grid-template-columns: 1fr;
  }
}

.global-error-message {
  background-color: #ffebee;
  color: #d32f2f;
  padding: 12px 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  position: relative;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.close-btn {
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #888;
}

.close-btn:hover {
  color: #d32f2f;
}

/* 修改删除按钮样式 */
.action-btn-danger {
  color: var(--danger-color, #f5222d);
}

.action-btn-danger:hover {
  background-color: #fff1f0;
  border-color: var(--danger-color, #f5222d);
}

/* 确认对话框样式 */
.confirm-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.confirm-dialog-content {
  background-color: white;
  border-radius: 8px;
  padding: 24px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.confirm-dialog-title {
  color: var(--text-primary);
  font-size: 18px;
  margin-top: 0;
  margin-bottom: 16px;
}

.confirm-dialog-message {
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.5;
}

.confirm-dialog-warning {
  color: var(--danger-color, #f5222d);
  font-weight: 500;
}

.confirm-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-danger {
  background-color: var(--danger-color, #f5222d);
  color: white;
}

.btn-danger:hover {
  background-color: #ff4d4f;
}

.btn-danger:disabled {
  background-color: #ffccc7;
  cursor: not-allowed;
}
</style>

<!-- 添加全局打印样式 -->
<style>
/* PDF打印样式 */
@media print {
  body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    color: #000;
  }
  
  table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 15px;
    page-break-inside: avoid;
  }
  
  th, td {
    border: 1px solid #000;
    padding: 8px;
    text-align: left;
  }
  
  th {
    background-color: #f2f2f2;
    font-weight: bold;
  }
  
  h1, h2, h3 {
    margin-top: 20px;
    margin-bottom: 10px;
    line-height: 1.4;
    page-break-after: avoid;
  }
  
  p {
    margin-bottom: 10px;
  }
}
</style> 