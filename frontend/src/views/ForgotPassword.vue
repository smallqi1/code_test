<template>
  <div class="forgot-password-container">
    <div class="forgot-password-card">
      <div class="header">
        <h2>{{ currentStep === 'verify-answers' ? '验证密保问题' : currentStep === 'reset' ? '重置密码' : '忘记密码' }}</h2>
        <p v-if="currentStep === 'start'">请输入您的用户名或邮箱，以找回您的密码</p>
        <p v-else-if="currentStep === 'verify-answers'">请回答您之前设置的密保问题，至少2个问题答案正确才能重置密码</p>
        <p v-else-if="currentStep === 'reset'">请输入您的新密码</p>
      </div>
      
      <!-- 第一步：输入用户名 -->
      <form v-if="currentStep === 'start'" @submit.prevent="findUser" class="form">
        <div class="form-group">
          <label for="username">用户名或邮箱</label>
          <input 
            type="text" 
            id="username" 
            v-model="username" 
            placeholder="请输入用户名或邮箱"
            required
          />
        </div>
        
        <div class="error-message" v-if="errorMessage">
          {{ errorMessage }}
        </div>
        
        <div class="actions">
          <button 
            type="submit" 
            class="primary-button"
            :disabled="isLoading"
          >
            <span v-if="isLoading">查询中...</span>
            <span v-else>下一步</span>
          </button>
          <router-link to="/login" class="back-link">返回登录</router-link>
        </div>
      </form>
      
      <!-- 第二步：回答密保问题 -->
      <form v-if="currentStep === 'verify-answers'" @submit.prevent="verifyAnswers" class="form">
        <div class="security-questions">
          <div 
            v-for="(question, index) in securityQuestions" 
            :key="index"
            class="question-item"
          >
            <label :for="`answer-${index}`">{{ question.question }}</label>
            <input 
              :id="`answer-${index}`" 
              v-model="securityAnswers[index].answer" 
              type="text" 
              placeholder="请输入答案"
              required
            />
          </div>
        </div>
        
        <div class="error-message" v-if="errorMessage">
          {{ errorMessage }}
        </div>
        
        <div class="actions">
          <button 
            type="submit" 
            class="primary-button"
            :disabled="isLoading"
          >
            <span v-if="isLoading">验证中...</span>
            <span v-else>下一步</span>
          </button>
          <button type="button" class="secondary-button" @click="goBack">返回上一步</button>
        </div>
      </form>
      
      <!-- 第三步：重置密码 -->
      <form v-if="currentStep === 'reset'" @submit.prevent="resetPassword" class="form">
        <div class="form-group">
          <label for="newPassword">新密码</label>
          <input 
            type="password" 
            id="newPassword" 
            v-model="newPassword" 
            placeholder="请输入新密码"
            required
          />
          <p class="password-hint">密码必须至少8个字符，并包含字母和数字</p>
        </div>
        
        <div class="form-group">
          <label for="confirmPassword">确认密码</label>
          <input 
            type="password" 
            id="confirmPassword" 
            v-model="confirmPassword" 
            placeholder="请再次输入新密码"
            required
          />
        </div>
        
        <div class="error-message" v-if="errorMessage">
          {{ errorMessage }}
        </div>
        
        <div class="success-message" v-if="successMessage">
          {{ successMessage }}
        </div>
        
        <div class="actions">
          <button 
            type="submit" 
            class="primary-button"
            :disabled="isLoading || !!successMessage"
          >
            <span v-if="isLoading">重置中...</span>
            <span v-else>重置密码</span>
          </button>
          <button 
            v-if="successMessage" 
            type="button" 
            class="success-button" 
            @click="goToLogin"
          >
            返回登录
          </button>
          <button v-else type="button" class="secondary-button" @click="goBack">返回上一步</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const AUTH_API_URL = 'http://localhost:5004/api/auth';
const router = useRouter();

// 状态
const currentStep = ref('start');
const username = ref('');
const errorMessage = ref('');
const successMessage = ref('');
const isLoading = ref(false);
const userId = ref(null);
const resetToken = ref('');
const verificationToken = ref('');

// 密保问题相关
const securityQuestions = ref([]);
const securityAnswers = reactive([
  { answer: '' },
  { answer: '' },
  { answer: '' }
]);

// 重置密码表单
const newPassword = ref('');
const confirmPassword = ref('');

// 查找用户
const findUser = async () => {
  if (!username.value.trim()) {
    errorMessage.value = '请输入用户名或邮箱';
    return;
  }
  
  errorMessage.value = '';
  isLoading.value = true;
  
  try {
    const response = await axios.post(`${AUTH_API_URL}/forgot-password`, {
      username: username.value
    });
    
    if (response.data.success) {
      // 保存用户ID和密保问题
      userId.value = response.data.userId;
      resetToken.value = response.data.resetToken;
      securityQuestions.value = response.data.questions;
      
      // 确保securityAnswers数组包含与问题数量相同的项
      while (securityAnswers.length < securityQuestions.value.length) {
        securityAnswers.push({ answer: '' });
      }
      
      // 进入下一步
      currentStep.value = 'verify-answers';
    } else {
      errorMessage.value = response.data.message || '找不到用户信息';
    }
  } catch (error) {
    console.error('找回密码错误:', error);
    errorMessage.value = error.response?.data?.message || '操作失败，请稍后重试';
  } finally {
    isLoading.value = false;
  }
};

// 验证密保问题答案
const verifyAnswers = async () => {
  // 检查是否所有答案都已填写
  const emptyAnswers = securityAnswers.filter(item => !item.answer.trim()).length;
  if (emptyAnswers > 0) {
    errorMessage.value = '请回答所有密保问题';
    return;
  }
  
  errorMessage.value = '';
  isLoading.value = true;
  
  try {
    const response = await axios.post(`${AUTH_API_URL}/verify-security-answers`, {
      userId: userId.value,
      resetToken: resetToken.value,
      answers: securityAnswers.map((item, index) => ({
        id: index,
        answer: item.answer
      }))
    });
    
    if (response.data.success) {
      // 保存验证令牌
      verificationToken.value = response.data.verificationToken;
      
      // 进入下一步
      currentStep.value = 'reset';
    } else {
      errorMessage.value = response.data.message || '密保问题验证失败';
    }
  } catch (error) {
    console.error('验证密保问题错误:', error);
    errorMessage.value = error.response?.data?.message || '验证失败，请稍后重试';
  } finally {
    isLoading.value = false;
  }
};

// 重置密码
const resetPassword = async () => {
  // 验证新密码
  if (newPassword.value.length < 8) {
    errorMessage.value = '密码长度必须至少为8个字符';
    return;
  }
  
  if (!/[A-Za-z]/.test(newPassword.value) || !/[0-9]/.test(newPassword.value)) {
    errorMessage.value = '密码必须包含字母和数字';
    return;
  }
  
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致';
    return;
  }
  
  errorMessage.value = '';
  successMessage.value = '';
  isLoading.value = true;
  
  try {
    const response = await axios.post(`${AUTH_API_URL}/reset-password`, {
      userId: userId.value,
      verificationToken: verificationToken.value,
      newPassword: newPassword.value
    });
    
    if (response.data.success) {
      successMessage.value = response.data.message || '密码重置成功，请使用新密码登录';
      
      // 清空表单
      newPassword.value = '';
      confirmPassword.value = '';
    } else {
      errorMessage.value = response.data.message || '密码重置失败';
    }
  } catch (error) {
    console.error('重置密码错误:', error);
    errorMessage.value = error.response?.data?.message || '重置失败，请稍后重试';
  } finally {
    isLoading.value = false;
  }
};

// 返回上一步
const goBack = () => {
  if (currentStep.value === 'verify-answers') {
    currentStep.value = 'start';
  } else if (currentStep.value === 'reset') {
    currentStep.value = 'verify-answers';
  }
  
  // 清除错误消息
  errorMessage.value = '';
};

// 前往登录页
const goToLogin = () => {
  router.push('/login');
};
</script>

<style scoped>
.forgot-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f8fa;
  padding: 20px;
}

.forgot-password-card {
  width: 100%;
  max-width: 500px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  padding: 30px;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h2 {
  font-size: 24px;
  color: #1a2942;
  margin-bottom: 10px;
}

.header p {
  color: #667085;
  font-size: 16px;
  line-height: 1.5;
}

.form {
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
  padding: 12px 16px;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  background-color: white;
  font-size: 16px;
  color: #1d2939;
  transition: border-color 0.3s;
}

.form-group input:focus {
  border-color: #2e90fa;
  outline: none;
  box-shadow: 0 0 0 4px rgba(46, 144, 250, 0.1);
}

.password-hint {
  font-size: 12px;
  color: #667085;
  margin-top: 6px;
}

.error-message {
  background-color: #fef3f2;
  color: #b42318;
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.success-message {
  background-color: #ecfdf3;
  color: #027a48;
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.primary-button {
  padding: 12px 20px;
  background-color: #2e90fa;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.primary-button:hover {
  background-color: #1570cd;
}

.primary-button:disabled {
  background-color: #b2ddff;
  cursor: not-allowed;
}

.secondary-button {
  padding: 12px 20px;
  background-color: white;
  color: #344054;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.secondary-button:hover {
  background-color: #f9fafb;
}

.success-button {
  padding: 12px 20px;
  background-color: #039855;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.success-button:hover {
  background-color: #027a48;
}

.back-link {
  text-align: center;
  color: #667085;
  text-decoration: none;
  margin-top: 8px;
  font-size: 14px;
}

.back-link:hover {
  color: #1570cd;
  text-decoration: underline;
}

.security-questions {
  margin-bottom: 20px;
}

.question-item {
  margin-bottom: 20px;
  padding: 15px;
  border-radius: 8px;
  background-color: #f9fafb;
}

.question-item label {
  display: block;
  font-weight: 500;
  margin-bottom: 8px;
  color: #344054;
}

.question-item input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  font-size: 14px;
}
</style> 