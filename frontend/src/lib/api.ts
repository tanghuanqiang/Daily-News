import axios from 'axios';

// API URL 配置
// 开发环境：VITE_API_URL=http://localhost:18888
// 生产环境：建议留空（使用相对路径）或设置为 https://dailynews.domtang.asia
// 使用相对路径（空字符串）会自动继承当前页面的协议，最适合同域部署
let API_URL = import.meta.env.VITE_API_URL;

// 处理 API URL
if (!API_URL || API_URL === '') {
  // 未设置或为空
  if (import.meta.env.DEV) {
    // 开发环境使用本地后端
    API_URL = 'http://localhost:18888';
  } else {
    // 生产环境使用相对路径，继承当前页面的协议（HTTPS）
    // 这是最安全的方式，避免 Mixed Content 错误
    API_URL = '';
  }
} else {
  // 已设置 VITE_API_URL
  // 在浏览器环境中，确保协议匹配当前页面
  if (typeof window !== 'undefined') {
    const isHttps = window.location.protocol === 'https:';
    const currentHost = window.location.host;
    
    if (isHttps) {
      // 当前页面是 HTTPS
      if (API_URL.startsWith('http://')) {
        // 如果 API URL 是 HTTP，强制转换为 HTTPS
        API_URL = API_URL.replace('http://', 'https://');
        console.warn('[API] 检测到 HTTPS 页面，已将 API URL 从 HTTP 转换为 HTTPS:', API_URL);
      } else if (API_URL.startsWith('https://')) {
        // 如果 API URL 是 HTTPS，检查域名是否匹配
        try {
          const apiHost = new URL(API_URL).host;
          if (apiHost === currentHost) {
            // 域名匹配，使用相对路径更安全（避免跨域和协议问题）
            API_URL = '';
            console.log('[API] 使用相对路径（同域部署，自动继承 HTTPS 协议）');
          }
        } catch (e) {
          // URL 解析失败，保持原值
          console.warn('[API] URL 解析失败，使用原始值:', API_URL);
        }
      }
    } else {
      // 当前页面是 HTTP（开发环境或测试环境）
      // 保持原值不变
    }
  }
}

// 调试信息（开发环境或特定域名）
if (import.meta.env.DEV || (typeof window !== 'undefined' && window.location.hostname.includes('dailynews.domtang.asia'))) {
  console.log('[API Config] 最终 API URL:', API_URL || '(相对路径，继承当前协议)');
  console.log('[API Config] 构建时 VITE_API_URL:', import.meta.env.VITE_API_URL || '(未设置)');
  console.log('[API Config] 当前页面:', typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : 'N/A');
}

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests and ensure HTTPS in production
api.interceptors.request.use((config) => {
  // 添加 token
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  // 运行时强制检查：如果页面是 HTTPS，确保 baseURL 也是 HTTPS
  // 这是最后的保障，防止构建时使用了 HTTP URL
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    if (config.baseURL && config.baseURL.startsWith('http://')) {
      // 强制将 HTTP 转换为 HTTPS
      config.baseURL = config.baseURL.replace('http://', 'https://');
      console.warn('[API Interceptor] 检测到 HTTP baseURL，已强制转换为 HTTPS:', config.baseURL);
    }
  }
  
  return config;
});

// Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }),
  
  register: (email: string, password: string) =>
    api.post('/api/auth/register', { email, password }),
  
  getMe: () => api.get('/api/auth/me'),
  
  sendVerificationCode: (email: string) =>
    api.post('/api/auth/send-verification-code', { email }),
  
  verifyCode: (email: string, code: string) =>
    api.post('/api/auth/verify-code', { email, code }),
  
  sendResetPasswordCode: (email: string) =>
    api.post('/api/auth/send-reset-password-code', { email }),
  
  resetPassword: (email: string, code: string, new_password: string) =>
    api.post('/api/auth/reset-password', { email, code, new_password }),
};

// Preferences API
export const preferencesAPI = {
  getMyPreferences: () => api.get('/api/preferences/me'),
  
  updateMyPreferences: (preferences: {
    hide_read?: boolean;
    sort_by?: 'time' | 'relevance';
    hidden_sources?: string[];
  }) => api.put('/api/preferences/me', preferences),
  
  markRead: (newsId: number) =>
    api.post(`/api/preferences/read/${newsId}`),
};

// Schedule API
export const scheduleAPI = {
  getMySchedule: () => api.get('/api/schedule/me'),
  
  updateMySchedule: (config: {
    enabled?: boolean;
    schedule_type?: 'daily';
    hour?: number;
    minute?: number;
  }) => api.put('/api/schedule/me', config),
  
  testEmail: () => api.post('/api/schedule/test-email'),
};

// Subscriptions API
export const subscriptionsAPI = {
  getAll: () => api.get('/api/subscriptions'),
  
  getPresetTopics: () => api.get('/api/subscriptions/preset-topics'),
  
  create: (topic: string, roast_mode: boolean = false) =>
    api.post('/api/subscriptions', { topic, roast_mode }),
  
  update: (id: number, data: { roast_mode?: boolean; is_active?: boolean }) =>
    api.put(`/api/subscriptions/${id}`, data),
  
  delete: (id: number) => api.delete(`/api/subscriptions/${id}`),
  
  // Custom RSS feeds
  getCustomRSSFeeds: () => api.get('/api/subscriptions/custom-rss'),
  
  createCustomRSSFeed: (topic: string, feed_url: string) =>
    api.post('/api/subscriptions/custom-rss', { topic, feed_url }),
  
  updateCustomRSSFeed: (id: number, data: { is_active?: boolean; roast_mode?: boolean }) =>
    api.put(`/api/subscriptions/custom-rss/${id}`, data),
  
  deleteCustomRSSFeed: (id: number) =>
    api.delete(`/api/subscriptions/custom-rss/${id}`),
};

// News API
export const newsAPI = {
  getDashboard: () => api.get('/api/news/dashboard'),
  
  refresh: () => api.post('/api/news/refresh'),
  
  getRefreshStatus: () => api.get('/api/news/refresh-status'),
};

export default api;
