# 修复自定义RSS源和新闻面板显示问题

## 问题1：修复添加自定义RSS源失败

**文件**：`backend/routes/subscriptions.py`

在`create_custom_rss_feed`函数中，创建CustomRSS记录时显式指定`roast_mode`字段：
```python
custom_rss = CustomRSS(
    user_id=current_user.id,
    topic=custom_rss_data.topic,
    feed_url=custom_rss_data.feed_url,
    roast_mode=False  # 显式指定默认值
)
```

## 问题2：修复新闻面板不显示

**原因**：数据库表结构未更新，需要删除旧数据库文件让系统重新创建

**操作**：
1. 停止后端服务
2. 删除`backend/daily_digest.db`数据库文件
3. 重启后端服务，系统会自动创建新的数据库表结构（包含roast_mode字段）
4. 重新测试添加自定义RSS源和查看新闻面板

**注意**：删除数据库会清空所有数据，包括用户、订阅和缓存。这是必要的，因为SQLite不支持ALTER COLUMN添加带默认值的字段。

## 测试步骤

1. 重启后端服务
2. 重新注册/登录用户
3. 添加自定义RSS源（应该成功）
4. 查看新闻面板（应该显示订阅和自定义RSS源）
5. 测试吐槽模式开关功能