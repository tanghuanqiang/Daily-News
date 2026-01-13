from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from auth import get_current_active_user
from models import User
from scheduler import send_email_to_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["Schedule"])


class UserScheduleConfig(BaseModel):
    """用户定时任务配置（仅支持每天固定时间）"""
    enabled: bool
    schedule_type: str = "daily"  # 固定为 "daily"
    hour: Optional[int] = None
    minute: Optional[int] = None


class UserScheduleStatus(BaseModel):
    """用户定时任务状态"""
    enabled: bool
    schedule_type: str
    hour: Optional[int]
    minute: Optional[int]
    last_email_sent_at: Optional[str]


@router.get("/me", response_model=UserScheduleStatus)
async def get_my_schedule(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的定时任务配置"""
    try:
        # Refresh user from database to get latest data
        db.refresh(current_user)
        
        return {
            "enabled": current_user.email_schedule_enabled,
            "schedule_type": "daily",  # 固定为 daily
            "hour": current_user.email_schedule_hour,
            "minute": current_user.email_schedule_minute,
            "last_email_sent_at": current_user.last_email_sent_at.isoformat() if current_user.last_email_sent_at else None
        }
    except Exception as e:
        logger.error(f"Failed to get user schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/me")
async def update_my_schedule(
    config: UserScheduleConfig,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户的定时任务配置（仅支持每天固定时间）"""
    try:
        # 只支持 daily 模式
        if config.schedule_type and config.schedule_type != "daily":
            raise HTTPException(status_code=400, detail="Only 'daily' schedule type is supported")
        
        # Validate daily schedule
        if config.hour is None or config.minute is None:
            raise HTTPException(status_code=400, detail="hour and minute are required")
        if not (0 <= config.hour <= 23) or not (0 <= config.minute <= 59):
            raise HTTPException(status_code=400, detail="Invalid hour or minute")
        
        # Update user schedule settings
        current_user.email_schedule_enabled = config.enabled
        current_user.email_schedule_type = "daily"  # 固定为 daily
        current_user.email_schedule_hour = config.hour or 9
        current_user.email_schedule_minute = config.minute or 0
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Updated schedule for user {current_user.email}: {config.schedule_type}, enabled={config.enabled}")
        
        return {
            "message": "Schedule updated successfully",
            "schedule": {
                "enabled": current_user.email_schedule_enabled,
                "schedule_type": "daily",
                "hour": current_user.email_schedule_hour,
                "minute": current_user.email_schedule_minute
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user schedule: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-email")
async def test_email_schedule(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """测试邮件发送功能（立即发送一次邮件给当前用户）"""
    try:
        # Send email to current user immediately
        send_email_to_user(current_user.id, db)
        return {
            "message": "Test email sent successfully",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Test email failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
