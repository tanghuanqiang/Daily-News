from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, date
from database import get_db, SessionLocal
from models import (
    NewsCache, 
    Subscription,
    NewsSummary,
    DashboardResponse,
    User,
    TopicRefreshStatus,
    UserPreference,
    UserNewsInteraction
)
from auth import get_current_active_user
from scheduler import refresh_topic_with_lock, can_refresh_topic, get_or_create_refresh_status
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news", tags=["News"])


def get_or_create_user_preference(user_id: int, db: Session) -> UserPreference:
    """获取或创建用户偏好设置"""
    from routes.preferences import get_or_create_user_preference as _get_pref
    return _get_pref(user_id, db)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    date_filter: Optional[str] = None
):
    """
    Get personalized news dashboard for current user
    Returns news for all subscribed topics with personalization (read status, filtering, sorting)
    """
    # Get user's active subscriptions
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).all()
    
    if not subscriptions:
        return {
            "topics": [],
            "last_global_update": None
        }
    
    # Get user preferences
    preference = get_or_create_user_preference(current_user.id, db)
    
    # Use today's date if not specified
    if not date_filter:
        date_filter = date.today().strftime("%Y-%m-%d")
    
    topics_data = []
    last_global_update = None
    
    # Get read news IDs for this user
    read_news_ids = set()
    if preference.hide_read:
        read_interactions = db.query(UserNewsInteraction.news_id).filter(
            and_(
                UserNewsInteraction.user_id == current_user.id,
                UserNewsInteraction.is_read == True
            )
        ).all()
        read_news_ids = {r[0] for r in read_interactions}
    
    # Get hidden sources
    hidden_sources = set(preference.hidden_sources or [])
    
    for sub in subscriptions:
        # Get news for this topic from cache
        query = db.query(NewsCache).filter(
            NewsCache.topic == sub.topic,
            NewsCache.date == date_filter
        )
        
        # Filter out hidden sources
        if hidden_sources:
            query = query.filter(~NewsCache.source.in_(hidden_sources))
        
        # Filter out read news if preference is set
        if preference.hide_read and read_news_ids:
            query = query.filter(~NewsCache.id.in_(read_news_ids))
        
        # Apply sorting
        if preference.sort_by == "time":
            news_items = query.order_by(NewsCache.fetched_at.desc()).limit(8).all()
        else:  # relevance: 按相关性分数排序
            news_items = query.order_by(NewsCache.relevance_score.desc(), NewsCache.fetched_at.desc()).limit(8).all()
        
        if news_items:
            # Get the latest update time
            latest_update = max(item.fetched_at for item in news_items)
            if not last_global_update or latest_update > last_global_update:
                last_global_update = latest_update
            
            # Get read status for each news item
            news_ids = [item.id for item in news_items]
            read_status_map = {}
            if news_ids:
                read_interactions = db.query(UserNewsInteraction).filter(
                    and_(
                        UserNewsInteraction.user_id == current_user.id,
                        UserNewsInteraction.news_id.in_(news_ids),
                        UserNewsInteraction.is_read == True
                    )
                ).all()
                read_status_map = {inter.news_id: True for inter in read_interactions}
            
            # Build news items with read status
            news_items_with_status = []
            for item in news_items:
                news_dict = {
                    "id": item.id,
                    "topic": item.topic,
                    "title": item.title,
                    "summary": item.summary,
                    "summary_roast": item.summary_roast,
                    "url": item.url,
                    "source": item.source,
                    "image_url": item.image_url,
                    "published_at": item.published_at,
                    "fetched_at": item.fetched_at,
                    "date": item.date,
                    "is_read": read_status_map.get(item.id, False)
                }
                news_items_with_status.append(news_dict)
            
            # Build news summary for topic
            topics_data.append({
                "topic": sub.topic,
                "news_items": news_items_with_status,
                "last_updated": latest_update,
                "roast_mode": sub.roast_mode
            })
    
    return {
        "topics": topics_data,
        "last_global_update": last_global_update
    }


@router.get("/topic/{topic}")
async def get_news_by_topic(
    topic: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    date_filter: Optional[str] = None,
    limit: int = 10
):
    """Get news for a specific topic"""
    if not date_filter:
        date_filter = date.today().strftime("%Y-%m-%d")
    
    news_items = db.query(NewsCache).filter(
        NewsCache.topic == topic,
        NewsCache.date == date_filter
    ).order_by(NewsCache.fetched_at.desc()).limit(limit).all()
    
    return {
        "topic": topic,
        "date": date_filter,
        "news_items": news_items,
        "count": len(news_items)
    }


@router.post("/refresh")
async def trigger_manual_refresh(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger news refresh for current user's topics (optimized with duplicate prevention)
    Returns refresh status for each topic
    """
    from scheduler import refresh_topic_with_lock
    
    # Get user subscriptions
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).all()
    
    if not subscriptions:
        raise HTTPException(
            status_code=400,
            detail="No active subscriptions found"
        )
    
    today = date.today().strftime("%Y-%m-%d")
    
    # Collect unique topics
    topics = list(set([sub.topic for sub in subscriptions]))
    
    # Check refresh status for each topic
    refresh_results = []
    
    for topic in topics:
        can_refresh, reason, status = can_refresh_topic(topic, today, db)
        
        if not can_refresh:
            if reason.startswith("recently_refreshed"):
                # Extract remaining seconds
                try:
                    remaining = int(reason.split("_")[-1].replace("s", ""))
                except:
                    remaining = 0
                refresh_results.append({
                    "topic": topic,
                    "status": "skipped",
                    "reason": "recently_refreshed",
                    "remaining_seconds": remaining,
                    "last_refreshed_at": status.last_refreshed_at.isoformat() if status.last_refreshed_at else None
                })
            elif reason == "currently_refreshing":
                refresh_results.append({
                    "topic": topic,
                    "status": "skipped",
                    "reason": "currently_refreshing",
                    "message": "该主题正在刷新中，请稍候"
                })
        else:
            # Schedule refresh in background
            def refresh_task(topic_name: str, date_str: str):
                db_session = SessionLocal()
                try:
                    refresh_topic_with_lock(topic_name, date_str, db_session)
                finally:
                    db_session.close()
            
            background_tasks.add_task(refresh_task, topic, today)
            refresh_results.append({
                "topic": topic,
                "status": "refreshing",
                "reason": "triggered",
                "message": "刷新任务已启动"
            })
    
    # Count results
    refreshed_count = sum(1 for r in refresh_results if r["status"] == "refreshing")
    skipped_count = sum(1 for r in refresh_results if r["status"] == "skipped")
    
    return {
        "message": f"刷新任务已启动: {refreshed_count} 个主题正在刷新，{skipped_count} 个主题跳过（已刷新或正在刷新中）",
        "results": refresh_results,
        "refreshed_count": refreshed_count,
        "skipped_count": skipped_count
    }


@router.get("/refresh-status")
async def get_refresh_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get refresh status for current user's subscribed topics"""
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).all()
    
    if not subscriptions:
        return {"topics": []}
    
    today = date.today().strftime("%Y-%m-%d")
    topics = list(set([sub.topic for sub in subscriptions]))
    
    statuses = []
    for topic in topics:
        status = get_or_create_refresh_status(topic, today, db)
        statuses.append({
            "topic": topic,
            "last_refreshed_at": status.last_refreshed_at.isoformat() if status.last_refreshed_at else None,
            "is_refreshing": status.is_refreshing,
            "date": status.date
        })
    
    return {
        "date": today,
        "topics": statuses
    }


@router.get("/stats")
async def get_news_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get statistics about cached news"""
    today = date.today().strftime("%Y-%m-%d")
    
    # Count news items by topic for today
    stats = db.query(
        NewsCache.topic,
        func.count(NewsCache.id).label('count')
    ).filter(
        NewsCache.date == today
    ).group_by(NewsCache.topic).all()
    
    return {
        "date": today,
        "stats": [{"topic": topic, "count": count} for topic, count in stats]
    }
