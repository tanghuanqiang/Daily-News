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
      console.warn('[API] 请求拦截器：已将 baseURL 从 HTTP 转换为 HTTPS');
    }
  }

  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
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

  register: (email: string, password: string, verification_code: string) =>
    api.post('/api/auth/register', { email, password, verification_code }),

  verifyEmail: (email: string, code: string) =>
    api.post('/api/auth/verify-email', { email, verification_code: code }),

  resendVerification: (email: string) =>
    api.post('/api/auth/resend-verification', { email }),

  forgotPassword: (email: string) =>
    api.post('/api/auth/forgot-password', { email }),

  resetPassword: (email: string, code: string, newPassword: string) =>
    api.post('/api/auth/reset-password', { email, verification_code: code, new_password: newPassword }),

  getMe: () => api.get('/api/auth/me'),

  updateProfile: (data: { username?: string; email_notifications?: boolean }) =>
    api.put('/api/auth/profile', data),
};

// Subscriptions API
export const subscriptionsAPI = {
  getAll: () => api.get('/api/subscriptions/'),

  create: (data: { topic: string; roast_mode?: boolean }) =>
    api.post('/api/subscriptions/', data),

  update: (id: number, data: { roast_mode?: boolean; is_active?: boolean }) =>
    api.put(`/api/subscriptions/${id}`, data),

  delete: (id: number) => api.delete(`/api/subscriptions/${id}`),

  // Custom RSS feeds
  getCustomFeeds: () => api.get('/api/subscriptions/custom-feeds'),

  createCustomFeed: (data: { topic: string; feed_url: string }) =>
    api.post('/api/subscriptions/custom-feeds', data),

  updateCustomFeed: (id: number, data: { is_active?: boolean; roast_mode?: boolean }) =>
    api.put(`/api/subscriptions/custom-feeds/${id}`, data),

  deleteCustomFeed: (id: number) => api.delete(`/api/subscriptions/custom-feeds/${id}`),
};

// Preferences API
export const preferencesAPI = {
  get: () => api.get('/api/preferences/'),

  update: (data: { hide_read?: boolean; sort_by?: string; hidden_sources?: string[] }) =>
    api.put('/api/preferences/', data),

  hideSource: (source: string) =>
    api.post('/api/preferences/hide-source', { source }),

  unhideSource: (source: string) =>
    api.post('/api/preferences/unhide-source', { source }),
};

// Schedule API
export const scheduleAPI = {
  getSchedule: () => api.get('/api/schedule/'),

  updateSchedule: (data: {
    enabled?: boolean;
    schedule_type?: string;
    hour?: number;
    minute?: number;
    day_of_week?: number;
    interval_hours?: number;
  }) => api.put('/api/schedule/', data),

  getSendNow: () => api.post('/api/schedule/send-now'),
};

// News API
export const newsAPI = {
  getDashboard: () => api.get('/api/news/dashboard'),

  refresh: () => api.post('/api/news/refresh'),

  getRefreshStatus: () => api.get('/api/news/refresh-status'),

  // RAG相关API
  // 获取相似新闻推荐
  getSimilarNews: (newsId: number, limit: number = 5) =>
    api.get(`/api/news/similar/${newsId}`, { params: { limit } }),

  // 获取个性化推荐新闻
  getPersonalizedRecommendations: (limit: number = 10) =>
    api.get('/api/news/recommendations/personalized', { params: { limit } }),

  // 混合搜索新闻
  hybridSearch: (query: string, limit: number = 10) =>
    api.get('/api/news/search/hybrid', { params: { query, limit } }),

  // 获取RAG系统状态
  getRagStatus: () => api.get('/api/news/rag/status'),
};

// P1: 反馈API
export const feedbackAPI = {
  createFeedback: (data: { news_id: number; feedback_type: string }) =>
    api.post('/api/feedback/', data),

  getMyFeedback: (feedback_type?: string) =>
    api.get('/api/feedback/my', { params: { feedback_type } }),

  getFeedbackStats: (newsId: number) =>
    api.get(`/api/feedback/stats/${newsId}`),

  deleteFeedback: (feedbackId: number) =>
    api.delete(`/api/feedback/${feedbackId}`)
};

// P1: 分享API
export const sharingAPI = {
  generateShareContent: (data: {
    news_id: number;
    platform?: string;
    use_roast_mode?: boolean;
  }) => api.post('/api/share/generate', data),

  getSupportedPlatforms: () =>
    api.get('/api/share/platforms'),

  trackShare: (data: { news_id: number; platform: string }) =>
    api.post('/api/share/track', data)
};

// P1: 成就API
export const achievementsAPI = {
  getDefinitions: (category?: string) =>
    api.get('/api/achievements/definitions', { params: { category } }),

  getMyAchievements: () =>
    api.get('/api/achievements/my'),

  getMyAchievementsWithProgress: () =>
    api.get('/api/achievements/my'),

  getStats: () =>
    api.get('/api/achievements/stats'),

  unlockAchievement: (achievementId: number) =>
    api.post(`/api/achievements/unlock/${achievementId}`)
};

// ============================================
// 原生 fetch 封装（用于 Admin 组件）
// ============================================

// 获取存储的 token
function getToken(): string | null {
  return localStorage.getItem('token');
}

// 通用的 fetch 封装，自动添加认证头
export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  // 添加认证头
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // 处理 URL
  let fullUrl = url;
  if (url.startsWith('/api/') && API_URL) {
    fullUrl = `${API_URL}${url}`;
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
  });

  // 处理 401 错误
  if (response.status === 401) {
    console.error('认证失败，请重新登录');
    // 可选：自动跳转到登录页
    // window.location.href = '/login';
  }

  return response;
}

// GET 请求封装
export async function get(url: string): Promise<Response> {
  return fetchWithAuth(url, { method: 'GET' });
}

// POST 请求封装
export async function post(url: string, data: any): Promise<Response> {
  return fetchWithAuth(url, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// PUT 请求封装
export async function put(url: string, data?: any): Promise<Response> {
  return fetchWithAuth(url, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  });
}

// DELETE 请求封装
export async function del(url: string): Promise<Response> {
  return fetchWithAuth(url, { method: 'DELETE' });
}

export default api;
