# 部署检查清单

## 1. 端口需求

### 后端API服务
- **默认端口**: 8000
- **配置方式**: 通过环境变量 `PORT` 或 `.env` 文件中的 `PORT` 配置
- **用途**: FastAPI后端服务端口

### 前端Web服务
- **开发环境**: 5173 (Vite开发服务器)
- **生产环境**: 80/443 (Nginx，通过Docker容器映射)
- **配置方式**: Docker容器端口映射，可在 `docker-compose.yml` 中修改

### 可选服务
- **Ollama本地LLM**: 11434 (仅在需要本地大模型时使用)
  - 如果使用云端LLM（DashScope/NVIDIA），**不需要**此端口

## 2. 部署条件评估

### ✅ 可直接部署（推荐方式）

**使用云端LLM服务（DashScope或NVIDIA）：**

- ✅ **无需本地大模型**：使用阿里云DashScope或NVIDIA GLM API，通过HTTP调用
- ✅ **无需GPU**：所有计算在云端完成
- ✅ **资源需求低**：仅需运行Python FastAPI服务
- ✅ **推荐配置**：
  - CPU: 1-2核心
  - 内存: 512MB - 1GB
  - 存储: 5-10GB（数据库和日志）

**数据库选择：**
- **SQLite（默认）**：适合单机部署，无需额外服务
- **PostgreSQL（推荐生产环境）**：更稳定，支持并发，可通过Docker Compose部署

### ⚠️ 需要额外条件（不推荐）

**使用本地Ollama：**

- ⚠️ **需要GPU支持**：推荐NVIDIA GPU，显存至少4GB
- ⚠️ **需要安装Ollama**：需在服务器上安装和运行Ollama服务
- ⚠️ **资源需求高**：
  - CPU: 4+核心
  - 内存: 8GB+
  - GPU: 显存4GB+（推荐）
  - 存储: 20GB+（模型文件）

**结论：建议使用云端LLM（DashScope或NVIDIA），无需特殊硬件条件，可直接部署**

## 3. 必需的环境变量

### 后端必需配置

```env
# JWT密钥（必须修改为强随机字符串）
SECRET_KEY=your-strong-random-secret-key-here

# LLM提供商（三选一）
# 选项1：阿里云DashScope（推荐）
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx

# 选项2：NVIDIA GLM API
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=your-nvidia-api-key

# 选项3：本地Ollama（需要额外部署Ollama服务）
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# 服务器配置（可选，默认8000）
PORT=8000
HOST=0.0.0.0

# CORS配置（必须配置前端域名）
CORS_ORIGINS=http://localhost:5173,http://your-domain.com

# 数据库（可选，默认SQLite）
DATABASE_URL=sqlite:///./daily_digest.db
# 或使用PostgreSQL
# DATABASE_URL=postgresql://user:password@db:5432/dailydigest

# 邮件服务（可选，二选一）
# 选项1：Resend（推荐）
RESEND_API_KEY=re_xxxxxxxxxxxxx
FROM_EMAIL=noreply@yourdomain.com

# 选项2：SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
DEFAULT_EMAIL_ACCOUNT=your-email@gmail.com
DEFAULT_EMAIL_PASSWORD=your-app-password

# 新闻API（至少配置一个）
GNEWS_API_KEY=your-gnews-api-key
NEWSDATA_API_KEY=your-newsdata-api-key
```

### 前端配置

```env
# API地址（必须）
VITE_API_URL=http://localhost:8000
# 生产环境改为实际后端地址
# VITE_API_URL=https://api.your-domain.com
```

## 4. 部署架构

### 推荐架构（使用Docker Compose）

```
┌─────────────────────────────────────────┐
│         Nginx (前端静态文件)              │
│         Port: 80/443                    │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         FastAPI (后端API)                │
│         Port: 8000                      │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│    PostgreSQL (可选) / SQLite (默认)     │
│    Port: 5432 (PostgreSQL)              │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│    云端LLM服务 (DashScope/NVIDIA)        │
│    (无需本地部署)                        │
└─────────────────────────────────────────┘
```

## 5. 资源需求估算

### 最小配置（使用云端LLM）
- **CPU**: 1核心
- **内存**: 512MB
- **存储**: 5GB
- **带宽**: 10Mbps

### 推荐配置（使用云端LLM）
- **CPU**: 2核心
- **内存**: 1GB
- **存储**: 10GB
- **带宽**: 20Mbps

### 不推荐配置（使用本地Ollama）
- **CPU**: 4+核心
- **内存**: 8GB+
- **GPU**: NVIDIA GPU (4GB+显存)
- **存储**: 20GB+
- **带宽**: 50Mbps+

## 6. 部署前检查

- [ ] 确认服务器满足资源需求
- [ ] 配置LLM API密钥（DashScope或NVIDIA）
- [ ] 配置邮件服务（如需要）
- [ ] 配置新闻API密钥
- [ ] 设置强随机SECRET_KEY
- [ ] 配置CORS_ORIGINS为实际前端域名
- [ ] 确认端口未被占用（8000）
- [ ] 如使用PostgreSQL，确认数据库连接信息

## 7. 成本估算

### 服务器成本（示例）
- **VPS（1核1G）**: ¥20-50/月
- **VPS（2核2G）**: ¥50-100/月

### 服务成本
- **DashScope API**: ¥0.008/1000 tokens，每月约¥5-20
- **NVIDIA GLM API**: 需查询NVIDIA定价
- **Resend邮件**: 免费3000封/月，超出后按量付费
- **GNews API**: 免费100次/天，付费计划$29/月起

**总成本估算：¥30-150/月（根据使用量）**
