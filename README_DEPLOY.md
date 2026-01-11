# 一键部署指南

## 📋 部署前准备

### 1. 系统要求

- **Docker** 20.10+
- **Docker Compose** 1.29+
- **操作系统**: Linux/macOS/Windows（推荐Linux服务器）

### 2. 检查端口占用

部署需要占用以下端口（可在`.env`文件中配置）：

- **后端API**: 默认 `8000`
- **前端Web**: 默认 `80`
- **PostgreSQL**: 默认 `5432`（仅在使用PostgreSQL时）

### 3. 配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下必需项：

```env
# 必须配置
SECRET_KEY=your-strong-random-secret-key-here  # 必须修改为强随机字符串

# LLM配置（三选一）
LLM_PROVIDER=dashscope  # 或 nvidia
DASHSCOPE_API_KEY=sk-xxxxx  # 使用DashScope时必需
# 或
NVIDIA_API_KEY=your-key  # 使用NVIDIA时必需

# 前端API地址（构建时使用）
VITE_API_URL=http://localhost:8000  # 生产环境改为实际域名
```

## 🚀 快速部署

### Linux/macOS

```bash
# 1. 给脚本执行权限
chmod +x deploy.sh

# 2. 运行部署脚本
./deploy.sh
```

### Windows

```cmd
deploy.bat
```

### 手动部署

如果脚本无法运行，可以手动执行：

```bash
# 1. 构建并启动服务
docker-compose up -d --build

# 2. 查看服务状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f
```

## 📝 部署后访问

部署成功后，可以通过以下地址访问：

- **前端界面**: http://localhost (或配置的端口)
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 🔧 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f          # 所有服务
docker-compose logs -f backend  # 仅后端
docker-compose logs -f frontend # 仅前端

# 停止服务
docker-compose down

# 停止并删除数据卷（注意：会删除数据库数据）
docker-compose down -v

# 重启服务
docker-compose restart

# 更新代码后重新部署
docker-compose up -d --build

# 进入容器（调试用）
docker-compose exec backend bash
docker-compose exec frontend sh
```

## 📊 服务架构

```
┌─────────────────────────────────────────┐
│         Nginx (前端静态文件)              │
│         Port: 80                         │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         FastAPI (后端API)                │
│         Port: 8000                       │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│    PostgreSQL (可选) / SQLite (默认)     │
│    Port: 5432 (PostgreSQL)               │
└─────────────────────────────────────────┘
```

## 🔐 生产环境建议

1. **修改SECRET_KEY**: 使用强随机字符串生成
   ```bash
   # Linux/macOS
   openssl rand -hex 32
   
   # 或使用Python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **配置HTTPS**: 使用Nginx反向代理并配置SSL证书

3. **使用PostgreSQL**: 生产环境推荐使用PostgreSQL
   ```env
   DATABASE_URL=postgresql://user:password@db:5432/dailydigest
   ```

4. **配置CORS**: 更新`.env`中的`CORS_ORIGINS`为实际前端域名
   ```env
   CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
   ```

5. **配置前端API地址**: 更新`VITE_API_URL`为实际后端地址
   ```env
   VITE_API_URL=https://api.your-domain.com
   ```

6. **备份数据库**: 定期备份PostgreSQL数据卷

## 🐛 故障排查

### 服务启动失败

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查端口占用
netstat -tuln | grep 8000
netstat -tuln | grep 80
```

### 数据库连接失败

- 检查`.env`中的`DATABASE_URL`配置
- 确认PostgreSQL容器正在运行：`docker-compose ps db`
- 查看数据库日志：`docker-compose logs db`

### 前端无法连接后端

- 检查`VITE_API_URL`配置（需要在构建时设置）
- 检查后端CORS配置：`.env`中的`CORS_ORIGINS`
- 确认后端服务运行：`curl http://localhost:8000/health`

### LLM服务失败

- 检查API密钥是否正确
- 查看后端日志确认错误信息
- 测试API密钥是否有效

## 📦 数据备份

### 备份PostgreSQL数据库

```bash
docker-compose exec db pg_dump -U postgres dailydigest > backup.sql
```

### 恢复PostgreSQL数据库

```bash
docker-compose exec -T db psql -U postgres dailydigest < backup.sql
```

### 备份SQLite数据库（如果使用SQLite）

```bash
docker-compose cp backend:/app/data/daily_digest.db ./backup.db
```

## 🔄 更新部署

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建并启动
docker-compose up -d --build

# 3. 查看更新日志
docker-compose logs -f
```

## 💰 资源需求

- **最小配置**: 1核512MB内存
- **推荐配置**: 2核1GB内存
- **存储**: 5-10GB（数据库和日志）

## 📚 更多信息

- 详细配置说明: 查看 `DEPLOYMENT_CHECKLIST.md`
- 环境变量说明: 查看 `.env.example`
- API文档: 部署后访问 `http://localhost:8000/docs`
