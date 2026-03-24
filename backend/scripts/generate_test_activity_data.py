#!/usr/bin/env python3
"""
生成测试用户活动数据
用于测试推送时间分析功能
"""

import sys
import os
from datetime import datetime, timedelta
import random

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from models import UserActivityLog, User
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_test_activity(user_id: int, days: int = 7):
    """
    为指定用户生成测试活动数据
    
    Args:
        user_id: 用户ID
        days: 生成过去多少天的数据
    """
    db = SessionLocal()
    
    try:
        logger.info(f"为用户 {user_id} 生成测试活动数据（过去 {days} 天）...")
        
        # 检查用户是否存在
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"用户 {user_id} 不存在")
            return False
        
        # 定义活动类型
        activity_types = ['login', 'read', 'share', 'feedback']
        
        # 生成每天的活动记录
        activities_created = 0
        
        for day_offset in range(days):
            # 计算日期
            current_time = datetime.utcnow() - timedelta(days=day_offset)
            
            # 每天生成 3-8 次活动
            daily_activities = random.randint(3, 8)
            
            for _ in range(daily_activities):
                # 随机选择活动时间（集中在某个时间段）
                # 模拟用户习惯：70%概率在固定时间段（比如上午9-11点）
                if random.random() < 0.7:
                    # 固定时间段（上午9-11点）
                    hour = random.randint(9, 11)
                else:
                    # 其他随机时间
                    hour = random.randint(0, 23)
                
                # 随机分钟
                minute = random.randint(0, 59)
                
                # 设置活动时间
                activity_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # 随机选择活动类型
                activity_type = random.choice(activity_types)
                
                # 创建活动记录
                log = UserActivityLog(
                    user_id=user_id,
                    activity_type=activity_type,
                    activity_time=activity_time,
                    hour_of_day=hour,
                    day_of_week=activity_time.weekday(),
                    extra_data={
                        "generated": True,
                        "source": "test_script",
                        "activity_index": activities_created + 1
                    }
                )
                
                db.add(log)
                activities_created += 1
        
        db.commit()
        logger.info(f"成功为用户 {user_id} 创建 {activities_created} 条测试活动记录")
        return True
        
    except Exception as e:
        logger.error(f"生成测试数据失败: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


def generate_for_all_users():
    """为所有用户生成测试数据"""
    db = SessionLocal()
    
    try:
        # 获取所有用户
        users = db.query(User).all()
        
        if not users:
            logger.warning("数据库中没有用户")
            return
        
        logger.info(f"为所有 {len(users)} 个用户生成测试活动数据...")
        
        success_count = 0
        
        for user in users:
            if generate_test_activity(user.id, days=7):
                success_count += 1
        
        logger.info(f"完成！为 {success_count}/{len(users)} 个用户生成测试数据")
        
    finally:
        db.close()


def clear_test_data():
    """清除测试生成的活动数据"""
    db = SessionLocal()
    
    try:
        logger.info("清除测试生成的活动数据...")
        
        # 删除带有 test 标记的数据
        deleted_count = db.query(UserActivityLog).filter(
            UserActivityLog.extra_data['generated'].astext == 'true'
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"已删除 {deleted_count} 条测试活动记录")
        
    except Exception as e:
        logger.error(f"清除测试数据失败: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='生成用户活动测试数据')
    parser.add_argument('--user-id', type=int, help='指定用户ID（可选）')
    parser.add_argument('--clear', action='store_true', help='清除测试数据')
    parser.add_argument('--days', type=int, default=7, help='生成过去多少天的数据（默认：7）')
    
    args = parser.parse_args()
    
    if args.clear:
        clear_test_data()
    elif args.user_id:
        generate_test_activity(args.user_id, days=args.days)
    else:
        generate_for_all_users()
