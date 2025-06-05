<template>
  <div class="user-management">
    <h1 class="page-title">用户管理</h1>
    
    <div class="admin-panel">
      <div class="table-operations">
        <div class="search-box">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索用户名或邮箱" 
            @input="filterUsers"
          />
          <i class="icon-search"></i>
        </div>
        
        <div class="filter-box">
          <select v-model="statusFilter" @change="filterUsers">
            <option value="all">所有状态</option>
            <option value="active">正常</option>
            <option value="banned">已封禁</option>
          </select>
        </div>
        
        <div class="filter-box">
          <select v-model="roleFilter" @change="filterUsers">
            <option value="all">所有角色</option>
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
            <option value="super_admin">超级管理者</option>
          </select>
        </div>
        
        <button class="refresh-btn" @click="loadUsers" :disabled="loading">
          <i class="icon-refresh"></i> 刷新
        </button>
      </div>
      
      <div class="info-bar" v-if="userStore.user.isSuperAdmin">
        <div class="admin-count">
          当前管理员: <strong>{{ adminCount }}</strong> / 最大: <strong>{{ maxAdminCount }}</strong>
        </div>
      </div>
      
      <div class="loading-indicator" v-if="loading">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      
      <div class="error-message" v-if="error">
        {{ error }}
      </div>
      
      <div class="table-container" v-if="!loading && !error">
        <table class="users-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>用户名</th>
              <th>邮箱</th>
              <th>角色</th>
              <th>状态</th>
              <th>注册时间</th>
              <th>最后登录</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredUsers" :key="user.id" 
                :class="{
                  'banned-user': user.status === 'banned',
                  'admin-user': user.role === 'admin',
                  'super-admin-user': user.role === 'super_admin'
                }">
              <td>{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
              <td>
                <span class="role-badge" :class="getRoleBadgeClass(user.role)">
                  <template v-if="user.role === 'admin'">管理员</template>
                  <template v-else-if="user.role === 'super_admin'">超级管理者</template>
                  <template v-else>普通用户</template>
                </span>
              </td>
              <td>
                <span class="status-badge" :class="getStatusBadgeClass(user.status)">
                  {{ user.status === 'active' ? '正常' : '已封禁' }}
                </span>
              </td>
              <td>{{ formatDate(user.created_at) }}</td>
              <td>{{ formatDate(user.last_login) }}</td>
              <td>
                <div class="action-buttons">
                  <!-- 超级管理者可以管理管理员角色 -->
                  <template v-if="userStore.user.isSuperAdmin && user.role !== 'super_admin'">
                    <button 
                      v-if="user.role === 'user' && adminCount < maxAdminCount"
                      class="action-btn promote-btn"
                      @click="showChangeRoleConfirm(user, 'admin')"
                      title="提升为管理员"
                    >
                      提升为管理员
                    </button>
                    
                    <button 
                      v-if="user.role === 'admin'"
                      class="action-btn demote-btn"
                      @click="showChangeRoleConfirm(user, 'user')"
                      title="降级为普通用户"
                    >
                      降级为用户
                    </button>
                  </template>
                  
                  <!-- 状态控制按钮 -->
                  <button 
                    class="action-btn" 
                    :class="user.status === 'active' ? 'ban-btn' : 'unban-btn'"
                    @click="toggleUserStatus(user)"
                    :disabled="cannotManageUser(user)"
                    :title="getStatusActionTitle(user)"
                  >
                    {{ user.status === 'active' ? '封禁' : '解封' }}
                  </button>
                </div>
              </td>
            </tr>
            
            <tr v-if="filteredUsers.length === 0">
              <td colspan="8" class="no-data">没有找到符合条件的用户</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    
    <!-- 确认对话框 - 状态更改 -->
    <div class="modal" v-if="showConfirmModal">
      <div class="modal-content">
        <h3>{{ confirmAction === 'ban' ? '封禁用户' : '解封用户' }}</h3>
        <p>您确定要{{ confirmAction === 'ban' ? '封禁' : '解封' }}用户 <strong>{{ selectedUser?.username }}</strong> 吗？</p>
        
        <div class="modal-actions">
          <button class="btn-cancel" @click="showConfirmModal = false">取消</button>
          <button 
            class="btn-confirm" 
            :class="confirmAction === 'ban' ? 'btn-danger' : 'btn-success'"
            @click="confirmStatusChange"
          >
            确认{{ confirmAction === 'ban' ? '封禁' : '解封' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- 确认对话框 - 角色更改 -->
    <div class="modal" v-if="showRoleModal">
      <div class="modal-content">
        <h3>{{ newRole === 'admin' ? '提升为管理员' : '降级为普通用户' }}</h3>
        <p>您确定要将用户 <strong>{{ selectedUser?.username }}</strong> {{ newRole === 'admin' ? '提升为管理员' : '降级为普通用户' }}吗？</p>
        
        <div class="modal-actions">
          <button class="btn-cancel" @click="showRoleModal = false">取消</button>
          <button 
            class="btn-confirm" 
            :class="newRole === 'admin' ? 'btn-primary' : 'btn-warning'"
            @click="confirmRoleChange"
          >
            确认{{ newRole === 'admin' ? '提升' : '降级' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { useUserStore } from '@/store/userStore'
import { useRouter } from 'vue-router'

// 正确的API URL - 确保与后端服务器的地址和端口匹配
const AUTH_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5004/api'
// 请求超时时间（毫秒）
const REQUEST_TIMEOUT = 10000 

// 状态
const users = ref([])
const loading = ref(false)
const error = ref(null)
const searchQuery = ref('')
const statusFilter = ref('all')
const roleFilter = ref('all')
const showConfirmModal = ref(false)
const showRoleModal = ref(false)
const selectedUser = ref(null)
const confirmAction = ref('')
const newRole = ref('')
const adminCount = ref(0)
const maxAdminCount = ref(5)

// 获取user store
const userStore = useUserStore()
const router = useRouter()

// 计算属性
const filteredUsers = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  
  return users.value.filter(user => {
    // 先应用状态过滤
    if (statusFilter.value !== 'all' && user.status !== statusFilter.value) {
      return false
    }
    
    // 应用角色过滤
    if (roleFilter.value !== 'all' && user.role !== roleFilter.value) {
      return false
    }
    
    // 再应用搜索过滤
    if (query) {
      return user.username.toLowerCase().includes(query) || 
             user.email.toLowerCase().includes(query)
    }
    
    return true
  })
})

// 方法
const loadUsers = async () => {
  if (!userStore.isLoggedIn || (userStore.user.role !== 'admin' && userStore.user.role !== 'super_admin')) {
    router.push('/')
    return
  }
  
  loading.value = true
  error.value = null
  
  try {
    const response = await axios.get(`${AUTH_API_URL}/admin/users`, {
      headers: { Authorization: `Bearer ${userStore.token}` },
      timeout: REQUEST_TIMEOUT,
      withCredentials: true
    })
    
    if (response.data.success) {
      users.value = response.data.users
      
      // 计算管理员数量
      adminCount.value = users.value.filter(user => 
        user.role === 'admin' && user.status === 'active'
      ).length
    } else {
      error.value = response.data.message || '加载用户列表失败'
    }
  } catch (err) {
    console.error('加载用户错误:', err)
    
    if (err.response) {
      // 服务器返回了错误状态码
      if (err.response.status === 403) {
        error.value = '权限不足，无法访问用户管理'
      } else {
        error.value = `服务器错误: ${err.response.status} - ${err.response.data?.message || '未知错误'}`
      }
    } else if (err.request) {
      // 请求已发送但没有收到响应
      error.value = '无法连接到服务器，请检查网络连接或服务器状态'
    } else {
      // 请求设置时出错
      error.value = '请求错误: ' + err.message
    }
  } finally {
    loading.value = false
  }
}

// 切换用户状态（封禁/解封）
const toggleUserStatus = (user) => {
  // 权限检查 - 由后端进一步验证
  if (cannotManageUser(user)) {
    return
  }
  
  selectedUser.value = user
  confirmAction.value = user.status === 'active' ? 'ban' : 'unban'
  showConfirmModal.value = true
}

// 确认状态变更操作
const confirmStatusChange = async () => {
  if (!selectedUser.value) return
  
  const newStatus = selectedUser.value.status === 'active' ? 'banned' : 'active'
  
  try {
    const response = await axios.put(
      `${AUTH_API_URL}/admin/users/${selectedUser.value.id}/status`, 
      { status: newStatus },
      { 
        headers: { Authorization: `Bearer ${userStore.token}` },
        timeout: REQUEST_TIMEOUT,
        withCredentials: true 
      }
    )
    
    if (response.data.success) {
      // 更新本地用户列表中的状态
      const user = users.value.find(u => u.id === selectedUser.value.id)
      if (user) {
        user.status = newStatus
      }
      
      // 如果是封禁管理员，更新管理员计数
      if (user.role === 'admin') {
        adminCount.value = users.value.filter(u => 
          u.role === 'admin' && u.status === 'active'
        ).length
      }
      
      // 显示成功消息
      alert(response.data.message)
    } else {
      alert('操作失败: ' + response.data.message)
    }
  } catch (err) {
    console.error('更新用户状态错误:', err)
    let errorMessage = '更新用户状态时发生错误'
    
    if (err.response && err.response.data && err.response.data.message) {
      errorMessage += ': ' + err.response.data.message
    }
    
    alert(errorMessage)
  } finally {
    showConfirmModal.value = false
    selectedUser.value = null
  }
}

// 显示角色变更确认
const showChangeRoleConfirm = (user, role) => {
  selectedUser.value = user
  newRole.value = role
  showRoleModal.value = true
}

// 确认角色变更操作
const confirmRoleChange = async () => {
  if (!selectedUser.value || !newRole.value) return
  
  try {
    const response = await axios.put(
      `${AUTH_API_URL}/admin/users/${selectedUser.value.id}/role`, 
      { role: newRole.value },
      { 
        headers: { Authorization: `Bearer ${userStore.token}` },
        timeout: REQUEST_TIMEOUT,
        withCredentials: true 
      }
    )
    
    if (response.data.success) {
      // 更新本地用户列表中的角色
      const user = users.value.find(u => u.id === selectedUser.value.id)
      if (user) {
        user.role = newRole.value
      }
      
      // 更新管理员计数
      adminCount.value = users.value.filter(u => 
        u.role === 'admin' && u.status === 'active'
      ).length
      
      // 显示成功消息
      alert(response.data.message)
    } else {
      alert('操作失败: ' + response.data.message)
    }
  } catch (err) {
    console.error('更新用户角色错误:', err)
    let errorMessage = '更新用户角色时发生错误'
    
    if (err.response && err.response.data && err.response.data.message) {
      errorMessage += ': ' + err.response.data.message
    }
    
    alert(errorMessage)
  } finally {
    showRoleModal.value = false
    selectedUser.value = null
    newRole.value = ''
  }
}

// 检查是否不能管理用户状态
const cannotManageUser = (user) => {
  // 不能修改自己
  if (isCurrentUser(user.id)) {
    return true
  }
  
  // 超级管理者可以管理管理员
  if (userStore.user.isSuperAdmin) {
    // 但不能管理其他超级管理者
    return user.role === 'super_admin'
  }
  
  // 普通管理员不能管理其他管理员
  return user.role === 'admin' || user.role === 'super_admin'
}

// 获取用户状态操作的提示信息
const getStatusActionTitle = (user) => {
  if (isCurrentUser(user.id)) {
    return '不能修改自己的状态'
  }
  
  if (user.role === 'super_admin') {
    return '不能修改超级管理者的状态'
  }
  
  if (user.role === 'admin' && !userStore.user.isSuperAdmin) {
    return '普通管理员不能修改其他管理员的状态'
  }
  
  return user.status === 'active' ? '封禁此用户' : '解封此用户'
}

const filterUsers = () => {
  // 仅用于触发计算属性重新计算
}

const isCurrentUser = (userId) => {
  return userStore.user.id === userId
}

const formatDate = (dateStr) => {
  if (!dateStr) return '从未'
  return dateStr
}

const getRoleBadgeClass = (role) => {
  return {
    'role-super-admin': role === 'super_admin',
    'role-admin': role === 'admin',
    'role-user': role === 'user'
  }
}

const getStatusBadgeClass = (status) => {
  return {
    'status-active': status === 'active',
    'status-banned': status === 'banned'
  }
}

// 监听用户角色变化，及时更新界面状态
watch(() => userStore.user.role, (newRole) => {
  if (newRole !== 'admin' && newRole !== 'super_admin') {
    router.push('/')
  }
})

// 生命周期钩子
onMounted(() => {
  // 检查用户是否是管理员
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  
  if (userStore.user.role !== 'admin' && userStore.user.role !== 'super_admin') {
    router.push('/')
    return
  }
  
  loadUsers()
})
</script>

<style scoped>
.user-management-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  margin-bottom: 20px;
  color: #1a2942;
}

.admin-panel {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.table-operations {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  gap: 15px;
  flex-wrap: wrap;
}

.info-bar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  background-color: #f0f9ff;
  padding: 10px 15px;
  border-radius: 6px;
  border-left: 3px solid #1976d2;
}

.admin-count {
  font-size: 14px;
  color: #1976d2;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 200px;
}

.search-box input {
  width: 100%;
  padding: 10px 15px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 14px;
}

.filter-box select {
  padding: 10px 15px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 14px;
  background-color: white;
  min-width: 120px;
}

.refresh-btn {
  background-color: #f0f0f0;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  padding: 0 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}

.refresh-btn:hover {
  background-color: #e0e0e0;
}

.loading-indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 30px;
  gap: 10px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3b96ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #e53935;
  text-align: center;
  padding: 20px;
}

.table-container {
  overflow-x: auto;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th,
.users-table td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.users-table th {
  background-color: #f9fafb;
  font-weight: 600;
  color: #344054;
}

.users-table tbody tr:hover {
  background-color: #f5f8ff;
}

.banned-user {
  background-color: #fff8f8;
}

.admin-user {
  background-color: #f0f7ff;
}

.super-admin-user {
  background-color: #f0f5ff;
  border-left: 3px solid #1976d2;
}

.role-badge, .status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.role-super-admin {
  background-color: #bbdefb;
  color: #0d47a1;
}

.role-admin {
  background-color: #e0f7fa;
  color: #00796b;
}

.role-user {
  background-color: #f0f4ff;
  color: #3b5998;
}

.status-active {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.status-banned {
  background-color: #ffebee;
  color: #c62828;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  border: none;
  border-radius: 4px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  font-weight: 500;
  white-space: nowrap;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ban-btn {
  background-color: #ffebee;
  color: #c62828;
}

.ban-btn:hover:not(:disabled) {
  background-color: #ffcdd2;
}

.unban-btn {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.unban-btn:hover:not(:disabled) {
  background-color: #c8e6c9;
}

.promote-btn {
  background-color: #e3f2fd;
  color: #1565c0;
}

.promote-btn:hover:not(:disabled) {
  background-color: #bbdefb;
}

.demote-btn {
  background-color: #fff8e1;
  color: #ff8f00;
}

.demote-btn:hover:not(:disabled) {
  background-color: #ffe082;
}

.no-data {
  text-align: center;
  color: #666;
  padding: 30px;
}

/* 确认对话框样式 - 使用更具体的选择器 */
.user-management .modal {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 1000 !important;
  width: 100vw !important;
  height: 100vh !important;
  transform: none !important;
}

.user-management .modal-content {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  width: 400px;
  max-width: 90%;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  position: relative !important;
  margin: 0 !important;
  transform: none !important;
}

.modal-content h3 {
  margin-top: 0;
  color: #1a2942;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  gap: 10px;
}

.btn-cancel, .btn-confirm {
  padding: 8px 16px;
  border-radius: 4px;
  border: none;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  background-color: #f0f0f0;
  color: #666;
}

.btn-confirm {
  color: white;
}

.btn-danger {
  background-color: #e53935;
}

.btn-success {
  background-color: #4caf50;
}

.btn-primary {
  background-color: #1976d2;
}

.btn-warning {
  background-color: #ff9800;
}

@media (max-width: 768px) {
  .table-operations {
    flex-direction: column;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>