import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/userStore'

// 布局组件
import MainLayout from '@/layouts/MainLayout.vue'

// 页面组件（使用懒加载提高性能）
// 注意：使用与Vite兼容的动态导入，移除webpack特定注释
const Dashboard = () => import('@/views/Dashboard.vue')
const HistoricalData = () => import('@/views/HistoricalData.vue')
const TrendAnalysis = () => import('@/views/TrendAnalysis.vue')
const SmartPrediction = () => import('@/views/SmartPrediction.vue')
const ReportGeneration = () => import('@/views/ReportGeneration.vue')
const Login = () => import('@/views/Login.vue')
const Register = () => import('@/views/Register.vue')
const ForgotPassword = () => import('@/views/ForgotPassword.vue')
const Profile = () => import('@/views/user/Profile.vue')
// 添加管理员页面
const UserManagement = () => import('@/views/admin/UserManagement.vue')

// 预加载策略配置
const PRELOAD_DELAY = 1500; // 延迟预加载时间(ms)
const VIEWS_TO_PRELOAD = ['HistoricalData', 'TrendAnalysis']; // 需要预加载的页面

// 优化动态预加载指定视图的函数
const preloadView = (viewName) => {
  // 确保只在客户端环境中执行预加载
  if (!window || !window.AppState) return;
  
  // 存储预加载状态的键
  const resourceKey = `view:${viewName}`;
  
  // 避免重复加载
  if (window.AppState.isResourcePreloaded(resourceKey)) {
    return;
  }
  
  // 首先标记为正在加载
  window.AppState.registerPreloadedResource(`${resourceKey}:loading`);
  
  // 使用requestIdleCallback在浏览器空闲时预加载，以避免影响主线程
  // 如果不支持requestIdleCallback，降级为setTimeout
  const schedulePreload = window.requestIdleCallback || setTimeout;
  
  schedulePreload(() => {
    try {
      // 使用Promise包装动态导入，并添加超时处理
      Promise.race([
        import(`@/views/${viewName}.vue`),
        new Promise((_, reject) => setTimeout(() => reject('预加载超时'), 10000))
      ])
      .then(() => {
        // 预加载成功，更新状态
        window.AppState.registerPreloadedResource(resourceKey);
        window.AppState.preloadedResources.delete(`${resourceKey}:loading`);
      })
      .catch(err => {
        console.warn(`预加载视图失败: ${viewName}`, err);
        window.AppState.preloadedResources.delete(`${resourceKey}:loading`);
      });
    } catch (e) {
      console.warn(`预加载视图出错: ${viewName}`, e);
      window.AppState.preloadedResources.delete(`${resourceKey}:loading`);
    }
  }, { timeout: 5000 }); // 如果是requestIdleCallback，设置最大等待时间
};

// 改进的智能预加载 - 优化性能和资源使用
const preloadCommonPages = () => {
  // 确保应用已就绪后才开始预加载
  if (!window.AppState || !window.AppState.ready) {
    // 等待应用就绪事件，然后再尝试预加载
    window.addEventListener('app:state', (event) => {
      if (event.detail && event.detail.ready) {
        // 应用就绪后再次调用本函数
        setTimeout(preloadCommonPages, PRELOAD_DELAY);
      }
    }, { once: true });
    return;
  }
  
  // 检查是否有需要预加载且尚未加载的视图
  const viewsToLoad = VIEWS_TO_PRELOAD.filter(
    view => !window.AppState.isResourcePreloaded(`view:${view}`)
  );
  
  if (viewsToLoad.length === 0) {
    return; // 所有需要预加载的视图都已加载
  }
  
  // 获取当前网络状态，避免在低速网络下预加载
  if (navigator.connection) {
    const conn = navigator.connection;
    if (conn.saveData || 
        (conn.effectiveType && (conn.effectiveType === 'slow-2g' || conn.effectiveType === '2g'))) {
      console.log('检测到低速网络或数据保护模式，跳过预加载');
      return;
    }
  }
  
  // 性能预加载 - 分批加载以避免影响主应用性能
  let index = 0;
  const loadNext = () => {
    if (index < viewsToLoad.length) {
      preloadView(viewsToLoad[index]);
      index++;
      // 每隔500ms加载一个组件，避免资源争用
      setTimeout(loadNext, 500);
    } else {
      // 所有组件预加载完成
      window.dispatchEvent(new CustomEvent('app:state', { 
        detail: { viewsPreloaded: true }
      }));
    }
  };
  
  // 延迟开始预加载
  setTimeout(loadNext, PRELOAD_DELAY);
};

const routes = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: Dashboard,
        meta: { 
          title: '首页',
          keepAlive: true,
          icon: '🏠'
        }
      },
      {
        path: '/historical-data',
        name: 'historicalData',
        component: HistoricalData,
        meta: { 
          title: '历史数据',
          keepAlive: true,
          icon: '📊'
        }
      },
      {
        path: '/trend-analysis',
        name: 'trendAnalysis',
        component: TrendAnalysis,
        meta: { 
          title: '趋势分析',
          keepAlive: true,
          icon: '📈'
        }
      },
      {
        path: '/smart-prediction',
        name: 'smartPrediction',
        component: SmartPrediction,
        meta: { 
          title: '智能预测', 
          keepAlive: true,
          icon: '🔮'
        }
      },
      {
        path: '/report-generation',
        name: 'reportGeneration',
        component: ReportGeneration,
        meta: { 
          title: '报告生成',
          keepAlive: true,
          icon: '📝',
          requiresAuth: true
        }
      },
      {
        path: '/profile',
        name: 'profile',
        component: Profile,
        meta: {
          title: '个人中心',
          requiresAuth: true
        }
      },
      // 添加管理员路由
      {
        path: '/admin/users',
        name: 'adminUsers',
        component: UserManagement,
        meta: {
          title: '用户管理',
          requiresAuth: true,
          requiresAdmin: true,
          icon: '👥'
        }
      }
    ]
  },
  {
    path: '/login',
    name: 'login',
    component: Login,
    meta: {
      title: '用户登录',
      layout: 'auth'
    }
  },
  {
    path: '/register',
    name: 'register',
    component: Register,
    meta: {
      title: '用户注册',
      layout: 'auth'
    }
  },
  {
    path: '/forgot-password',
    name: 'forgotPassword',
    component: ForgotPassword,
    meta: {
      title: '忘记密码',
      layout: 'auth'
    }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 如果有保存的位置，则使用它
    if (savedPosition) {
      return savedPosition;
    }
    // 如果目标路由有哈希，则滚动到哈希位置
    if (to.hash) {
      return { el: to.hash };
    }
    // 否则回到顶部，但使用平滑滚动
    return { top: 0, behavior: 'smooth' };
  }
})

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 广东省空气质量监测系统` : '广东省空气质量监测系统'
  
  // 获取用户状态
  const userStore = useUserStore()
  
  // 检查用户是否已登录
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    // 用户未登录，重定向到登录页
    next({ 
      name: 'login',
      query: { redirect: to.fullPath }
    })
  } else if (to.meta.requiresAdmin && userStore.user.role !== 'admin' && userStore.user.role !== 'super_admin' && !userStore.user.isSuperAdmin) {
    // 用户不是管理员或超级管理者，重定向到首页
    next({ name: 'home' })
  } else if ((to.name === 'login' || to.name === 'register') && userStore.isLoggedIn) {
    // 用户已登录，尝试访问登录或注册页，重定向到首页
    next({ name: 'home' })
  } else {
    // 正常导航
    next()
  }
})

// 全局后置钩子 - 预加载优化
router.afterEach((to) => {
  // 如果是首页，预加载常用页面
  if (to.name === 'home') {
    preloadCommonPages();
    
    // 通知路由变化
    window.dispatchEvent(new CustomEvent('app:state', { 
      detail: { 
        route: to.name,
        ready: true
      } 
    }));
  } else {
    // 其他页面也通知路由变化
    window.dispatchEvent(new CustomEvent('app:state', { 
      detail: { 
        route: to.name
      } 
    }));
  }
})

export default router