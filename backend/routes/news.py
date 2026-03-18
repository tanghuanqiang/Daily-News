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
    UserNewsInteraction,
    CustomRSSFeed
)
from auth import get_current_active_user
from scheduler import refresh_topic_with_lock, can_refresh_topic, get_or_create_refresh_status
import logging

# RAG Integration
try:
    from rag.retrieval_service import get_retrieval_service
    from rag.vector_store import get_vector_store
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG modules not available")

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
    
    # Get user's active custom RSS feeds
    custom_feeds = db.query(CustomRSSFeed).filter(
        CustomRSSFeed.user_id == current_user.id,
        CustomRSSFeed.is_active == True
    ).all()
    
    # Create a combined list of topics with their roast_mode
    # For subscriptions, use subscription's roast_mode
    # For custom RSS feeds, use feed's roast_mode
    topic_configs = {}
    for sub in subscriptions:
        topic_configs[sub.topic] = {"roast_mode": sub.roast_mode, "type": "subscription"}
    
    for feed in custom_feeds:
        # If topic already exists from subscription, keep subscription's roast_mode
        # Otherwise, use feed's roast_mode
        if feed.topic not in topic_configs:
            topic_configs[feed.topic] = {"roast_mode": feed.roast_mode, "type": "custom_rss"}
    
    if not topic_configs:
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
    
    # Process all topics (from both subscriptions and custom RSS feeds)
    for topic, config in topic_configs.items():
        # Get news for this topic from cache
        query = db.query(NewsCache).filter(
            NewsCache.topic == topic,
            NewsCache.date == date_filter
        )
        
        # Filter out hidden sources
        if hidden_sources:
            query = query.filter(~NewsCache.source.in_(hidden_sources))
        
        # Filter out read news if preference is set
        if preference.hide_read and read_news_ids:
            query = query.filter(~NewsCache.id.in_(read_news_ids))
        
        # Apply sorting - always show latest 16 items by creation time (fetched_at)
        if preference.sort_by == "time":
            news_items = query.order_by(NewsCache.fetched_at.desc()).limit(16).all()
        else:  # relevance: 按相关性分数排序，但仍然限制16条
            news_items = query.order_by(NewsCache.relevance_score.desc(), NewsCache.fetched_at.desc()).limit(16).all()
        
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
                "topic": topic,
                "news_items": news_items_with_status,
                "last_updated": latest_update,
                "roast_mode": config["roast_mode"]
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
    
    # Get user's active custom RSS feeds
    custom_feeds = db.query(CustomRSSFeed).filter(
        CustomRSSFeed.user_id == current_user.id,
        CustomRSSFeed.is_active == True
    ).all()
    
    # Collect unique topics from subscriptions and custom RSS feeds
    topics = set([sub.topic for sub in subscriptions])
    topics.update([feed.topic for feed in custom_feeds])
    topics = list(topics)
    
    if not topics:
        raise HTTPException(
            status_code=400,
            detail="No active subscriptions found"
        )
    
    today = date.today().strftime("%Y-%m-%d")
    
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
    
    # Get user's active custom RSS feeds
    custom_feeds = db.query(CustomRSSFeed).filter(
        CustomRSSFeed.user_id == current_user.id,
        CustomRSSFeed.is_active == True
    ).all()
    
    # Collect unique topics from both subscriptions and custom RSS feeds
    topics = set([sub.topic for sub in subscriptions])
    topics.update([feed.topic for feed in custom_feeds])
    topics = list(topics)
    
    if not topics:
        return {"topics": []}
    
    today = date.today().strftime("%Y-%m-%d")
    
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


# RAG API Endpoints
@router.get("/similar/{news_id}")
async def get_similar_news(
    news_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get similar news articles for a given news ID
    
    Args:
        news_id: ID of the news article
        top_k: Number of similar articles to return
    
    Returns:
        List of similar news articles with similarity scores
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available"
        )
    
    try:
        # Get the news article
        news = db.query(NewsCache).filter(NewsCache.id == news_id).first()
        if not news:
            raise HTTPException(
                status_code=404,
                detail="News article not found"
            )
        
        # Get retrieval service
        retrieval_service = get_retrieval_service()
        if not retrieval_service.is_available:
            raise HTTPException(
                status_code=503,
                detail="Retrieval service not available"
            )
        
        # Find similar news
        similar_news = retrieval_service.find_similar_to_news(
            news_id=str(news_id),
            title=news.title,
            content=news.summary,
            top_k=top_k,
            min_similarity=0.4
        )
        
        # Extract news IDs from similar results
        similar_news_ids = []
        for item in similar_news:
            doc_id = item.get("id", "")
            if doc_id.startswith("news_"):
                # Extract news ID from document ID
                try:
                    target_news_id = int(doc_id.split("_")[1])
                    similar_news_ids.append(target_news_id)
                except:
                    continue
        
        # Fetch full news data for similar articles
        if similar_news_ids:
            similar_articles = db.query(NewsCache).filter(
                NewsCache.id.in_(similar_news_ids)
            ).all()
            
            # Build response with similarity scores
            result = []
            for article in similar_articles:
                # Find matching similarity score
                similarity_score = 0.0
                for sim_item in similar_news:
                    doc_id = sim_item.get("id", "")
                    if doc_id.startswith(f"news_{article.id}_"):
                        similarity_score = sim_item.get("score", 0.0)
                        break
                
                result.append({
                    "id": article.id,
                    "title": article.title,
                    "summary": article.summary,
                    "summary_roast": article.summary_roast,
                    "url": article.url,
                    "source": article.source,
                    "image_url": article.image_url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "similarity_score": similarity_score
                })
            
            return {
                "news_id": news_id,
                "original_title": news.title,
                "similar_articles": result,
                "count": len(result)
            }
        else:
            return {
                "news_id": news_id,
                "original_title": news.title,
                "similar_articles": [],
                "count": 0,
                "message": "No similar articles found"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get similar news: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve similar news: {str(e)}"
        )


@router.get("/recommendations/personalized")
async def get_personalized_recommendations(
    limit: int = 10,
    topic: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get personalized news recommendations based on user's reading history
    
    Args:
        limit: Number of recommendations to return
        topic: Optional topic filter
    
    Returns:
        List of recommended news articles
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available"
        )
    
    try:
        # Get retrieval service
        retrieval_service = get_retrieval_service()
        if not retrieval_service.is_available:
            raise HTTPException(
                status_code=503,
                detail="Retrieval service not available"
            )
        
        # Get personalized recommendations
        recommendations = retrieval_service.get_personalized_recommendations(
            db=db,
            user_id=current_user.id,
            topic=topic,
            limit=limit
        )
        
        # Extract news IDs from recommendations
        recommended_news_ids = []
        for item in recommendations:
            doc_id = item.get("id", "")
            if doc_id.startswith("news_"):
                try:
                    target_news_id = int(doc_id.split("_")[1])
                    recommended_news_ids.append(target_news_id)
                except:
                    continue
        
        # Fetch full news data
        if recommended_news_ids:
            articles = db.query(NewsCache).filter(
                NewsCache.id.in_(recommended_news_ids)
            ).all()
            
            # Build response
            result = []
            for article in articles:
                # Find matching recommendation score
                rec_score = 0.0
                for rec_item in recommendations:
                    doc_id = rec_item.get("id", "")
                    if doc_id.startswith(f"news_{article.id}_"):
                        rec_score = rec_item.get("score", 0.0)
                        break
                
                result.append({
                    "id": article.id,
                    "title": article.title,
                    "summary": article.summary,
                    "summary_roast": article.summary_roast,
                    "url": article.url,
                    "source": article.source,
                    "image_url": article.image_url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "topic": article.topic,
                    "recommendation_score": rec_score
                })
            
            return {
                "user_id": current_user.id,
                "recommendations": result,
                "count": len(result),
                "topic": topic
            }
        else:
            return {
                "user_id": current_user.id,
                "recommendations": [],
                "count": 0,
                "topic": topic,
                "message": "No recommendations found. Try reading more news to build your interest profile."
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get personalized recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.get("/search/hybrid")
async def hybrid_search_news(
    query: str,
    topic: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Hybrid search combining vector similarity and time-based scoring
    
    Args:
        query: Search query text
        topic: Optional topic filter
        limit: Number of results
    
    Returns:
        Ranked list of news articles
    """
    if not RAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="RAG service not available"
        )
    
    if not query or not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )
    
    try:
        # Get retrieval service
        retrieval_service = get_retrieval_service()
        if not retrieval_service.is_available:
            raise HTTPException(
                status_code=503,
                detail="Retrieval service not available"
            )
        
        # Perform hybrid search
        search_results = retrieval_service.hybrid_search(
            query_text=query,
            db=db,
            topic=topic,
            limit=limit,
            time_weight=0.3,
            similarity_weight=0.7
        )
        
        # Extract news IDs from search results
        search_news_ids = []
        for item in search_results:
            doc_id = item.get("id", "")
            if doc_id.startswith("news_"):
                try:
                    target_news_id = int(doc_id.split("_")[1])
                    search_news_ids.append(target_news_id)
                except:
                    continue
        
        # Fetch full news data
        if search_news_ids:
            articles = db.query(NewsCache).filter(
                NewsCache.id.in_(search_news_ids)
            ).all()
            
            # Build response with hybrid scores
            result = []
            for article in articles:
                # Find matching search result
                hybrid_score = 0.0
                similarity_score = 0.0
                time_score = 0.0
                
                for search_item in search_results:
                    doc_id = search_item.get("id", "")
                    if doc_id.startswith(f"news_{article.id}_"):
                        hybrid_score = search_item.get("hybrid_score", 0.0)
                        similarity_score = search_item.get("similarity_score", 0.0)
                        time_score = search_item.get("time_score", 0.0)
                        break
                
                result.append({
                    "id": article.id,
                    "title": article.title,
                    "summary": article.summary,
                    "summary_roast": article.summary_roast,
                    "url": article.url,
                    "source": article.source,
                    "image_url": article.image_url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "topic": article.topic,
                    "hybrid_score": hybrid_score,
                    "similarity_score": similarity_score,
                    "time_score": time_score
                })
            
            # Sort by hybrid score (already sorted but just in case)
            result.sort(key=lambda x: x["hybrid_score"], reverse=True)
            
            return {
                "query": query,
                "topic": topic,
                "results": result,
                "count": len(result)
            }
        else:
            return {
                "query": query,
                "topic": topic,
                "results": [],
                "count": 0,
                "message": "No search results found"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/rag/status")
async def get_rag_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get RAG system status and statistics
    
    Returns:
        RAG system availability and statistics
    """
    if not RAG_AVAILABLE:
        return {
            "available": False,
            "message": "RAG modules not installed"
        }
    
    try:
        # Get vector store stats
        vector_store = get_vector_store()
        vector_stats = vector_store.get_stats()
        
        # Get retrieval service status
        retrieval_service = get_retrieval_service()
        
        return {
            "available": True,
            "vector_store": {
                "is_available": vector_store.is_available,
                "document_count": vector_stats.get("document_count", 0),
                "storage_size": vector_stats.get("storage_size", 0),
                "persist_directory": vector_stats.get("persist_directory", "")
            },
            "retrieval_service": {
                "is_available": retrieval_service.is_available
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get RAG status: {str(e)}")
        return {
            "available": False,
            "error": str(e)
        }

