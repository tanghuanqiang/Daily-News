import axios from 'axios';

// 如果 VITE_API_URL 未设置或为空，使用相对路径（适用于生产环境通过 nginx 代理）
// 开发环境：VITE_API_URL=http://localhost:18888
// 生产环境：VITE_API_URL=https://dailynews.domtang.asia 或留空使用相对路径
const API_URL = import.meta.env.VITE_API_URL !== undefined && import.meta.env.VITE_API_URL !== ''
  ? import.meta.env.VITE_API_URL
  : import.meta.env.DEV
  ? 'http://localhost:18888'
  : ''; // 生产环境使用相对路径，通过 nginx HTTPS 代理

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
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
