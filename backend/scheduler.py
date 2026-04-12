from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal, settings
from models import User, Subscription, NewsCache, SystemLog, TopicRefreshStatus, CustomRSSFeed
from news_fetcher import NewsFetcher, deduplicate_articles
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)


def get_current_date_in_timezone() -> str:
    """获取配置时区的当前日期（YYYY-MM-DD格式）"""
    tz = pytz.timezone(settings.TIMEZONE)
    return datetime.now(tz).date().strftime("%Y-%m-%d")


def update_news_for_topic(topic: str, date_str: str, db: Session, lock_id: str = None) -> dict:
    """Update news for a specific topic (optimized: one topic refresh instead of per-user)
    
    解耦设计: 只抓取新闻并存库，AI 摘要通过异步任务队列处理。
    
    Args:
        topic: Topic name
        date_str: Date string (YYYY-MM-DD)
        db: Database session
        lock_id: Lock ID for concurrent refresh protection
    
    Returns:
        dict: {"success": bool, "articles_count": int, "tasks_enqueued": int, "error": str}
    """
    try:
        # Get all active custom RSS feeds for this topic (from all users)
        custom_feeds = db.query(CustomRSSFeed).filter(
            CustomRSSFeed.topic == topic,
            CustomRSSFeed.is_active == True
        ).all()
        
        # Convert to list of dicts for NewsFetcher
        custom_rss_feeds = [
            {
                "topic": feed.topic,
                "feed_url": feed.feed_url,
                "is_active": feed.is_active
            }
            for feed in custom_feeds
        ]
        
        fetcher = NewsFetcher(custom_rss_feeds=custom_rss_feeds)
        
        logger.info(f"Fetching news for topic: {topic} (date: {date_str})")
        
        # Fetch news articles - limit to 16 per topic
        articles = fetcher.fetch_news(topic, max_articles=16)
        
        if not articles:
            logger.warning(f"No articles found for topic: {topic}")
            return {"success": True, "articles_count": 0, "tasks_enqueued": 0, "error": None}
        
        # Deduplicate
        articles = deduplicate_articles(articles)
        
        # Limit to 16 articles
        articles = articles[:16]
        
        created_count = 0
        new_news_ids = []
        
        # Process articles: save to DB first, enqueue AI tasks separately
        for article in articles:
            try:
                # For RSS articles, check by entry_id first
                entry_id = article.get("entry_id")
                existing = None
                
                if entry_id:
                    existing = db.query(NewsCache).filter(
                        NewsCache.entry_id == entry_id
                    ).first()
                else:
                    existing = db.query(NewsCache).filter(
                        NewsCache.url == article["url"],
                        NewsCache.date == date_str,
                        NewsCache.topic == topic
                    ).first()
                
                if existing:
                    logger.debug(f"Article already exists, skipping: {article.get('title', 'Unknown')[:50]}...")
                    continue
                
                # Generate fallback summary (截断) for immediate display
                content = article.get("content", "") or ""
                if content and len(content) > 100:
                    fallback_summary = content[:100] + "..."
                elif content:
                    fallback_summary = content
                else:
                    fallback_summary = article.get("title", "暂无内容")
                
                # Save article with fallback summary (no LLM call here)
                news_cache = NewsCache(
                    topic=topic,
                    title=article["title"],
                    summary=fallback_summary,
                    summary_roast=None,
                    url=article["url"],
                    source=article.get("source"),
                    image_url=article.get("image_url"),
                    published_at=article.get("published_at"),
                    date=date_str,
                    relevance_score=0.5,  # 默认分数，后续由 AI 评估
                    raw_content=content[:1000],  # 保存原始内容供 AI 使用
                    entry_id=entry_id,
                    summary_status="pending"  # 标记为等待 AI 总结
                )
                db.add(news_cache)
                db.commit()
                db.refresh(news_cache)
                
                new_news_ids.append(news_cache.id)
                created_count += 1
                logger.debug(f"Saved article '{article.get('title', 'Unknown')[:50]}...' for topic {topic}")
                    
            except Exception as e:
                logger.error(f"Error processing article '{article.get('title', 'Unknown')}' for topic {topic}: {str(e)}")
                db.rollback()
                continue
        
        # Enqueue AI summary tasks for new articles (decoupled from fetch)
        tasks_enqueued = 0
        if new_news_ids:
            try:
                from services.summary_queue import SummaryTaskQueue
                queue = SummaryTaskQueue(db)
                tasks_enqueued = queue.enqueue_batch(new_news_ids)
                logger.info(f"Enqueued {tasks_enqueued} AI summary tasks for {len(new_news_ids)} new articles (topic: {topic})")
            except Exception as e:
                logger.error(f"Failed to enqueue summary tasks: {e}")
        
        logger.info(f"Updated {created_count} articles for topic: {topic}, enqueued {tasks_enqueued} AI tasks")
        
        return {"success": True, "articles_count": created_count, "tasks_enqueued": tasks_enqueued, "error": None}
        
    except Exception as e:
        logger.error(f"Error updating news for topic {topic}: {str(e)}")
        db.rollback()
        return {"success": False, "articles_count": 0, "tasks_enqueued": 0, "error": str(e)}


def get_or_create_refresh_status(topic: str, date_str: str, db: Session) -> TopicRefreshStatus:
    """Get or create refresh status for a topic+date"""
    status = db.query(TopicRefreshStatus).filter(
        TopicRefreshStatus.topic == topic,
        TopicRefreshStatus.date == date_str
    ).first()
    
    if not status:
        status = TopicRefreshStatus(
            topic=topic,
            date=date_str,
            is_refreshing=False,
            last_refreshed_at=None
        )
        db.add(status)
        db.commit()
        db.refresh(status)
    
    return status


def can_refresh_topic(topic: str, date_str: str, db: Session, min_interval_minutes: int = 5) -> tuple[bool, str, TopicRefreshStatus]:
    """Check if a topic can be refreshed (not recently refreshed and not currently refreshing)
    
    Returns:
        (can_refresh: bool, reason: str, status: TopicRefreshStatus)
    """
    status = get_or_create_refresh_status(topic, date_str, db)
    
    # Check if currently refreshing
    if status.is_refreshing:
        # Check if lock is stale (older than 10 minutes)
        if status.refresh_lock_id:
            # Lock exists, consider it stale if last_refreshed_at is old
            if status.last_refreshed_at:
                lock_age = datetime.utcnow() - status.last_refreshed_at
                if lock_age.total_seconds() > 600:  # 10 minutes
                    logger.warning(f"Stale lock detected for {topic} on {date_str}, clearing it")
                    status.is_refreshing = False
                    status.refresh_lock_id = None
                    db.commit()
                    db.refresh(status)
                else:
                    return (False, "currently_refreshing", status)
            else:
                # Lock exists but no refresh time, clear it
                status.is_refreshing = False
                status.refresh_lock_id = None
                db.commit()
                db.refresh(status)
    
    # Check if recently refreshed
    if status.last_refreshed_at:
        time_since_refresh = datetime.utcnow() - status.last_refreshed_at
        if time_since_refresh.total_seconds() < min_interval_minutes * 60:
            remaining_seconds = int(min_interval_minutes * 60 - time_since_refresh.total_seconds())
            return (False, f"recently_refreshed_{remaining_seconds}s", status)
    
    return (True, "ok", status)


def mark_refreshing(topic: str, date_str: str, lock_id: str, db: Session):
    """Mark topic as refreshing"""
    status = get_or_create_refresh_status(topic, date_str, db)
    status.is_refreshing = True
    status.refresh_lock_id = lock_id
    db.commit()


def mark_refreshed(topic: str, date_str: str, db: Session):
    """Mark topic as refreshed"""
    status = get_or_create_refresh_status(topic, date_str, db)
    status.is_refreshing = False
    status.refresh_lock_id = None
    status.last_refreshed_at = datetime.utcnow()
    db.commit()


def refresh_topic_with_lock(topic: str, date_str: str, db: Session) -> dict:
    """Refresh a topic with lock protection
    
    Returns:
        dict: {"success": bool, "articles_count": int, "skipped": bool, "reason": str}
    """
    lock_id = str(uuid.uuid4())
    
    # Check if can refresh
    can_refresh, reason, status = can_refresh_topic(topic, date_str, db)
    
    if not can_refresh:
        if reason.startswith("recently_refreshed"):
            return {
                "success": True,
                "articles_count": 0,
                "skipped": True,
                "reason": reason
            }
        elif reason == "currently_refreshing":
            return {
                "success": False,
                "articles_count": 0,
                "skipped": True,
                "reason": "currently_refreshing"
            }
    
    # Mark as refreshing
    try:
        mark_refreshing(topic, date_str, lock_id, db)
        
        # Refresh news
        result = update_news_for_topic(topic, date_str, db, lock_id)
        
        # Mark as refreshed
        mark_refreshed(topic, date_str, db)
        
        result["skipped"] = False
        result["reason"] = "refreshed"
        return result
        
    except Exception as e:
        logger.error(f"Error refreshing topic {topic}: {str(e)}")
        # Clear lock on error
        try:
            status = get_or_create_refresh_status(topic, date_str, db)
            status.is_refreshing = False
            status.refresh_lock_id = None
            db.commit()
        except:
            pass
        return {
            "success": False,
            "articles_count": 0,
            "skipped": False,
            "reason": "error",
            "error": str(e)
        }


# 保留向后兼容的函数（用于邮件发送等场景）
def update_news_for_user(user_id: int, db: Session):
    """Update news for a specific user's subscriptions (legacy function, now uses topic-level refresh)
    
    This function is kept for backward compatibility but now uses the optimized topic-level refresh.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return
        
        subscriptions = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == True
        ).all()
        
        # Get user's active custom RSS feeds
        custom_feeds = db.query(CustomRSSFeed).filter(
            CustomRSSFeed.user_id == user_id,
            CustomRSSFeed.is_active == True
        ).all()
        
        # Collect unique topics from both subscriptions and custom RSS feeds
        topics = set([sub.topic for sub in subscriptions])
        topics.update([feed.topic for feed in custom_feeds])
        topics = list(topics)
        
        if not topics:
            logger.info(f"No active subscriptions or custom RSS feeds for user {user.email}")
            return
        
        today = get_current_date_in_timezone()
        
        # Refresh each topic (will use lock protection)
        for topic in topics:
            refresh_topic_with_lock(topic, today, db)
        
    except Exception as e:
        logger.error(f"Error updating news for user {user_id}: {str(e)}")


def daily_news_update():
    """Daily scheduled task to update news for all users (optimized: topic-level refresh)"""
    logger.info("Starting daily news update (optimized)...")
    
    db = SessionLocal()
    try:
        # Get all active users with subscriptions
        users = db.query(User).filter(User.is_active == True).all()
        
        if not users:
            logger.info("No active users found")
            return
        
        # Collect all unique topics from all users' subscriptions
        all_topics = set()
        user_count = 0
        
        for user in users:
            subscriptions = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.is_active == True
            ).all()
            
            # Get user's active custom RSS feeds
            custom_feeds = db.query(CustomRSSFeed).filter(
                CustomRSSFeed.user_id == user.id,
                CustomRSSFeed.is_active == True
            ).all()
            
            # Collect topics from both subscriptions and custom RSS feeds
            user_topics = set([sub.topic for sub in subscriptions])
            user_topics.update([feed.topic for feed in custom_feeds])
            
            if user_topics:
                user_count += 1
                all_topics.update(user_topics)
        
        logger.info(f"Found {len(all_topics)} unique topics from {user_count} users with subscriptions")
        
        today = get_current_date_in_timezone()
        
        # Refresh each topic (will handle locks and duplicates)
        refreshed_topics = 0
        skipped_topics = 0
        
        for topic in all_topics:
            result = refresh_topic_with_lock(topic, today, db)
            if result["skipped"]:
                skipped_topics += 1
            else:
                refreshed_topics += 1
        
        # Log completion
        log = SystemLog(
            log_type="fetch",
            message="Daily news update completed (optimized)",
            log_metadata={
                "users_count": user_count,
                "topics_count": len(all_topics),
                "refreshed_topics": refreshed_topics,
                "skipped_topics": skipped_topics,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        db.add(log)
        db.commit()
        
        logger.info(f"Daily news update completed: {refreshed_topics} topics refreshed, {skipped_topics} skipped")
        
    except Exception as e:
        logger.error(f"Daily news update failed: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def send_scheduled_emails():
    """定时邮件任务 - 检查所有用户并发送邮件（根据每个用户的配置）
    
    注意：此函数只从数据库读取已缓存的新闻，不会触发新闻刷新。
    新闻刷新由 daily_news_update 任务独立处理。
    """
    logger.info("Starting scheduled email check task...")
    
    db = SessionLocal()
    try:
        # 直接从数据库读取新闻，不触发刷新
        # 检查并发送邮件（根据每个用户的定时配置）
        send_daily_emails(db)
        
        logger.info("Scheduled email task completed successfully")
        
    except Exception as e:
        logger.error(f"Scheduled email task failed: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def get_user_push_time(user: User) -> tuple[int, int]:
    """获取用户的推送时间（小时和分钟）
    
    如果用户启用了个性化推送且设置了推送时间，则使用个性化时间。
    否则使用系统默认时间（DAILY_UPDATE_HOUR）。
    
    Args:
        user: 用户对象
        
    Returns:
        tuple: (target_hour, target_minute)
    """
    # 如果用户启用了个性化推送且有设置时间，使用用户设置
    if user.email_schedule_enabled and user.email_schedule_hour is not None:
        target_hour = user.email_schedule_hour
        target_minute = user.email_schedule_minute or 0
        logger.debug(f"用户 {user.id} 使用个性化推送时间: {target_hour:02d}:{target_minute:02d}")
    else:
        # 使用系统默认时间
        target_hour = settings.DAILY_UPDATE_HOUR
        target_minute = settings.DAILY_UPDATE_MINUTE or 0
        logger.debug(f"用户 {user.id} 使用默认推送时间: {target_hour:02d}:{target_minute:02d}")
    
    return target_hour, target_minute


def should_send_email_to_user(user: User, current_time: datetime) -> bool:
    """检查是否应该向用户发送邮件（支持个性化推送时间）
    
    使用配置的时区来比较时间，确保时区一致性。
    支持两种模式：
    1. 个性化推送：读取用户的 email_schedule_hour 字段
    2. 默认推送：使用系统配置的 DAILY_UPDATE_HOUR
    
    发送条件：
    - 用户启用了邮件通知
    - 在目标推送时间的小时范围内（例如9:00-9:59）
    - 今天还没发送过邮件
    """
    if not user.email_notifications:
        logger.debug(f"跳过用户 {user.id}: 邮件通知已禁用")
        return False
    
    # 只支持 daily 模式
    schedule_type = user.email_schedule_type or "daily"
    if schedule_type != "daily":
        logger.debug(f"跳过用户 {user.id}: 不支持的推送类型 {schedule_type}")
        return False
    
    # 获取用户的推送时间（个性化或默认）
    target_hour, target_minute = get_user_push_time(user)
    
    # 检查今天是否已发送（这个检查优先，避免无效的时间检查）
    last_sent = user.last_email_sent_at
    current_date = current_time.date()
    
    if last_sent:
        # 将 last_sent 转换为配置时区进行比较
        tz = pytz.timezone(settings.TIMEZONE)
        if last_sent.tzinfo is None:
            # 如果 last_sent 是 naive datetime，假设它是 UTC
            last_sent_tz = pytz.UTC.localize(last_sent)
        else:
            last_sent_tz = last_sent
        
        # 转换为配置时区
        last_sent_in_tz = last_sent_tz.astimezone(tz)
        
        if last_sent_in_tz.date() >= current_date:
            logger.debug(f"跳过用户 {user.id}: 今天已发送过邮件 (上次发送: {last_sent_in_tz})")
            return False
    
    # 时间检查：放宽到目标时间前后30分钟的窗口
    # 这样可以确保在每10分钟检查一次的情况下，不会漏掉发送
    # 例如用户设置9:00，则在8:30-9:30之间都可以发送
    current_minutes = current_time.hour * 60 + current_time.minute
    target_minutes = target_hour * 60 + target_minute
    time_diff = abs(current_minutes - target_minutes)
    
    # 如果跨越了午夜，需要特殊处理
    if time_diff > 12 * 60:  # 如果差值超过12小时，说明跨越了午夜
        time_diff = 24 * 60 - time_diff
    
    # 允许30分钟的窗口期
    if time_diff > 30:
        logger.debug(f"跳过用户 {user.id}: 当前时间 {current_time.hour:02d}:{current_time.minute:02d} 不在目标时间 {target_hour:02d}:{target_minute:02d} 的30分钟窗口内（差值{time_diff}分钟）")
        return False
    
    # 首次发送或今天未发送，满足时间条件则发送
    if not last_sent:
        logger.info(f"准备发送邮件给用户 {user.id} {user.email}: 今天尚未发送")
    else:
        logger.info(f"准备发送邮件给用户 {user.id} {user.email}: 今天尚未发送（在目标时间窗口内）")
    
    return True


def send_email_to_user(user_id: int, db: Session):
    """向指定用户发送邮件"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return
        
        if not user.email_notifications:
            logger.info(f"User {user.email} has email notifications disabled")
            return
        
        # Get user's subscriptions
        subscriptions = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True
        ).all()
        
        if not subscriptions:
            logger.info(f"User {user.email} has no active subscriptions")
            return
        
        today = get_current_date_in_timezone()
        
        # Build email content
        email_body = build_email_digest(user, subscriptions, today, db)
        
        # Send email
        send_email(user.email, f"📰 Daily Digest - {today}", email_body)
        
        # Update last sent time (使用配置时区的当前时间)
        tz = pytz.timezone(settings.TIMEZONE)
        user.last_email_sent_at = datetime.now(tz)
        db.commit()
        
        logger.info(f"Sent email to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send email to user {user_id}: {str(e)}")
        db.rollback()


def send_daily_emails(db: Session):
    """检查所有用户并发送邮件（支持个性化推送时间）
    
    使用配置的时区（settings.TIMEZONE）来获取当前时间，而不是服务器本地时间。
    统计使用个性化推送的用户数量。
    """
    try:
        # Get all active users with email notifications enabled
        users = db.query(User).filter(
            User.is_active == True,
            User.email_notifications == True
        ).all()
        
        if not users:
            logger.info("No users with email notifications enabled")
            return
        
        # 使用配置的时区获取当前时间，而不是服务器本地时间
        tz = pytz.timezone(settings.TIMEZONE)
        current_time = datetime.now(tz)
        sent_count = 0
        personalized_count = 0
        default_count = 0
        
        for user in users:
            try:
                # Check if should send email based on user's schedule
                if should_send_email_to_user(user, current_time):
                    # 统计个性化推送 vs 默认推送
                    if user.email_schedule_enabled and user.email_schedule_hour is not None:
                        personalized_count += 1
                    else:
                        default_count += 1
                    
                    send_email_to_user(user.id, db)
                    sent_count += 1
                # 否则跳过（日志已在 should_send_email_to_user 中记录）
                    
            except Exception as e:
                logger.error(f"Failed to process email for user {user.email}: {str(e)}")
        
        # Log completion with detailed stats
        today = get_current_date_in_timezone()
        personalized_pct = (personalized_count / sent_count * 100) if sent_count > 0 else 0
        
        log = SystemLog(
            log_type="email",
            message=f"Processed scheduled emails, sent to {sent_count} users (个性化: {personalized_count}, 默认: {default_count})",
            log_metadata={
                "date": today,
                "total_users": len(users),
                "sent_count": sent_count,
                "personalized_count": personalized_count,
                "default_count": default_count,
                "personalized_percentage": round(personalized_pct, 1),
                "current_time": current_time.isoformat()
            }
        )
        db.add(log)
        db.commit()
        
        logger.info(f"Email check completed: {sent_count}/{len(users)} users received emails")
        if sent_count > 0:
            logger.info(f"  - 个性化推送: {personalized_count} 个用户 ({personalized_pct:.1f}%)")
            logger.info(f"  - 默认推送: {default_count} 个用户 ({100-personalized_pct:.1f}%)")
        
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        db.rollback()


def build_email_digest(user: User, subscriptions: list, date_str: str, db: Session) -> str:
    """Build HTML email digest"""
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            h1 {{ color: #2563eb; }}
            h2 {{ color: #1e40af; border-bottom: 2px solid #3b82f6; padding-bottom: 5px; }}
            .news-item {{ margin: 15px 0; padding: 10px; background: #f3f4f6; border-radius: 5px; }}
            .news-title {{ font-weight: bold; color: #1f2937; }}
            .news-summary {{ margin: 5px 0; }}
            a {{ color: #2563eb; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>📰 Daily Digest - {date_str}</h1>
        <p>Hi {user.email},</p>
        <p>Here's your personalized news digest for today:</p>
    """
    
    for sub in subscriptions:
        # Get news for this topic
        news_items = db.query(NewsCache).filter(
            NewsCache.topic == sub.topic,
            NewsCache.date == date_str
        ).limit(5).all()
        
        if not news_items:
            continue
        
        html += f"\n<h2>{sub.topic}</h2>\n"
        
        for item in news_items:
            summary = item.summary_roast if sub.roast_mode else item.summary
            html += f"""
            <div class="news-item">
                <div class="news-title">{item.title}</div>
                <div class="news-summary">{summary}</div>
                <a href="{item.url}" target="_blank">Read more →</a>
            </div>
            """
    
    html += """
        <hr>
        <p style="color: #6b7280; font-size: 12px;">
            You're receiving this because you enabled email notifications in Daily Digest Agent.
            <br>To unsubscribe, please update your settings in the dashboard.
        </p>
    </body>
    </html>
    """
    
    return html


def send_email(to_email: str, subject: str, html_body: str, from_name: str = None):
    """Send email via SMTP or Resend, using default account if configured
    
    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        html_body: HTML邮件内容
        from_name: 发件人名称（可选）
    
    Raises:
        ValueError: If no email service is configured
        Exception: If email sending fails
    """
    last_error = None
    
    # Try Resend first (if configured)
    if settings.RESEND_API_KEY and settings.RESEND_API_KEY != "":
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            
            # 如果提供了from_name，使用 "名称 <邮箱>" 的格式
            if from_name:
                from_email = f"{from_name} <{settings.FROM_EMAIL}>"
            else:
                from_email = settings.FROM_EMAIL
            
            params = {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            
            resend.Emails.send(params)
            logger.info(f"Email sent via Resend to {to_email}")
            return
        except Exception as e:
            last_error = e
            logger.error(f"Resend email failed: {str(e)}")
            # Continue to try SMTP
    
    # Use default email account if configured, otherwise use SMTP settings
    smtp_user = settings.DEFAULT_EMAIL_ACCOUNT if settings.DEFAULT_EMAIL_ACCOUNT else settings.SMTP_USER
    smtp_password = settings.DEFAULT_EMAIL_PASSWORD if settings.DEFAULT_EMAIL_PASSWORD else settings.SMTP_PASSWORD
    
    # Fallback to SMTP
    if settings.SMTP_HOST and smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            
            # 如果提供了from_name，使用 "名称 <邮箱>" 的格式
            if from_name:
                msg['From'] = f"{from_name} <{smtp_user}>"
            else:
                msg['From'] = smtp_user
            
            msg['To'] = to_email
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Try SSL first (port 465), then TLS (port 587)
            if settings.SMTP_PORT == 465:
                # Use SSL connection
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
                server.quit()
            else:
                # Use TLS connection
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent via SMTP to {to_email} (from {smtp_user})")
            return
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP认证失败: {str(e)}\n提示：Gmail用户需要使用'应用专用密码'而不是普通密码"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except (smtplib.SMTPConnectError, ConnectionError, TimeoutError) as e:
            error_msg = f"SMTP连接失败: {str(e)}\n提示：请检查网络连接、防火墙设置和SMTP服务器地址"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            last_error = e
            error_msg = f"SMTP邮件发送失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
    
    # No email service configured
    error_msg = "未配置邮件服务。请配置以下之一：\n1. RESEND_API_KEY\n2. SMTP_HOST + DEFAULT_EMAIL_ACCOUNT + DEFAULT_EMAIL_PASSWORD"
    logger.error(error_msg)
    if last_error:
        raise Exception(f"{error_msg}\n最后尝试的错误: {str(last_error)}") from last_error
    else:
        raise ValueError(error_msg)


def start_scheduler():
    """Start the background scheduler - checks user schedules every hour"""
    try:
        # Daily news update at configured time (optimized)
        scheduler.add_job(
            daily_news_update,
            CronTrigger(
                hour=settings.DAILY_UPDATE_HOUR,
                minute=settings.DAILY_UPDATE_MINUTE,
                timezone=settings.TIMEZONE
            ),
            id='daily_news_update',
            replace_existing=True
        )
        
        # Check user email schedules every 10 minutes
        # This allows each user to have their own schedule
        scheduler.add_job(
            send_scheduled_emails,
            IntervalTrigger(
                minutes=10,  # Check every 10 minutes for better delivery window
                timezone=settings.TIMEZONE
            ),
            id='check_user_email_schedules',
            replace_existing=True
        )
        
        # AI summary task worker — process async summarization tasks
        # Runs every 3 seconds, respects rate limiter (30 RPM)
        from services.summary_worker import worker_cycle, cleanup_old_tasks
        worker_interval = getattr(settings, 'SUMMARY_WORKER_INTERVAL', 3)
        
        scheduler.add_job(
            worker_cycle,
            IntervalTrigger(seconds=worker_interval),
            id='summary_task_worker',
            replace_existing=True,
            max_instances=1  # 防止重叠执行
        )
        
        # Clean up old completed/failed tasks (daily at 3 AM)
        scheduler.add_job(
            cleanup_old_tasks,
            CronTrigger(hour=3, minute=0, timezone=settings.TIMEZONE),
            id='cleanup_summary_tasks',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info(
            f"Scheduler started (optimized) - "
            f"News update at {settings.DAILY_UPDATE_HOUR}:{settings.DAILY_UPDATE_MINUTE:02d}, "
            f"Email check every 10 minutes, "
            f"Summary worker every {worker_interval}s ({settings.TIMEZONE})"
        )
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")


def stop_scheduler():
    """Stop the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
