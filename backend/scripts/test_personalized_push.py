#!/usr/bin/env python3
"""
测试个性化推送功能
验证邮件调度器是否正确读取个性化推送时间
"""

import sys
import os
from datetime import datetime

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from models import User, UserActivityLog
from scheduler import should_send_email_to_user, get_user_push_time
import pytz
from database import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_user_push_time():
    """测试获取用户推送时间功能"""
    logger.info("=== 测试获取用户推送时间 ===")
    
    db = SessionLocal()
    try:
        # 创建测试用户
        test_user = User(
            email="test_push@example.com",
            hashed_password="test_hash",
            email_notifications=True,
            is_active=True
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        # 测试1: 用户没有启用个性化推送
        logger.info("\n测试1: 用户未启用个性化推送")
        hour, minute = get_user_push_time(test_user)
        logger.info(f"结果: {hour:02d}:{minute:02d} (应使用默认时间 {settings.DAILY_UPDATE_HOUR:02d}:{settings.DAILY_UPDATE_MINUTE:02d})")
        assert hour == settings.DAILY_UPDATE_HOUR, f"期望小时 {settings.DAILY_UPDATE_HOUR}, 实际 {hour}"
        
        # 测试2: 启用个性化推送，设置推送时间为14:30
        logger.info("\n测试2: 启用个性化推送，时间设为14:30")
        test_user.email_schedule_enabled = True
        test_user.email_schedule_hour = 14
        test_user.email_schedule_minute = 30
        db.commit()
        
        hour, minute = get_user_push_time(test_user)
        logger.info(f"结果: {hour:02d}:{minute:02d}")
        assert hour == 14, f"期望小时 14, 实际 {hour}"
        assert minute == 30, f"期望分钟 30, 实际 {minute}"
        
        # 测试3: 只设置小时，分钟为None
        logger.info("\n测试3: 只设置小时，分钟为None")
        test_user.email_schedule_minute = None
        db.commit()
        
        hour, minute = get_user_push_time(test_user)
        logger.info(f"结果: {hour:02d}:{minute:02d}")
        assert hour == 14, f"期望小时 14, 实际 {hour}"
        assert minute == 0, f"期望分钟 0, 实际 {minute}"
        
        logger.info("\n✅ 所有测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        try:
            if 'test_user' in locals():
                db.delete(test_user)
                db.commit()
        except:
            pass
        db.close()


def test_should_send_email():
    """测试是否应该发送邮件的判断逻辑"""
    logger.info("\n=== 测试邮件发送判断逻辑 ===")
    
    db = SessionLocal()
    try:
        # 创建测试用户
        test_user = User(
            email="test_send@example.com",
            hashed_password="test_hash",
            email_notifications=True,
            is_active=True,
            email_schedule_enabled=True,
            email_schedule_hour=10,
            email_schedule_minute=0
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        # 获取时区
        tz = pytz.timezone(settings.TIMEZONE)
        
        # 测试1: 当前时间匹配推送时间
        logger.info("\n测试1: 当前时间匹配推送时间（10:05）")
        current_time = datetime.now(tz).replace(hour=10, minute=5, second=0, microsecond=0)
        should_send = should_send_email_to_user(test_user, current_time)
        logger.info(f"结果: {should_send} (期望: True)")
        
        # 测试2: 当前小时匹配但分钟不匹配
        logger.info("\n测试2: 当前小时匹配但分钟不匹配（10:15，窗口为10:00-10:09）")
        current_time = datetime.now(tz).replace(hour=10, minute=15, second=0, microsecond=0)
        should_send = should_send_email_to_user(test_user, current_time)
        logger.info(f"结果: {should_send} (期望: False)")
        
        # 测试3: 当前时间完全不匹配
        logger.info("\n测试3: 当前时间完全不匹配（14:05）")
        current_time = datetime.now(tz).replace(hour=14, minute=5, second=0, microsecond=0)
        should_send = should_send_email_to_user(test_user, current_time)
        logger.info(f"结果: {should_send} (期望: False)")
        
        # 测试4: 用户禁用邮件通知
        logger.info("\n测试4: 用户禁用邮件通知")
        test_user.email_notifications = False
        db.commit()
        
        current_time = datetime.now(tz).replace(hour=10, minute=5, second=0, microsecond=0)
        should_send = should_send_email_to_user(test_user, current_time)
        logger.info(f"结果: {should_send} (期望: False)")
        
        logger.info("\n✅ 所有测试通过！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试数据
        try:
            if 'test_user' in locals():
                db.delete(test_user)
                db.commit()
        except:
            pass
        db.close()


def test_with_real_users():
    """使用真实用户数据测试"""
    logger.info("\n=== 使用真实用户数据测试 ===")
    
    db = SessionLocal()
    try:
        # 查询有活动记录的用户
        users_with_activity = db.query(UserActivityLog.user_id).distinct().limit(5).all()
        
        if not users_with_activity:
            logger.info("数据库中没有用户活动记录，跳过此测试")
            return True
        
        tz = pytz.timezone(settings.TIMEZONE)
        current_time = datetime.now(tz)
        
        logger.info(f"查询到 {len(users_with_activity)} 个有活动记录的用户")
        logger.info(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        for user_tuple in users_with_activity:
            user_id = user_tuple[0]
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user or not user.email_notifications:
                continue
            
            logger.info(f"\n用户 {user_id} ({user.email}):")
            
            # 获取推送时间
            hour, minute = get_user_push_time(user)
            schedule_type = "个性化" if user.email_schedule_enabled else "默认"
            logger.info(f"  - 推送类型: {schedule_type}")
            logger.info(f"  - 推送时间: {hour:02d}:{minute:02d}")
            
            # 检查是否应该发送邮件
            should_send = should_send_email_to_user(user, current_time)
            logger.info(f"  - 是否应发送: {should_send}")
        
        logger.info("\n✅ 真实用户测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("开始测试个性化推送功能")
    logger.info("=" * 60)
    
    all_passed = True
    
    # 运行测试
    all_passed &= test_user_push_time()
    all_passed &= test_should_send_email()
    all_passed &= test_with_real_users()
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ 所有测试通过！个性化推送功能正常工作")
    else:
        logger.error("❌ 部分测试失败，请检查日志")
    logger.info("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
