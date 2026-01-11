# 邮件发送问题排查指南

## 常见问题

### 1. SMTP连接超时

**症状**: `socket.timeout: timed out` 或 `ConnectionError`

**可能原因**:
- 网络连接问题
- 防火墙阻止SMTP端口
- SMTP服务器地址或端口错误
- 需要使用SSL而不是TLS

**解决方案**:

1. **检查网络连接**:
   ```bash
   telnet smtp.gmail.com 587
   # 或
   telnet smtp.gmail.com 465
   ```

2. **尝试使用SSL端口**:
   在 `.env` 文件中修改：
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=465  # 使用SSL端口
   ```

3. **检查防火墙设置**:
   - 确保允许出站连接到SMTP端口（587或465）
   - 某些网络环境可能阻止SMTP连接

### 2. SMTP认证失败

**症状**: `SMTPAuthenticationError` 或 `535 Authentication failed`

**可能原因**:
- 用户名或密码错误
- Gmail需要使用应用专用密码
- 账户未启用"允许不够安全的应用"

**解决方案**:

1. **Gmail用户**:
   - 访问 https://myaccount.google.com/apppasswords
   - 生成"应用专用密码"
   - 在 `.env` 中使用应用专用密码，而不是普通密码

2. **其他邮箱服务**:
   - 检查是否需要启用SMTP功能
   - 确认用户名格式（可能需要完整邮箱地址）

### 3. 未配置邮件服务

**症状**: `ValueError: 未配置邮件服务`

**解决方案**:

配置以下之一：

**选项1: 使用Resend API（推荐）**
```env
RESEND_API_KEY=re_xxxxxxxxxxxxx
FROM_EMAIL=noreply@yourdomain.com
```

**选项2: 使用SMTP**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587  # 或 465 for SSL
DEFAULT_EMAIL_ACCOUNT=your-email@gmail.com
DEFAULT_EMAIL_PASSWORD=your-app-password
```

### 4. 邮件发送成功但收不到

**可能原因**:
- 邮件被标记为垃圾邮件
- 发送地址未验证
- 收件箱过滤规则

**解决方案**:
- 检查垃圾邮件文件夹
- 将发送地址添加到联系人
- 使用已验证的发送地址

## 测试步骤

1. **运行诊断脚本**:
   ```bash
   cd backend
   python test_email_send.py
   ```

2. **检查配置**:
   ```bash
   python -c "from database import settings; print('SMTP:', settings.SMTP_HOST); print('Account:', settings.DEFAULT_EMAIL_ACCOUNT)"
   ```

3. **测试SMTP连接**:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-password')
   ```

## Gmail配置示例

```env
# Gmail SMTP配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587  # TLS
# 或
SMTP_PORT=465  # SSL

DEFAULT_EMAIL_ACCOUNT=your-email@gmail.com
DEFAULT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  # 应用专用密码（16位，带空格）
```

**重要**: Gmail必须使用应用专用密码，不能使用普通密码！

## 其他邮箱服务配置

### Outlook/Hotmail
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
```

### QQ邮箱
```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
# 需要使用授权码，不是QQ密码
```

### 163邮箱
```env
SMTP_HOST=smtp.163.com
SMTP_PORT=25  # 或 465
```

## 调试技巧

1. **查看详细日志**:
   检查后端日志输出，查找 `[ERROR]` 标记

2. **测试简单邮件**:
   使用 `test_email_send.py` 脚本发送测试邮件

3. **检查网络**:
   确保服务器可以访问SMTP服务器

4. **验证配置**:
   确保 `.env` 文件中的配置正确，没有多余空格
