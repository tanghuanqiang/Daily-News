#!/usr/bin/env python3
"""
测试邀请系统完整流程
- 邀请码生成
- 邀请码验证
- 邀请码使用
- 邀请统计
- 成就解锁
"""

import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import User, InvitationCode, UserInvitationStats, AchievementDefinition
from services.invitation_service import InvitationService
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_test_data(db):
    """设置测试数据"""
    logger.info("=== 设置测试数据 ===")
    
    # 创建测试用户（如果还不存在）
    inviter = db.query(User).filter(User.email == "inviter@example.com").first()
    if not inviter:
        inviter = User(
            email="inviter@example.com",
            hashed_password="test_hash",
            email_notifications=True,
            is_active=True
        )
        db.add(inviter)
        db.commit()
        db.refresh(inviter)
        logger.info(f"创建邀请人用户: ID={inviter.id}, email={inviter.email}")
    else:
        logger.info(f"使用现有邀请人用户: ID={inviter.id}, email={inviter.email}")
    
    # 为测试清理之前的邀请码
    db.query(InvitationCode).filter(InvitationCode.generated_by == inviter.id).delete()
    db.commit()
    
    return inviter


def test_generate_invitations(service, inviter_id):
    """测试生成多个邀请码"""
    logger.info("\n=== 测试生成邀请码 ===")
    
    codes = []
    for i in range(3):
        code = service.generate_invitation_code(inviter_id)
        if code:
            codes.append(code)
            logger.info(f"生成邀请码 {i+1}: {code}")
        else:
            logger.error(f"生成邀请码 {i+1} 失败")
    
    assert len(codes) == 3, f"期望生成3个邀请码，实际生成 {len(codes)} 个"
    
    # 验证统计
    stats = service.get_user_invitation_stats(inviter_id)
    logger.info(f"\n邀请统计: {stats}")
    assert stats["total_invited"] == 3, f"期望总邀请数为3，实际为 {stats['total_invited']}"
    
    return codes


def test_validate_invitations(service, codes):
    """测试验证邀请码"""
    logger.info("\n=== 测试验证邀请码 ===")
    
    # 测试有效邀请码
    for code in codes:
        is_valid, inviter_id, message = service.validate_invitation_code(code)
        logger.info(f"验证邀请码 {code}: 有效={is_valid}, 邀请人={inviter_id}, 消息={message}")
        assert is_valid, f"邀请码 {code} 应该有效"
    
    # 测试无效邀请码
    is_valid, inviter_id, message = service.validate_invitation_code("INVALID12")
    logger.info(f"\n验证无效邀请码 INVALID12: 有效={is_valid}, 消息={message}")
    assert not is_valid, "无效邀请码应该验证失败"
    
    logger.info("\n✅ 验证测试通过")


def test_use_invitation(service, db, inviter_id, invitation_code):
    """测试使用邀请码"""
    logger.info("\n=== 测试使用邀请码 ===")
    
    # 创建被邀请用户
    invitee = User(
        email="invitee@example.com",
        hashed_password="test_hash",
        email_notifications=True,
        is_active=True
    )
    db.add(invitee)
    db.commit()
    db.refresh(invitee)
    logger.info(f"创建被邀请用户: ID={invitee.id}, email={invitee.email}")
    
    # 使用邀请码
    reward = service.use_invitation_code(invitation_code, invitee.id)
    logger.info(f"使用邀请码结果: {reward}")
    
    assert reward is not None, "使用邀请码应该成功"
    assert reward["inviter_id"] == inviter_id, "邀请人ID应该匹配"
    assert reward["invitee_id"] == invitee.id, "被邀请人ID应该匹配"
    assert reward["inviter_points"] == 20, "邀请人应该获得20点数"
    assert reward["invitee_points"] == 10, "被邀请人应该获得10点数"
    
    # 验证邀请码状态
    db.refresh(db.query(InvitationCode).filter(InvitationCode.code == invitation_code).first())
    invitation = db.query(InvitationCode).filter(InvitationCode.code == invitation_code).first()
    assert invitation.is_used, "邀请码应该标记为已使用"
    assert invitation.used_by == invitee.id, "邀请码应该记录使用人"
    assert invitation.used_at is not None, "邀请码应该记录使用时间"
    
    # 验证统计更新
    stats = service.get_user_invitation_stats(inviter_id)
    logger.info(f"\n使用后邀请统计: {stats}")
    assert stats["successful_invites"] == 1, "成功邀请数应该为1"
    assert stats["total_points_earned"] == 20, "邀请人应该获得20点数"
    assert stats["invite_success_rate"] == 33.3, "邀请成功率应该约为33.3%"
    
    logger.info("\n✅ 使用邀请码测试通过")
    
    return invitee


def test_duplicate_use(service, invitee_id, invitation_code):
    """测试重复使用的防护"""
    logger.info("\n=== 测试重复使用的防护 ===")
    
    # 尝试重复使用邀请码
    reward = service.use_invitation_code(invitation_code, invitee_id)
    logger.info(f"重复使用邀请码结果: {reward}")
    
    assert reward is None, "重复使用邀请码应该失败"
    
    logger.info("\n✅ 重复使用防护测试通过")


def test_multiple_invites(service, db, inviter_id):
    """测试多个邀请的使用"""
    logger.info("\n=== 测试多个邀请的使用 ===")
    
    # 生成更多邀请码
    codes = []
    for i in range(2):
        code = service.generate_invitation_code(inviter_id)
        codes.append(code)
        logger.info(f"生成邀请码: {code}")
    
    # 创建更多被邀请用户
    for i, code in enumerate(codes):
        invitee = User(
            email=f"invitee{i+2}@example.com",
            hashed_password="test_hash",
            email_notifications=True,
            is_active=True
        )
        db.add(invitee)
        db.commit()
        db.refresh(invitee)
        
        # 使用邀请码
        reward = service.use_invitation_code(code, invitee.id)
        logger.info(f"用户 {invitee.id} 使用邀请码 {code}: {reward is not None}")
        assert reward is not None, f"邀请码 {code} 应该使用成功"
    
    # 验证统计
    stats = service.get_user_invitation_stats(inviter_id)
    logger.info(f"\n最终邀请统计: {stats}")
    assert stats["total_invited"] == 5, "总邀请数应该为5"
    assert stats["successful_invites"] == 3, "成功邀请数应该为3"
    assert stats["total_points_earned"] == 60, "总获得点数应该为60"
    
    logger.info("\n✅ 多个邀请测试通过")


def test_achievements(service, inviter_id):
    """测试成就解锁"""
    logger.info("\n=== 测试成就解锁 ===")
    
    # 检查并尝试解锁成就
    service.check_invitation_achievements(inviter_id)
    
    # 验证成就解锁（需要查询数据库）
    db = SessionLocal()
    try:
        # 检查 invite_first 成就（1次成功邀请）
        achievement = db.query(AchievementDefinition).filter(
            AchievementDefinition.code == "invite_first"
        ).first()
        
        if achievement:
            from models import UserAchievement
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == inviter_id,
                UserAchievement.achievement_id == achievement.id
            ).first()
            
            if user_achievement:
                logger.info(f"✅ 用户 {inviter_id} 已解锁成就: invite_first")
            else:
                logger.info(f"ℹ️  用户 {inviter_id} 尚未解锁 invite_first 成就")
        
        # 检查 invite_5 成就（5次成功邀请）
        achievement = db.query(AchievementDefinition).filter(
            AchievementDefinition.code == "invite_5"
        ).first()
        
        if achievement:
            user_achievement = db.query(UserAchievement).filter(
                UserAchievement.user_id == inviter_id,
                UserAchievement.achievement_id == achievement.id
            ).first()
            
            if user_achievement:
                logger.info(f"✅ 用户 {inviter_id} 已解锁成就: invite_5")
            else:
                logger.info(f"ℹ️  用户 {inviter_id} 尚未解锁 invite_5 成就（需要5次成功邀请）")
        
    finally:
        db.close()
    
    logger.info("\n✅ 成就解锁测试完成")


def cleanup_test_data(db, inviter_id):
    """清理测试数据"""
    logger.info("\n=== 清理测试数据 ===")
    
    # 删除测试生成的邀请码
    deleted_invitations = db.query(InvitationCode).filter(
        InvitationCode.generated_by == inviter_id
    ).delete()
    logger.info(f"删除邀请码记录: {deleted_invitations} 条")
    
    # 删除测试用户的邀请统计
    deleted_stats = db.query(UserInvitationStats).filter(
        UserInvitationStats.user_id == inviter_id
    ).delete()
    logger.info(f"删除邀请统计: {deleted_stats} 条")
    
    # 删除测试用户
    db.query(User).filter(User.email.like("invitee%@example.com")).delete()
    db.query(User).filter(User.email == "inviter@example.com").delete()
    
    db.commit()
    logger.info("测试数据清理完成")


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("开始测试邀请系统完整流程")
    logger.info("=" * 60)
    
    db = SessionLocal()
    service = InvitationService(db)
    
    try:
        # 1. 设置测试数据
        inviter = setup_test_data(db)
        
        # 2. 测试生成邀请码
        codes = test_generate_invitations(service, inviter.id)
        
        # 3. 测试验证邀请码
        test_validate_invitations(service, codes)
        
        # 4. 测试使用邀请码
        invitee = test_use_invitation(service, db, inviter.id, codes[0])
        
        # 5. 测试重复使用的防护
        test_duplicate_use(service, invitee.id, codes[0])
        
        # 6. 测试多个邀请的使用
        test_multiple_invites(service, db, inviter.id)
        
        # 7. 测试成就解锁
        test_achievements(service, inviter.id)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有测试通过！邀请系统工作正常")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        cleanup_test_data(db, inviter.id)
        db.close()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
