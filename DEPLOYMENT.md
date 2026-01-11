# 部署指南

## Railway 后端部署

### 步骤 1：准备项目

1. 创建 `runtime.txt`（可选）：
```
python-3.11
```

2. 创建 `Procfile`：
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

### 步骤 2：Railway 配置

1. 访问 https://railway.app/
2. 点击 "New Project" → "Deploy from GitHub repo"
3. 选择你的仓库
4. 配置环境变量（Settings → Variables）：

```
SECRET_KEY=your-production-secret-key
DASHSCOPE_API_KEY=sk-xxxxx
GNEWS_API_KEY=xxxxx
RESEND_API_KEY=re_xxxxx
FROM_EMAIL=noreply@yourdomain.com
CORS_ORIGINS=https://your-frontend-domain.vercel.app
DATABASE_URL=postgresql://...（Railway 自动提供）
```

5. 部署设置：
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 步骤 3：数据库

Railway 会自动提供 PostgreSQL，无需额外配置。

## Vercel 前端部署

### 步骤 1：构建优化

确保 `package.json` 构建脚本正确：
```json
{
  "scripts": {
    "build": "tsc && vite build",
    "preview": "vite preview"
  }
}
```

### 步骤 2：Vercel 配置

1. 访问 https://vercel.com/
2. Import Git Repository
3. 配置：
   - Framework Preset: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

4. 环境变量：
```
VITE_API_URL=https://your-backend.railway.app
```

### 步骤 3：部署

点击 Deploy，几分钟后即可访问。

## 域名配置

### 后端域名（Railway）
1. Railway Settings → Domains
2. Generate Domain 或添加自定义域名

### 前端域名（Vercel）
1. Vercel Settings → Domains
2. Add Domain

### CORS 更新
部署后，记得在 Railway 环境变量中更新 `CORS_ORIGINS`：
```
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

## 生产环境检查清单

- [ ] 更换强随机 SECRET_KEY
- [ ] 配置生产环境数据库（PostgreSQL）
- [ ] 启用 HTTPS
- [ ] 限制 CORS 源
- [ ] 配置邮件服务
- [ ] 测试定时任务
- [ ] 监控日志和错误
- [ ] 备份数据库

## 环境变量汇总

### 后端必需
- `SECRET_KEY` - JWT 密钥
- `DASHSCOPE_API_KEY` - 阿里云 Qwen API
- `DATABASE_URL` - 数据库连接（Railway 自动提供）
- `CORS_ORIGINS` - 允许的前端域名

### 后端可选
- `GNEWS_API_KEY` - GNews API
- `NEWSDATA_API_KEY` - NewsData API
- `RESEND_API_KEY` - Resend 邮件服务
- `FROM_EMAIL` - 发件人邮箱
- `DAILY_UPDATE_HOUR` - 每日更新时间（小时）
- `TIMEZONE` - 时区

### 前端
- `VITE_API_URL` - 后端 API 地址

## 故障排查

### 部署失败
检查构建日志，确保所有依赖正确安装

### CORS 错误
检查后端 CORS_ORIGINS 是否包含前端域名

### API 调用失败
确保前端 VITE_API_URL 指向正确的后端地址

### 数据库连接失败
检查 DATABASE_URL 格式和数据库服务状态

## 成本估算

- Railway: $5/月（包含数据库）
- Vercel: 免费（Hobby 计划）
- 阿里云 Qwen: <$5/月（低流量）
- Resend: 免费（3000封/月）

**总计：~$10/月**

## 更新部署

### 后端更新
```bash
git add .
git commit -m "Update backend"
git push
```
Railway 会自动重新部署

### 前端更新
```bash
git add .
git commit -m "Update frontend"
git push
```
Vercel 会自动重新部署

## 回滚

### Railway
Deployments → 选择之前的部署 → Redeploy

### Vercel
Deployments → 选择之前的部署 → Promote to Production
