#!/usr/bin/env python3
"""
邀请系统服务
- 邀请码生成、验证、统计
- 邀请奖励计算
- 与成就系统集成
"""

import sys
import os
from pathlib import Path
import secrets
import string
import hashlib
from datetime import datetime
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models import InvitationCode, UserInvitationStats, User, AchievementDefinition, UserAchievement
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)


class InvitationService:
    """邀请系统服务类"""
    
    CODE_LENGTH = 8  # 邀请码长度
    CODE_CHARS = string.ascii_uppercase + string.digits  # 邀请码字符集（大写字母+数字）
    
    # 邀请奖励配置
    INVITER_REWARD_POINTS = 20  # 邀请人获得的点数
    INVITEE_REWARD_POINTS = 10  # 被邀请人获得的点数
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_invitation_code(self, user_id: int) -> Optional[str]:
        """
        为用户生成邀请码
        
        Args:
            user_id: 生成邀请码的用户ID
            
        Returns:
            邀请码字符串，如果生成失败返回None
        """
        try:
            # 检查用户是否存在
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"用户不存在: {user_id}")
                return None
            
            # 生成唯一邀请码
            max_attempts = 10
            for attempt in range(max_attempts):
                code = self._generate_code()
                
                # 检查邀请码是否已存在
                existing = self.db.query(InvitationCode).filter(
                    InvitationCode.code == code
                ).first()
                
                if not existing:
                    # 创建邀请码记录
                    invitation = InvitationCode(
                        code=code,
                        generated_by=user_id,
                        is_used=False
                    )
                    self.db.add(invitation)
                    
                    # 更新用户邀请统计
                    self._update_invitation_stats(user_id, increment_total=True)
                    
                    self.db.commit()
                    logger.info(f"为用户 {user_id} 生成邀请码: {code}")
                    return code
            
            logger.error(f"生成邀请码失败，已尝试 {max_attempts} 次")
            return None
            
        except Exception as e:
            logger.error(f"生成邀请码失败 (用户ID: {user_id}): {str(e)}")
            self.db.rollback()
            return None
    
    def _generate_code(self) -> str:
        """生成随机邀请码"""
        # 使用更安全的随机数生成
        random_bytes = secrets.token_bytes(16)
        hash_value = hashlib.sha256(random_bytes).hexdigest()
        
        # 取前CODE_LENGTH个字符，并转换为大写字母和数字
        code = ''.join(
            self.CODE_CHARS[int(c, 16) % len(self.CODE_CHARS)]
            for c in hash_value[:self.CODE_LENGTH]
        )
        
        return code
    
    def validate_invitation_code(self, code: str) -> Tuple[bool, Optional[int], str]:
        """
        验证邀请码是否有效
        
        Args:
            code: 邀请码
            
        Returns:
            Tuple: (是否有效, 邀请人用户ID, 消息)
        """
        try:
            invitation = self.db.query(InvitationCode).filter(
                InvitationCode.code == code
            ).first()
            
            if not invitation:
                return False, None, "邀请码无效"
            
            if invitation.is_used:
                return False, None, "邀请码已被使用"
            
            return True, invitation.generated_by, "邀请码有效"
            
        except Exception as e:
            logger.error(f"验证邀请码失败: {str(e)}")
            return False, None, "验证失败，请稍后重试"
    
    def use_invitation_code(self, code: str, new_user_id: int) -> Optional[Dict]:
        """
        使用邀请码（新用户注册时调用）
        
        Args:
            code: 邀请码
            new_user_id: 新注册用户ID
            
        Returns:
            Dict: 奖励信息，包含邀请人和被邀请人获得的点数
        """
        try:
            # 验证邀请码
            is_valid, inviter_id, message = self.validate_invitation_code(code)
            if not is_valid:
                logger.warning(f"使用无效邀请码: {code}, 用户: {new_user_id}, 原因: {message}")
                return None
            
            # 检查新用户是否已使用过邀请码
            existing_use = self.db.query(InvitationCode).filter(
                InvitationCode.used_by == new_user_id
            ).first()
            
            if existing_use:
                logger.warning(f"用户 {new_user_id} 已经使用过邀请码")
                return None
            
            # 标记邀请码为已使用
            invitation = self.db.query(InvitationCode).filter(
                InvitationCode.code == code
            ).first()
            
            invitation.is_used = True
            invitation.used_by = new_user_id
            invitation.used_at = datetime.utcnow()
            
            # 更新邀请人统计
            self._update_invitation_stats(
                inviter_id,
                increment_successful=True,
                points_earned=self.INVITER_REWARD_POINTS
            )
            
            # 为被邀请人添加统计记录（如果不存在）
            self._get_or_create_invitation_stats(new_user_id)
            
            self.db.commit()
            
            logger.info(f"邀请码使用成功: {code}, 邀请人: {inviter_id}, 新用户: {new_user_id}")
            
            return {
                "inviter_id": inviter_id,
                "invitee_id": new_user_id,
                "inviter_points": self.INVITER_REWARD_POINTS,
                "invitee_points": self.INVITEE_REWARD_POINTS,
                "invitation_code": code
            }
            
        except Exception as e:
            logger.error(f"使用邀请码失败 (邀请码: {code}, 用户: {new_user_id}): {str(e)}")
            self.db.rollback()
            return None
    
    def get_user_invitation_stats(self, user_id: int) -> Optional[Dict]:
        """
        获取用户的邀请统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 邀请统计信息
        """
        try:
            stats = self.db.query(UserInvitationStats).filter(
                UserInvitationStats.user_id == user_id
            ).first()
            
            if not stats:
                return {
                    "total_invited": 0,
                    "successful_invites": 0,
                    "total_points_earned": 0,
                    "last_invited_at": None,
                    "invite_success_rate": 0.0
                }
            
            # 计算邀请成功率
            success_rate = 0.0
            if stats.total_invited > 0:
                success_rate = (stats.successful_invites / stats.total_invited) * 100
            
            return {
                "total_invited": stats.total_invited,
                "successful_invites": stats.successful_invites,
                "total_points_earned": stats.total_points_earned,
                "last_invited_at": stats.last_invited_at.isoformat() if stats.last_invited_at else None,
                "invite_success_rate": round(success_rate, 1)
            }
            
        except Exception as e:
            logger.error(f"获取邀请统计失败 (用户ID: {user_id}): {str(e)}")
            return None
    
    def get_user_invitations(self, user_id: int) -> list:
        """
        获取用户生成的所有邀请码
        
        Args:
            user_id: 用户ID
            
        Returns:
            List: 邀请码列表
        """
        try:
            invitations = self.db.query(InvitationCode).filter(
                InvitationCode.generated_by == user_id
            ).order_by(InvitationCode.created_at.desc()).all()
            
            return [
                {
                    "code": inv.code,
                    "is_used": inv.is_used,
                    "used_by": inv.used_by,
                    "created_at": inv.created_at.isoformat(),
                    "used_at": inv.used_at.isoformat() if inv.used_at else None
                }
                for inv in invitations
            ]
            
        except Exception as e:
            logger.error(f"获取用户邀请码失败 (用户ID: {user_id}): {str(e)}")
            return []
    
    def _update_invitation_stats(self, user_id: int, increment_total: bool = False,
                                 increment_successful: bool = False, points_earned: int = 0):
        """更新用户邀请统计"""
        try:
            stats = self.db.query(UserInvitationStats).filter(
                UserInvitationStats.user_id == user_id
            ).first()
            
            if not stats:
                stats = UserInvitationStats(
                    user_id=user_id,
                    total_invited=0,
                    successful_invites=0,
                    total_points_earned=0
                )
                self.db.add(stats)
            
            if increment_total:
                stats.total_invited += 1
                stats.last_invited_at = datetime.utcnow()
            
            if increment_successful:
                stats.successful_invites += 1
                stats.total_points_earned += points_earned
            
        except Exception as e:
            logger.error(f"更新邀请统计失败 (用户ID: {user_id}): {str(e)}")
            raise
    
    def _get_or_create_invitation_stats(self, user_id: int) -> UserInvitationStats:
        """获取或创建用户邀请统计记录"""
        stats = self.db.query(UserInvitationStats).filter(
            UserInvitationStats.user_id == user_id
        ).first()
        
        if not stats:
            stats = UserInvitationStats(
                user_id=user_id,
                total_invited=0,
                successful_invites=0,
                total_points_earned=0
            )
            self.db.add(stats)
        
        return stats
    
    def check_invitation_achievements(self, user_id: int):
        """
        检查并解锁邀请相关的成就
        
        Args:
            user_id: 用户ID
        """
        try:
            stats = self.get_user_invitation_stats(user_id)
            if not stats:
                return
            
            successful_invites = stats["successful_invites"]
            
            # 定义成就阈值
            achievement_thresholds = {
                "invite_first": 1,      # 首次邀请
                "invite_5": 5,          # 邀请5人
                "invite_10": 10,        # 邀请10人
                "invite_master": 20     # 邀请达人（20人）
            }
            
            # 检查每个成就
            for code, threshold in achievement_thresholds.items():
                if successful_invites >= threshold:
                    self._unlock_achievement(user_id, code)
            
        except Exception as e:
            logger.error(f"检查邀请成就失败 (用户ID: {user_id}): {str(e)}")
    
    def _unlock_achievement(self, user_id: int, achievement_code: str):
        """解锁成就"""
        try:
            # 查询成就定义
            achievement = self.db.query(AchievementDefinition).filter(
                AchievementDefinition.code == achievement_code
            ).first()
            
            if not achievement:
                logger.warning(f"成就不存在: {achievement_code}")
                return
            
            # 检查是否已解锁
            existing = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            ).first()
            
            if existing:
                return  # 已解锁，跳过
            
            # 解锁成就
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                progress_data={"unlocked_by": "invitation_system"}
            )
            self.db.add(user_achievement)
            
            logger.info(f"用户 {user_id} 解锁成就: {achievement_code}")
            
        except Exception as e:
            logger.error(f"解锁成就失败 (用户ID: {user_id}, 成就: {achievement_code}): {str(e)}")
            self.db.rollback()


def main():
    """测试邀请服务"""
    logging.basicConfig(level=logging.INFO)
    
    db = SessionLocal()
    try:
        service = InvitationService(db)
        
        # 测试生成邀请码
        logger.info("=== 测试邀请码生成 ===")
        code = service.generate_invitation_code(1)  # 假设用户1存在
        if code:
            logger.info(f"生成邀请码: {code}")
        else:
            logger.error("生成邀请码失败")
            return
        
        # 测试验证邀请码
        logger.info("\n=== 测试邀请码验证 ===")
        is_valid, inviter_id, message = service.validate_invitation_code(code)
        logger.info(f"验证结果: {is_valid}, 邀请人: {inviter_id}, 消息: {message}")
        
        # 测试获取邀请统计
        logger.info("\n=== 测试获取邀请统计 ===")
        stats = service.get_user_invitation_stats(1)
        logger.info(f"邀请统计: {stats}")
        
        # 测试获取用户邀请码列表
        logger.info("\n=== 测试获取邀请码列表 ===")
        invitations = service.get_user_invitations(1)
        logger.info(f"邀请码列表: {invitations}")
        
        logger.info("\n✅ 所有测试完成！")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
