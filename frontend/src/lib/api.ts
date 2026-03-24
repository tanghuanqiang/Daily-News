// API 工具函数 - 自动添加认证头

const API_BASE_URL = '';

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
  
  const response = await fetch(`${API_BASE_URL}${url}`, {
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
