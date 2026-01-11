# Daily Digest Agent - 每日新闻摘要Agent

<div align="center">

📰 一个基于 AI 的个性化新闻摘要Web应用

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3.3-3178C6.svg?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4.1-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)

</div>

## 📖 项目简介

Daily Digest Agent 是一个智能新闻摘要应用，通过AI技术自动抓取、分析和总结新闻内容，为用户提供个性化的新闻摘要服务。系统支持多种新闻源、AI摘要生成、定时邮件推送等功能，帮助用户高效获取感兴趣的新闻信息。

### 核心功能

- 🎯 **个性化订阅**：自由订阅感兴趣的新闻主题（科技、AI、财经、娱乐等）
- 🤖 **AI智能摘要**：支持阿里云DashScope、NVIDIA GLM API或本地Ollama生成简洁摘要
- 🤪 **吐槽模式**：幽默俏皮的段子风格摘要，让阅读新闻更有趣
- 📧 **邮件推送**：可配置的定时邮件推送，支持每日、每周或自定义间隔
- 🎨 **精美界面**：基于 shadcn/ui 的现代化 UI，支持深色模式
- 📱 **移动端优化**：完美适配桌面和移动设备，响应式设计

## 🏗️ 系统架构

### 整体架构设计

```
┌─────────────────┐
│   Frontend      │  React + TypeScript + Vite
│   (React SPA)   │  └─ 用户界面、状态管理、API调用
└────────┬────────┘
         │ HTTP/REST API
┌────────▼────────┐
│   Backend       │  FastAPI + SQLAlchemy
│   (FastAPI)     │  └─ 业务逻辑、数据持久化、定时任务
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│ SQLite│ │ External│
│  或   │ │   APIs  │
│PostgreSQL│ │ LLM/News│
└───────┘ └─────────┘
```

### 后端架构

**技术栈：**
- **FastAPI** - 现代高性能 Python Web 框架，自动生成API文档
- **SQLAlchemy** - ORM 数据库操作，支持SQLite和PostgreSQL
- **APScheduler** - 定时任务调度，支持邮件推送定时任务
- **JWT** - 用户认证和授权，无状态认证机制
- **Pydantic** - 数据验证和配置管理

**核心模块：**

```
backend/
├── main.py              # FastAPI应用入口，生命周期管理
├── database.py          # 数据库配置、连接池、模型基类
├── models.py            # 数据模型（User、Subscription、NewsCache）
├── auth.py              # 用户认证逻辑（密码哈希、JWT生成）
├── news_fetcher.py      # 新闻抓取模块（GNews/NewsData/RSS）
├── summarizer.py        # LLM摘要生成模块（多提供商支持）
├── scheduler.py         # 定时任务调度器（邮件推送）
└── routes/              # API路由模块
    ├── auth.py          # 认证相关API（注册/登录/重置密码）
    ├── subscriptions.py # 订阅管理API（增删改查）
    ├── news.py          # 新闻相关API（获取/刷新摘要）
    ├── schedule.py      # 邮件调度API（配置定时推送）
    └── preferences.py   # 用户偏好设置API
```

**数据流程：**

```
1. 用户订阅主题
   ↓
2. NewsFetcher 定时抓取新闻（GNews/NewsData/RSS）
   ↓
3. 新闻缓存到 NewsCache 表
   ↓
4. Summarizer 调用 LLM 生成摘要
   ↓
5. 摘要存储到 NewsCache.summary
   ↓
6. Dashboard API 返回给前端展示
   ↓
7. Scheduler 定时发送邮件摘要（可选）
```

**LLM支持：**
- **DashScope（阿里云通义千问）** - 推荐，云端服务，无需GPU，性能稳定
- **NVIDIA GLM API** - 云端服务，无需GPU，支持多种模型
- **Ollama（本地模型）** - 需要本地部署，需要GPU，适合离线环境

### 前端架构

**技术栈：**
- **React 18** + **TypeScript** - UI框架，类型安全
- **Vite** - 快速构建工具，HMR热更新
- **Tailwind CSS** - 原子化CSS框架，快速样式开发
- **shadcn/ui** - 高质量UI组件库，可定制
- **Zustand** - 轻量级状态管理，简单易用
- **Axios** - HTTP客户端，请求拦截和错误处理
- **React Router** - 客户端路由管理

**项目结构：**

```
frontend/
├── src/
│   ├── pages/           # 页面组件
│   │   ├── LoginPage.tsx        # 登录页面
│   │   ├── RegisterPage.tsx     # 注册页面
│   │   ├── DashboardPage.tsx    # 新闻仪表板（主页面）
│   │   ├── SettingsPage.tsx     # 设置页面
│   │   └── ForgotPasswordPage.tsx # 密码重置
│   ├── components/       # 可复用组件
│   │   ├── ui/          # shadcn/ui组件（Button/Card/Dialog等）
│   │   ├── SubscriptionManager.tsx  # 订阅管理组件
│   │   ├── ScheduleSettings.tsx     # 邮件调度设置
│   │   └── PreferencesSettings.tsx  # 偏好设置
│   ├── store/           # 状态管理
│   │   └── authStore.ts # 用户认证状态（Zustand）
│   └── lib/             # 工具函数
│       ├── api.ts       # API客户端封装（Axios）
│       └── utils.ts     # 通用工具函数
```

**设计特点：**
- **移动端优先**：响应式设计，完美适配手机和桌面
- **现代化UI**：使用shadcn/ui组件库，支持深色模式
- **用户体验**：流畅的动画和交互反馈，Toast通知系统
- **类型安全**：完整的TypeScript类型定义

## 🚀 快速开始

### 前置要求

- **Python 3.10+**（本地开发）
- **Node.js 18+**（本地开发）
- **Docker & Docker Compose**（推荐部署方式）

### 快速部署（推荐）

使用Docker Compose一键部署：

```bash
# 1. 复制环境变量配置
cp env.example .env

# 2. 编辑 .env 文件，填入必需的配置
# 特别注意：SECRET_KEY 和 LLM API密钥

# 3. 运行部署脚本
# Linux/macOS
chmod +x deploy.sh
./deploy.sh

# Windows
deploy.bat

# 或手动部署
docker-compose up -d --build
```

**访问地址：**
- 前端：http://localhost
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs

### 本地开发

**后端：**
```bash
cd backend
pip install -r requirements.txt
cp env.example .env
# 编辑 .env 文件
python main.py
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

详细配置说明请查看 [QUICKSTART.md](QUICKSTART.md)

## 📁 项目结构

```
Daily-News/
├── backend/                 # FastAPI后端
│   ├── main.py             # 应用入口
│   ├── database.py         # 数据库配置
│   ├── models.py           # 数据模型
│   ├── auth.py             # 认证逻辑
│   ├── news_fetcher.py     # 新闻抓取
│   ├── summarizer.py       # AI摘要
│   ├── scheduler.py        # 定时任务
│   ├── routes/             # API路由
│   ├── requirements.txt    # Python依赖
│   └── Dockerfile          # Docker镜像
│
├── frontend/                # React前端
│   ├── src/                # 源代码
│   ├── package.json        # 依赖配置
│   ├── vite.config.ts      # Vite配置
│   └── Dockerfile          # Docker镜像
│
├── docker-compose.yml       # Docker编排配置
├── env.example             # 环境变量示例
├── deploy.sh               # 一键部署脚本（Linux/macOS）
├── deploy.bat              # 一键部署脚本（Windows）
└── README.md               # 本文档
```

## 🔧 配置说明

### 必需配置

在 `.env` 文件中配置：

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
CORS_ORIGINS=http://localhost:5173,http://your-domain.com
```

详细配置说明请查看 `env.example` 文件。

## 📚 文档

- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署详细说明
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - 部署检查清单

## 🔒 安全建议

1. **修改SECRET_KEY**：生产环境必须使用强随机密钥
2. **HTTPS**：生产环境必须使用HTTPS
3. **API Key保护**：不要将`.env`文件提交到Git
4. **CORS配置**：限制允许的前端域名
5. **数据库安全**：使用PostgreSQL并配置强密码

## 📝 开发计划

- [ ] Telegram Bot推送
- [ ] 阅读进度标记（已读/未读）
- [ ] 多语言支持
- [ ] 新闻收藏功能
- [ ] 导出摘要为PDF/Markdown

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 License

MIT License

---

**Made with ❤️ by AI**

如有问题，欢迎提Issue或联系开发者。
