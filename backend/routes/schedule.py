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
    """用户定时任务配置"""
    enabled: bool
    schedule_type: str  # "daily", "weekly", "interval"
    hour: Optional[int] = None
    minute: Optional[int] = None
    day_of_week: Optional[int] = None  # 0=周一, 6=周日
    interval_hours: Optional[int] = None  # 间隔小时数


class UserScheduleStatus(BaseModel):
    """用户定时任务状态"""
    enabled: bool
    schedule_type: str
    hour: Optional[int]
    minute: Optional[int]
    day_of_week: Optional[int]
    interval_hours: Optional[int]
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
            "schedule_type": current_user.email_schedule_type,
            "hour": current_user.email_schedule_hour,
            "minute": current_user.email_schedule_minute,
            "day_of_week": current_user.email_schedule_day_of_week,
            "interval_hours": current_user.email_schedule_interval_hours,
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
    """更新当前用户的定时任务配置"""
    try:
        # Validate schedule type
        if config.schedule_type not in ["daily", "weekly", "interval"]:
            raise HTTPException(status_code=400, detail="schedule_type must be 'daily', 'weekly', or 'interval'")
        
        # Validate based on schedule type
        if config.schedule_type == "daily":
            if config.hour is None or config.minute is None:
                raise HTTPException(status_code=400, detail="hour and minute are required for daily schedule")
            if not (0 <= config.hour <= 23) or not (0 <= config.minute <= 59):
                raise HTTPException(status_code=400, detail="Invalid hour or minute")
        
        elif config.schedule_type == "weekly":
            if config.hour is None or config.minute is None or config.day_of_week is None:
                raise HTTPException(status_code=400, detail="hour, minute, and day_of_week are required for weekly schedule")
            if not (0 <= config.hour <= 23) or not (0 <= config.minute <= 59) or not (0 <= config.day_of_week <= 6):
                raise HTTPException(status_code=400, detail="Invalid hour, minute, or day_of_week")
        
        elif config.schedule_type == "interval":
            if config.interval_hours is None or config.interval_hours <= 0:
                raise HTTPException(status_code=400, detail="interval_hours must be positive for interval schedule")
        
        # Update user schedule settings
        current_user.email_schedule_enabled = config.enabled
        current_user.email_schedule_type = config.schedule_type
        current_user.email_schedule_hour = config.hour or 9
        current_user.email_schedule_minute = config.minute or 0
        current_user.email_schedule_day_of_week = config.day_of_week or 0
        current_user.email_schedule_interval_hours = config.interval_hours or 24
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"Updated schedule for user {current_user.email}: {config.schedule_type}, enabled={config.enabled}")
        
        return {
            "message": "Schedule updated successfully",
            "schedule": {
                "enabled": current_user.email_schedule_enabled,
                "schedule_type": current_user.email_schedule_type,
                "hour": current_user.email_schedule_hour,
                "minute": current_user.email_schedule_minute,
                "day_of_week": current_user.email_schedule_day_of_week,
                "interval_hours": current_user.email_schedule_interval_hours
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
