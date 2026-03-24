from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
from models import User, NewsCache, UserPreference, InvitationCode, UserInvitationStats, Experiment, ExperimentVariant
from auth import get_current_user
import logging

router = APIRouter(prefix="/api/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def require_admin(current_user: User = Depends(get_current_user)):
    """验证管理员权限"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ==================== 概览数据 ====================

@router.get("/overview", response_model=Dict[str, Any])
def get_overview_data(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取系统概览数据"""
    try:
        # 用户统计
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        
        # 新闻统计
        total_news = db.query(NewsCache).count()
        
        # 邀请统计
        total_invites = db.query(InvitationCode).count()
        used_invites = db.query(InvitationCode).filter(InvitationCode.is_used == True).count()
        invite_success_rate = (used_invites / total_invites * 100) if total_invites > 0 else 0
        
        # 实验统计
        total_experiments = db.query(Experiment).count()
        running_experiments = db.query(Experiment).filter(Experiment.status == "running").count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "active_rate": round(active_users / total_users * 100, 1) if total_users > 0 else 0
            },
            "news": {
                "total": total_news
            },
            "invitations": {
                "total": total_invites,
                "used": used_invites,
                "success_rate": round(invite_success_rate, 1)
            },
            "experiments": {
                "total": total_experiments,
                "running": running_experiments
            }
        }
    except Exception as e:
        logger.error(f"获取概览数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取数据失败: {str(e)}")


# ==================== 用户管理 ====================

@router.get("/users", response_model=List[Dict[str, Any]])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户列表"""
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        
        result = []
        for user in users:
            # 获取用户偏好
            prefs = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
            
            # 获取邀请统计
            invite_stats = db.query(UserInvitationStats).filter(
                UserInvitationStats.user_id == user.id
            ).first()
            
            result.append({
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "email_verified": user.email_verified,
                "email_notifications": user.email_notifications,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "preferences": {
                    "hide_read": prefs.hide_read if prefs else False,
                    "sort_by": prefs.sort_by if prefs else "time",
                    "hidden_sources": prefs.hidden_sources if prefs else []
                } if prefs else None,
                "invitation_stats": {
                    "total_invited": invite_stats.total_invited if invite_stats else 0,
                    "successful_invites": invite_stats.successful_invites if invite_stats else 0,
                    "total_points_earned": invite_stats.total_points_earned if invite_stats else 0
                } if invite_stats else None
            })
        
        return result
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户列表失败: {str(e)}")


@router.get("/users/{user_id}", response_model=Dict[str, Any])
def get_user_detail(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取用户详细信息"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 获取用户偏好
        prefs = db.query(UserPreference).filter(UserPreference.user_id == user.id).first()
        
        # 获取邀请统计
        invite_stats = db.query(UserInvitationStats).filter(
            UserInvitationStats.user_id == user.id
        ).first()
        
        # 获取用户邀请码
        user_invitations = db.query(InvitationCode).filter(
            InvitationCode.generated_by == user.id
        ).all()
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "email_verified": user.email_verified,
            "email_notifications": user.email_notifications,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "preferences": {
                "hide_read": prefs.hide_read if prefs else False,
                "sort_by": prefs.sort_by if prefs else "time",
                "hidden_sources": prefs.hidden_sources if prefs else []
            } if prefs else None,
            "invitation_stats": {
                "total_invited": invite_stats.total_invited if invite_stats else 0,
                "successful_invites": invite_stats.successful_invites if invite_stats else 0,
                "total_points_earned": invite_stats.total_points_earned if invite_stats else 0,
                "last_invited_at": invite_stats.last_invited_at.isoformat() if invite_stats and invite_stats.last_invited_at else None
            } if invite_stats else None,
            "invitation_codes": [
                {
                    "code": inv.code,
                    "is_used": inv.is_used,
                    "used_by": inv.used_by,
                    "created_at": inv.created_at.isoformat() if inv.created_at else None,
                    "used_at": inv.used_at.isoformat() if inv.used_at else None
                }
                for inv in user_invitations
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户详情失败: {str(e)}")


# ==================== 新闻管理 ====================

@router.get("/news", response_model=List[Dict[str, Any]])
def get_all_news(
    skip: int = 0,
    limit: int = 100,
    topic: str = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取新闻列表"""
    try:
        query = db.query(NewsCache)
        
        if topic:
            query = query.filter(NewsCache.topic == topic)
        
        news = query.offset(skip).limit(limit).all()
        
        return [
            {
                "id": article.id,
                "title": article.title,
                "topic": article.topic,
                "summary": article.summary,
                "source": article.source,
                "url": article.url,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None
            }
            for article in news
        ]
    except Exception as e:
        logger.error(f"获取新闻列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取新闻列表失败: {str(e)}")


# ==================== 邀请管理 ====================

@router.get("/invitations", response_model=List[Dict[str, Any]])
def get_all_invitations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取所有邀请码"""
    try:
        invitations = db.query(InvitationCode).offset(skip).limit(limit).all()
        
        return [
            {
                "id": inv.id,
                "code": inv.code,
                "generated_by": inv.generated_by,
                "is_used": inv.is_used,
                "used_by": inv.used_by,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "used_at": inv.used_at.isoformat() if inv.used_at else None
            }
            for inv in invitations
        ]
    except Exception as e:
        logger.error(f"获取邀请码列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取邀请码列表失败: {str(e)}")


@router.get("/invitations/stats", response_model=List[Dict[str, Any]])
def get_invitation_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取邀请统计排行"""
    try:
        stats = db.query(UserInvitationStats).all()
        
        # 获取用户名
        result = []
        for stat in stats:
            user = db.query(User).filter(User.id == stat.user_id).first()
            if user:
                result.append({
                    "user_id": stat.user_id,
                    "username": user.username,
                    "email": user.email,
                    "total_invited": stat.total_invited,
                    "successful_invites": stat.successful_invites,
                    "total_points_earned": stat.total_points_earned,
                    "last_invited_at": stat.last_invited_at.isoformat() if stat.last_invited_at else None,
                    "success_rate": round(stat.successful_invites / stat.total_invited * 100, 1) if stat.total_invited > 0 else 0
                })
        
        # 按成功邀请数排序
        result.sort(key=lambda x: x["successful_invites"], reverse=True)
        
        return result
    except Exception as e:
        logger.error(f"获取邀请统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取邀请统计失败: {str(e)}")


# ==================== A/B测试管理 ====================

@router.get("/experiments", response_model=List[Dict[str, Any]])
def get_all_experiments(
    status: str = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取实验列表"""
    try:
        query = db.query(Experiment)
        
        if status:
            query = query.filter(Experiment.status == status)
        
        experiments = query.all()
        
        result = []
        for exp in experiments:
            # 获取版本信息
            variants = db.query(ExperimentVariant).filter(
                ExperimentVariant.experiment_id == exp.id
            ).all()
            
            # 获取参与用户数
            from models import UserExperimentAssignment
            total_users = db.query(UserExperimentAssignment).filter(
                UserExperimentAssignment.experiment_id == exp.id
            ).count()
            
            result.append({
                "id": exp.id,
                "name": exp.name,
                "description": exp.description,
                "status": exp.status,
                "traffic_allocation": exp.traffic_allocation,
                "created_by": exp.created_by,
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
                "started_at": exp.started_at.isoformat() if exp.started_at else None,
                "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
                "variant_count": len(variants),
                "total_users": total_users
            })
        
        return result
    except Exception as e:
        logger.error(f"获取实验列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实验列表失败: {str(e)}")


@router.get("/experiments/{experiment_id}", response_model=Dict[str, Any])
def get_experiment_detail(
    experiment_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取实验详细信息"""
    try:
        exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not exp:
            raise HTTPException(status_code=404, detail="实验不存在")
        
        # 获取版本详情
        variants = db.query(ExperimentVariant).filter(
            ExperimentVariant.experiment_id == exp.id
        ).all()
        
        # 获取用户分配数据
        from models import UserExperimentAssignment, ExperimentEvent
        assignments = db.query(UserExperimentAssignment).filter(
            UserExperimentAssignment.experiment_id == exp.id
        ).all()
        
        # 统计每个版本的数据
        variant_stats = []
        for variant in variants:
            variant_users = db.query(UserExperimentAssignment).filter(
                UserExperimentAssignment.variant_id == variant.id
            ).count()
            
            # 获取事件统计
            events = db.query(ExperimentEvent).filter(
                ExperimentEvent.variant_id == variant.id
            ).all()
            
            event_stats = {}
            for event in events:
                event_type = event.event_type
                if event_type not in event_stats:
                    event_stats[event_type] = 0
                event_stats[event_type] += 1
            
            variant_stats.append({
                "id": variant.id,
                "name": variant.name,
                "traffic_weight": variant.traffic_weight,
                "config": variant.config,
                "user_count": variant_users,
                "event_stats": event_stats
            })
        
        return {
            "id": exp.id,
            "name": exp.name,
            "description": exp.description,
            "status": exp.status,
            "traffic_allocation": exp.traffic_allocation,
            "created_by": exp.created_by,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
            "started_at": exp.started_at.isoformat() if exp.started_at else None,
            "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
            "variants": variant_stats,
            "total_users": len(assignments)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实验详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实验详情失败: {str(e)}")


@router.put("/experiments/{experiment_id}/status")
def update_experiment_status(
    experiment_id: int,
    status: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """更新实验状态"""
    try:
        from services.experiment_service import ExperimentService
        
        service = ExperimentService(db)
        success = service.update_experiment_status(
            experiment_id=experiment_id,
            status=status
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="实验不存在或状态更新失败")
        
        return {"success": True, "message": "实验状态更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新实验状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新实验状态失败: {str(e)}")


# ==================== 系统日志 ====================

@router.get("/logs/system")
def get_system_logs(
    lines: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """获取系统日志（返回模拟数据，实际项目中应该读取日志文件）"""
    try:
        # 在实际项目中，这里应该读取日志文件
        # 这里返回一些模拟数据作为示例
        import datetime
        
        mock_logs = [
            {
                "timestamp": (datetime.datetime.now() - datetime.timedelta(minutes=i)).isoformat(),
                "level": "INFO" if i % 3 != 0 else "WARNING" if i % 5 != 0 else "ERROR",
                "message": f"系统运行正常 - 操作 {i}"
            }
            for i in range(lines)
        ]
        
        return mock_logs
    except Exception as e:
        logger.error(f"获取系统日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统日志失败: {str(e)}")


# ==================== 数据导出 ====================

@router.get("/export/users")
def export_users(
    format: str = "json",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """导出用户数据"""
    try:
        users = db.query(User).all()
        
        data = [
            {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "email_verified": user.email_verified,
                "email_notifications": user.email_notifications
            }
            for user in users
        ]
        
        if format == "csv":
            import csv
            import io
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return {"content": output.getvalue(), "format": "csv"}
        
        return {"content": data, "format": "json"}
    except Exception as e:
        logger.error(f"导出用户数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出用户数据失败: {str(e)}")
