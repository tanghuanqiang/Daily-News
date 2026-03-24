# Daily-News 管理员面板使用指南

## 功能概述

管理员面板提供了完整的系统管理和数据监控功能，让您可以直观地查看和操作Daily-News项目的各项数据。

## 主要功能模块

### 1. 概览页面 (Overview)
- **实时统计卡片**: 用户总数、新闻数量、邀请码使用率、运行中实验数
- **图表展示**:
  - 用户活跃度趋势图（折线图）
  - 新闻主题分布图（饼图）
- **最近活动**: 系统事件实时展示

### 2. 用户管理 (Users)
- **用户列表**: 查看所有注册用户
- **搜索功能**: 按邮箱或用户名搜索
- **详细信息**: 
  - 基本信息（邮箱、用户名、注册时间）
  - 状态（活跃/禁用、普通用户/管理员）
  - 偏好设置（订阅主题）
  - 邀请统计（邀请人数、获得点数）
- **统计卡片**: 总用户数、活跃用户、管理员数量

### 3. 新闻管理 (News)
- **文章列表**: 查看所有抓取的新闻
- **筛选功能**: 按主题筛选
- **详细信息**:
  - 标题和摘要
  - 主题标签
  - 来源信息
  - 发布时间和抓取时间
- **统计卡片**: 总文章数、主题数量、今日新增、本周新增

### 4. 邀请管理 (Invitations)
- **标签页切换**:
  - 邀请码列表: 查看所有邀请码
  - 排行榜: 邀请达人排行榜
- **邀请码信息**:
  - 邀请码内容
  - 创建者
  - 使用状态
  - 使用者
  - 创建和使用时间
- **排行榜**:
  - 排名（显示奖牌图标）
  - 用户信息
  - 邀请统计（总人数、成功数、成功率）
  - 获得点数
  - 最后邀请时间
- **统计卡片**: 总邀请码、已使用、使用率、TOP用户

### 5. 实验管理 (Experiments)
- **实验列表**: 查看所有A/B测试实验
- **状态筛选**: 按状态筛选（草稿/运行中/暂停/已完成）
- **实验信息**:
  - 实验名称和描述
  - 状态标签
  - 流量分配百分比
  - 版本数量
  - 参与用户数
  - 创建时间
- **操作按钮**:
  - 启动（草稿状态）
  - 暂停（运行中状态）
  - 恢复（暂停状态）
  - 完成（运行中状态）
- **可视化仪表板**: 跳转到实验结果可视化页面
- **统计卡片**: 总实验数、运行中、总参与用户、平均版本数

### 6. 日志查看 (Logs)
- **日志筛选**: 按级别筛选（全部/信息/警告/错误）
- **日志内容**:
  - 时间戳
  - 级别标签
  - 消息内容
- **滚动区域**: 支持长日志列表滚动
- **操作按钮**: 刷新日志、导出日志
- **统计卡片**: 总日志数、信息数、警告数、错误数

## 访问方式

### 1. 设置管理员权限

首先，需要将您的用户账户设置为管理员：

```sql
-- 连接到SQLite数据库
sqlite3 daily_digest.db

-- 将指定用户设置为管理员
UPDATE users SET is_admin = true WHERE email = 'your@email.com';

-- 验证设置
SELECT email, is_admin FROM users WHERE email = 'your@email.com';
```

### 2. 访问管理员面板

#### 方法一：通过导航栏
1. 登录Daily-News系统
2. 在Dashboard页面右上角找到紫色盾牌图标 🛡️
3. 点击图标即可进入管理员面板

#### 方法二：直接访问
1. 登录系统
2. 直接访问URL: `http://localhost:5173/admin`

### 3. 权限控制

- 只有 `is_admin = true` 的用户才能访问管理员面板
- 非管理员用户访问 `/admin` 路径会自动跳转回 `/dashboard`
- 所有管理员API都有权限验证，非管理员调用会返回403错误

## API接口文档

### 查看API文档

访问: `http://localhost:8000/docs`

在Swagger UI中，展开 `admin` 标签查看所有管理员API接口。

### 主要API端点

#### 概览数据
- `GET /api/admin/overview` - 获取系统概览统计

#### 用户管理
- `GET /api/admin/users` - 获取用户列表
- `GET /api/admin/users/{user_id}` - 获取用户详情

#### 新闻管理
- `GET /api/admin/news` - 获取新闻列表

#### 邀请管理
- `GET /api/admin/invitations` - 获取邀请码列表
- `GET /api/admin/invitations/stats` - 获取邀请统计排行

#### 实验管理
- `GET /api/admin/experiments` - 获取实验列表
- `GET /api/admin/experiments/{experiment_id}` - 获取实验详情
- `PUT /api/admin/experiments/{experiment_id}/status` - 更新实验状态

#### 系统日志
- `GET /api/admin/logs/system` - 获取系统日志

#### 数据导出
- `GET /api/admin/export/users` - 导出用户数据

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLAlchemy + SQLite
- **认证**: JWT Token + 管理员权限验证

### 前端
- **框架**: React 18 + TypeScript
- **路由**: React Router v6
- **UI组件**: shadcn/ui + Radix UI
- **样式**: Tailwind CSS
- **图表**: Recharts
- **图标**: Lucide React

## 安装依赖

如果您在启动前端时遇到Recharts相关的错误，请安装依赖：

```bash
cd D:\gitRepositories\Daily-News\frontend
npm install recharts
# 或
pnpm add recharts
```

## 配置管理员账户

### 创建第一个管理员

如果系统中还没有管理员账户，可以通过以下方式创建：

```python
# 在backend目录下运行Python脚本
python -c "
from database import SessionLocal
from models import User
from auth import get_password_hash

# 创建数据库会话
db = SessionLocal()

# 检查是否已存在管理员
existing_admin = db.query(User).filter(User.is_admin == True).first()

if existing_admin:
    print(f'已存在管理员: {existing_admin.email}')
else:
    # 创建新管理员账户
    admin_user = User(
        email='admin@example.com',
        username='admin',
        hashed_password=get_password_hash('admin123'),
        is_admin=True,
        is_active=True,
        email_verified=True,
        email_notifications=True
    )
    db.add(admin_user)
    db.commit()
    print('管理员账户创建成功！')
    print('邮箱: admin@example.com')
    print('密码: admin123')
    print('请及时修改密码！')

db.close()
"
```

## 使用建议

### 1. 日常监控
- 每天查看概览页面的统计卡片，了解系统运行状况
- 关注用户活跃度趋势，及时调整推送策略
- 监控邀请码使用情况，评估病毒式增长效果

### 2. 用户管理
- 定期检查用户列表，关注异常账户
- 通过邀请统计了解核心用户（邀请达人）
- 必要时禁用恶意用户账户

### 3. 内容管理
- 监控新闻抓取情况，确保各主题内容充足
- 关注新闻质量，必要时调整抓取源

### 4. 实验管理
- 谨慎启动实验，确保配置正确
- 定期查看实验结果，及时暂停效果不佳的实验
- 使用可视化仪表板深入分析实验数据

### 5. 日志分析
- 关注ERROR级别日志，及时发现系统问题
- 定期查看WARNING日志，预防潜在问题
- 使用日志导出功能进行离线分析

## 安全注意事项

1. **保护管理员账户**: 使用强密码，定期更换
2. **限制管理员数量**: 只给信任的用户管理员权限
3. **监控管理员操作**: 所有管理员操作都有日志记录
4. **安全退出**: 使用完毕后及时退出管理员账户
5. **数据备份**: 定期备份数据库，防止数据丢失

## 故障排除

### 无法访问管理员面板

**问题**: 看不到管理员按钮或无法访问/admin路径

**解决**:
1. 确认已登录
2. 检查用户is_admin字段是否为true
3. 刷新页面或重新登录
4. 检查浏览器控制台是否有错误信息

### API返回403错误

**问题**: 调用管理员API时返回403 Forbidden

**解决**:
1. 确认用户有管理员权限
2. 检查JWT Token是否有效
3. 确认请求头中包含正确的Authorization信息

### 图表不显示

**问题**: 概览页面的图表区域空白

**解决**:
1. 确认已安装recharts: `npm list recharts`
2. 检查浏览器控制台是否有JavaScript错误
3. 确认API返回数据格式正确
4. 尝试刷新页面

### 实验状态无法更新

**问题**: 点击启动/暂停按钮无反应

**解决**:
1. 检查网络连接
2. 查看浏览器控制台是否有错误
3. 确认实验状态转换逻辑正确（例如：已完成实验不能重新启动）
4. 检查服务器日志

## 扩展功能

管理员面板支持轻松扩展，您可以：

1. **添加新的数据看板**: 在AdminOverview中添加新的图表
2. **增加管理功能**: 在AdminUsers中添加用户编辑/删除功能
3. **集成更多日志**: 扩展AdminLogs以显示应用日志、错误日志等
4. **添加数据导出**: 实现更多数据导出功能（CSV/Excel）

## 技术支持

如遇到问题或有功能建议，请联系开发团队或提交Issue。

---

**Daily-News Admin Panel v1.0**  
*为更好的新闻体验而设计*
