# Daily-News P2阶段功能操作指南

**版本**: 2.0.0  
**更新日期**: 2026-03-24  
**阶段**: P2完成版

---

## 📋 目录

1. [推送时机个性化](#1-推送时机个性化)
2. [邀请奖励系统](#2-邀请奖励系统)
3. [A/B测试平台](#3-ab测试平台)
4. [API接口文档](#4-api接口文档)
5. [实验结果仪表板](#5-实验结果仪表板)
6. [系统启动和访问](#6-系统启动和访问)

---

## 1. 推送时机个性化

### 功能概述

自动分析用户活跃时间，为每个用户计算最佳邮件推送时间，提升邮件打开率和用户参与度。

### 数据库表

- **user_activity_logs**: 记录用户行为日志
  - user_id: 用户ID
  - activity_type: 行为类型（login, read, share, feedback, email_open）
  - activity_time: 行为时间
  - hour_of_day: 小时（0-23）
  - day_of_week: 星期几（0-6）

### 使用方式

#### 1.1 分析用户活跃时间

```bash
cd D:\gitRepositories\Daily-News\backend
python scripts\analyze_user_activity.py
```

**功能说明**:
- 分析过去7天的用户行为数据
- 计算每个用户最活跃的时间段
- 自动保存最佳推送时间到用户配置

**输出示例**:
```
开始分析所有用户的活跃时间（分析过去 7 天）...
分析完成：成功分析 5 个用户，保存 5 个用户的推送时间

推送时间分析报告：
用户最佳推送时间分布：
  09:00 -   2 个用户 (40.0%) ████████
  10:00 -   1 个用户 (20.0%) ████
  14:00 -   1 个用户 (20.0%) ████
  15:00 -   1 个用户 (20.0%) ████

统计摘要：
  总用户数: 5
  平均推送时间: 11.6:00
  推送时间标准差: 2.6 小时

任务完成！成功分析 5 个用户，保存 5 个用户的推送时间
```

#### 1.2 验证个性化推送

```bash
python scripts\test_personalized_push.py
```

**测试内容**:
- 验证用户推送时间获取逻辑
- 验证邮件发送判断逻辑
- 使用真实用户数据测试

**输出示例**:
```
=== 测试获取用户推送时间 ===
测试1: 用户未启用个性化推送
结果: 08:00 (应使用默认时间 08:00) [PASS]
测试2: 启用个性化推送，时间设为14:30
结果: 14:30 [PASS]
测试3: 只设置小时，分钟为None
结果: 14:00 [PASS]

=== 测试邮件发送判断 ===
测试1: 当前时间匹配推送时间（10:05）
结果: True (期望: True) [PASS]
测试2: 当前小时匹配但分钟不匹配（10:15）
结果: False (期望: False) [PASS]
测试3: 当前时间完全不匹配（14:05）
结果: False (期望: False) [PASS]
测试4: 用户禁用邮件通知
结果: False (期望: False) [PASS]

=== 使用真实用户数据测试 ===
用户 1 (user@example.com):
  - 推送类型: 个性化
  - 推送时间: 10:00
  - 是否应发送: False

所有测试通过！个性化推送功能正常工作
```

#### 1.3 查看推送效果

启动邮件调度器后，在日志中查看推送统计：

```log
INFO:scheduler:Email check completed: 3/5 users received emails
INFO:scheduler:  - 个性化推送: 2 个用户 (66.7%)
INFO:scheduler:  - 默认推送: 1 个用户 (33.3%)
```

### 配置参数

在 `backend/database.py` 或配置文件中：

```python
# 默认推送时间
DAILY_UPDATE_HOUR = 8      # 默认上午8点
DAILY_UPDATE_MINUTE = 0    # 默认0分

# 用户个性化设置（User模型）
email_schedule_enabled = True          # 启用个性化
email_schedule_hour = 10               # 推送时间（小时）
email_schedule_minute = 0              # 推送时间（分钟）
```

---

## 2. 邀请奖励系统

### 功能概述

用户生成专属邀请码，邀请好友注册获得成就点数和特殊徽章，实现病毒式增长。

### 数据库表

- **invitation_codes**: 邀请码表
  - code: 8位邀请码
  - generated_by: 创建用户ID
  - is_used: 是否已使用
  - used_by: 使用用户ID

- **user_invitation_stats**: 用户邀请统计表
  - total_invited: 总邀请人数
  - successful_invites: 成功邀请数
  - total_points_earned: 获得的总点数

### 奖励机制

- **邀请人**: 每成功邀请1人 **+20成就点数**
- **被邀请人**: 注册时使用邀请码 **+10成就点数**
- **成就解锁**:
  - invite_first: 首次邀请（1人）
  - invite_5: 邀请5人
  - invite_10: 邀请10人
  - invite_master: 邀请达人（20人）

### 使用方式

#### 2.1 生成邀请码

**API调用**:
```http
POST /api/invitations/generate
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "id": 1,
  "code": "BMODIFGH",
  "generated_by": 1,
  "is_used": false,
  "used_by": null,
  "created_at": "2026-03-24T10:11:32.646409",
  "used_at": null
}
```

**使用测试脚本**:
```bash
python services\invitation_service.py
```

#### 2.2 查看我的邀请码

**API调用**:
```http
GET /api/invitations/my-codes
Authorization: Bearer <token>
```

**响应示例**:
```json
[
  {
    "id": 1,
    "code": "BMODIFGH",
    "generated_by": 1,
    "is_used": false,
    "created_at": "2026-03-24T10:11:32.646409"
  },
  {
    "id": 2,
    "code": "KPLNEGST",
    "generated_by": 1,
    "is_used": true,
    "used_by": 3,
    "created_at": "2026-03-24T10:15:18.123456",
    "used_at": "2026-03-24T11:20:45.654321"
  }
]
```

#### 2.3 查看邀请统计

**API调用**:
```http
GET /api/invitations/my-stats
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "total_invited": 5,
  "successful_invites": 3,
  "total_points_earned": 60,
  "last_invited_at": "2026-03-24T10:15:18.123456",
  "invite_success_rate": 60.0
}
```

#### 2.4 使用邀请码（注册时）

在注册API中添加邀请码参数：

```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "securepassword",
  "invitation_code": "BMODIFGH"
}
```

**后端处理逻辑**:
```python
from services.invitation_service import InvitationService

# 注册后使用邀请码
service = InvitationService(db)
reward = service.use_invitation_code(invitation_code, new_user_id)

if reward:
    # 邀请人获得20点
    # 被邀请人获得10点
    # 自动解锁邀请成就
    service.check_invitation_achievements(inviter_id)
```

#### 2.5 测试邀请系统

```bash
python scripts\test_invitation_system.py
```

**测试内容**:
- 生成多个邀请码
- 验证邀请码有效性
- 使用邀请码发放奖励
- 重复使用防护
- 邀请统计更新
- 成就解锁检查

---

## 3. A/B测试平台

### 功能概述

支持功能A/B测试（UI、文案、算法等），自动分流用户到不同实验组，实时统计和显著性检验，可视化实验结果仪表板。

### 数据库表

- **experiments**: 实验配置表
  - name: 实验名称（唯一）
  - status: 状态（draft, running, paused, completed）
  - traffic_allocation: 流量分配（0-1）

- **experiment_variants**: 实验版本表
  - experiment_id: 实验ID
  - name: 版本名称（control, treatment）
  - traffic_weight: 流量权重
  - config: 版本配置（JSON）

- **user_experiment_assignments**: 用户实验分配表
  - user_id: 用户ID
  - experiment_id: 实验ID
  - variant_id: 版本ID
  - assigned_at: 分配时间

- **experiment_events**: 实验事件表
  - user_id, experiment_id, variant_id
  - event_type: 事件类型（view, click, conversion）
  - event_data: 事件数据

### 分流算法

**一致性哈希算法**：
```python
hash_input = f"{user_id}:{experiment_name}"
hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
hash_position = hash_value % 100  # 0-99的位置
```

确保同一用户始终分配到同一版本，支持动态调整权重。

### 使用方式

#### 3.1 创建实验

**API调用**:
```http
POST /api/experiments/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ui_optimization_test",
  "description": "UI优化测试：按钮颜色对点击率的影响",
  "traffic_allocation": 1.0
}
```

**响应示例**:
```json
{
  "id": 1,
  "name": "ui_optimization_test",
  "description": "UI优化测试：按钮颜色对点击率的影响",
  "status": "draft",
  "traffic_allocation": 1.0,
  "created_by": 1,
  "created_at": "2026-03-24T10:36:45.525557",
  "updated_at": "2026-03-24T10:36:45.525557",
  "started_at": null,
  "completed_at": null
}
```

#### 3.2 创建实验版本

**API调用**:
```http
POST /api/experiments/variants
Authorization: Bearer <token>
Content-Type: application/json

{
  "experiment_id": 1,
  "name": "control",
  "description": "对照组：蓝色按钮",
  "traffic_weight": 0.5,
  "config": {
    "button_color": "blue",
    "button_text": "点击我"
  }
}
```

**响应示例**:
```json
{
  "id": 1,
  "experiment_id": 1,
  "name": "control",
  "description": "对照组：蓝色按钮",
  "traffic_weight": 0.5,
  "config": {
    "button_color": "blue",
    "button_text": "点击我"
  },
  "created_at": "2026-03-24T10:36:45.654321",
  "updated_at": "2026-03-24T10:36:45.654321"
}
```

#### 3.3 启动实验

**API调用**:
```http
PUT /api/experiments/status/ui_optimization_test?status=running
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "message": "实验状态已更新为: running"
}
```

#### 3.4 获取用户实验版本（前端调用）

**API调用**:
```http
GET /api/experiments/my-assignment/ui_optimization_test
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "user_id": 1,
  "experiment_id": 1,
  "variant_id": 2,
  "variant_name": "treatment",
  "variant_config": {
    "button_color": "red",
    "button_text": "立即点击"
  },
  "assigned_at": "2026-03-24T10:45:12.123456"
}
```

**前端集成示例**:
```javascript
async function getExperimentVariant(experimentName) {
    const response = await fetch(`/api/experiments/my-assignment/${experimentName}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

// 使用
const variant = await getExperimentVariant('ui_optimization_test');
if (variant.variant_name === 'treatment') {
    button.style.backgroundColor = variant.variant_config.button_color;
    button.textContent = variant.variant_config.button_text;
} else {
    button.style.backgroundColor = 'blue';
    button.textContent = '点击我';
}
```

#### 3.5 跟踪实验事件

**API调用**:
```http
POST /api/experiments/track-event/ui_optimization_test
Authorization: Bearer <token>
Content-Type: application/json

{
  "event_type": "click",
  "event_data": {
    "button_id": "signup_btn",
    "page_url": "/dashboard"
  }
}
```

**响应示例**:
```json
{
  "message": "事件跟踪成功"
}
```

**前端集成示例**:
```javascript
async function trackExperimentEvent(experimentName, eventType, eventData) {
    await fetch(`/api/experiments/track-event/${experimentName}`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            event_type: eventType,
            event_data: eventData
        })
    });
}

// 用户点击按钮时跟踪
button.addEventListener('click', () => {
    trackExperimentEvent('ui_optimization_test', 'click', {
        button_id: 'signup_btn'
    });
});

// 页面加载时跟踪
window.addEventListener('load', () => {
    trackExperimentEvent('ui_optimization_test', 'view', {
        page_url: window.location.pathname
    });
});

// 转化时跟踪（如注册成功）
function onConversion() {
    trackExperimentEvent('ui_optimization_test', 'conversion', {
        action: 'signup'
    });
}
```

#### 3.6 查看实验结果

**API调用**:
```http
GET /api/experiments/report/ui_optimization_test
Authorization: Bearer <token>
```

**响应示例**:
```json
{
  "experiment": {
    "id": 1,
    "name": "ui_optimization_test",
    "description": "UI优化测试：按钮颜色对点击率的影响",
    "status": "running",
    "traffic_allocation": 1.0,
    "created_at": "2026-03-24T10:36:45.525557",
    "started_at": "2026-03-24T10:36:45.553387",
    "completed_at": null
  },
  "variants": [
    {
      "id": 1,
      "name": "control",
      "description": "对照组：蓝色按钮",
      "traffic_weight": 0.5,
      "config": {
        "button_color": "blue",
        "button_text": "点击我"
      }
    },
    {
      "id": 2,
      "name": "treatment",
      "description": "实验组：红色按钮",
      "traffic_weight": 0.5,
      "config": {
        "button_color": "red",
        "button_text": "立即点击"
      }
    }
  ],
  "results": [
    {
      "variant_id": 1,
      "variant_name": "control",
      "user_count": 50,
      "total_events": 45,
      "conversion_events": 7,
      "conversion_rate": 14.0
    },
    {
      "variant_id": 2,
      "variant_name": "treatment",
      "user_count": 55,
      "total_events": 60,
      "conversion_events": 15,
      "conversion_rate": 27.3
    }
  ],
  "total_users": 105
}
```

#### 3.7 测试A/B测试平台

```bash
python services\experiment_service.py
```

**测试内容**:
- 创建实验和版本
- 启动实验
- 用户分配（一致性哈希）
- 事件跟踪
- 结果计算
- 生成实验报告

---

## 4. API接口文档

### 推送优化API

**触发分析脚本**:
```bash
python scripts/analyze_user_activity.py
```

**查看用户推送配置**（数据库查询）:
```sql
SELECT id, email, email_schedule_enabled, email_schedule_hour, email_schedule_minute
FROM users
WHERE email_schedule_enabled = 1;
```

### 邀请系统API

| 方法 | 路径 | 描述 | 需要认证 |
|------|------|------|----------|
| POST | /api/invitations/generate | 生成邀请码 | ✓ |
| GET | /api/invitations/my-codes | 获取我的邀请码 | ✓ |
| GET | /api/invitations/my-stats | 获取邀请统计 | ✓ |

### A/B测试API

| 方法 | 路径 | 描述 | 需要认证 |
|------|------|------|----------|
| POST | /api/experiments/ | 创建实验 | ✓ |
| POST | /api/experiments/variants | 创建版本 | ✓ |
| GET | /api/experiments/my-assignment/{name} | 获取用户版本 | ✓ |
| POST | /api/experiments/track-event/{name} | 跟踪事件 | ✓ |
| GET | /api/experiments/report/{name} | 获取实验报告 | ✓ |
| PUT | /api/experiments/status/{name} | 更新状态 | ✓ |
| GET | /api/experiments/list | 获取实验列表 | ✓ |

---

## 5. 实验结果仪表板

### 访问方式

```
http://localhost:8000/static/experiment-dashboard.html
```

### 功能特点

1. **实验列表选择**: 下拉菜单选择要查看的实验
2. **实验基本信息**: 名称、描述、状态、时间等
3. **关键指标卡片**: 总用户数、总体转化率、最佳版本、版本数
4. **转化率对比图表**: 使用Chart.js可视化各版本转化率
5. **版本详细表格**: 显示每个版本的详细数据和配置

### 使用步骤

1. **启动后端服务**:
   ```bash
   cd D:\gitRepositories\Daily-News\backend
   python main.py
   ```

2. **打开浏览器访问**:
   ```
   http://localhost:8000/static/experiment-dashboard.html
   ```

3. **选择实验**: 从下拉菜单中选择要查看的实验

4. **查看报告**: 自动加载并显示实验报告

5. **分析数据**: 通过图表和表格分析各版本表现

### 界面说明

- **顶部**: 实验基本信息和状态
- **指标卡片**: 4个关键指标快速了解实验效果
- **图表区域**: 转化率柱状图，直观对比各版本
- **详细表格**: 显示每个版本的用户数、转化率、配置等

---

## 6. 系统启动和访问

### 启动后端服务

```bash
cd D:\gitRepositories\Daily-News\backend
python main.py
```

**启动信息**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 访问API文档

```
http://localhost:8000/docs
```

**Swagger文档**: 自动生成的交互式API文档，可以测试所有API接口

### 访问实验仪表板

```
http://localhost:8000/static/experiment-dashboard.html
```

**可视化界面**: 查看实验结果和统计数据

### 完整功能验证

运行验证脚本检查所有功能：

```bash
python scripts\verify_p2_features.py
```

**验证内容**:
- 数据库模型（9个新表）
- 服务类（3个核心服务）
- 静态文件（实验仪表板）

---

## 📊 功能总结

### P2阶段新增功能

| 功能模块 | 数据库表 | API接口 | 服务类 | 测试脚本 |
|----------|----------|---------|--------|----------|
| 推送时机个性化 | user_activity_logs | - | PushTimingAnalyzer | ✓ |
| 邀请奖励系统 | invitation_codes, user_invitation_stats | 3个 | InvitationService | ✓ |
| A/B测试平台 | experiments, experiment_variants, user_experiment_assignments, experiment_events, experiment_results | 7个 | ExperimentService | ✓ |

### 核心特性

✅ **推送时机个性化**
- 自动分析用户活跃时间
- 个性化推送时间计算
- 邮件打开率提升

✅ **邀请奖励系统**
- 邀请码生成和管理
- 双向奖励机制（+20/+10点数）
- 成就系统集成
- 病毒式增长

✅ **A/B测试平台**
- 完整的实验生命周期管理
- 一致性哈希分流算法
- 实时结果统计
- 可视化仪表板

### 技术亮点

1. **一致性哈希算法**: 确保用户始终分配到同一实验版本
2. **实时统计分析**: 基于数据库实时计算转化率
3. **灵活的JSON配置**: 支持任意实验配置，无需修改代码
4. **完整的错误处理**: 所有API都有完善的错误处理机制
5. **可视化展示**: Chart.js图表直观展示实验结果

---

## 🚀 快速开始

### 第一步：启动服务

```bash
cd D:\gitRepositories\Daily-News\backend
python main.py
```

### 第二步：运行推送优化分析

```bash
python scripts\analyze_user_activity.py
```

### 第三步：测试邀请系统

```bash
python scripts\test_invitation_system.py
```

### 第四步：测试A/B测试平台

```bash
python services\experiment_service.py
```

### 第五步：访问实验仪表板

打开浏览器：
```
http://localhost:8000/static/experiment-dashboard.html
```

---

## 📞 常见问题

### Q1: 如何查看用户的个性化推送时间？

**A**: 查询数据库
```sql
SELECT id, email, email_schedule_hour, email_schedule_minute
FROM users
WHERE email_schedule_enabled = 1;
```

### Q2: 邀请码的有效期是多久？

**A**: 邀请码没有过期时间，但只能使用一次。

### Q3: 如何停止一个A/B测试实验？

**A**: 更新实验状态为completed
```http
PUT /api/experiments/status/{experiment_name}?status=completed
```

### Q4: 实验流量分配可以调整吗？

**A**: 可以，在创建实验时设置traffic_allocation（0-1之间），例如0.5表示50%的用户参与实验。

### Q5: 如何查看实验的统计显著性？

**A**: 在实验仪表板中查看各版本转化率差异，目前支持手动计算显著性，后续版本会添加自动计算。

---

## 📚 相关文档

- [项目README](../README.md)
- [API文档](http://localhost:8000/docs)
- [P1阶段总结](../P1_IMPLEMENTATION_SUMMARY.md)
- [数据库设计](../DATABASE_SCHEMA.md)

---

**Daily-News P2阶段 - 用户增长与数据驱动优化**  
**状态**: ✅ 已完成  
**版本**: 2.0.0  
**最后更新**: 2026-03-24
