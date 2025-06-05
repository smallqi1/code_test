<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <div class="card-header">
          <h2>个人中心</h2>
        </div>
      </template>
      
      <div class="profile-content">
        <div class="user-avatar">
          <div v-if="userStore.user.avatar" class="avatar-image">
            <img :src="userStore.user.avatar" alt="用户头像">
          </div>
          <div v-else class="default-avatar">
            {{ userStore.user.username ? userStore.user.username.substring(0, 1).toUpperCase() : 'U' }}
          </div>
        </div>
        
        <div class="user-info">
          <div class="info-item">
            <span class="label">用户名:</span>
            <span class="value">{{ userStore.user.username }}</span>
          </div>
          <div class="info-item">
            <span class="label">邮箱:</span>
            <span class="value">{{ userStore.user.email }}</span>
          </div>
          <div class="info-item">
            <span class="label">角色:</span>
            <span class="value">
              <template v-if="userStore.user.role === 'super_admin' || userStore.user.isSuperAdmin">超级管理者</template>
              <template v-else-if="userStore.user.role === 'admin'">管理员</template>
              <template v-else>普通用户</template>
            </span>
          </div>
          <div class="info-item">
            <span class="label">密保问题:</span>
            <span class="value">
              <template v-if="securityQuestionsStatus">
                已设置
                <el-button link @click="showSecurityQuestionsDialog">查看/修改</el-button>
              </template>
              <template v-else>
                未设置
                <el-button link @click="showSecurityQuestionsDialog">立即设置</el-button>
              </template>
            </span>
          </div>
        </div>
        
        <div class="action-buttons">
          <el-button type="primary" @click="showChangePasswordDialog">修改密码</el-button>
          <el-button type="danger" @click="confirmDeleteAccount">注销账号</el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="changePasswordDialogVisible"
      title="修改密码"
      width="400px"
      align-center
    >
      <el-form 
        :model="passwordForm" 
        :rules="passwordRules" 
        ref="passwordFormRef" 
        label-width="100px"
        status-icon
      >
        <el-form-item label="当前密码" prop="currentPassword">
          <el-input 
            v-model="passwordForm.currentPassword" 
            type="password" 
            show-password
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input 
            v-model="passwordForm.newPassword" 
            type="password" 
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input 
            v-model="passwordForm.confirmPassword" 
            type="password" 
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="changePasswordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="changePassword" :loading="loading">
            确认修改
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 设置密保问题对话框 -->
    <el-dialog
      v-model="securityQuestionsDialogVisible"
      :title="securityQuestionsStatus ? '修改密保问题' : '设置密保问题'"
      width="500px"
      align-center
    >
      <div class="security-questions-form">
        <p class="tip">请在以下7个问题中选择3个作为密保问题，并设置答案。忘记密码时，需要正确回答至少2个问题才能重置密码。</p>
        
        <el-form :model="securityForm" ref="securityFormRef" label-width="0">
          <div v-for="(item, index) in securityForm.questions" :key="index" class="question-item">
            <div class="question-header">问题 {{ index + 1 }}</div>
            <el-form-item :prop="`questions[${index}].question`" :rules="[{ required: true, message: '请选择密保问题', trigger: 'change' }]">
              <el-select 
                v-model="item.question" 
                placeholder="请选择密保问题" 
                style="width: 100%"
                :disabled="loading"
              >
                <el-option
                  v-for="question in availableQuestions"
                  :key="question"
                  :label="question"
                  :value="question"
                  :disabled="isQuestionSelected(question, index)"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item :prop="`questions[${index}].answer`" :rules="[{ required: true, message: '请输入答案', trigger: 'blur' }]">
              <el-input
                v-model="item.answer"
                placeholder="请输入答案"
                :disabled="loading"
              />
            </el-form-item>
          </div>
        </el-form>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="securityQuestionsDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveSecurityQuestions" :loading="loading">
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useUserStore } from '@/store/userStore';
import { ElMessage, ElMessageBox } from 'element-plus';
import axios from 'axios';

const AUTH_API_URL = 'http://localhost:5004/api/auth';
const userStore = useUserStore();
const passwordFormRef = ref(null);
const securityFormRef = ref(null);
const loading = ref(false);

// 密保问题相关
const securityQuestionsStatus = ref(false);
const securityQuestionsDialogVisible = ref(false);
const availableQuestions = ref([]);

// 密保问题表单
const securityForm = reactive({
  questions: [
    { question: '', answer: '' },
    { question: '', answer: '' },
    { question: '', answer: '' }
  ]
});

// 修改密码表单
const changePasswordDialogVisible = ref(false);
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
});

// 表单验证规则
const passwordRules = {
  currentPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6个字符', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'));
        } else {
          callback();
        }
      },
      trigger: 'blur'
    }
  ]
};

// 判断问题是否已被选择
const isQuestionSelected = (question, currentIndex) => {
  return securityForm.questions.some((item, index) => 
    index !== currentIndex && item.question === question
  );
};

// 显示修改密码对话框
const showChangePasswordDialog = () => {
  passwordForm.currentPassword = '';
  passwordForm.newPassword = '';
  passwordForm.confirmPassword = '';
  changePasswordDialogVisible.value = true;
};

// 显示密保问题设置对话框
const showSecurityQuestionsDialog = () => {
  // 重置表单
  securityForm.questions.forEach(item => {
    item.question = '';
    item.answer = '';
  });
  
  securityQuestionsDialogVisible.value = true;
};

// 获取密保问题列表
const fetchSecurityQuestions = async () => {
  try {
    const response = await axios.get(`${AUTH_API_URL}/security-questions`);
    if (response.data.success) {
      availableQuestions.value = response.data.questions;
    }
  } catch (error) {
    console.error('获取密保问题列表失败:', error);
    ElMessage.error('获取密保问题列表失败');
  }
};

// 获取用户密保问题状态
const fetchUserSecurityQuestionsStatus = async () => {
  try {
    const response = await axios.get(
      `${AUTH_API_URL}/security-questions/user`,
      {
        headers: { Authorization: `Bearer ${userStore.token}` }
      }
    );
    
    if (response.data.success) {
      securityQuestionsStatus.value = response.data.hasSecurityQuestions;
    }
  } catch (error) {
    console.error('获取密保问题状态失败:', error);
  }
};

// 保存密保问题设置
const saveSecurityQuestions = async () => {
  if (!securityFormRef.value) return;
  
  await securityFormRef.value.validate(async (valid) => {
    if (!valid) return;
    
    loading.value = true;
    try {
      const response = await axios.post(
        `${AUTH_API_URL}/security-questions/setup`,
        {
          questions: securityForm.questions
        },
        {
          headers: { Authorization: `Bearer ${userStore.token}` }
        }
      );
      
      if (response.data.success) {
        ElMessage.success('密保问题设置成功');
        securityQuestionsDialogVisible.value = false;
        securityQuestionsStatus.value = true;
      } else {
        ElMessage.error(response.data.message || '密保问题设置失败');
      }
    } catch (error) {
      console.error('密保问题设置失败:', error);
      ElMessage.error(error.response?.data?.message || '密保问题设置失败，请稍后重试');
    } finally {
      loading.value = false;
    }
  });
};

// 修改密码
const changePassword = async () => {
  if (!passwordFormRef.value) return;
  
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return;
    
    loading.value = true;
    try {
      // 添加额外的配置，处理500错误
      const response = await axios.post(
        `${AUTH_API_URL}/change-password`,
        {
          currentPassword: passwordForm.currentPassword,
          newPassword: passwordForm.newPassword
        },
        {
          headers: { Authorization: `Bearer ${userStore.token}` },
          validateStatus: function (status) {
            // 接受所有状态码，包括500
            return true;
          }
        }
      );
      
      // 打印响应状态和详细信息以便调试
      console.log('密码修改API响应状态:', response.status);
      console.log('密码修改API响应内容:', response.data);
      
      // 处理不同的HTTP状态码
      if (response.status === 500) {
        ElMessage.error('服务器内部错误，请联系管理员或稍后重试');
        return;
      }
      
      if (response.data.success) {
        ElMessage.success('密码修改成功');
        changePasswordDialogVisible.value = false;
      } else {
        // 显示更具体的错误信息
        const errorMsg = response.data.message || 
                         (response.data.error ? `错误: ${response.data.error}` : '密码修改失败');
        ElMessage.error(errorMsg);
      }
    } catch (error) {
      console.error('密码修改出错:', error);
      // 显示更详细的错误信息
      const errorMessage = error.response?.data?.message || 
                          error.response?.data?.error || 
                          error.message || 
                          '密码修改失败，请稍后重试';
      ElMessage.error(errorMessage);
    } finally {
      loading.value = false;
    }
  });
};

// 确认注销账号
const confirmDeleteAccount = () => {
  ElMessageBox.confirm(
    '注销账号后，所有数据将被永久删除且无法恢复，确定要继续吗？',
    '注销账号确认',
    {
      confirmButtonText: '确认注销',
      cancelButtonText: '取消',
      type: 'warning',
      distinguishCancelAndClose: true,
      confirmButtonClass: 'el-button--danger'
    }
  ).then(() => {
    deleteAccount();
  }).catch(() => {
    // 用户取消操作，不做任何处理
  });
};

// 注销账号
const deleteAccount = async () => {
  loading.value = true;
  try {
    const response = await axios.delete(
      `${AUTH_API_URL}/delete-account`,
      {
        headers: { Authorization: `Bearer ${userStore.token}` }
      }
    );
    
    if (response.data.success) {
      ElMessage.success('账号已成功注销');
      userStore.logout();
      // 跳转到登录页
      window.location.href = '/login';
    } else {
      ElMessage.error(response.data.message || '账号注销失败');
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.message || '账号注销失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

// 页面加载时获取密保问题列表和用户状态
onMounted(async () => {
  await fetchSecurityQuestions();
  await fetchUserSecurityQuestionsStatus();
});
</script>

<style scoped>
.profile-container {
  max-width: 800px;
  margin: 20px auto;
  padding: 0 20px;
}

.profile-card {
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.profile-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.user-avatar {
  width: 120px;
  height: 120px;
  margin-bottom: 30px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid #eaeaea;
}

.avatar-image {
  width: 100%;
  height: 100%;
}

.avatar-image img {
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
  font-size: 48px;
  font-weight: bold;
}

.user-info {
  width: 100%;
  max-width: 400px;
  margin-bottom: 30px;
}

.info-item {
  display: flex;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.label {
  font-weight: bold;
  color: #606266;
  width: 80px;
}

.value {
  flex: 1;
  color: #333;
}

.action-buttons {
  display: flex;
  gap: 20px;
  margin-top: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

/* 密保问题表单样式 */
.security-questions-form {
  padding: 0 10px;
}

.tip {
  color: #909399;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.5;
}

.question-item {
  margin-bottom: 20px;
  padding: 15px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.question-header {
  font-weight: bold;
  margin-bottom: 10px;
  color: #333;
}
</style> 