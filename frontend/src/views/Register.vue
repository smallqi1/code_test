<template>
  <div class="register-container">
    <div class="register-card">
      <div class="register-header">
        <h2>注册账号</h2>
        <p>创建账号以访问更多功能</p>
      </div>
      
      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label for="username">用户名</label>
          <input 
            type="text" 
            id="username" 
            v-model="registerForm.username" 
            placeholder="请输入用户名（3-20个字符）"
            required
          />
          <span class="error-text" v-if="validationErrors.username">{{ validationErrors.username }}</span>
        </div>
        
        <div class="form-group">
          <label for="email">邮箱</label>
          <input 
            type="email" 
            id="email" 
            v-model="registerForm.email" 
            placeholder="请输入邮箱"
            required
          />
          <span class="error-text" v-if="validationErrors.email">{{ validationErrors.email }}</span>
        </div>
        
        <div class="form-group">
          <label for="password">密码</label>
          <div class="password-input">
            <input 
              :type="showPassword ? 'text' : 'password'" 
              id="password" 
              v-model="registerForm.password" 
              placeholder="请输入密码（至少8位，包含字母和数字）"
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
        
        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <div class="password-input">
            <input 
              :type="showConfirmPassword ? 'text' : 'password'" 
              id="confirmPassword" 
              v-model="registerForm.confirmPassword" 
              placeholder="请再次输入密码"
              required
            />
            <button 
              type="button" 
              class="toggle-password"
              @click="showConfirmPassword = !showConfirmPassword"
            >
              {{ showConfirmPassword ? '隐藏' : '显示' }}
            </button>
          </div>
          <span class="error-text" v-if="validationErrors.confirmPassword">{{ validationErrors.confirmPassword }}</span>
        </div>
        
        <div class="form-agreement">
          <input type="checkbox" id="agreement" v-model="registerForm.agreement" required />
          <label for="agreement">
            我已阅读并同意 <a href="#" @click.prevent="showTerms = true">用户协议</a> 和 <a href="#" @click.prevent="showPrivacy = true">隐私政策</a>
          </label>
        </div>
        <span class="error-text" v-if="validationErrors.agreement">{{ validationErrors.agreement }}</span>
        
        <div class="error-message" v-if="registerError">
          {{ registerError }}
        </div>
        
        <button 
          type="submit" 
          class="register-button"
          :disabled="isLoading"
        >
          <span v-if="isLoading">注册中...</span>
          <span v-else>注册</span>
        </button>
      </form>
      
      <div class="register-footer">
        <p>已有账号? <router-link to="/login">立即登录</router-link></p>
        <p><router-link to="/">返回首页</router-link></p>
      </div>
    </div>
    
    <!-- 用户协议模态框 -->
    <div class="modal" v-if="showTerms">
      <div class="modal-content">
        <div class="modal-header">
          <h3>用户协议</h3>
          <button @click="showTerms = false" class="close-button">&times;</button>
        </div>
        <div class="modal-body">
          <h4>1. 接受条款</h4>
          <p>欢迎使用广东省空气质量监测系统。使用本系统即表示您已阅读并同意以下条款。</p>
          
          <h4>2. 服务描述</h4>
          <p>本系统提供广东省空气质量数据的监测、分析和预测服务，旨在为用户提供空气质量相关的信息支持。</p>
          
          <h4>3. 用户责任</h4>
          <p>用户应当遵守中国的法律法规，不得利用本系统从事违法活动。用户应妥善保管账号和密码，对账号下的所有行为负责。</p>
          
          <h4>4. 数据使用</h4>
          <p>本系统展示的数据仅供参考，不作为官方数据依据。用户在引用数据时，应注明数据来源。</p>
          
          <h4>5. 免责声明</h4>
          <p>系统不保证服务一定能满足用户的所有需求，也不保证服务不会中断。对于因网络、系统故障等原因导致的服务中断或数据丢失，本系统不承担责任。</p>
        </div>
        <div class="modal-footer">
          <button @click="showTerms = false" class="modal-button">我已阅读</button>
        </div>
      </div>
    </div>
    
    <!-- 隐私政策模态框 -->
    <div class="modal" v-if="showPrivacy">
      <div class="modal-content">
        <div class="modal-header">
          <h3>隐私政策</h3>
          <button @click="showPrivacy = false" class="close-button">&times;</button>
        </div>
        <div class="modal-body">
          <h4>1. 信息收集</h4>
          <p>我们收集的个人信息包括：用户名、邮箱地址和密码（加密存储）。</p>
          
          <h4>2. 信息使用</h4>
          <p>我们使用收集的信息用于提供、维护和改进服务，以及与用户进行沟通。</p>
          
          <h4>3. 信息安全</h4>
          <p>我们采取合理的安全措施保护用户信息，防止未经授权的访问、使用或披露。</p>
          
          <h4>4. Cookie使用</h4>
          <p>我们使用Cookie来改善用户体验，包括记住登录状态和用户偏好设置。</p>
          
          <h4>5. 信息共享</h4>
          <p>除非得到用户明确授权或法律要求，我们不会向第三方分享用户的个人信息。</p>
        </div>
        <div class="modal-footer">
          <button @click="showPrivacy = false" class="modal-button">我已阅读</button>
        </div>
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
const showConfirmPassword = ref(false)
const registerError = ref('')
const showTerms = ref(false)
const showPrivacy = ref(false)
const validationErrors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreement: ''
})

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreement: false
})

// 计算属性
const isLoading = computed(() => userStore.authLoading)

// 方法
const validateForm = () => {
  // 重置错误信息
  registerError.value = ''
  for (const key in validationErrors) {
    validationErrors[key] = ''
  }
  
  let isValid = true
  
  // 验证用户名
  if (!registerForm.username.trim()) {
    validationErrors.username = '请输入用户名'
    isValid = false
  } else if (registerForm.username.length < 3 || registerForm.username.length > 20) {
    validationErrors.username = '用户名长度必须在3到20个字符之间'
    isValid = false
  }
  
  // 验证邮箱
  if (!registerForm.email.trim()) {
    validationErrors.email = '请输入邮箱'
    isValid = false
  } else {
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    if (!emailPattern.test(registerForm.email)) {
      validationErrors.email = '请输入有效的邮箱地址'
      isValid = false
    }
  }
  
  // 验证密码
  if (!registerForm.password) {
    validationErrors.password = '请输入密码'
    isValid = false
  } else if (registerForm.password.length < 8) {
    validationErrors.password = '密码长度必须至少为8个字符'
    isValid = false
  } else if (!/[A-Za-z]/.test(registerForm.password) || !/[0-9]/.test(registerForm.password)) {
    validationErrors.password = '密码必须包含字母和数字'
    isValid = false
  }
  
  // 验证确认密码
  if (!registerForm.confirmPassword) {
    validationErrors.confirmPassword = '请确认密码'
    isValid = false
  } else if (registerForm.password !== registerForm.confirmPassword) {
    validationErrors.confirmPassword = '两次输入的密码不一致'
    isValid = false
  }
  
  // 验证协议同意
  if (!registerForm.agreement) {
    validationErrors.agreement = '请阅读并同意用户协议和隐私政策'
    isValid = false
  }
  
  return isValid
}

const handleRegister = async () => {
  // 表单验证
  if (!validateForm()) return
  
  try {
    // 调用注册
    const result = await userStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })
    
    if (result.success) {
      // 注册成功，跳转到首页
      router.push('/')
    } else {
      // 注册失败，显示错误信息
      registerError.value = result.message || '注册失败，请稍后重试'
    }
  } catch (error) {
    registerError.value = '注册过程中发生错误，请稍后重试'
    console.error('注册错误:', error)
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f8fa;
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 500px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h2 {
  font-size: 24px;
  color: #1a2942;
  margin-bottom: 10px;
}

.register-header p {
  color: #667085;
  font-size: 16px;
}

.register-form {
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

.form-agreement {
  display: flex;
  align-items: flex-start;
  margin-bottom: 20px;
}

.form-agreement input {
  margin-right: 10px;
  margin-top: 4px;
}

.form-agreement label {
  font-size: 14px;
  color: #667085;
  line-height: 1.5;
}

.form-agreement a {
  color: #3b96ff;
  text-decoration: none;
}

.form-agreement a:hover {
  text-decoration: underline;
}

.register-button {
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

.register-button:hover {
  background-color: #2a7fd9;
}

.register-button:disabled {
  background-color: #95c1ff;
  cursor: not-allowed;
}

.register-footer {
  text-align: center;
  color: #667085;
  font-size: 14px;
}

.register-footer a {
  color: #3b96ff;
  text-decoration: none;
}

.register-footer a:hover {
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

/* 模态框样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  border-radius: 10px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
}

.modal-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eeeeee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  color: #1a2942;
  font-size: 20px;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  font-weight: bold;
  color: #667085;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
  font-size: 14px;
  line-height: 1.6;
  color: #344054;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-body h4 {
  margin-top: 20px;
  margin-bottom: 10px;
  color: #1a2942;
}

.modal-body p {
  margin-bottom: 15px;
}

.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid #eeeeee;
  text-align: right;
}

.modal-button {
  background-color: #3b96ff;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
}

.modal-button:hover {
  background-color: #2a7fd9;
}
</style> 