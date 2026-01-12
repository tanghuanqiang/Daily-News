from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from database import get_db
from models import User, UserPreference, UserPreferenceResponse, UserPreferenceUpdate, NewsCache, UserNewsInteraction
from auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


def get_or_create_user_preference(user_id: int, db: Session) -> UserPreference:
    """获取或创建用户偏好设置"""
    preference = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not preference:
        preference = UserPreference(
            user_id=user_id,
            hide_read=False,
            sort_by="time",
            hidden_sources=[]
        )
        db.add(preference)
        db.commit()
        db.refresh(preference)
    return preference


@router.get("/me", response_model=UserPreferenceResponse)
async def get_my_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的偏好设置"""
    preference = get_or_create_user_preference(current_user.id, db)
    return preference


@router.put("/me", response_model=UserPreferenceResponse)
async def update_my_preferences(
    update_data: UserPreferenceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户的偏好设置"""
    preference = get_or_create_user_preference(current_user.id, db)
    
    if update_data.hide_read is not None:
        preference.hide_read = update_data.hide_read
    if update_data.sort_by is not None:
        if update_data.sort_by not in ["time", "relevance"]:
            raise HTTPException(status_code=400, detail="sort_by must be 'time' or 'relevance'")
        preference.sort_by = update_data.sort_by
    if update_data.hidden_sources is not None:
        preference.hidden_sources = update_data.hidden_sources
    
    preference.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preference)
    
    return preference


@router.post("/read/{news_id}")
async def mark_news_read(
    news_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """标记新闻为已读"""
    # 检查新闻是否存在
    news = db.query(NewsCache).filter(NewsCache.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    
    # 检查是否已有记录
    interaction = db.query(UserNewsInteraction).filter(
        and_(
            UserNewsInteraction.user_id == current_user.id,
            UserNewsInteraction.news_id == news_id
        )
    ).first()
    
    if interaction:
        if not interaction.is_read:
            interaction.is_read = True
            interaction.read_at = datetime.utcnow()
            db.commit()
    else:
        interaction = UserNewsInteraction(
            user_id=current_user.id,
            news_id=news_id,
            is_read=True,
            read_at=datetime.utcnow()
        )
        db.add(interaction)
        db.commit()
    
    return {"success": True, "message": "News marked as read"}


@router.post("/mark-unread/{news_id}")
async def mark_news_unread(
    news_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """标记新闻为未读"""
    interaction = db.query(UserNewsInteraction).filter(
        and_(
            UserNewsInteraction.user_id == current_user.id,
            UserNewsInteraction.news_id == news_id
        )
    ).first()
    
    if interaction:
        interaction.is_read = False
        interaction.read_at = None
        db.commit()
        return {"success": True, "message": "News marked as unread"}
    else:
        return {"success": True, "message": "News was already unread"}
