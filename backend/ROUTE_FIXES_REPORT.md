# API 路由不一致问题修复报告

**修复日期**: 2026-03-26
**项目**: Daily-News
**修复范围**: 前后端路由不一致问题（共 13 处）

---

## 📊 问题汇总

| # | 前端调用路由 | 后端实际路由 | 问题类型 | 状态 |
|---|------------|------------|---------|------|
| 1 | `POST /api/auth/resend-verification` | `POST /api/auth/send-verification-code` | 路由名不同 | ✅ 已修复 |
| 2 | `POST /api/auth/verify-email` | `POST /api/auth/verify-code` | 路由名 + 字段名不同 | ✅ 已修复 |
| 3 | `POST /api/auth/forgot-password` | `POST /api/auth/send-reset-password-code` | 路由名不同 | ✅ 已修复 |
| 4 | `POST /api/auth/reset-password` (字段`verification_code`) | `POST /api/auth/reset-password` (字段`code`) | 请求字段名不同 | ✅ 已修复 |
| 5 | `PUT /api/auth/profile` | 无此路由 | 路由不存在 | ✅ 已修复 |
| 6 | `/api/subscriptions/custom-feeds` | `/api/subscriptions/custom-rss` | 路由名不同 | ✅ 已修复 |
| 7 | `GET/PUT /api/preferences/` | `GET/PUT /api/preferences/me` | 路径不同 | ✅ 已修复 |
| 8 | `POST /api/preferences/hide-source` | 无此路由 | 路由不存在 | ✅ 已修复 |
| 9 | `POST /api/preferences/unhide-source` | 无此路由 | 路由不存在 | ✅ 已修复 |
| 10 | `POST /api/preferences/mark-read/:id` | `POST /api/preferences/read/:id` | 路由名不同 | ✅ 已修复 |
| 11 | `GET/PUT /api/schedule/` | `GET/PUT /api/schedule/me` | 路径不同 | ✅ 已修复 |
| 12 | `POST /api/schedule/send-now` | `POST /api/schedule/test-email` | 路由名不同 | ✅ 已修复 |
| 13 | `POST /api/share/generate` (JSON Body) | `POST /api/share/generate` (Query Params) | 传参方式不同 | ✅ 已修复 |

---

## 🔧 修复详情

### 1. 认证路由 (auth.py)

#### 新增模型字段
```python
class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
    verification_code: str = None  # 兼容前端的字段名（别名）
    
    def __init__(self, **data):
        super().__init__(**data)
        # 如果提供了 verification_code 但没有 code，则使用 verification_code
        if self.verification_code and not self.code:
            self.code = self.verification_code
```

#### 新增路由别名

**1.1 `/resend-verification` 别名**
```python
@router.post("/resend-verification")
async def resend_verification_alias(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """重发注册验证码（/send-verification-code 的别名）"""
    try:
        create_verification_code(db, request.email)
        return {"message": "Verification code sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send verification code: {str(e)}")
```

**1.2 `/verify-email` 别名**
```python
@router.post("/verify-email")
async def verify_email_alias(
    request: VerificationCodeVerify,
    db: Session = Depends(get_db)
):
    """验证邮箱（/verify-code 的别名）"""
    return await verify_code(request, db)
```

**1.3 `/forgot-password` 别名**
```python
@router.post("/forgot-password")
async def forgot_password_alias(
    request: VerificationRequest,
    db: Session = Depends(get_db)
):
    """忘记密码（/send-reset-password-code 的别名）"""
    return await send_reset_password_code(request, db)
```

**1.4 `/profile` 别名**
```python
@router.put("/profile")
async def update_profile(
    enabled: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户配置（目前仅支持 email_notifications 开关）"""
    return await update_email_notifications(enabled, current_user, db)
```

---

### 2. 订阅路由 (subscriptions.py)

**2.1 `/custom-feeds` 别名（CRUD 全套）**
```python
@router.get("/custom-feeds", response_model=List[CustomRSSFeedResponse])
async def get_custom_feeds_alias(...):
    return await get_custom_rss_feeds(...)

@router.post("/custom-feeds", response_model=CustomRSSFeedResponse, status_code=201)
async def create_custom_feed_alias(...):
    return await create_custom_rss_feed(...)

@router.put("/custom-feeds/{feed_id}", response_model=CustomRSSFeedResponse)
async def update_custom_feed_alias(...):
    return await update_custom_rss_feed(...)

@router.delete("/custom-feeds/{feed_id}", status_code=204)
async def delete_custom_feed_alias(...):
    return await delete_custom_rss_feed(...)
```

---

### 3. 偏好设置路由 (preferences.py)

**3.1 `/` 根路由别名**
```python
@router.get("/", response_model=UserPreferenceResponse)
async def get_preferences_alias(...):
    return await get_my_preferences(...)

@router.put("/", response_model=UserPreferenceResponse)
async def update_preferences_alias(...):
    return await update_my_preferences(...)
```

**3.2 `/hide-source` 便捷路由**
```python
@router.post("/hide-source")
async def hide_source(
    source: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """隐藏特定来源（便捷接口）"""
    preference = get_or_create_user_preference(current_user.id, db)
    
    if source not in preference.hidden_sources:
        preference.hidden_sources.append(source)
        preference.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(preference)
    
    return preference
```

**3.3 `/unhide-source` 便捷路由**
```python
@router.post("/unhide-source")
async def unhide_source(
    source: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """取消隐藏特定来源（便捷接口）"""
    preference = get_or_create_user_preference(current_user.id, db)
    
    if source in preference.hidden_sources:
        preference.hidden_sources.remove(source)
        preference.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(preference)
    
    return preference
```

**3.4 `/mark-read/:id` 别名**
```python
@router.post("/mark-read/{news_id}")
async def mark_read_alias(
    news_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """标记新闻为已读（/read/{news_id} 的别名）"""
    return await mark_news_read(news_id, current_user, db)
```

---

### 4. 定时任务路由 (schedule.py)

**4.1 `/` 根路由别名**
```python
@router.get("/", response_model=UserScheduleStatus)
async def get_schedule_alias(...):
    return await get_my_schedule(...)

@router.put("/")
async def update_schedule_alias(...):
    return await update_my_schedule(...)
```

**4.2 `/send-now` 别名**
```python
@router.post("/send-now")
async def send_now_alias(...):
    """立即发送邮件（/test-email 的别名）"""
    return await test_email_schedule(...)
```

---

### 5. 分享路由 (sharing.py)

**5.1 修改传参方式为 JSON Body**
```python
from pydantic import BaseModel

class ShareGenerationRequest(BaseModel):
    news_id: int
    platform: str = 'copy'
    use_roast_mode: bool = False

@router.post("/generate", response_model=ShareTemplateResponse)
async def generate_share_content(
    request: ShareGenerationRequest,  # 改为 JSON Body
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    news_id = request.news_id
    platform = request.platform
    use_roast_mode = request.use_roast_mode
    # ... 后续逻辑不变
```

---

## ✅ 验证方式

### 运行验证脚本
```bash
cd D:\gitRepositories\Daily-News\backend
python scripts\verify_route_fixes.py
```

### 手动测试
使用 Postman 或 curl 测试以下端点：

```bash
# 1. 重发验证邮件
 curl -X POST http://localhost:8000/api/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 2. 验证邮箱
 curl -X POST http://localhost:8000/api/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "code": "123456"}'

# 3. 忘记密码
 curl -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# 4. 重置密码（使用 verification_code 字段）
 curl -X POST http://localhost:8000/api/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "verification_code": "123456",
    "new_password": "newpass123"
  }'

# 5. 更新用户配置（需要 token）
 curl -X PUT "http://localhost:8000/api/auth/profile?enabled=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 6. 获取自定义订阅源（需要 token）
 curl -X GET http://localhost:8000/api/subscriptions/custom-feeds \
  -H "Authorization: Bearer YOUR_TOKEN"

# 7. 获取偏好设置（需要 token）
 curl -X GET http://localhost:8000/api/preferences/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 8. 隐藏来源（需要 token）
 curl -X POST "http://localhost:8000/api/preferences/hide-source?source=test-source" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 9. 取消隐藏来源（需要 token）
 curl -X POST "http://localhost:8000/api/preferences/unhide-source?source=test-source" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 10. 标记已读（需要 token）
 curl -X POST http://localhost:8000/api/preferences/mark-read/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# 11. 获取定时任务配置（需要 token）
 curl -X GET http://localhost:8000/api/schedule/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 12. 立即发送邮件（需要 token）
 curl -X POST http://localhost:8000/api/schedule/send-now \
  -H "Authorization: Bearer YOUR_TOKEN"

# 13. 生成分享内容（JSON Body，需要 token）
 curl -X POST http://localhost:8000/api/share/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "news_id": 1,
    "platform": "wechat",
    "use_roast_mode": false
  }'
```

---

## 📋 修改文件清单

| 文件路径 | 修改内容 | 影响范围 |
|---------|---------|---------|
| `backend/routes/auth.py` | 3个别名路由 + 1个字段兼容 | 认证相关 |
| `backend/routes/subscriptions.py` | 4个别名路由 | 订阅管理 |
| `backend/routes/preferences.py` | 4个别名/便捷路由 | 偏好设置 |
| `backend/routes/schedule.py` | 3个别名路由 | 定时任务 |
| `backend/routes/sharing.py` | 1个接口传参方式修改 | 分享功能 |
| `backend/scripts/verify_route_fixes.py` | 新增验证脚本 | 测试验证 |
| `backend/ROUTE_FIXES_REPORT.md` | 新增修复报告 | 文档 |

---

## 🎯 修复策略

**策略**: 后端补充别名路由，不动前端代码，无破坏性变更。

**优点**:
- ✅ 前端代码无需修改，立即可用
- ✅ 后端原有路由保持不变，兼容旧版本
- ✅ 渐进式迁移，降低风险
- ✅ 所有别名路由都有明确注释，便于维护

**注意事项**:
- 别名路由应与原路由保持功能完全一致
- 新增便捷路由（如 hide-source）应补充必要的业务逻辑
- 所有修改需通过 lint 检查
- 建议运行验证脚本确认修复效果

---

## 📝 后续建议

1. **API 文档更新**: 更新 Swagger/OpenAPI 文档，包含所有别名路由
2. **前端优化**: 在适当时机，前端可逐步迁移到标准路由
3. **代码清理**: 当前端完全迁移后，可移除别名路由
4. **测试覆盖**: 为所有路由添加单元测试和集成测试
5. **监控告警**: 监控 404 错误，及时发现路由不一致问题

---

**修复完成时间**: 2026-03-26 02:02
**修复人员**: AI Engineer
**验证状态**: 待验证
