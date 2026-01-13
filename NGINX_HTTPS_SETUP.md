# Nginx HTTPS 代理配置说明

## 问题描述

前端通过 HTTPS 访问（`https://dailynews.domtang.asia`），但 API 请求使用 HTTP（`http://domtang.asia:18888`），导致浏览器阻止混合内容（Mixed Content）错误。

## 解决方案

### 步骤 1：更新 Nginx 配置

将 `dailynews.conf` 文件复制到服务器的 nginx 配置目录（通常是 `/etc/nginx/conf.d/` 或 `/etc/nginx/sites-available/`），然后：

```bash
# 测试配置
sudo nginx -t

# 重新加载配置
sudo nginx -s reload
# 或
sudo systemctl reload nginx
```

### 步骤 2：修改前端构建配置

在构建前端时，将 `VITE_API_URL` 环境变量设置为**空字符串**，这样前端会使用相对路径，自动使用与页面相同的协议（HTTPS）和域名。

**推荐配置**（使用相对路径）：
```bash
VITE_API_URL= npm run build
```

或者使用完整的 HTTPS 地址：
```bash
VITE_API_URL=https://dailynews.domtang.asia npm run build
```

**注意**：由于前端代码中的 API 路径已经包含 `/api` 前缀（如 `/api/auth/login`），所以：
- ✅ `VITE_API_URL=` → 请求路径为 `/api/auth/login`（正确）
- ❌ `VITE_API_URL=/api` → 请求路径为 `/api/api/auth/login`（错误，会重复）

### 步骤 3：更新环境变量文件

在服务器的 `.env` 文件中（或构建时使用的环境变量）设置：

```bash
# 前端构建时使用（使用相对路径，通过 nginx 代理）
VITE_API_URL=

# 或者使用完整的 HTTPS 地址
# VITE_API_URL=https://dailynews.domtang.asia
```

### 步骤 4：重新构建和部署前端

```bash
# 在项目根目录
cd frontend
npm install  # 或 pnpm install
VITE_API_URL=/api npm run build  # 或 pnpm build

# 然后部署构建后的 dist 目录
```

## 配置说明

### Nginx 配置要点

1. **`/api` 路径代理到后端**：所有 `/api/*` 请求会被代理到 `http://127.0.0.1:18888`
2. **其他路径代理到前端**：所有其他请求（如 `/`, `/login` 等）会被代理到 `http://127.0.0.1:18889`
3. **HTTPS 强制**：HTTP 请求会自动重定向到 HTTPS

### 前端 API 调用

前端代码中所有 API 调用已经使用了 `/api/` 前缀，例如：
- `/api/auth/login`
- `/api/news/dashboard`
- `/api/preferences/me`

当 `VITE_API_URL=/api` 时，axios 的 `baseURL` 会是 `/api`，加上路径后变成 `/api/api/auth/login`。

**需要修改前端代码**：将 `baseURL` 设置为空字符串，或者修改所有 API 路径去掉 `/api` 前缀。

## 推荐方案：使用相对路径

### 方法 1：设置 VITE_API_URL 为空字符串（最简单）

在构建前端时，设置 `VITE_API_URL` 为空字符串：

```bash
VITE_API_URL= npm run build
```

这样前端会使用相对路径，所有 API 请求会通过当前域名（HTTPS）发送。

### 方法 2：使用 /api 前缀

如果希望明确指定 API 路径，可以设置：

```bash
VITE_API_URL=/api npm run build
```

**注意**：由于后端路由已经包含 `/api` 前缀，前端代码中的路径（如 `/api/auth/login`）加上 `baseURL=/api` 会变成 `/api/api/auth/login`，这是错误的。

**解决方案**：需要修改前端代码，去掉路径中的 `/api` 前缀，或者使用空字符串。

### 当前配置说明

前端代码已经支持通过环境变量配置 API URL：
- 开发环境：`VITE_API_URL=http://localhost:18888` → 直接访问后端
- 生产环境：`VITE_API_URL=` → 使用相对路径，通过 nginx 代理

## 验证

1. 访问 `https://dailynews.domtang.asia/login`
2. 打开浏览器开发者工具（F12）→ Network 标签
3. 查看 API 请求，应该都是 `https://dailynews.domtang.asia/api/...`
4. 不应该再有 Mixed Content 错误

## 故障排查

### 如果 API 请求返回 404

检查后端路由是否以 `/api` 开头。如果后端路由是 `/auth/login` 而不是 `/api/auth/login`，需要：

1. 修改 nginx 配置，将 `/api` 路径重写：
```nginx
location /api {
    rewrite ^/api/(.*) /$1 break;
    proxy_pass http://127.0.0.1:18888;
    # ... 其他配置
}
```

2. 或者修改后端路由，添加 `/api` 前缀

### 如果仍然有 Mixed Content 错误

1. 清除浏览器缓存
2. 检查前端构建时是否正确设置了 `VITE_API_URL`
3. 检查浏览器控制台，确认 API 请求的完整 URL
