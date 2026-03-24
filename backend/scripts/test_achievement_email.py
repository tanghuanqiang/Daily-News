#!/usr/bin/env python3
"""
测试成就邮件通知功能
运行此脚本测试成就解锁时是否正确发送邮件通知
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from models import User, AchievementDefinition, NewsFeedback
import sys
import os

# 直接导入 achievement_service，绕过 services/__init__.py
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
service_path = os.path.join(backend_dir, 'services')
sys.path.insert(0, service_path)

from achievement_service import check_and_unlock_achievements
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_achievement_email():
    """测试成就邮件通知"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("测试成就邮件通知功能")
        print("=" * 60)
        
        # 步骤1: 获取测试用户
        print("\n[步骤1] 获取测试用户...")
        user = db.query(User).first()
        
        if not user:
            print("[错误] 数据库中没有用户，请先创建用户")
            return
        
        print(f"[成功] 找到用户: {user.email} (ID: {user.id})")
        print(f"   邮件通知设置: {'开启' if user.email_notifications else '关闭'}")
        
        if not user.email_notifications:
            print("\n[警告] 用户未开启邮件通知，将跳过邮件发送")
        
        # 步骤2: 检查现有成就
        print("\n[步骤2] 检查用户已有成就...")
        from models import UserAchievement
        existing_achievements = db.query(UserAchievement).filter(
            UserAchievement.user_id == user.id
        ).all()
        
        print(f"[信息] 用户已有 {len(existing_achievements)} 个已解锁成就")
        
        # 步骤3: 创建测试反馈数据（模拟用户行为）
        print("\n[步骤3] 创建测试反馈数据...")
        
        # 检查是否已有足够的反馈数据
        feedback_count = db.query(NewsFeedback).filter(
            NewsFeedback.user_id == user.id,
            NewsFeedback.feedback_type == 'like'
        ).count()
        
        print(f"   当前点赞反馈数量: {feedback_count}")
        
        # 如果反馈数量不足，创建一些测试数据
        if feedback_count < 5:
            print("   创建测试反馈数据...")
            
            # 获取一些新闻ID
            from models import NewsCache
            news_items = db.query(NewsCache).limit(5).all()
            
            if not news_items:
                print("[错误] 数据库中没有新闻数据")
                return
            
            # 创建点赞反馈
            for i, news in enumerate(news_items[:5]):
                # 检查是否已存在
                existing = db.query(NewsFeedback).filter(
                    NewsFeedback.user_id == user.id,
                    NewsFeedback.news_id == news.id,
                    NewsFeedback.feedback_type == 'like'
                ).first()
                
                if not existing:
                    feedback = NewsFeedback(
                        user_id=user.id,
                        news_id=news.id,
                        feedback_type='like'
                    )
                    db.add(feedback)
                    print(f"     创建点赞反馈: 新闻ID {news.id}")
            
            db.commit()
            print("[成功] 测试反馈数据创建完成")
        else:
            print("[信息] 反馈数据充足，无需创建")
        
        # 步骤4: 触发成就检测
        print("\n[步骤4] 触发成就检测...")
        print(f"   触发类型: read (阅读)")
        print(f"   用户ID: {user.id}")
        
        # 获取一个新闻ID用于测试
        from models import NewsCache
        news = db.query(NewsCache).first()
        
        if not news:
            print("[错误] 没有新闻数据")
            return
        
        unlocked_achievements = check_and_unlock_achievements(
            user_id=user.id,
            trigger_type='read',
            news_id=news.id,
            db=db
        )
        
        print(f"\n[成功] 成就检测完成")
        print(f"   解锁的成就数量: {len(unlocked_achievements)}")
        
        if unlocked_achievements:
            print("\n   解锁的成就详情:")
            for item in unlocked_achievements:
                achievement = item.get('achievement')
                if achievement:
                    print(f"   - {achievement.name} (+{achievement.points}点数)")
        else:
            print("   未解锁新成就（可能已解锁过或条件不满足）")
        
        # 步骤5: 验证邮件发送
        print("\n[步骤5] 验证邮件发送...")
        print("   请检查日志输出中是否有 '成就通知邮件已发送' 或相关错误信息")
        print("   如果用户开启了邮件通知且配置了邮件服务，应该会收到邮件")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_achievement_email()
