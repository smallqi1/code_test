<template>
  <div class="main-layout">
    <div class="main-content">
      <!-- 左侧边栏 -->
      <aside class="sidebar">
        <nav class="main-nav">
          <ul>
            <li>
              <router-link to="/" class="nav-link" :class="{ active: currentRoute === 'home' }">
                <span>首页</span>
              </router-link>
            </li>
            <li v-for="route in filteredRoutes" :key="route.name">
              <router-link :to="route.path" class="nav-link" :class="{ active: currentRoute === route.name }">
                <span>{{ route.meta ? route.meta.title : route.name }}</span>
              </router-link>
            </li>
          </ul>
        </nav>
        
        <div class="sidebar-footer">
          <!-- 移动时间显示到这里 -->
          <div class="sidebar-time-display">
            <div class="time-display"> 
              <i class="time-icon">🕒</i>
              {{ currentTime }}
            </div>
          </div>
          
          <!-- 移动用户信息到这里 -->
          <div class="sidebar-user-info">
            <div class="user-menu" v-if="userStore.isLoggedIn">
              <button class="user-button" @click.stop="toggleUserMenu">
                <div class="avatar-container">
                  <img v-if="userStore.user.avatar" :src="userStore.user.avatar" alt="头像" class="user-avatar" />
                  <div v-else class="default-avatar">{{ userStore.user.username ? userStore.user.username.substring(0, 1).toUpperCase() : 'U' }}</div>
                </div>
                <span class="username">{{ userStore.user.username || userStore.user.name }}</span>
                <i class="arrow-icon">▼</i>
              </button>
              
              <div class="dropdown-menu" v-if="userMenuOpen" @click.stop>
                <div class="dropdown-header">
                  <strong>{{ userStore.user.username || userStore.user.name }}</strong>
                  <small>{{ userStore.user.email }}</small>
                </div>
                <ul class="dropdown-options">
                  <li>
                    <router-link to="/profile" class="menu-item" @click.stop="userMenuOpen = false">
                      个人中心
                    </router-link>
                  </li>
                  <li class="divider"></li>
                  <li>
                    <button @click.stop="logout" class="logout-button">
                      退出登录
                    </button>
                  </li>
                </ul>
              </div>
            </div>
            
            <div class="auth-buttons" v-else>
              <router-link to="/login" class="login-button">登录</router-link>
              <router-link to="/register" class="register-button">注册</router-link>
            </div>
          </div>
          
          <!-- 原来的版本号信息 -->
          <div class="version-info">
            v1.0.0
          </div>
        </div>
      </aside>
      
      <!-- 主要内容区域 -->
      <main class="content-area">
        <router-view v-slot="{ Component, route }">
          <keep-alive>
            <component :is="Component" :key="route.name" v-if="route.meta?.keepAlive" />
          </keep-alive>
          <component :is="Component" :key="route.name" v-if="!route.meta?.keepAlive" />
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 状态
const currentTime = ref(new Date().toLocaleString('zh-CN'))
const userMenuOpen = ref(false)

// 计算属性
const currentRoute = computed(() => route.name)
const filteredRoutes = computed(() => {
  // 获取用户角色
  const isAdmin = userStore.user.role === 'admin' || userStore.user.role === 'super_admin' || userStore.user.isSuperAdmin
  
  // 过滤出非首页的路由，避免重复显示
  return router.options.routes[0].children.filter(r => {
    // 基本条件：有标题且不是首页
    const basicCondition = r.meta && r.meta.title && r.name !== 'home'
    
    // 管理员路由检查：如果路由需要管理员权限，则只对管理员显示
    if (r.meta && r.meta.requiresAdmin) {
      return basicCondition && isAdmin
    }
    
    return basicCondition
  })
})

// 方法
const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

const toggleUserMenu = (event) => {
  event.stopPropagation() // 阻止事件冒泡
  userMenuOpen.value = !userMenuOpen.value
}

const logout = () => {
  userStore.logout()
  userMenuOpen.value = false
  router.push('/login')
}

// 点击页面其他地方关闭用户菜单
const closeUserMenu = (event) => {
  // 确保点击的不是菜单本身或其子元素
  const userMenuElement = document.querySelector('.user-menu')
  const dropdownElement = document.querySelector('.dropdown-menu')
  
  if (userMenuOpen.value && 
      userMenuElement && 
      !userMenuElement.contains(event.target) && 
      dropdownElement && 
      !dropdownElement.contains(event.target)) {
    userMenuOpen.value = false
  }
}

// 设置时间更新定时器
let timeInterval
onMounted(() => {
  timeInterval = setInterval(updateTime, 1000)
  
  // 添加点击外部关闭菜单的事件监听
  document.addEventListener('click', closeUserMenu)
})

onBeforeUnmount(() => {
  clearInterval(timeInterval)
  // 移除事件监听
  document.removeEventListener('click', closeUserMenu)
})
</script>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background-color: var(--body-bg);
  color: var(--text-primary);
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 220px;
  background-color: #e6f0ff;
  color: #333;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow-y: auto;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  border-right: 1px solid #d0e1ff;
}

.main-nav {
  padding: 20px 0;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  color: #2c3e50;
  text-decoration: none;
  transition: all 0.3s;
  border-left: 3px solid transparent;
  font-weight: 500;
  justify-content: center;
  margin: 2px 0;
  border-radius: 0 4px 4px 0;
}

/* 添加span样式使文本完全居中 */
.nav-link span {
  text-align: center;
  width: 100%;
}

.nav-link:hover, .nav-link.active {
  color: #1976d2;
  background-color: rgba(25, 118, 210, 0.1);
  border-left: 3px solid #1976d2;
}

.sidebar-footer {
  padding: 15px 0;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  margin-top: auto;
}

.sidebar-time-display {
  margin-bottom: 12px;
  padding: 0 15px;
}

.time-display {
  font-size: 13px;
  color: #1976d2;
  background-color: rgba(25, 118, 210, 0.08);
  padding: 6px 12px;
  border-radius: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
  white-space: nowrap;
  justify-content: center;
  border: 1px solid rgba(25, 118, 210, 0.15);
}

.time-icon {
  font-size: 13px;
  color: #1976d2;
}

.sidebar-user-info {
  padding: 0 15px;
  margin-bottom: 15px;
  position: relative;
  z-index: 10;
}

.version-info {
  font-size: 12px;
  color: #909399;
  text-align: center;
  padding: 0 15px;
}

.content-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: var(--body-bg);
}

.user-menu {
  position: relative;
  width: 100%;
  z-index: 100;
}

.user-button {
  display: flex;
  align-items: center;
  background-color: rgba(25, 118, 210, 0.08);
  border: 1px solid rgba(25, 118, 210, 0.2);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 20px;
  transition: all 0.3s;
  width: 100%;
  justify-content: center;
}

.user-button:hover {
  background-color: rgba(25, 118, 210, 0.12);
  transform: translateY(-2px);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.avatar-container {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  overflow: hidden;
  margin-right: 8px;
  border: 1px solid rgba(25, 118, 210, 0.3);
}

.user-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.default-avatar {
  width: 100%;
  height: 100%;
  background-color: #3b96ff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 16px;
  text-transform: uppercase;
}

.username {
  font-size: 13px;
  font-weight: 500;
  margin-right: 4px;
  color: #1976d2;
}

.arrow-icon {
  font-size: 9px;
  color: #1976d2;
  transition: transform 0.3s;
}

.dropdown-menu {
  position: absolute;
  top: auto;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 220px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
  margin-bottom: 10px;
  z-index: 1000;
  overflow: hidden;
  animation: menuAppear 0.2s ease-out;
}

@keyframes menuAppear {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.dropdown-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.dropdown-header strong {
  font-size: 15px;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.dropdown-header small {
  font-size: 13px;
  color: var(--text-secondary);
  word-break: break-all;
}

.dropdown-options {
  list-style: none;
  padding: 0;
  margin: 0;
}

.dropdown-options li {
  margin: 0;
}

.dropdown-options li a,
.dropdown-options li button {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  text-decoration: none;
  color: var(--text-primary);
  font-size: 15px;
  transition: background-color 0.2s;
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  font-weight: 500;
}

.dropdown-options li a:hover,
.dropdown-options li button:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.menu-item {
  color: var(--text-primary);
  display: block;
  width: 100%;
}

.divider {
  height: 1px;
  background-color: var(--border-color);
  margin: 5px 0;
}

.logout-button {
  color: #e53935;
}

.auth-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.login-button,
.register-button {
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.2s;
}

.login-button {
  color: #3b96ff;
  background-color: transparent;
  border: 1px solid #3b96ff;
}

.login-button:hover {
  background-color: rgba(59, 150, 255, 0.1);
}

.register-button {
  color: white;
  background-color: #3b96ff;
  border: 1px solid #3b96ff;
}

.register-button:hover {
  background-color: #2a7fd9;
  border-color: #2a7fd9;
}
</style> 