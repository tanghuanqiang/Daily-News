from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from database import get_db
from models import (
    User,
    Experiment,
    ExperimentVariant,
    ExperimentCreate,
    ExperimentResponse,
    ExperimentVariantCreate,
    ExperimentVariantResponse,
    ExperimentAssignmentResponse,
    ExperimentReport
)
from auth import get_current_active_user
from services.experiment_service import ExperimentService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])


@router.post("/", response_model=ExperimentResponse)
async def create_experiment(
    experiment_data: ExperimentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建实验（管理员功能）
    
    Args:
        experiment_data: 实验数据（名称、描述、流量分配）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        创建的实验信息
    """
    try:
        service = ExperimentService(db)
        
        experiment_id = service.create_experiment(
            name=experiment_data.name,
            description=experiment_data.description,
            traffic_allocation=experiment_data.traffic_allocation,
            created_by=current_user.id
        )
        
        if not experiment_id:
            raise HTTPException(
                status_code=400,
                detail="创建实验失败，实验名称可能已存在"
            )
        
        # 查询创建的实验
        experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        
        return experiment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建实验失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建实验失败: {str(e)}"
        )


@router.post("/variants", response_model=ExperimentVariantResponse)
async def create_experiment_variant(
    variant_data: ExperimentVariantCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    创建实验版本（管理员功能）
    
    Args:
        variant_data: 版本数据（实验ID、名称、权重、配置）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        创建的版本信息
    """
    try:
        service = ExperimentService(db)
        
        variant_id = service.create_experiment_variant(
            experiment_id=variant_data.experiment_id,
            name=variant_data.name,
            traffic_weight=variant_data.traffic_weight,
            config=variant_data.config,
            description=variant_data.description
        )
        
        if not variant_id:
            raise HTTPException(
                status_code=400,
                detail="创建实验版本失败，版本名称可能已存在或实验不存在"
            )
        
        # 查询创建的版本
        variant = db.query(ExperimentVariant).filter(ExperimentVariant.id == variant_id).first()
        
        return variant
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建实验版本失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"创建实验版本失败: {str(e)}"
        )


@router.get("/my-assignment/{experiment_name}", response_model=ExperimentAssignmentResponse)
async def get_my_experiment_assignment(
    experiment_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取当前用户在指定实验中的分配版本（前端调用）
    
    Args:
        experiment_name: 实验名称
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        分配的实验版本信息
    """
    try:
        service = ExperimentService(db)
        
        variant = service.get_experiment_variant(
            user_id=current_user.id,
            experiment_name=experiment_name
        )
        
        if not variant:
            # 如果未分配到版本，返回默认响应
            return {
                "user_id": current_user.id,
                "experiment_id": 0,
                "variant_id": 0,
                "variant_name": "default",
                "variant_config": {},
                "assigned_at": None
            }
        
        # 查询分配记录
        assignment = db.query(UserExperimentAssignment).filter(
            UserExperimentAssignment.user_id == current_user.id,
            UserExperimentAssignment.variant_id == variant["id"]
        ).first()
        
        return {
            "user_id": current_user.id,
            "experiment_id": assignment.experiment_id if assignment else 0,
            "variant_id": variant["id"],
            "variant_name": variant["name"],
            "variant_config": variant["config"],
            "assigned_at": assignment.assigned_at if assignment else None
        }
        
    except Exception as e:
        logger.error(f"获取实验分配失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取实验分配失败: {str(e)}"
        )


@router.post("/track-event/{experiment_name}")
async def track_experiment_event(
    experiment_name: str,
    event_type: str,
    event_data: Optional[Dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    跟踪实验事件（前端调用）
    
    Args:
        experiment_name: 实验名称
        event_type: 事件类型（view, click, conversion等）
        event_data: 事件数据
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        成功消息
    """
    try:
        service = ExperimentService(db)
        
        success = service.track_experiment_event(
            user_id=current_user.id,
            experiment_name=experiment_name,
            event_type=event_type,
            event_data=event_data or {}
        )
        
        if success:
            return {"message": "事件跟踪成功"}
        else:
            return {"message": "事件跟踪失败，实验未运行或用户未分配"}
        
    except Exception as e:
        logger.error(f"跟踪实验事件失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"跟踪实验事件失败: {str(e)}"
        )


@router.get("/report/{experiment_name}", response_model=ExperimentReport)
async def get_experiment_report(
    experiment_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取实验报告（管理员功能）
    
    Args:
        experiment_name: 实验名称
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        完整的实验报告
    """
    try:
        service = ExperimentService(db)
        
        report = service.get_experiment_report(experiment_name)
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail="实验不存在或报告生成失败"
            )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实验报告失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取实验报告失败: {str(e)}"
        )


@router.put("/status/{experiment_name}")
async def update_experiment_status(
    experiment_name: str,
    status: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新实验状态（管理员功能）
    
    Args:
        experiment_name: 实验名称
        status: 新状态（draft, running, paused, completed）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        成功消息
    """
    try:
        # 验证状态
        valid_statuses = ["draft", "running", "paused", "completed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"无效的状态。必须是: {', '.join(valid_statuses)}"
            )
        
        service = ExperimentService(db)
        
        success = service.update_experiment_status(experiment_name, status)
        
        if success:
            return {"message": f"实验状态已更新为: {status}"}
        else:
            raise HTTPException(
                status_code=400,
                detail="更新实验状态失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新实验状态失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"更新实验状态失败: {str(e)}"
        )


@router.get("/list", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    获取实验列表（管理员功能）
    
    Args:
        status: 可选的状态筛选
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        实验列表
    """
    try:
        query = db.query(Experiment)
        
        # 如果指定了状态，添加筛选条件
        if status:
            valid_statuses = ["draft", "running", "paused", "completed"]
            if status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的状态。必须是: {', '.join(valid_statuses)}"
                )
            query = query.filter(Experiment.status == status)
        
        # 按创建时间倒序排列
        experiments = query.order_by(Experiment.created_at.desc()).all()
        
        return experiments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实验列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取实验列表失败: {str(e)}"
        )
