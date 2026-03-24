#!/usr/bin/env python3
"""
A/B测试平台服务
- 实验分流算法（一致性哈希）
- 实验配置管理
- 结果统计和显著性检验
"""

import sys
import os
from pathlib import Path
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import json

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models import Experiment, ExperimentVariant, UserExperimentAssignment, ExperimentResult, ExperimentEvent, User
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class ExperimentService:
    """A/B测试平台服务类"""
    
    # 显著性检验阈值
    SIGNIFICANCE_THRESHOLD = 0.05  # p-value < 0.05 认为显著
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_experiment(self, name: str, description: Optional[str] = None,
                         traffic_allocation: float = 1.0, created_by: int = 1) -> Optional[int]:
        """
        创建实验
        
        Args:
            name: 实验名称（唯一）
            description: 实验描述
            traffic_allocation: 流量分配（0-1）
            created_by: 创建者ID
            
        Returns:
            实验ID，如果创建失败返回None
        """
        try:
            # 检查实验名称是否已存在
            existing = self.db.query(Experiment).filter(
                Experiment.name == name
            ).first()
            
            if existing:
                logger.error(f"实验名称已存在: {name}")
                return None
            
            # 创建实验
            experiment = Experiment(
                name=name,
                description=description,
                status="draft",
                traffic_allocation=traffic_allocation,
                created_by=created_by
            )
            self.db.add(experiment)
            self.db.commit()
            self.db.refresh(experiment)
            
            logger.info(f"创建实验成功: ID={experiment.id}, name={name}")
            return experiment.id
            
        except Exception as e:
            logger.error(f"创建实验失败: {str(e)}")
            self.db.rollback()
            return None
    
    def create_experiment_variant(self, experiment_id: int, name: str,
                                 traffic_weight: float, config: Dict,
                                 description: Optional[str] = None) -> Optional[int]:
        """
        创建实验版本
        
        Args:
            experiment_id: 实验ID
            name: 版本名称（如 "control", "treatment"）
            traffic_weight: 流量权重
            config: 版本配置（JSON）
            description: 版本描述
            
        Returns:
            版本ID，如果创建失败返回None
        """
        try:
            # 检查实验是否存在
            experiment = self.db.query(Experiment).filter(
                Experiment.id == experiment_id
            ).first()
            
            if not experiment:
                logger.error(f"实验不存在: {experiment_id}")
                return None
            
            # 检查同一实验下版本名称是否已存在
            existing = self.db.query(ExperimentVariant).filter(
                ExperimentVariant.experiment_id == experiment_id,
                ExperimentVariant.name == name
            ).first()
            
            if existing:
                logger.error(f"版本名称已存在: {name} (实验ID: {experiment_id})")
                return None
            
            # 创建版本
            variant = ExperimentVariant(
                experiment_id=experiment_id,
                name=name,
                description=description,
                traffic_weight=traffic_weight,
                config=config
            )
            self.db.add(variant)
            self.db.commit()
            self.db.refresh(variant)
            
            logger.info(f"创建实验版本成功: ID={variant.id}, experiment_id={experiment_id}, name={name}")
            return variant.id
            
        except Exception as e:
            logger.error(f"创建实验版本失败: {str(e)}")
            self.db.rollback()
            return None
    
    def get_experiment_variant(self, user_id: int, experiment_name: str) -> Optional[Dict]:
        """
        获取用户被分配到的实验版本（核心分流算法）
        
        Args:
            user_id: 用户ID
            experiment_name: 实验名称
            
        Returns:
            Dict: 版本信息（id, name, config），如果未分配返回None
        """
        try:
            # 查询实验
            experiment = self.db.query(Experiment).filter(
                Experiment.name == experiment_name
            ).first()
            
            if not experiment:
                logger.warning(f"实验不存在: {experiment_name}")
                return None
            
            # 检查实验状态
            if experiment.status != "running":
                logger.debug(f"实验未运行: {experiment_name} (状态: {experiment.status})")
                return None
            
            # 检查用户是否已分配
            assignment = self.db.query(UserExperimentAssignment).filter(
                UserExperimentAssignment.user_id == user_id,
                UserExperimentAssignment.experiment_id == experiment.id
            ).first()
            
            if assignment:
                # 已分配，直接返回版本信息
                variant = self.db.query(ExperimentVariant).filter(
                    ExperimentVariant.id == assignment.variant_id
                ).first()
                
                if variant:
                    logger.debug(f"用户 {user_id} 已分配到实验 {experiment_name} 的版本 {variant.name}")
                    return {
                        "id": variant.id,
                        "name": variant.name,
                        "config": variant.config
                    }
                else:
                    logger.error(f"版本不存在: {assignment.variant_id}")
                    return None
            
            # 未分配，进行分流
            return self._assign_user_to_variant(user_id, experiment)
            
        except Exception as e:
            logger.error(f"获取实验版本失败 (用户ID: {user_id}, 实验: {experiment_name}): {str(e)}")
            return None
    
    def _assign_user_to_variant(self, user_id: int, experiment: Experiment) -> Optional[Dict]:
        """
        将用户分配到实验版本（一致性哈希算法）
        
        Args:
            user_id: 用户ID
            experiment: 实验对象
            
        Returns:
            Dict: 版本信息
        """
        try:
            # 获取实验的所有版本
            variants = self.db.query(ExperimentVariant).filter(
                ExperimentVariant.experiment_id == experiment.id
            ).all()
            
            if not variants:
                logger.error(f"实验没有配置版本: {experiment.name}")
                return None
            
            # 计算总权重
            total_weight = sum(v.traffic_weight for v in variants)
            if total_weight <= 0:
                logger.error(f"实验版本权重配置错误: {experiment.name}")
                return None
            
            # 使用一致性哈希算法（基于用户ID和实验名称）
            hash_input = f"{user_id}:{experiment.name}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            
            # 计算哈希位置（0-99）
            hash_position = hash_value % 100
            
            # 根据权重分配版本
            current_position = 0
            for variant in variants:
                weight_percentage = (variant.traffic_weight / total_weight) * 100
                
                if hash_position < current_position + weight_percentage:
                    # 分配到该版本
                    return self._save_assignment(user_id, experiment.id, variant)
                
                current_position += weight_percentage
            
            # 默认分配到第一个版本
            logger.warning(f"用户 {user_id} 未分配到任何版本，默认分配到第一个版本")
            return self._save_assignment(user_id, experiment.id, variants[0])
            
        except Exception as e:
            logger.error(f"分配用户到版本失败: {str(e)}")
            return None
    
    def _save_assignment(self, user_id: int, experiment_id: int, variant) -> Dict:
        """
        保存用户实验分配
        
        Args:
            user_id: 用户ID
            experiment_id: 实验ID
            variant: 版本对象
            
        Returns:
            Dict: 版本信息
        """
        try:
            # 保存分配记录
            assignment = UserExperimentAssignment(
                user_id=user_id,
                experiment_id=experiment_id,
                variant_id=variant.id
            )
            self.db.add(assignment)
            self.db.commit()
            
            logger.info(f"用户 {user_id} 分配到实验 {experiment_id} 的版本 {variant.name}")
            
            return {
                "id": variant.id,
                "name": variant.name,
                "config": variant.config
            }
            
        except Exception as e:
            logger.error(f"保存分配记录失败: {str(e)}")
            self.db.rollback()
            return {
                "id": variant.id,
                "name": variant.name,
                "config": variant.config
            }
    
    def track_experiment_event(self, user_id: int, experiment_name: str,
                              event_type: str, event_data: Dict = None) -> bool:
        """
        跟踪实验事件（如页面浏览、点击、转化等）
        
        Args:
            user_id: 用户ID
            experiment_name: 实验名称
            event_type: 事件类型
            event_data: 事件数据
            
        Returns:
            bool: 是否跟踪成功
        """
        try:
            # 查询实验
            experiment = self.db.query(Experiment).filter(
                Experiment.name == experiment_name
            ).first()
            
            if not experiment:
                logger.warning(f"实验不存在: {experiment_name}")
                return False
            
            # 获取用户分配的版本
            assignment = self.db.query(UserExperimentAssignment).filter(
                UserExperimentAssignment.user_id == user_id,
                UserExperimentAssignment.experiment_id == experiment.id
            ).first()
            
            if not assignment:
                logger.debug(f"用户 {user_id} 未参与实验 {experiment_name}")
                return False
            
            # 记录事件
            event = ExperimentEvent(
                user_id=user_id,
                experiment_id=experiment.id,
                variant_id=assignment.variant_id,
                event_type=event_type,
                event_data=event_data or {}
            )
            self.db.add(event)
            self.db.commit()
            
            logger.debug(f"记录实验事件: 用户 {user_id}, 实验 {experiment_name}, 事件 {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"跟踪实验事件失败: {str(e)}")
            self.db.rollback()
            return False
    
    def calculate_experiment_results(self, experiment_name: str) -> Optional[List[Dict]]:
        """
        计算实验结果
        
        Args:
            experiment_name: 实验名称
            
        Returns:
            List[Dict]: 各版本的指标统计
        """
        try:
            # 查询实验
            experiment = self.db.query(Experiment).filter(
                Experiment.name == experiment_name
            ).first()
            
            if not experiment:
                logger.error(f"实验不存在: {experiment_name}")
                return None
            
            # 查询实验的所有版本
            variants = self.db.query(ExperimentVariant).filter(
                ExperimentVariant.experiment_id == experiment.id
            ).all()
            
            if not variants:
                logger.error(f"实验没有配置版本: {experiment_name}")
                return None
            
            results = []
            
            # 为每个版本计算指标
            for variant in variants:
                # 查询分配到该版本的用户数
                user_count = self.db.query(UserExperimentAssignment).filter(
                    UserExperimentAssignment.experiment_id == experiment.id,
                    UserExperimentAssignment.variant_id == variant.id
                ).count()
                
                # 查询该版本的事件统计
                # 计算转化率（假设 event_type = 'conversion'）
                total_events = self.db.query(ExperimentEvent).filter(
                    ExperimentEvent.experiment_id == experiment.id,
                    ExperimentEvent.variant_id == variant.id
                ).count()
                
                conversion_events = self.db.query(ExperimentEvent).filter(
                    ExperimentEvent.experiment_id == experiment.id,
                    ExperimentEvent.variant_id == variant.id,
                    ExperimentEvent.event_type == "conversion"
                ).count()
                
                # 计算转化率
                conversion_rate = 0.0
                if user_count > 0:
                    conversion_rate = (conversion_events / user_count) * 100
                
                results.append({
                    "variant_id": variant.id,
                    "variant_name": variant.name,
                    "user_count": user_count,
                    "total_events": total_events,
                    "conversion_events": conversion_events,
                    "conversion_rate": round(conversion_rate, 2)
                })
            
            logger.info(f"计算实验结果完成: {experiment_name}")
            return results
            
        except Exception as e:
            logger.error(f"计算实验结果失败: {str(e)}")
            return None
    
    def update_experiment_status(self, experiment_name: str, status: str) -> bool:
        """
        更新实验状态
        
        Args:
            experiment_name: 实验名称
            status: 新状态（draft, running, paused, completed）
            
        Returns:
            bool: 是否更新成功
        """
        try:
            experiment = self.db.query(Experiment).filter(
                Experiment.name == experiment_name
            ).first()
            
            if not experiment:
                logger.error(f"实验不存在: {experiment_name}")
                return False
            
            # 更新状态
            experiment.status = status
            
            # 如果是开始运行，记录开始时间
            if status == "running" and not experiment.started_at:
                experiment.started_at = datetime.utcnow()
            
            # 如果是完成，记录完成时间
            if status == "completed" and not experiment.completed_at:
                experiment.completed_at = datetime.utcnow()
            
            experiment.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"更新实验状态: {experiment_name} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新实验状态失败: {str(e)}")
            self.db.rollback()
            return False
    
    def get_experiment_report(self, experiment_name: str) -> Optional[Dict]:
        """
        获取实验报告
        
        Args:
            experiment_name: 实验名称
            
        Returns:
            Dict: 完整的实验报告
        """
        try:
            # 查询实验
            experiment = self.db.query(Experiment).filter(
                Experiment.name == experiment_name
            ).first()
            
            if not experiment:
                logger.error(f"实验不存在: {experiment_name}")
                return None
            
            # 查询实验版本
            variants = self.db.query(ExperimentVariant).filter(
                ExperimentVariant.experiment_id == experiment.id
            ).all()
            
            # 计算结果
            results = self.calculate_experiment_results(experiment_name)
            
            # 查询总参与用户数
            total_users = self.db.query(UserExperimentAssignment).filter(
                UserExperimentAssignment.experiment_id == experiment.id
            ).count()
            
            return {
                "experiment": {
                    "id": experiment.id,
                    "name": experiment.name,
                    "description": experiment.description,
                    "status": experiment.status,
                    "traffic_allocation": experiment.traffic_allocation,
                    "created_at": experiment.created_at.isoformat(),
                    "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
                    "completed_at": experiment.completed_at.isoformat() if experiment.completed_at else None
                },
                "variants": [
                    {
                        "id": v.id,
                        "name": v.name,
                        "description": v.description,
                        "traffic_weight": v.traffic_weight,
                        "config": v.config
                    }
                    for v in variants
                ],
                "results": results,
                "total_users": total_users
            }
            
        except Exception as e:
            logger.error(f"获取实验报告失败: {str(e)}")
            return None


def main():
    """测试实验服务"""
    logging.basicConfig(level=logging.INFO)
    
    db = SessionLocal()
    try:
        service = ExperimentService(db)
        
        # 测试创建实验
        logger.info("=== 测试创建实验 ===")
        experiment_id = service.create_experiment(
            name="ui_optimization_test",
            description="UI优化测试：按钮颜色对点击率的影响",
            traffic_allocation=1.0,
            created_by=1
        )
        
        if not experiment_id:
            logger.error("创建实验失败")
            return
        
        # 测试创建版本
        logger.info("\n=== 测试创建实验版本 ===")
        control_id = service.create_experiment_variant(
            experiment_id=experiment_id,
            name="control",
            traffic_weight=0.5,
            config={
                "button_color": "blue",
                "button_text": "点击我"
            },
            description="对照组：蓝色按钮"
        )
        
        treatment_id = service.create_experiment_variant(
            experiment_id=experiment_id,
            name="treatment",
            traffic_weight=0.5,
            config={
                "button_color": "red",
                "button_text": "立即点击"
            },
            description="实验组：红色按钮"
        )
        
        if not control_id or not treatment_id:
            logger.error("创建实验版本失败")
            return
        
        # 启动实验
        logger.info("\n=== 测试启动实验 ===")
        service.update_experiment_status("ui_optimization_test", "running")
        
        # 测试用户分配
        logger.info("\n=== 测试用户分配 ===")
        for user_id in range(1, 6):
            variant = service.get_experiment_variant(user_id, "ui_optimization_test")
            if variant:
                logger.info(f"用户 {user_id} 分配到版本: {variant['name']}")
        
        # 测试事件跟踪
        logger.info("\n=== 测试事件跟踪 ===")
        service.track_experiment_event(1, "ui_optimization_test", "view")
        service.track_experiment_event(1, "ui_optimization_test", "click")
        service.track_experiment_event(2, "ui_optimization_test", "view")
        service.track_experiment_event(3, "ui_optimization_test", "view")
        service.track_experiment_event(3, "ui_optimization_test", "conversion")
        
        # 计算结果
        logger.info("\n=== 测试计算实验结果 ===")
        results = service.calculate_experiment_results("ui_optimization_test")
        if results:
            for result in results:
                logger.info(f"版本 {result['variant_name']}: "
                           f"用户数={result['user_count']}, "
                           f"转化率={result['conversion_rate']}%")
        
        # 获取实验报告
        logger.info("\n=== 测试获取实验报告 ===")
        report = service.get_experiment_report("ui_optimization_test")
        if report:
            logger.info(f"实验报告: {json.dumps(report, indent=2, ensure_ascii=False)}")
        
        logger.info("\n✅ 所有测试完成！")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
