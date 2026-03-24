from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from database import get_db
from models import (
    User,
    InvitationCodeResponse,
    InvitationStatsResponse,
    InvitationRewardResponse
)
from auth import get_current_active_user
from services.invitation_service import InvitationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invitations", tags=["Invitations"])


@router.post("/generate", response_model=InvitationCodeResponse)
async def generate_invitation_code(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    生成邀请码
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        生成的邀请码
    """
    try:
        service = InvitationService(db)
        
        code = service.generate_invitation_code(current_user.id)
        
        if not code:
            raise HTTPException(
                status_code=400,
                detail="生成邀请码失败"
            )
        
        # 查询生成的邀请码记录
        from models import InvitationCode
        invitation = db.query(InvitationCode).filter(InvitationCode.code == code).first()
        
        return invitation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成邀请码失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"生成邀请码失败: {str(e)}"
        )


@router.get("/my-codes", response_model=List[InvitationCodeResponse])
async def get_my_invitation_codes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取我的邀请码列表
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        邀请码列表
    """
    try:
        service = InvitationService(db)
        
        invitations = service.get_user_invitations(current_user.id)
        
        # 查询邀请码记录
        from models import InvitationCode
        codes = db.query(InvitationCode).filter(
            InvitationCode.generated_by == current_user.id
        ).order_by(InvitationCode.created_at.desc()).all()
        
        return codes
        
    except Exception as e:
        logger.error(f"获取邀请码列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取邀请码列表失败: {str(e)}"
        )


@router.get("/my-stats", response_model=InvitationStatsResponse)
async def get_my_invitation_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取我的邀请统计
    
    Args:
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        邀请统计信息
    """
    try:
        service = InvitationService(db)
        
        stats = service.get_user_invitation_stats(current_user.id)
        
        if not stats:
            # 返回默认统计
            stats = {
                "total_invited": 0,
                "successful_invites": 0,
                "total_points_earned": 0,
                "last_invited_at": None,
                "invite_success_rate": 0.0
            }
        
        return stats
        
    except Exception as e:
        logger.error(f"获取邀请统计失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取邀请统计失败: {str(e)}"
        )
