# Daily Digest Agent - 快速启动指南

## 第一次使用？按照以下步骤操作：

### 1️⃣ 后端设置（5分钟）

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp env.example .env
```

**编辑 `.env` 文件，必须填写以下内容：**

```env
# 随机生成一个密钥（可以使用在线工具）
SECRET_KEY=your-random-secret-key-here

# 阿里云通义千问 API Key（必须，如果使用云端模型）
# 获取地址：https://dashscope.console.aliyun.com/
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxx

# LLM 设置 (DashScope 或 Local Ollama)
# 默认使用 'dashscope', 如需使用本地 Ollama 请设置为 'ollama'
LLM_PROVIDER=dashscope
# Ollama 配置 (仅在 LLM_PROVIDER=ollama 时生效)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# 注意：如果使用 Ollama，请确保本地已安装 Ollama 并运行了模型
# ollama pull qwen3:8b
# ollama serve

# 新闻 API（至少配置一个）
# GNews: https://gnews.io/register（免费100次/月）
GNEWS_API_KEY=your-gnews-key

# 或者使用 NewsData.io: https://newsdata.io/register（免费200次/天）
NEWSDATA_API_KEY=your-newsdata-key
```

**启动后端：**

```bash
python main.py
```

✅ 看到 "Application startup complete" 表示成功！

### 2️⃣ 前端设置（3分钟）

```bash
cd frontend

# 安装依赖（首次需要几分钟）
npm install

# 启动开发服务器
npm run dev
```

✅ 浏览器自动打开 `http://localhost:5173`

### 3️⃣ 开始使用

1. **注册账户**
   - 打开浏览器访问 `http://localhost:5173`
   - 点击"注册"，使用任意邮箱和密码（本地开发无需真实邮箱）

2. **添加订阅**
   - 登录后，点击右上角"设置"图标
   - 点击热门主题快速订阅，如"科技"、"AI"
   - 或输入自定义主题名称
   - **新增**：可以添加自定义RSS源，支持中文技术博客

3. **获取新闻**
   - 点击右上角"刷新"按钮（⟳）
   - 等待几秒，新闻将自动加载
   - 展开任意主题卡片查看摘要
   - **新增**：系统会智能防重复刷新，避免资源浪费

4. **体验吐槽模式**
   - 在订阅管理中，打开任意主题的"吐槽模式"开关
   - 再次刷新，查看AI生成的幽默摘要 🤪

5. **个性化设置**（新增功能）
   - 在设置页面配置偏好：
     - **隐藏已读**：自动隐藏已读新闻
     - **排序方式**：按时间或相关性排序
     - **隐藏来源**：过滤不感兴趣的新闻来源
   - 点击新闻卡片标记为已读/未读

## 🎯 常见问题

### Q: 后端启动报错 "ModuleNotFoundError"
**A:** 确保已激活虚拟环境并安装依赖：
```bash
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Q: 前端启动后页面空白
**A:** 检查浏览器控制台，确保后端已启动（http://localhost:8000）

### Q: 刷新后没有新闻
**A:** 
1. 检查 `.env` 文件中是否配置了 API Key
2. 查看后端终端日志，确认是否有错误信息
3. 如果API额度用尽，会自动降级到RSS源（速度较慢）

### Q: 如何获取阿里云 API Key？
**A:** 
1. 访问 https://dashscope.console.aliyun.com/
2. 登录阿里云账号（没有则注册）
3. 点击"API-KEY管理"
4. 创建新的 API Key
5. 复制到 `.env` 文件

### Q: 邮件推送如何配置？
**A:** 
推荐使用 Resend（免费额度充足）：
1. 访问 https://resend.com/
2. 注册并获取 API Key
3. 在 `.env` 中配置：
```env
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=noreply@yourdomain.com
```

## 🔍 验证安装

### 检查后端
访问 http://localhost:8000/docs 应该看到 API 文档

### 检查前端
访问 http://localhost:5173 应该看到登录页面

### 检查数据库
后端启动后，会自动创建 `daily_digest.db` 文件

## 📚 下一步

- 查看 [README.md](README.md) 了解完整功能
- 尝试添加自定义RSS源（如阮一峰、酷壳等中文技术博客）
- 配置用户偏好（隐藏已读、排序方式、过滤来源）
- 配置定时任务，每天自动更新新闻
- 部署到生产环境（Railway + Vercel）

## 🆕 新功能亮点

- ✅ **自定义RSS源**：支持添加任意RSS源，内置中文技术博客
- ✅ **阅读状态**：标记已读/未读，支持隐藏已读新闻
- ✅ **智能排序**：按时间或相关性排序，LLM评估新闻重要性
- ✅ **来源过滤**：隐藏不感兴趣的新闻来源
- ✅ **防重复刷新**：智能刷新控制，避免资源浪费

## 💡 提示

- 开发时保持后端和前端都运行
- 修改代码后会自动热重载
- 使用深色模式保护眼睛（点击右上角月亮图标）

需要帮助？查看完整 README 或提交 Issue！
