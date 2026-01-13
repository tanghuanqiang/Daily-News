# Nginx HTTPS 后端代理配置指南

## 问题描述

前端已经通过 HTTPS 访问（`https://dailynews.domtang.asia`），但后端 API 请求需要使用 HTTPS，以便前后端能够正常通信。

## 解决方案

### 1. Nginx 配置

已更新的 `dailynews.conf` 配置文件包含以下要点：

- **`/api` 路径代理到后端**：所有 `/api/*` 请求会被代理到 `http://127.0.0.1:18888`（后端服务）
- **其他路径代理到前端**：所有其他请求（如 `/`, `/login` 等）会被代理到 `http://127.0.0.1:18889`（前端服务）
- **HTTPS 强制**：HTTP 请求会自动重定向到 HTTPS
- **正确的请求头设置**：包括 `X-Forwarded-Proto` 等，确保后端知道请求是通过 HTTPS 到达的

### 2. 更新 Nginx 配置到服务器

```bash
# 1. 将 dailynews.conf 复制到服务器
scp dailynews.conf user@your-server:/etc/nginx/conf.d/

# 2. 测试配置
sudo nginx -t

# 3. 重新加载配置
sudo nginx -s reload
# 或
sudo systemctl reload nginx
```

### 3. 后端 CORS 配置

在后端的 `.env` 文件中，确保 `CORS_ORIGINS` 包含 HTTPS 域名：

```bash
# 开发环境
CORS_ORIGINS=http://localhost:5173,http://localhost

# 生产环境（使用 HTTPS）
CORS_ORIGINS=https://dailynews.domtang.asia
```

然后重启后端服务。

### 4. 前端构建配置

#### 方法 1：使用相对路径（推荐）

在构建前端时，将 `VITE_API_URL` 设置为空字符串：

```bash
cd frontend
VITE_API_URL= npm run build
# 或
VITE_API_URL= pnpm build
```

这样前端会使用相对路径，所有 API 请求会通过当前域名（HTTPS）发送到 `/api/*`，nginx 会自动代理到后端。

#### 方法 2：使用完整的 HTTPS 地址

```bash
cd frontend
VITE_API_URL=https://dailynews.domtang.asia npm run build
```

### 5. 前端代码说明

前端代码已经更新，支持以下配置：

- **开发环境**：如果 `VITE_API_URL` 未设置，默认使用 `http://localhost:18888`
- **生产环境**：如果 `VITE_API_URL` 未设置，使用空字符串（相对路径），通过 nginx HTTPS 代理

前端 API 调用路径已经包含 `/api` 前缀（如 `/api/auth/login`），所以：
- ✅ `VITE_API_URL=` → 请求路径为 `/api/auth/login`（正确）
- ✅ `VITE_API_URL=https://dailynews.domtang.asia` → 请求路径为 `https://dailynews.domtang.asia/api/auth/login`（正确）

### 6. 验证配置

1. 访问 `https://dailynews.domtang.asia/login`
2. 打开浏览器开发者工具（F12）→ Network 标签
3. 查看 API 请求，应该都是 `https://dailynews.domtang.asia/api/...`
4. 不应该再有 Mixed Content 错误
5. 所有 API 请求应该返回 200 状态码（或相应的成功状态码）

### 7. 故障排查

#### 如果 API 请求返回 404

1. 检查 nginx 配置中的 `proxy_pass` 是否正确指向后端端口（18888）
2. 检查后端服务是否正在运行：`curl http://127.0.0.1:18888/health`
3. 检查后端路由是否以 `/api` 开头

#### 如果仍然有 CORS 错误

1. 检查后端 `.env` 文件中的 `CORS_ORIGINS` 是否包含 `https://dailynews.domtang.asia`
2. 重启后端服务
3. 清除浏览器缓存

#### 如果仍然有 Mixed Content 错误

1. 确保前端构建时正确设置了 `VITE_API_URL`
2. 清除浏览器缓存
3. 检查浏览器控制台，确认 API 请求的完整 URL 是否为 HTTPS

### 8. 架构说明

```
用户浏览器
    ↓ HTTPS
Nginx (dailynews.domtang.asia:443)
    ├─ /api/* → 代理到 → 后端服务 (127.0.0.1:18888)
    └─ /* → 代理到 → 前端服务 (127.0.0.1:18889)
```

所有请求都通过 HTTPS，nginx 负责：
- SSL/TLS 终止
- 请求路由（/api 到后端，其他到前端）
- 添加必要的请求头（X-Forwarded-Proto 等）
