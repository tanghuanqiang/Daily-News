from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import (
    Subscription, 
    SubscriptionCreate, 
    SubscriptionUpdate, 
    SubscriptionResponse,
    CustomRSSFeed,
    CustomRSSFeedCreate,
    CustomRSSFeedUpdate,
    CustomRSSFeedResponse,
    User
)
from auth import get_current_active_user

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])


@router.get("/", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all subscriptions for current user"""
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.is_active == True
    ).all()
    return subscriptions


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription"""
    # Check if subscription already exists
    existing = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.topic == subscription_data.topic,
        Subscription.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already subscribed to this topic"
        )
    
    # Create subscription
    subscription = Subscription(
        user_id=current_user.id,
        topic=subscription_data.topic,
        roast_mode=subscription_data.roast_mode
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    
    return subscription


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update subscription settings"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Update fields
    if subscription_data.roast_mode is not None:
        subscription.roast_mode = subscription_data.roast_mode
    if subscription_data.is_active is not None:
        subscription.is_active = subscription_data.is_active
    
    db.commit()
    db.refresh(subscription)
    
    return subscription


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    db.delete(subscription)
    db.commit()
    
    return None


# Preset topics endpoint
PRESET_TOPICS = [
    # 预设主题
    "科技", "AI", "财经", "股市", "国际时事", 
    "娱乐", "体育", "搞笑", "奇闻", "科学",
    # 中文技术/编程/开发者社区（强烈推荐）
    "阮一峰的网络日志",
    "酷壳 CoolShell",
    "美团技术团队",
    "少数派（数字生产力）",
    "玉伯的博客/蚂蚁体验",
    "粥里有勺糖",
    "黑泽的博客",
    "独立开发者周刊",
]

@router.get("/preset-topics")
async def get_preset_topics():
    """Get list of preset popular topics"""
    return {"topics": PRESET_TOPICS}


# Custom RSS endpoints
@router.get("/custom-rss", response_model=List[CustomRSSFeedResponse])
async def get_custom_rss_feeds(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all custom RSS feeds for current user"""
    feeds = db.query(CustomRSSFeed).filter(
        CustomRSSFeed.user_id == current_user.id
    ).all()
    return feeds


@router.post("/custom-rss", response_model=CustomRSSFeedResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_rss_feed(
    feed_data: CustomRSSFeedCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new custom RSS feed"""
    # Validate URL format
    if not feed_data.feed_url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format. URL must start with http:// or https://"
        )
    
    # Create custom RSS feed
    custom_feed = CustomRSSFeed(
        user_id=current_user.id,
        topic=feed_data.topic,
        feed_url=feed_data.feed_url,
        is_active=True
    )
    db.add(custom_feed)
    db.commit()
    db.refresh(custom_feed)
    
    return custom_feed


@router.put("/custom-rss/{feed_id}", response_model=CustomRSSFeedResponse)
async def update_custom_rss_feed(
    feed_id: int,
    feed_data: CustomRSSFeedUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update custom RSS feed settings"""
    custom_feed = db.query(CustomRSSFeed).filter(
        CustomRSSFeed.id == feed_id,
        CustomRSSFeed.user_id == current_user.id
    ).first()
    
    if not custom_feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom RSS feed not found"
        )
    
    # Update fields
    if feed_data.is_active is not None:
        custom_feed.is_active = feed_data.is_active
    if feed_data.roast_mode is not None:
        custom_feed.roast_mode = feed_data.roast_mode
    
    db.commit()
    db.refresh(custom_feed)
    
    return custom_feed


@router.delete("/custom-rss/{feed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_rss_feed(
    feed_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a custom RSS feed"""
    custom_feed = db.query(CustomRSSFeed).filter(
        CustomRSSFeed.id == feed_id,
        CustomRSSFeed.user_id == current_user.id
    ).first()
    
    if not custom_feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom RSS feed not found"
        )
    
    db.delete(custom_feed)
    db.commit()
    
    return None
