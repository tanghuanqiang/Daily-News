# Docker Compose 一键部署指南

## 📋 概述

本项目已配置 Docker Compose 一键部署，所有服务（前端、后端、数据库）可通过单个命令启动。

## 🚀 快速开始

### 1. 前置要求

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git**（用于克隆仓库）

### 2. 部署步骤

#### 步骤 1：克隆仓库（如果从服务器下载）

```bash
git clone <your-repository-url>
cd Daily-News
```

#### 步骤 2：配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑 .env 文件，填入必需的配置
# 特别注意以下配置：
# - SECRET_KEY（必须修改为强随机字符串）
# - LLM_PROVIDER 和对应的 API Key
# - 新闻 API Key（至少配置一个）
```

#### 步骤 3：一键部署

**Linux/macOS:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

**或手动部署:**
```bash
docker-compose up -d --build
```

### 3. 验证部署

部署完成后，访问以下地址验证：

- **前端界面**: http://localhost:18889
- **后端API**: http://localhost:18888
- **API文档**: http://localhost:18888/docs
- **健康检查**: http://localhost:18888/health

## 🔧 端口配置

为了避免与 dailynews 等常见服务冲突，默认端口已配置为：

| 服务 | 默认端口 | 环境变量 | 说明 |
|------|---------|---------|------|
| 后端API | 18888 | `BACKEND_PORT` | 避免与常见服务冲突 |
| 前端Web | 18889 | `FRONTEND_PORT` | 避免与常见服务冲突 |
| PostgreSQL | 15432 | `POSTGRES_PORT` | 避免与标准PostgreSQL 5432冲突 |

如需修改端口，请在 `.env` 文件中设置相应的环境变量。

## 📝 环境变量配置

### 必需配置

在 `.env` 文件中必须配置以下内容：

```env
# JWT密钥（必须修改为强随机字符串）
SECRET_KEY=your-strong-random-secret-key

# LLM配置（三选一）
LLM_PROVIDER=dashscope  # 或 nvidia 或 ollama
DASHSCOPE_API_KEY=sk-xxxxx  # 使用DashScope时必需

# 新闻API（至少配置一个）
GNEWS_API_KEY=your-key
# 或
NEWSDATA_API_KEY=your-key

# CORS配置（必须配置前端域名）
CORS_ORIGINS=http://localhost:18889,http://your-domain.com
```

### 可选配置

```env
# 端口配置（可选，使用默认值即可）
BACKEND_PORT=18888
FRONTEND_PORT=18889
POSTGRES_PORT=15432

# 数据库配置（可选，默认使用SQLite）
DATABASE_URL=sqlite:///./daily_digest.db
# 或使用PostgreSQL（推荐生产环境）
# DATABASE_URL=postgresql://postgres:postgres@db:5432/dailydigest

# 邮件服务配置（可选）
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=noreply@yourdomain.com
```

详细配置说明请查看 `env.example` 文件。

## 🛠️ 常用命令

### 查看服务状态

```bash
docker-compose ps
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 停止服务

```bash
docker-compose down
```

### 停止并删除数据卷

```bash
docker-compose down -v
```

⚠️ **警告**: 此命令会删除所有数据，包括数据库！

### 重新构建镜像

```bash
docker-compose build --no-cache
docker-compose up -d
```

### 更新代码后重新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 🔍 故障排查

### 端口冲突

如果遇到端口冲突错误：

1. 检查端口占用：
   ```bash
   # Linux/macOS
   netstat -tuln | grep :18888
   ss -tuln | grep :18888
   
   # Windows
   netstat -ano | findstr :18888
   ```

2. 修改 `.env` 文件中的端口配置：
   ```env
   BACKEND_PORT=18890
   FRONTEND_PORT=18891
   ```

3. 重新启动服务：
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### 服务无法启动

1. 查看详细日志：
   ```bash
   docker-compose logs backend
   docker-compose logs frontend
   ```

2. 检查环境变量配置：
   ```bash
   # 确保 .env 文件存在且配置正确
   cat .env
   ```

3. 检查 Docker 资源：
   ```bash
   docker system df
   docker ps -a
   ```

### 数据库连接失败

1. 检查数据库服务状态：
   ```bash
   docker-compose ps db
   docker-compose logs db
   ```

2. 验证数据库连接字符串：
   ```env
   DATABASE_URL=postgresql://postgres:postgres@db:5432/dailydigest
   ```

3. 重启数据库服务：
   ```bash
   docker-compose restart db
   ```

### 前端无法访问后端API

1. 检查 CORS 配置：
   ```env
   CORS_ORIGINS=http://localhost:18889,http://your-domain.com
   ```

2. 检查前端构建时的 API URL：
   ```env
   VITE_API_URL=http://localhost:18888
   ```

3. 重新构建前端：
   ```bash
   docker-compose build frontend
   docker-compose up -d frontend
   ```

## 📊 服务架构

```
┌─────────────────────────────────────────┐
│         Frontend (Nginx)                │
│         Port: 18889                     │
│         Container: daily-digest-frontend│
└─────────────────┬───────────────────────┘
                  │
                  │ HTTP
                  │
┌─────────────────▼───────────────────────┐
│         Backend (FastAPI)               │
│         Port: 18888                     │
│         Container: daily-digest-backend │
└─────────────────┬───────────────────────┘
                  │
                  │ SQL
                  │
┌─────────────────▼───────────────────────┐
│         PostgreSQL                      │
│         Port: 15432                     │
│         Container: daily-digest-db      │
└─────────────────────────────────────────┘
```

## 🔒 安全建议

1. **修改默认密码**: 如果使用 PostgreSQL，请修改默认用户名和密码
2. **使用 HTTPS**: 生产环境必须使用 HTTPS
3. **限制 CORS**: 只允许信任的域名访问
4. **保护 API Key**: 不要将 `.env` 文件提交到 Git
5. **定期备份**: 定期备份数据库数据

## 📚 相关文档

- [README.md](README.md) - 项目完整文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [DEPLOYMENT.md](DEPLOYMENT.md) - 云平台部署指南
- [env.example](env.example) - 环境变量配置示例

## 💡 提示

- 首次部署可能需要几分钟时间构建镜像
- 建议在生产环境使用 PostgreSQL 而非 SQLite
- 定期查看日志以监控服务状态
- 使用 `docker-compose logs -f` 实时查看日志

## 🆘 获取帮助

如遇到问题，请：

1. 查看本文档的故障排查部分
2. 查看服务日志：`docker-compose logs`
3. 检查 GitHub Issues
4. 提交新的 Issue 描述问题

---

**祝部署顺利！** 🚀
