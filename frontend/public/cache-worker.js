// 缓存名称和版本
const CACHE_NAME = 'air-quality-app-cache-v1';

// 需要缓存的资源列表
const CACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.ico',
  '/guangdong.json' // 添加广东地图数据，与预加载资源保持一致
];

// 需要缓存的静态资源类型
const CACHEABLE_TYPES = [
  'image/jpeg',
  'image/png', 
  'image/gif',
  'image/svg+xml',
  'image/webp',
  'text/css',
  'text/javascript',
  'application/javascript',
  'application/json', // 添加JSON类型
  'font/woff',
  'font/woff2',
  'font/ttf'
];

// 安装事件 - 预缓存重要资源
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Install');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Cache opened');
        return cache.addAll(CACHE_URLS);
      })
  );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activate');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[Service Worker] Claiming clients');
      // 立即接管页面，无需刷新
      return self.clients.claim();
    })
  );
});

// 排除的CDN域名列表
const EXCLUDED_CDN_DOMAINS = [
  'cdn.jsdelivr.net'
];

// 请求拦截 - 缓存策略
self.addEventListener('fetch', (event) => {
  // 只处理GET请求
  if (event.request.method !== 'GET') return;
  
  // 解析请求URL
  const url = new URL(event.request.url);
  
  // 忽略API请求和非静态资源
  if (url.pathname.startsWith('/api/') || url.pathname.includes('/socket.io/')) {
    return;
  }
  
  // 检查是否是排除的CDN资源
  const isCDNResource = EXCLUDED_CDN_DOMAINS.some(domain => url.hostname.includes(domain));
  
  // 对CDN资源使用网络优先策略，但不尝试缓存它们
  if (isCDNResource) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          // 尝试从缓存返回，如果网络请求失败
          return caches.match(event.request);
        })
    );
    return;
  }

  // 特殊处理JSON地图数据，使用缓存优先策略
  if (url.pathname.endsWith('.json')) {
    event.respondWith(
      caches.match(event.request)
        .then((cachedResponse) => {
          if (cachedResponse) {
            // 返回缓存中的响应，但同时在后台更新缓存
            const fetchPromise = fetch(event.request)
              .then((networkResponse) => {
                // 更新缓存
                caches.open(CACHE_NAME).then((cache) => {
                  cache.put(event.request, networkResponse.clone());
                });
                return networkResponse;
              })
              .catch(() => cachedResponse);
            
            return cachedResponse;
          }
          
          // 如果缓存中没有，则从网络获取
          return fetch(event.request)
            .then((response) => {
              // 缓存响应
              const responseToCache = response.clone();
              caches.open(CACHE_NAME).then((cache) => {
                cache.put(event.request, responseToCache);
              });
              return response;
            });
        })
    );
    return;
  }

  // 其他资源使用网络优先策略
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 检查是否成功获取到响应且是有效的响应
        if (!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }
        
        // 检查内容类型是否是可缓存的
        const contentType = response.headers.get('content-type');
        const isCacheable = contentType && CACHEABLE_TYPES.some(type => contentType.includes(type));
        
        // 如果是静态资源，则缓存它
        if (isCacheable || /\.(js|css|png|jpg|jpeg|gif|svg|webp|woff|woff2|ttf|json)$/i.test(url.pathname)) {
          const responseToCache = response.clone();
          
          caches.open(CACHE_NAME)
            .then((cache) => {
              cache.put(event.request, responseToCache);
            });
        }
        
        return response;
      })
      .catch(() => {
        // 网络请求失败时，尝试从缓存中获取
        return caches.match(event.request);
      })
  );
}); 