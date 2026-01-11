# 定时邮件发送配置指南

## 功能说明

系统支持定时获取新闻并发送邮件摘要给所有注册用户。支持三种定时模式：
- **每天** (daily): 每天固定时间发送
- **每周** (weekly): 每周固定日期和时间发送
- **间隔** (interval): 每隔N小时发送一次

## 配置步骤

### 1. 配置默认邮箱账户

在 `backend/.env` 文件中添加以下配置：

```env
# 默认发送邮箱账户（用于SMTP发送）
DEFAULT_EMAIL_ACCOUNT=your-email@gmail.com
DEFAULT_EMAIL_PASSWORD=your-app-password

# SMTP服务器配置（如果使用Gmail，使用以下配置）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

**重要提示：**
- 如果使用Gmail，需要生成"应用专用密码"而不是普通密码
- 生成应用专用密码：Google账户 → 安全性 → 两步验证 → 应用专用密码
- 其他邮箱服务商请参考其SMTP配置文档

### 2. 配置定时任务模式

在 `backend/.env` 文件中配置定时任务：

#### 每天发送（推荐）

```env
# 每天发送
EMAIL_SCHEDULE_TYPE=daily
EMAIL_SCHEDULE_HOUR=9      # 每天9点
EMAIL_SCHEDULE_MINUTE=0    # 0分
```

#### 每周发送

```env
# 每周发送
EMAIL_SCHEDULE_TYPE=weekly
EMAIL_SCHEDULE_HOUR=9      # 9点
EMAIL_SCHEDULE_MINUTE=0    # 0分
EMAIL_SCHEDULE_DAY_OF_WEEK=0  # 0=周一, 1=周二, ..., 6=周日
```

#### 间隔发送

```env
# 每隔N小时发送
EMAIL_SCHEDULE_TYPE=interval
EMAIL_SCHEDULE_INTERVAL_HOURS=24  # 每24小时（即每天）
```

### 3. 时区配置

```env
TIMEZONE=Asia/Shanghai  # 根据你的时区调整
```

## 完整配置示例

```env
# 默认邮箱账户
DEFAULT_EMAIL_ACCOUNT=your-email@gmail.com
DEFAULT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx

# SMTP配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# 定时任务配置（每天上午9点发送）
EMAIL_SCHEDULE_TYPE=daily
EMAIL_SCHEDULE_HOUR=9
EMAIL_SCHEDULE_MINUTE=0
TIMEZONE=Asia/Shanghai
```

## API接口

### 查看定时任务状态

```bash
GET /api/schedule/status
```

返回当前定时任务配置和下次执行时间。

### 测试邮件发送

```bash
POST /api/schedule/test
```

立即执行一次邮件发送任务（用于测试）。

### 查看所有定时任务

```bash
GET /api/schedule/jobs
```

列出所有已配置的定时任务。

## 工作流程

1. **定时触发**: 根据配置的时间，系统自动触发 `send_scheduled_emails()` 任务
2. **获取新闻**: 为所有活跃用户更新其订阅主题的新闻
3. **生成摘要**: 使用LLM为每条新闻生成摘要（普通模式和吐槽模式）
4. **发送邮件**: 向所有启用邮件通知的用户发送个性化摘要邮件

## 邮件内容

邮件包含：
- 用户订阅的所有主题
- 每个主题的最新5条新闻
- 每条新闻的标题、AI摘要和原文链接
- 根据用户的订阅设置显示普通摘要或吐槽摘要

## 注意事项

1. **用户必须启用邮件通知**: 只有 `email_notifications=True` 的用户才会收到邮件
2. **用户必须有活跃订阅**: 没有订阅主题的用户不会收到邮件
3. **确保邮箱服务可用**: 系统会先尝试Resend API，失败后使用SMTP
4. **日志记录**: 所有邮件发送操作都会记录到系统日志中

## 故障排查

### 邮件发送失败

1. 检查 `.env` 文件中的邮箱账户和密码是否正确
2. 检查SMTP服务器配置是否正确
3. 查看后端日志中的错误信息
4. 使用 `/api/schedule/test` 接口测试邮件发送

### 定时任务未执行

1. 检查 `EMAIL_SCHEDULE_TYPE` 配置是否正确
2. 检查时区配置是否正确
3. 查看 `/api/schedule/status` 确认任务状态
4. 查看后端日志确认调度器是否正常启动
