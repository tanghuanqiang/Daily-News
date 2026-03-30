from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
from models import (
    AchievementDefinition,
    UserAchievement,
    User,
    AchievementDefinitionResponse,
    AchievementWithProgress,
    UserAchievementResponse
)
from auth import get_current_active_user
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/achievements", tags=["Achievements"])


@router.get("/definitions", response_model=List[AchievementDefinitionResponse])
async def get_achievement_definitions(
    category: str = None,
    db: Session = Depends(get_db)
):
    """
    获取所有成就定义
    
    Args:
        category: 可选的类别筛选（reading, exploration, early_bird, sharing）
        db: 数据库会话
        
    Returns:
        成就定义列表
    """
    try:
        query = db.query(AchievementDefinition).filter(AchievementDefinition.is_active == True)
        
        if category:
            query = query.filter(AchievementDefinition.category == category)
        
        achievements = query.order_by(AchievementDefinition.points.desc()).all()
        
        return achievements
        
    except Exception as e:
        logger.error(f"获取成就定义失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取成就定义失败: {str(e)}"
        )


@router.get("/my", response_model=List[AchievementWithProgress])
async def get_my_achievements_with_progress(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户的所有成就（包含进度）
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        成就列表（包含解锁状态和进度）
    """
    try:
        # 获取所有成就定义
        all_achievements = db.query(AchievementDefinition).filter(
            AchievementDefinition.is_active == True
        ).all()
        
        # 获取用户已解锁的成就
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id
        ).all()
        
        # 构建已解锁成就的ID集合
        unlocked_achievement_ids = {
            ua.achievement_id for ua in user_achievements
        }
        
        # 构建响应 - 扁平化结构
        result = []
        for achievement in all_achievements:
            is_unlocked = achievement.id in unlocked_achievement_ids
            
            # 获取解锁时间
            unlocked_at = next((
                ua.unlocked_at for ua in user_achievements 
                if ua.achievement_id == achievement.id
            ), None)
            
            # 计算进度（简化版本，实际项目中需要根据具体逻辑计算）
            progress = 1.0 if is_unlocked else 0.0
            current_value = 1 if is_unlocked else 0
            requirement_value = 1
            
            # 扁平化返回，与前端期望一致
            result.append({
                "id": achievement.id,
                "code": achievement.code,
                "name": achievement.name,
                "description": achievement.description,
                "icon": achievement.icon,
                "category": achievement.category,
                "points": achievement.points,
                "is_unlocked": is_unlocked,
                "unlocked_at": unlocked_at,
                "progress": progress,
                "current_value": current_value,
                "requirement_value": requirement_value
            })
        
        return result
        
    except Exception as e:
        logger.error(f"获取用户成就失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户成就失败: {str(e)}"
        )


@router.get("/my/unlocked", response_model=List[UserAchievementResponse])
async def get_my_unlocked_achievements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户已解锁的成就
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        已解锁成就列表
    """
    try:
        user_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id
        ).order_by(UserAchievement.unlocked_at.desc()).all()
        
        return user_achievements
        
    except Exception as e:
        logger.error(f"获取已解锁成就失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取已解锁成就失败: {str(e)}"
        )


@router.get("/stats")
async def get_achievement_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取成就统计信息
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        统计信息
    """
    try:
        # 总成就数
        total_achievements = db.query(AchievementDefinition).filter(
            AchievementDefinition.is_active == True
        ).count()
        
        # 已解锁成就数
        unlocked_count = db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id
        ).count()
        
        # 总点数
        total_points = db.query(func.sum(AchievementDefinition.points)).join(
            UserAchievement,
            UserAchievement.achievement_id == AchievementDefinition.id
        ).filter(
            UserAchievement.user_id == current_user.id
        ).scalar() or 0
        
        # 解锁率
        unlock_rate = (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0
        
        return {
            "total_achievements": total_achievements,
            "unlocked_count": unlocked_count,
            "total_points": total_points,
            "unlock_rate": round(unlock_rate, 2)
        }
        
    except Exception as e:
        logger.error(f"获取成就统计失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取成就统计失败: {str(e)}"
        )


@router.post("/unlock/{achievement_id}")
async def unlock_achievement(
    achievement_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    解锁成就（管理员或内部调用）
    
    Args:
        achievement_id: 成就ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        解锁的成就信息
    """
    try:
        # 检查成就是否存在
        achievement = db.query(AchievementDefinition).filter(
            AchievementDefinition.id == achievement_id,
            AchievementDefinition.is_active == True
        ).first()
        
        if not achievement:
            raise HTTPException(
                status_code=404,
                detail="成就不存在或未启用"
            )
        
        # 检查是否已解锁
        existing = db.query(UserAchievement).filter(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_id == achievement_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="您已经解锁了这个成就"
            )
        
        # 创建用户成就记录
        user_achievement = UserAchievement(
            user_id=current_user.id,
            achievement_id=achievement_id,
            progress_data={"auto_unlocked": True}
        )
        db.add(user_achievement)
        db.commit()
        db.refresh(user_achievement)
        
        logger.info(f"用户 {current_user.email} 解锁成就: {achievement.name}")
        
        return {
            "message": "成就已解锁",
            "achievement": achievement,
            "unlocked_at": user_achievement.unlocked_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解锁成就失败: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"解锁成就失败: {str(e)}"
        )
