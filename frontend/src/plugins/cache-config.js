/**
 * 缓存配置模块
 * 用于优化资源加载和缓存策略
 */

/**
 * 配置service worker来处理缓存
 * 注意：这只会在https或localhost环境中工作
 */
export function registerCacheWorker() {
  if ('serviceWorker' in navigator) {
    // 避免重复注册
    if (window.__cacheWorkerRegistered) return;
    
    window.__cacheWorkerRegistered = true;
    
    // 添加CDN资源备用加载机制
    setupCDNFallbacks();
    
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/cache-worker.js')
        .then(registration => {
          console.log('Cache ServiceWorker registered with scope:', registration.scope);
          
          // 监听Service Worker更新
          registration.onupdatefound = () => {
            const installingWorker = registration.installing;
            if (installingWorker) {
              installingWorker.onstatechange = () => {
                if (installingWorker.state === 'installed') {
                  if (navigator.serviceWorker.controller) {
                    console.log('ServiceWorker已更新，将在页面刷新后生效');
                  } else {
                    console.log('ServiceWorker已安装，初次使用缓存');
                  }
                }
              };
            }
          };
        })
        .catch(error => {
          console.log('Cache ServiceWorker registration failed:', error);
          // 如果Service Worker注册失败，使用传统资源加载
          setupCDNFallbacks(true);
        });
    });
  } else {
    // 不支持Service Worker，使用传统资源加载方式
    setupCDNFallbacks(true);
  }
}

/**
 * 设置CDN资源备用加载策略
 * @param {boolean} forceFallback - 是否强制使用备用策略
 */
function setupCDNFallbacks(forceFallback = false) {
  // Material Design Icons备用加载
  const mdiCssUrl = 'https://cdn.jsdelivr.net/npm/@mdi/font@latest/css/materialdesignicons.min.css';
  
  // 检查页面是否已经加载了MDI样式
  if (document.querySelector(`link[href*="materialdesignicons"]`) && !forceFallback) {
    return;
  }
  
  // 创建link元素加载样式
  const loadMDI = () => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = mdiCssUrl;
    
    // 错误处理：如果CDN加载失败，尝试其他备用CDN
    link.onerror = () => {
      console.warn('主要CDN加载失败，尝试备用CDN');
      link.href = 'https://unpkg.com/@mdi/font@latest/css/materialdesignicons.min.css';
      
      // 如果备用CDN也失败，尝试本地资源（如果有）
      link.onerror = () => {
        console.warn('备用CDN加载失败');
        // 这里可以添加更多备用策略
      };
    };
    
    document.head.appendChild(link);
  };
  
  // 如果强制使用备用，或者在网页加载完成后Service Worker出错，直接加载
  if (forceFallback) {
    loadMDI();
  } else {
    // 等待一小段时间，如果Service Worker没有处理好资源，则使用备用方案
    setTimeout(() => {
      if (!document.querySelector(`link[href*="materialdesignicons"]`)) {
        loadMDI();
      }
    }, 3000);
  }
}

// 缓存配置常量
const CACHE_CONFIG = {
  // 最长缓存时间
  HTML_MAX_AGE: 86400, // 24小时
  RESOURCES_MAX_AGE: 3600, // 1小时
  SERVICE_WORKER_MAX_AGE: 86400, // 24小时
  
  // 检查当前页面meta标签中的缓存设置
  getHtmlCacheControl() {
    const metaCache = document.querySelector('meta[http-equiv="Cache-Control"]');
    if (metaCache) {
      const content = metaCache.getAttribute('content');
      if (content && content.includes('max-age=')) {
        try {
          const maxAge = parseInt(content.split('max-age=')[1]);
          if (!isNaN(maxAge)) {
            return maxAge;
          }
        } catch (e) {}
      }
    }
    return this.HTML_MAX_AGE;
  },
  
  // 添加缓存破坏参数到URL
  addCacheBuster(url) {
    if (!url) return url;
    
    // 不需要缓存破坏的URL模式
    const noCacheBustPatterns = [
      /^https?:\/\/cdn\.jsdelivr\.net\//i, // CDN 资源已经有版本号
      /fontawesome/i,
      /materialdesignicons/i,
      /\?v=\d+/i, // 已经有版本号的资源
      /\.html$/i // HTML文件不添加缓存破坏
    ];
    
    // 检查URL是否匹配不需要缓存破坏的模式
    for (const pattern of noCacheBustPatterns) {
      if (pattern.test(url)) {
        return url;
      }
    }
    
    // 判断URL类型
    const isResource = /\.(jpg|jpeg|png|gif|svg|webp|css|js|woff|woff2|ttf|eot)$/i.test(url);
    
    // 只对静态资源添加缓存破坏
    if (!isResource) {
      return url;
    }
    
    // 添加缓存破坏参数（以v参数为例，使用版本号或时间戳）
    const separator = url.includes('?') ? '&' : '?';
    
    // 使用时间戳每小时更新一次
    const version = Math.floor(Date.now() / 3600000);
    
    return `${url}${separator}v=${version}`;
  }
};

/**
 * 为fetch请求添加缓存逻辑
 */
export function setupFetchCache() {
  // 避免重复修补
  if (window.__fetchCacheSetup) return;
  window.__fetchCacheSetup = true;
  
  // 保存原始fetch函数
  const originalFetch = window.fetch;
  
  // 获取页面本身的缓存策略
  const htmlMaxAge = CACHE_CONFIG.getHtmlCacheControl();
  
  // 重写fetch函数，添加缓存头
  window.fetch = function(url, options = {}) {
    // 添加缓存破坏参数
    const bustUrl = CACHE_CONFIG.addCacheBuster(url);
    
    // 判断URL类型
    const isResource = /\.(jpg|jpeg|png|gif|svg|webp|css|js|woff|woff2|ttf|eot)$/i.test(bustUrl);
    const isCacheWorker = bustUrl.includes('cache-worker.js');
    const isHTMLPage = bustUrl.endsWith('.html') || bustUrl.endsWith('/') || bustUrl.includes('text/html');
    const isAPIRequest = bustUrl.includes('/api/');
    
    options.headers = options.headers || {};
    
    // 为不同类型的资源应用合适的缓存策略
    if (isResource) {
      // 静态资源缓存
      options.headers['Cache-Control'] = `max-age=${CACHE_CONFIG.RESOURCES_MAX_AGE}`;
    }
    else if (isCacheWorker) {
      // Service Worker缓存
      options.headers['Cache-Control'] = `max-age=${CACHE_CONFIG.SERVICE_WORKER_MAX_AGE}`;
    }
    else if (isHTMLPage) {
      // HTML页面缓存，与meta设置保持一致
      options.headers['Cache-Control'] = `max-age=${htmlMaxAge}`;
    }
    else if (isAPIRequest) {
      // API请求不缓存
      options.headers['Cache-Control'] = 'no-cache';
      options.headers['Pragma'] = 'no-cache';
    }
    
    // 调用原始fetch
    return originalFetch.call(this, bustUrl, options);
  };
}

/**
 * 预加载关键资源
 * @param {Array} resources - 要预加载的资源URL列表
 */
export function preloadResources(resources = []) {
  if (!resources || !resources.length) return;
  
  // 使用全局应用状态记录预加载资源
  if (!window.AppState) {
    console.warn('AppState未定义，使用简化版资源预加载');
    window.AppState = {
      preloadedResources: new Set(),
      registerPreloadedResource(url) {
        if (!this.preloadedResources.has(url)) {
          this.preloadedResources.add(url);
          return true;
        }
        return false;
      },
      isResourcePreloaded(url) {
        return this.preloadedResources.has(url);
      }
    };
  }
  
  // 记录成功预加载的资源数量
  let preloadedCount = 0;
  const totalResources = resources.length;
  
  resources.forEach(url => {
    // 添加缓存破坏参数
    const bustUrl = CACHE_CONFIG.addCacheBuster(url);
    
    // 检查URL是否已经预加载
    if (window.AppState.isResourcePreloaded(bustUrl)) {
      preloadedCount++;
      return; // 跳过已预加载的资源
    }
    
    // 提取资源文件名，不包含查询参数
    const cleanUrl = bustUrl.split('?')[0];
    
    // 创建预加载链接
    const link = document.createElement('link');
    link.rel = 'preload';
    
    // 资源加载完成回调
    const markAsLoaded = () => {
      window.AppState.registerPreloadedResource(bustUrl);
      preloadedCount++;
      
      // 如果所有资源都预加载完成，触发事件
      if (preloadedCount === totalResources) {
        window.dispatchEvent(new CustomEvent('app:state', { 
          detail: { 
            resourcesPreloaded: true,
            preloadedResources: Array.from(new Set(resources.map(r => CACHE_CONFIG.addCacheBuster(r))))
          } 
        }));
      }
    };
    
    // 根据文件类型设置as属性
    if (/\.css$/i.test(cleanUrl)) {
      link.as = 'style';
      link.href = bustUrl;
      
      // 对于CSS文件，添加一个额外的link以实际加载样式
      const styleLink = document.createElement('link');
      styleLink.rel = 'stylesheet';
      styleLink.href = bustUrl;
      styleLink.onload = markAsLoaded;
      styleLink.onerror = markAsLoaded; // 即使出错也标记为已处理
      document.head.appendChild(styleLink);
    } else if (/\.js$/i.test(cleanUrl)) {
      link.as = 'script';
      link.href = bustUrl;
      link.onload = markAsLoaded;
      link.onerror = markAsLoaded;
    } else if (/\.(jpg|jpeg|png|gif|webp|svg)$/i.test(cleanUrl)) {
      link.as = 'image';
      link.href = bustUrl;
      link.onload = markAsLoaded;
      link.onerror = markAsLoaded;
    } else if (/\.(woff|woff2|ttf|eot)$/i.test(cleanUrl)) {
      link.as = 'font';
      link.crossOrigin = 'anonymous';
      link.href = bustUrl;
      link.onload = markAsLoaded;
      link.onerror = markAsLoaded;
    } else if (/\.json$/i.test(cleanUrl)) {
      link.as = 'fetch';
      link.crossOrigin = 'anonymous';
      link.href = bustUrl;
      link.onload = markAsLoaded;
      link.onerror = markAsLoaded;
    } else {
      // 如果无法确定资源类型，仍然记录但不预加载
      window.AppState.registerPreloadedResource(bustUrl);
      preloadedCount++;
      return;
    }
    
    document.head.appendChild(link);
  });
}

/**
 * 初始化缓存配置
 * @param {Object} options - 缓存配置选项
 */
export function initCacheConfig(options = {}) {
  // 根据环境和选项决定是否启用service worker
  if (options.enableServiceWorker !== false) {
    registerCacheWorker();
  }
  
  // 设置fetch缓存
  if (options.enableFetchCache !== false) {
    setupFetchCache();
  }
  
  // 预加载资源
  if (options.resources && Array.isArray(options.resources)) {
    preloadResources(options.resources);
  }
  
  // 清除资源预加载警告（开发环境）
  if (process.env.NODE_ENV === 'development') {
    clearPreloadWarnings();
  }
  
  console.log('✅ 资源缓存配置已应用');
}

/**
 * 清除浏览器预加载资源警告
 * 在开发环境中使用，避免不必要的控制台警告
 */
function clearPreloadWarnings() {
  // 仅在开发环境生效
  if (process.env.NODE_ENV !== 'development') return;
  
  // 创建一个MutationObserver来监听控制台警告
  const observer = new MutationObserver((mutations) => {
    // 获取现有控制台错误输出
    const consoleOutput = console.warn;
    
    // 重写控制台警告函数，过滤预加载资源警告
    console.warn = function(...args) {
      if (args[0] && typeof args[0] === 'string') {
        // 如果警告是关于预加载资源的，则忽略
        if (args[0].includes('was preloaded using link preload but not used within') ||
            args[0].includes('Please make sure it has an appropriate `as` value')) {
          return;
        }
      }
      // 传递其他警告
      consoleOutput.apply(console, args);
    };
  });
  
  // 开始观察文档变化
  observer.observe(document, { 
    childList: true,
    subtree: true 
  });
  
  // 60秒后停止拦截警告（足够页面完全加载）
  setTimeout(() => {
    observer.disconnect();
  }, 60000);
}

export default {
  initCacheConfig,
  preloadResources
}; 