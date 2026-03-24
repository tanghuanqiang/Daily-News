# 管理员面板快速测试指南

## 快速开始（5分钟）

### 1. 安装依赖

```bash
cd D:\gitRepositories\Daily-News\frontend
npm install recharts
```

### 2. 启动服务

**启动后端（终端1）:**
```bash
cd D:\gitRepositories\Daily-News\backend
python main.py
```

**启动前端（终端2）:**
```bash
cd D:\gitRepositories\Daily-News\frontend
npm run dev
```

### 3. 设置管理员账户

```bash
cd D:\gitRepositories\Daily-News\backend
python scripts\setup_admin.py
```

按照提示创建管理员账户。

### 4. 登录并访问

1. 打开浏览器访问: http://localhost:5173
2. 使用刚才创建的管理员账户登录
3. 点击右上角紫色盾牌图标 🛡️
4. 进入管理员面板！

## 功能测试清单

### ✅ 概览页面
- [ ] 查看统计卡片（用户、新闻、邀请、实验）
- [ ] 查看用户活跃度趋势图
- [ ] 查看新闻主题分布图
- [ ] 查看最近活动日志

### ✅ 用户管理
- [ ] 查看用户列表
- [ ] 使用搜索框搜索用户
- [ ] 查看用户详细信息（偏好、邀请统计）
- [ ] 查看统计卡片（总数、活跃、管理员）

### ✅ 新闻管理
- [ ] 查看新闻列表
- [ ] 使用搜索框搜索新闻
- [ ] 查看新闻详细信息（主题、来源、时间）
- [ ] 查看统计卡片（总数、主题数、新增）

### ✅ 邀请管理
- [ ] 切换"邀请码"和"排行榜"标签
- [ ] 查看邀请码列表（状态、使用者）
- [ ] 查看排行榜（排名、成功率、点数）
- [ ] 使用搜索框搜索
- [ ] 查看统计卡片

### ✅ 实验管理
- [ ] 查看实验列表
- [ ] 使用状态筛选器
- [ ] 点击"启动"按钮（草稿实验）
- [ ] 点击"暂停"按钮（运行中实验）
- [ ] 点击"恢复"按钮（暂停实验）
- [ ] 点击"完成"按钮（运行中实验）
- [ ] 点击"可视化仪表板"按钮
- [ ] 查看统计卡片

### ✅ 日志查看
- [ ] 查看日志列表
- [ ] 使用级别筛选器（信息/警告/错误）
- [ ] 点击"刷新"按钮
- [ ] 查看统计卡片

## API测试（可选）

使用浏览器或Postman测试API：

```bash
# 获取概览数据
curl http://localhost:8000/api/admin/overview

# 获取用户列表
curl http://localhost:8000/api/admin/users

# 获取邀请统计
curl http://localhost:8000/api/admin/invitations/stats

# 获取实验列表
curl http://localhost:8000/api/admin/experiments
```

## 常见问题

### Q: 看不到管理员按钮？
A: 确认您的账户is_admin=true，重新登录试试。

### Q: 图表不显示？
A: 确认已安装recharts，检查浏览器控制台错误。

### Q: API返回403错误？
A: 确认已登录且有管理员权限。

### Q: 如何添加更多管理员？
A: 使用setup_admin.py脚本，或手动设置is_admin=true。

## 成功标志

✅ **测试成功**: 所有功能模块都能正常访问和操作
✅ **数据正确**: 显示的数据与数据库一致
✅ **权限正常**: 非管理员无法访问
✅ **响应及时**: 页面加载和操作响应快速

## 下一步

- 阅读完整指南: [ADMIN_PANEL_GUIDE.md](./ADMIN_PANEL_GUIDE.md)
- 查看API文档: http://localhost:8000/docs
- 自定义和扩展功能

---

🎉 **测试完成！欢迎使用Daily-News管理员面板！**
