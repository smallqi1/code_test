<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h2>用户登录</h2>
        <p>请登录以访问更多功能</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label for="username">用户名或邮箱</label>
          <input 
            type="text" 
            id="username" 
            v-model="loginForm.username" 
            placeholder="请输入用户名或邮箱"
            required
          />
          <span class="error-text" v-if="validationErrors.username">{{ validationErrors.username }}</span>
        </div>
        
        <div class="form-group">
          <label for="password">密码</label>
          <div class="password-input">
            <input 
              :type="showPassword ? 'text' : 'password'" 
              id="password" 
              v-model="loginForm.password" 
              placeholder="请输入密码"
              required
            />
            <button 
              type="button" 
              class="toggle-password"
              @click="showPassword = !showPassword"
            >
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>
          <span class="error-text" v-if="validationErrors.password">{{ validationErrors.password }}</span>
        </div>
        
        <div class="form-options">
          <div class="remember-me">
            <input type="checkbox" id="remember" v-model="loginForm.remember" />
            <label for="remember">记住我</label>
          </div>
          
          <router-link to="/forgot-password" class="forgot-password">忘记密码?</router-link>
        </div>
        
        <div class="error-message" v-if="loginError">
          {{ loginError }}
        </div>
        
        <button 
          type="submit" 
          class="login-button"
          :disabled="isLoading"
        >
          <span v-if="isLoading">登录中...</span>
          <span v-else>登录</span>
        </button>
      </form>
      
      <div class="login-footer">
        <p>还没有账号? <router-link to="/register">立即注册</router-link></p>
        <p><router-link to="/">返回首页</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'

const router = useRouter()
const userStore = useUserStore()

// 状态
const showPassword = ref(false)
const loginError = ref('')
const validationErrors = reactive({
  username: '',
  password: ''
})

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  remember: false
})

// 计算属性
const isLoading = computed(() => userStore.authLoading)

// 方法
const validateForm = () => {
  // 重置错误信息
  loginError.value = ''
  validationErrors.username = ''
  validationErrors.password = ''
  
  let isValid = true
  
  // 验证用户名/邮箱
  if (!loginForm.username.trim()) {
    validationErrors.username = '请输入用户名或邮箱'
    isValid = false
  }
  
  // 验证密码
  if (!loginForm.password.trim()) {
    validationErrors.password = '请输入密码'
    isValid = false
  }
  
  return isValid
}

const handleLogin = async () => {
  // 表单验证
  if (!validateForm()) return
  
  try {
    // 调用登录
    const result = await userStore.login({
      username: loginForm.username,
      password: loginForm.password
    })
    
    if (result.success) {
      // 登录成功，跳转到首页
      router.push('/')
    } else {
      // 登录失败，显示错误信息
      loginError.value = result.message || '登录失败，请检查用户名和密码'
    }
  } catch (error) {
    loginError.value = '登录过程中发生错误，请稍后重试'
    console.error('登录错误:', error)
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f8fa;
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 450px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  font-size: 24px;
  color: #1a2942;
  margin-bottom: 10px;
}

.login-header p {
  color: #667085;
  font-size: 16px;
}

.login-form {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #344054;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 12px 15px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #3b96ff;
  box-shadow: 0 0 0 3px rgba(59, 150, 255, 0.15);
}

.password-input {
  position: relative;
}

.toggle-password {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #667085;
  cursor: pointer;
  font-size: 14px;
}

.toggle-password:hover {
  color: #3b96ff;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.remember-me {
  display: flex;
  align-items: center;
}

.remember-me input {
  margin-right: 8px;
}

.forgot-password {
  color: #3b96ff;
  text-decoration: none;
  font-size: 14px;
}

.forgot-password:hover {
  text-decoration: underline;
}

.login-button {
  width: 100%;
  padding: 12px;
  background-color: #3b96ff;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.login-button:hover {
  background-color: #2a7fd9;
}

.login-button:disabled {
  background-color: #95c1ff;
  cursor: not-allowed;
}

.login-footer {
  text-align: center;
  color: #667085;
  font-size: 14px;
}

.login-footer a {
  color: #3b96ff;
  text-decoration: none;
}

.login-footer a:hover {
  text-decoration: underline;
}

.error-message {
  background-color: #fef3f2;
  color: #b42318;
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
  text-align: center;
}

.error-text {
  color: #b42318;
  font-size: 12px;
  margin-top: 5px;
  display: block;
}
</style> 