import { defineStore } from 'pinia'
import axios from 'axios'

// 定义用户角色常量
export const USER_ROLE_SUPER_ADMIN = 'super_admin'
export const USER_ROLE_ADMIN = 'admin'
export const USER_ROLE_USER = 'user'
export const USER_ROLE_GUEST = 'guest'

// 用户API基础URL
const AUTH_API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5004/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: {
      id: null,
      name: '访客用户',
      username: null,
      email: null,
      avatar: null,
      role: USER_ROLE_GUEST,
      isSuperAdmin: false
    },
    token: null,
    isAuthenticated: false,
    preferences: {
      defaultCity: '广州',
      chartType: 'line', // 默认图表类型
      refreshInterval: 5 // 数据刷新间隔（分钟）
    },
    notifications: [],
    authLoading: false,
    authError: null
  }),
  
  getters: {
    isLoggedIn() {
      return this.isAuthenticated && !!this.token
    },
    unreadNotificationCount() {
      return this.notifications.filter(n => !n.read).length
    },
    authHeader() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {}
    },
    // 检查是否是管理员或超级管理员
    isAdmin() {
      return this.user.role === USER_ROLE_ADMIN || this.user.role === USER_ROLE_SUPER_ADMIN
    }
  },
  
  actions: {
    initializeSettings() {
      // 从本地存储加载用户偏好设置
      const savedPreferences = localStorage.getItem('user_preferences')
      if (savedPreferences) {
        this.preferences = JSON.parse(savedPreferences)
      }
      
      // 从本地存储加载通知
      const savedNotifications = localStorage.getItem('user_notifications')
      if (savedNotifications) {
        this.notifications = JSON.parse(savedNotifications)
      }
      
      // 从本地存储加载令牌
      const savedToken = localStorage.getItem('auth_token')
      if (savedToken) {
        this.token = savedToken
        this.validateToken()
      }
    },
    
    async login(credentials) {
      try {
        this.authLoading = true
        this.authError = null
        
        const response = await axios.post(`${AUTH_API_URL}/login`, credentials, {
          withCredentials: true,
          timeout: 10000
        })
        
        if (response.data.success) {
          const { token, user } = response.data
          
          // 保存令牌到本地存储
          localStorage.setItem('auth_token', token)
          
          // 更新状态
          this.token = token
          this.user = {
            id: user.id,
            name: user.username,
            username: user.username,
            email: user.email,
            role: user.role,
            avatar: user.avatar || null,
            isSuperAdmin: user.role === USER_ROLE_SUPER_ADMIN
          }
          this.isAuthenticated = true
          
          return { success: true }
        }
        
        return { success: false, message: response.data.message || '登录失败' }
      } catch (error) {
        this.authError = error.response?.data?.message || '登录时发生错误'
        return { 
          success: false, 
          message: this.authError
        }
      } finally {
        this.authLoading = false
      }
    },
    
    async register(userData) {
      try {
        this.authLoading = true
        this.authError = null
        
        const response = await axios.post(`${AUTH_API_URL}/register`, userData, {
          withCredentials: true,
          timeout: 10000
        })
        
        if (response.data.success) {
          const { token, user } = response.data
          
          // 保存令牌到本地存储
          localStorage.setItem('auth_token', token)
          
          // 更新状态
          this.token = token
          this.user = {
            id: user.id,
            name: user.username,
            username: user.username,
            email: user.email,
            role: user.role,
            avatar: user.avatar || null,
            isSuperAdmin: user.role === USER_ROLE_SUPER_ADMIN
          }
          this.isAuthenticated = true
          
          return { success: true }
        }
        
        return { success: false, message: response.data.message || '注册失败' }
      } catch (error) {
        this.authError = error.response?.data?.message || '注册时发生错误'
        return { 
          success: false, 
          message: this.authError
        }
      } finally {
        this.authLoading = false
      }
    },
    
    async validateToken() {
      if (!this.token) return { success: false }
      
      try {
        const response = await axios.get(`${AUTH_API_URL}/validate`, {
          headers: { Authorization: `Bearer ${this.token}` },
          timeout: 5000,
          withCredentials: true
        })
        
        // 检查HTTP状态
        if (response.status !== 200) {
          // 如果服务器错误，我们仍然保持用户当前状态而不强制登出
          if (response.status >= 500) {
            return { success: true, serverError: true };
          }
          
          // 其他错误则清除令牌
          this.logout();
          return { success: false };
        }
        
        if (response.data && response.data.success) {
          const { user } = response.data
          
          // 更新用户信息
          this.user = {
            id: user.id,
            name: user.username,
            username: user.username,
            email: user.email,
            role: user.role,
            avatar: user.avatar || null,
            isSuperAdmin: user.isSuperAdmin
          }
          this.isAuthenticated = true
          
          return { success: true }
        }
        
        // 验证失败，清除令牌
        this.logout()
        return { success: false }
      } catch (error) {
        // 如果是网络错误或超时错误，不登出用户
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout') || 
            error.message.includes('Network Error')) {
          return { success: true, networkError: true };
        }
        
        // 其他错误，清除令牌
        this.logout()
        return { success: false }
      }
    },
    
    async getUserInfo() {
      if (!this.token || !this.isAuthenticated) return null
      
      try {
        const response = await axios.get(`${AUTH_API_URL}/user`, {
          headers: { Authorization: `Bearer ${this.token}` },
          withCredentials: true,
          timeout: 5000
        })
        
        if (response.data.success) {
          return response.data.user
        }
        
        return null
      } catch (error) {
        return null
      }
    },
    
    logout() {
      // 清除令牌
      localStorage.removeItem('auth_token')
      
      // 重置状态
      this.token = null
      this.isAuthenticated = false
      this.user = {
        id: null,
        name: '访客用户',
        username: null,
        email: null,
        avatar: null,
        role: USER_ROLE_GUEST,
        isSuperAdmin: false
      }
    },
    
    setChartType(type) {
      this.preferences.chartType = type
      this.savePreferences()
    },
    
    setRefreshInterval(minutes) {
      this.preferences.refreshInterval = minutes
      this.savePreferences()
    },
    
    setDefaultCity(city) {
      this.preferences.defaultCity = city
      this.savePreferences()
    },
    
    savePreferences() {
      localStorage.setItem('user_preferences', JSON.stringify(this.preferences))
    },
    
    addNotification(notification) {
      // 添加通知
      const id = Date.now()
      this.notifications.unshift({
        id,
        title: notification.title,
        message: notification.message,
        type: notification.type || 'info',
        read: false,
        time: new Date().toISOString()
      })
      
      // 保存到本地存储
      this.saveNotifications()
      
      return id
    },
    
    markNotificationAsRead(id) {
      const notification = this.notifications.find(n => n.id === id)
      if (notification) {
        notification.read = true
        this.saveNotifications()
      }
    },
    
    deleteNotification(id) {
      this.notifications = this.notifications.filter(n => n.id !== id)
      this.saveNotifications()
    },
    
    saveNotifications() {
      localStorage.setItem('user_notifications', JSON.stringify(this.notifications))
    }
  }
}) 