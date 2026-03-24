from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import (
    NewsFeedback,
    NewsFeedbackCreate,
    NewsFeedbackResponse,
    User,
    NewsCache
)
from auth import get_current_active_user
from services.achievement_service import check_and_unlock_achievements
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("/", response_model=NewsFeedbackResponse)
async def create_feedback(
    feedback_data: NewsFeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建新闻反馈（点赞/点踩/分享）
    
    Args:
        feedback_data: 包含news_id和feedback_type
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        创建的反馈记录
    """
    try:
        # 验证反馈类型
        valid_feedback_types = ['like', 'dislike', 'share']
        if feedback_data.feedback_type not in valid_feedback_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的反馈类型。必须是: {', '.join(valid_feedback_types)}"
            )
        
        # 检查新闻是否存在
        news = db.query(NewsCache).filter(NewsCache.id == feedback_data.news_id).first()
        if not news:
            raise HTTPException(
                status_code=404,
                detail="新闻不存在"
            )
        
        # 检查是否已经存在相同反馈
        existing = db.query(NewsFeedback).filter(
            NewsFeedback.user_id == current_user.id,
            NewsFeedback.news_id == feedback_data.news_id,
            NewsFeedback.feedback_type == feedback_data.feedback_type
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="您已经提交过这种反馈"
            )
        
        # 创建反馈记录
        feedback = NewsFeedback(
            user_id=current_user.id,
            news_id=feedback_data.news_id,
            feedback_type=feedback_data.feedback_type
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        logger.info(f"用户 {current_user.email} 对新闻 {feedback_data.news_id} 提交反馈: {feedback_data.feedback_type}")
        
        # 成就检测
        try:
            if feedback_data.feedback_type == 'like':
                # 阅读相关成就检测
                check_and_unlock_achievements(
                    user_id=current_user.id,
                    trigger_type='read',
                    news_id=feedback_data.news_id,
                    db=db
                )
        except Exception as e:
            logger.error(f"成就检测失败: {str(e)}")
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建反馈失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"创建反馈失败: {str(e)}"
        )


@router.get("/my", response_model=List[NewsFeedbackResponse])
async def get_my_feedback(
    feedback_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的反馈历史
    
    Args:
        feedback_type: 可选的反馈类型筛选
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        反馈历史列表
    """
    try:
        query = db.query(NewsFeedback).filter(NewsFeedback.user_id == current_user.id)
        
        # 如果指定了反馈类型，添加筛选条件
        if feedback_type:
            if feedback_type not in ['like', 'dislike', 'share']:
                raise HTTPException(
                    status_code=400,
                    detail="无效的反馈类型"
                )
            query = query.filter(NewsFeedback.feedback_type == feedback_type)
        
        # 按创建时间倒序排列
        feedbacks = query.order_by(NewsFeedback.created_at.desc()).all()
        
        return feedbacks
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取反馈历史失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取反馈历史失败: {str(e)}"
        )


@router.get("/stats/{news_id}")
async def get_feedback_stats(
    news_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定新闻的反馈统计
    
    Args:
        news_id: 新闻ID
        db: 数据库会话
        
    Returns:
        反馈统计数据
    """
    try:
        # 检查新闻是否存在
        news = db.query(NewsCache).filter(NewsCache.id == news_id).first()
        if not news:
            raise HTTPException(
                status_code=404,
                detail="新闻不存在"
            )
        
        # 统计各种反馈的数量
        stats = db.query(
            NewsFeedback.feedback_type,
            func.count(NewsFeedback.id).label('count')
        ).filter(
            NewsFeedback.news_id == news_id
        ).group_by(NewsFeedback.feedback_type).all()
        
        # 构建响应
        result = {
            "news_id": news_id,
            "total_feedback": 0,
            "like_count": 0,
            "dislike_count": 0,
            "share_count": 0
        }
        
        for stat in stats:
            result["total_feedback"] += stat.count
            if stat.feedback_type == 'like':
                result["like_count"] = stat.count
            elif stat.feedback_type == 'dislike':
                result["dislike_count"] = stat.count
            elif stat.feedback_type == 'share':
                result["share_count"] = stat.count
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取反馈统计失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取反馈统计失败: {str(e)}"
        )


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    删除自己的反馈（可选功能）
    
    Args:
        feedback_id: 反馈ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        成功消息
    """
    try:
        feedback = db.query(NewsFeedback).filter(
            NewsFeedback.id == feedback_id,
            NewsFeedback.user_id == current_user.id
        ).first()
        
        if not feedback:
            raise HTTPException(
                status_code=404,
                detail="反馈不存在或无权删除"
            )
        
        db.delete(feedback)
        db.commit()
        
        logger.info(f"用户 {current_user.email} 删除反馈 {feedback_id}")
        
        return {"message": "反馈已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除反馈失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除反馈失败: {str(e)}"
        )
