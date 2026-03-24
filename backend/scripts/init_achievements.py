#!/usr/bin/env python3
"""
成就定义数据初始化脚本
运行此脚本将预设的成就定义添加到数据库中
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from models import AchievementDefinition

# 预设成就定义
ACHIEVEMENT_DEFINITIONS = [
    {
        "code": "first_read",
        "name": "首次阅读",
        "description": "阅读了第一条新闻，欢迎来到Daily-News！",
        "icon": "📰",
        "category": "reading",
        "requirement_config": {"count": 1},
        "points": 10
    },
    {
        "code": "read_10",
        "name": "阅读新手",
        "description": "累计阅读了10条新闻，继续保持阅读习惯！",
        "icon": "📖",
        "category": "reading",
        "requirement_config": {"count": 10},
        "points": 20
    },
    {
        "code": "read_50",
        "name": "阅读达人",
        "description": "累计阅读了50条新闻，你已经是资讯达人！",
        "icon": "📚",
        "category": "reading",
        "requirement_config": {"count": 50},
        "points": 50
    },
    {
        "code": "reading_streak_7d",
        "name": "连续阅读7天",
        "description": "连续7天都有阅读记录，好习惯养成！",
        "icon": "🔥",
        "category": "reading",
        "requirement_config": {"days": 7},
        "points": 30
    },
    {
        "code": "share_first",
        "name": "首次分享",
        "description": "第一次分享新闻，让知识传播得更远！",
        "icon": "📤",
        "category": "sharing",
        "requirement_config": {"count": 1},
        "points": 15
    },
    {
        "code": "share_10",
        "name": "分享达人",
        "description": "累计分享了10条新闻，感谢你的分享精神！",
        "icon": "🚀",
        "category": "sharing",
        "requirement_config": {"count": 10},
        "points": 40
    },
    {
        "code": "topic_explorer",
        "name": "主题探索者",
        "description": "阅读了5个不同主题的新闻，视野正在拓展！",
        "icon": "🌐",
        "category": "exploration",
        "requirement_config": {"topics": 5},
        "points": 25
    },
    {
        "code": "early_bird",
        "name": "早起鸟",
        "description": "在早上6点前阅读新闻，拥抱美好清晨！",
        "icon": "🌅",
        "category": "early_bird",
        "requirement_config": {"hour": 6},
        "points": 20
    },
    {
        "code": "critical_thinker",
        "name": "批判性思维",
        "description": "对10条新闻提供了反馈（点赞或点踩），保持独立思考！",
        "icon": "🤔",
        "category": "reading",
        "requirement_config": {"feedback_count": 10},
        "points": 35
    },
    {
        "code": "news_master",
        "name": "资讯大师",
        "description": "累计阅读100条新闻，你已经是资讯领域的专家！",
        "icon": "👑",
        "category": "reading",
        "requirement_config": {"count": 100},
        "points": 100
    }
]


def init_achievements():
    """初始化成就定义数据"""
    db = SessionLocal()
    
    try:
        print("开始初始化成就定义数据...")
        
        added_count = 0
        skipped_count = 0
        
        for achievement_data in ACHIEVEMENT_DEFINITIONS:
            # 检查是否已经存在
            existing = db.query(AchievementDefinition).filter(
                AchievementDefinition.code == achievement_data["code"]
            ).first()
            
            if existing:
                print(f"跳过已存在的成就: {achievement_data['name']} ({achievement_data['code']})")
                skipped_count += 1
                continue
            
            # 创建新的成就定义
            achievement = AchievementDefinition(
                code=achievement_data["code"],
                name=achievement_data["name"],
                description=achievement_data["description"],
                icon=achievement_data["icon"],
                category=achievement_data["category"],
                requirement_config=achievement_data["requirement_config"],
                points=achievement_data["points"],
                is_active=True
            )
            
            db.add(achievement)
            added_count += 1
            print(f"添加成就: {achievement_data['name']} ({achievement_data['code']}) - {achievement_data['points']}点数")
        
        db.commit()
        
        print(f"\n初始化完成！")
        print(f"添加新成就: {added_count} 个")
        print(f"跳过已存在: {skipped_count} 个")
        print(f"总计: {added_count + skipped_count} 个成就定义")
        
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def list_achievements():
    """列出数据库中所有的成就定义"""
    db = SessionLocal()
    
    try:
        achievements = db.query(AchievementDefinition).all()
        
        if not achievements:
            print("数据库中没有成就定义")
            return
        
        print(f"\n数据库中的成就定义 ({len(achievements)} 个):")
        print("-" * 80)
        
        for achievement in achievements:
            status = "✅ 启用" if achievement.is_active else "❌ 禁用"
            print(f"{achievement.name} ({achievement.code})")
            print(f"  描述: {achievement.description}")
            print(f"  图标: {achievement.icon} | 类别: {achievement.category} | 点数: {achievement.points}")
            print(f"  条件: {achievement.requirement_config}")
            print(f"  状态: {status}")
            print("-" * 80)
        
    finally:
        db.close()


def clear_achievements():
    """清空所有成就定义（谨慎使用）"""
    confirm = input("\n⚠️  警告: 这将删除所有成就定义！是否继续? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("操作已取消")
        return
    
    db = SessionLocal()
    
    try:
        # 检查是否有用户已解锁的成就
        from models import UserAchievement
        user_achievements_count = db.query(UserAchievement).count()
        
        if user_achievements_count > 0:
            confirm = input(f"\n⚠️  发现 {user_achievements_count} 个用户已解锁的成就！同时删除这些记录? (yes/no): ")
            
            if confirm.lower() == 'yes':
                db.query(UserAchievement).delete()
                print(f"已删除 {user_achievements_count} 个用户成就记录")
        
        # 删除成就定义
        count = db.query(AchievementDefinition).delete()
        db.commit()
        
        print(f"\n已删除 {count} 个成就定义")
        
    except Exception as e:
        print(f"删除失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='管理成就定义数据')
    parser.add_argument('action', choices=['init', 'list', 'clear'], 
                       help='操作: init(初始化), list(列表), clear(清空)')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_achievements()
    elif args.action == 'list':
        list_achievements()
    elif args.action == 'clear':
        clear_achievements()
