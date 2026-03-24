from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from models import (
    UserAchievement,
    AchievementDefinition,
    NewsFeedback,
    NewsCache,
    User
)
from database import get_db, settings
from scheduler import send_email
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_achievement_email(
    achievement: AchievementDefinition,
    user: User,
    stats: Dict
) -> str:
    """
    构建成就解锁邮件的HTML内容
    
    Args:
        achievement: 成就定义
        user: 用户对象
        stats: 成就统计信息
        
    Returns:
        HTML邮件内容
    """
    unlock_rate = stats.get('unlock_rate', 0)
    unlocked_count = stats.get('unlocked_count', 0)
    total_achievements = stats.get('total_achievements', 0)
    total_points = stats.get('total_points', 0)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎉 恭喜解锁新成就</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px 30px;
                text-align: center;
                color: white;
            }}
            .achievement-icon {{
                font-size: 64px;
                margin-bottom: 20px;
                display: block;
            }}
            .achievement-title {{
                font-size: 28px;
                font-weight: bold;
                margin: 0 0 10px 0;
            }}
            .achievement-name {{
                font-size: 24px;
                margin: 0;
                opacity: 0.9;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .achievement-card {{
                background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
                border: 2px solid #e0e7ff;
            }}
            .achievement-description {{
                font-size: 18px;
                color: #4a5568;
                margin: 20px 0;
                line-height: 1.6;
            }}
            .achievement-points {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .stats-section {{
                background: #f7fafc;
                border-radius: 15px;
                padding: 25px;
                margin-top: 30px;
            }}
            .stats-title {{
                font-size: 20px;
                font-weight: bold;
                color: #2d3748;
                margin-bottom: 20px;
                text-align: center;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 20px;
            }}
            .stat-item {{
                text-align: center;
                padding: 15px;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #667eea;
                display: block;
            }}
            .stat-label {{
                font-size: 14px;
                color: #718096;
                margin-top: 5px;
            }}
            .progress-bar {{
                background: #e2e8f0;
                border-radius: 10px;
                height: 20px;
                overflow: hidden;
                margin-top: 15px;
            }}
            .progress-fill {{
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                height: 100%;
                border-radius: 10px;
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }}
            .footer {{
                background: #f7fafc;
                padding: 20px 30px;
                text-align: center;
                border-top: 1px solid #e2e8f0;
                font-size: 14px;
                color: #718096;
            }}
            .cta-button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 30px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                margin-top: 20px;
                transition: transform 0.2s ease;
            }}
            .cta-button:hover {{
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span class="achievement-icon">{achievement.icon or '🏆'}</span>
                <h1 class="achievement-title">🎉 恭喜解锁新成就！</h1>
                <h2 class="achievement-name">{achievement.name}</h2>
            </div>
            
            <div class="content">
                <div class="achievement-card">
                    <div class="achievement-description">
                        {achievement.description}
                    </div>
                    <div class="achievement-points">
                        +{achievement.points} 成就点数
                    </div>
                </div>
                
                <div class="stats-section">
                    <h3 class="stats-title">您的成就进度</h3>
                    
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-value">{unlocked_count}</span>
                            <div class="stat-label">已解锁成就</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{total_achievements}</span>
                            <div class="stat-label">总成就数</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{total_points}</span>
                            <div class="stat-label">总点数</div>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">{unlocked_count}/{total_achievements}</span>
                            <div class="stat-label">进度</div>
                        </div>
                    </div>
                    
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {unlock_rate}%;">
                            {unlock_rate}%
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>继续加油！更多成就在等待着您去发现。</p>
                <a href="#" class="cta-button">查看所有成就</a>
                <p style="margin-top: 20px; font-size: 12px; color: #a0aec0;">
                    此邮件由 Daily-News 成就系统自动发送<br>
                    您可以在个人设置中管理邮件通知偏好
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


class AchievementChecker:
    """成就检测服务，自动检测用户行为并解锁成就"""


class AchievementChecker:
    """成就检测服务，自动检测用户行为并解锁成就"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _get_user_achievement_stats(self, user_id: int) -> Dict:
        """
        获取用户成就统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计信息字典
        """
        try:
            # 总成就数
            total_achievements = self.db.query(AchievementDefinition).filter(
                AchievementDefinition.is_active == True
            ).count()
            
            # 已解锁成就数
            unlocked_count = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id
            ).count()
            
            # 总点数
            total_points = self.db.query(func.sum(AchievementDefinition.points)).join(
                UserAchievement,
                UserAchievement.achievement_id == AchievementDefinition.id
            ).filter(
                UserAchievement.user_id == user_id
            ).scalar() or 0
            
            # 解锁率
            unlock_rate = (unlocked_count / total_achievements * 100) if total_achievements > 0 else 0
            
            return {
                "total_achievements": total_achievements,
                "unlocked_count": unlocked_count,
                "total_points": total_points,
                "unlock_rate": round(unlock_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"获取用户成就统计失败: {str(e)}")
            return {
                "total_achievements": 0,
                "unlocked_count": 0,
                "total_points": 0,
                "unlock_rate": 0
            }
    
    def check_reading_achievements(self, user_id: int, news_id: int) -> List[Dict]:
        """
        检查与阅读相关的成就
        
        Args:
            user_id: 用户ID
            news_id: 新闻ID
            
        Returns:
            解锁的成就列表
        """
        unlocked_achievements = []
        
        try:
            # 检查首次阅读成就
            unlocked = self._check_first_read(user_id)
            if unlocked:
                unlocked_achievements.extend(unlocked)
            
            # 检查阅读数量成就
            unlocked = self._check_reading_count(user_id)
            if unlocked:
                unlocked_achievements.extend(unlocked)
            
            # 检查主题多样性成就
            unlocked = self._check_topic_diversity(user_id)
            if unlocked:
                unlocked_achievements.extend(unlocked)
            
        except Exception as e:
            logger.error(f"检查阅读成就失败: {str(e)}")
        
        return unlocked_achievements
    
    def check_sharing_achievements(self, user_id: int, news_id: int) -> List[Dict]:
        """
        检查与分享相关的成就
        
        Args:
            user_id: 用户ID
            news_id: 新闻ID
            
        Returns:
            解锁的成就列表
        """
        unlocked_achievements = []
        
        try:
            # 检查分享达人成就
            unlocked = self._check_sharing_count(user_id)
            if unlocked:
                unlocked_achievements.extend(unlocked)
            
        except Exception as e:
            logger.error(f"检查分享成就失败: {str(e)}")
        
        return unlocked_achievements
    
    def check_streak_achievements(self, user_id: int) -> List[Dict]:
        """
        检查连续阅读成就（定时任务调用）
        
        Args:
            user_id: 用户ID
            
        Returns:
            解锁的成就列表
        """
        unlocked_achievements = []
        
        try:
            unlocked = self._check_reading_streak(user_id)
            if unlocked:
                unlocked_achievements.extend(unlocked)
            
        except Exception as e:
            logger.error(f"检查连续阅读成就失败: {str(e)}")
        
        return unlocked_achievements
    
    def _check_first_read(self, user_id: int) -> Optional[List[Dict]]:
        """检查首次阅读成就"""
        # 获取首次阅读成就定义
        achievement = self.db.query(AchievementDefinition).filter(
            AchievementDefinition.code == 'first_read',
            AchievementDefinition.is_active == True
        ).first()
        
        if not achievement:
            return None
        
        # 检查是否已解锁
        existing = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()
        
        if existing:
            return None
        
        # 检查是否已有阅读记录（通过feedback表判断）
        read_count = self.db.query(NewsFeedback).filter(
            NewsFeedback.user_id == user_id,
            NewsFeedback.feedback_type == 'like'
        ).count()
        
        # 如果这是第一条阅读记录
        if read_count == 1:
            return self._unlock_achievement(user_id, achievement.id)
        
        return None
    
    def _check_reading_count(self, user_id: int) -> Optional[List[Dict]]:
        """检查阅读数量成就"""
        # 获取所有阅读数量相关的成就
        achievements = self.db.query(AchievementDefinition).filter(
            AchievementDefinition.category == 'reading',
            AchievementDefinition.code.like('read_%'),
            AchievementDefinition.is_active == True
        ).all()
        
        unlocked = []
        
        for achievement in achievements:
            # 检查是否已解锁
            existing = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            ).first()
            
            if existing:
                continue
            
            # 从配置中获取需要的阅读数量
            required_count = achievement.requirement_config.get('count', 0)
            if not required_count:
                continue
            
            # 查询实际阅读数量
            actual_count = self.db.query(NewsFeedback).filter(
                NewsFeedback.user_id == user_id,
                NewsFeedback.feedback_type == 'like'
            ).count()
            
            # 如果满足条件，解锁成就
            if actual_count >= required_count:
                unlocked_achievement = self._unlock_achievement(user_id, achievement.id)
                if unlocked_achievement:
                    unlocked.extend(unlocked_achievement)
        
        return unlocked if unlocked else None
    
    def _check_topic_diversity(self, user_id: int) -> Optional[List[Dict]]:
        """检查主题多样性成就"""
        achievement = self.db.query(AchievementDefinition).filter(
            AchievementDefinition.code == 'topic_explorer',
            AchievementDefinition.is_active == True
        ).first()
        
        if not achievement:
            return None
        
        # 检查是否已解锁
        existing = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()
        
        if existing:
            return None
        
        # 从配置中获取需要的不同主题数量
        required_topics = achievement.requirement_config.get('topics', 0)
        if not required_topics:
            return None
        
        # 查询用户阅读过的不同主题数量（简化实现，实际项目中需要从新闻表关联查询）
        # 这里暂时使用feedback表中的记录作为参考
        unique_topics = self.db.query(func.count(func.distinct(NewsFeedback.news_id))).filter(
            NewsFeedback.user_id == user_id,
            NewsFeedback.feedback_type == 'like'
        ).scalar()
        
        # 如果满足条件，解锁成就
        if unique_topics >= required_topics:
            return self._unlock_achievement(user_id, achievement.id)
        
        return None
    
    def _check_sharing_count(self, user_id: int) -> Optional[List[Dict]]:
        """检查分享数量成就"""
        # 获取所有分享相关的成就
        achievements = self.db.query(AchievementDefinition).filter(
            AchievementDefinition.category == 'sharing',
            AchievementDefinition.is_active == True
        ).all()
        
        unlocked = []
        
        for achievement in achievements:
            # 检查是否已解锁
            existing = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement.id
            ).first()
            
            if existing:
                continue
            
            # 从配置中获取需要的分享数量
            required_count = achievement.requirement_config.get('count', 0)
            if not required_count:
                continue
            
            # 查询实际分享数量
            actual_count = self.db.query(NewsFeedback).filter(
                NewsFeedback.user_id == user_id,
                NewsFeedback.feedback_type == 'share'
            ).count()
            
            # 如果满足条件，解锁成就
            if actual_count >= required_count:
                unlocked_achievement = self._unlock_achievement(user_id, achievement.id)
                if unlocked_achievement:
                    unlocked.extend(unlocked_achievement)
        
        return unlocked if unlocked else None
    
    def _check_reading_streak(self, user_id: int) -> Optional[List[Dict]]:
        """检查连续阅读成就"""
        # 获取连续阅读相关的成就
        achievement = self.db.query(AchievementDefinition).filter(
            AchievementDefinition.code == 'reading_streak_7d',
            AchievementDefinition.is_active == True
        ).first()
        
        if not achievement:
            return None
        
        # 检查是否已解锁
        existing = self.db.query(UserAchievement).filter(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == achievement.id
        ).first()
        
        if existing:
            return None
        
        # 从配置中获取需要的连续天数
        required_days = achievement.requirement_config.get('days', 0)
        if not required_days:
            return None
        
        # 查询连续阅读天数（简化实现）
        # 这里假设有阅读记录的日期就是连续阅读的日期
        # 实际项目中需要更复杂的逻辑来处理真正的连续天数
        today = datetime.utcnow().date()
        streak_days = 0
        
        for i in range(required_days):
            check_date = today - timedelta(days=i)
            
            # 查询这一天是否有阅读记录
            has_read = self.db.query(NewsFeedback).filter(
                NewsFeedback.user_id == user_id,
                NewsFeedback.feedback_type == 'like',
                func.date(NewsFeedback.created_at) == check_date
            ).first()
            
            if has_read:
                streak_days += 1
            else:
                break
        
        # 如果满足条件，解锁成就
        if streak_days >= required_days:
            return self._unlock_achievement(user_id, achievement.id)
        
        return None
    
    def _unlock_achievement(self, user_id: int, achievement_id: int) -> Optional[List[Dict]]:
        """
        解锁成就
        
        Args:
            user_id: 用户ID
            achievement_id: 成就ID
            
        Returns:
            解锁的成就信息列表
        """
        try:
            # 获取成就定义
            achievement = self.db.query(AchievementDefinition).filter(
                AchievementDefinition.id == achievement_id
            ).first()
            
            if not achievement:
                logger.error(f"成就不存在: {achievement_id}")
                return None
            
            # 检查是否已解锁（双重检查）
            existing = self.db.query(UserAchievement).filter(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id
            ).first()
            
            if existing:
                return None
            
            # 创建用户成就记录
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement_id,
                progress_data={"auto_unlocked": True}
            )
            self.db.add(user_achievement)
            self.db.commit()
            self.db.refresh(user_achievement)
            
            logger.info(f"用户 {user_id} 解锁成就: {achievement.name}")
            
            # 发送成就通知邮件（错误隔离，不影响主流程）
            try:
                self._send_achievement_notification(user_id, achievement)
            except Exception as e:
                logger.error(f"发送成就通知邮件失败（但不影响解锁流程）: {str(e)}")
            
            return [{
                "achievement": achievement,
                "unlocked_at": user_achievement.unlocked_at
            }]
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"解锁成就失败: {str(e)}")
            return None
    
    def _send_achievement_notification(self, user_id: int, achievement: AchievementDefinition):
        """
        发送成就解锁通知邮件
        
        Args:
            user_id: 用户ID
            achievement: 成就定义
        """
        # 查询用户信息
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error(f"用户不存在: {user_id}")
            return
        
        # 检查用户是否开启了邮件通知
        if not user.email_notifications:
            logger.info(f"用户 {user_id} 未开启邮件通知，跳过成就邮件")
            return
        
        # 检查用户是否有邮箱
        if not user.email:
            logger.warning(f"用户 {user_id} 没有邮箱地址，无法发送成就通知")
            return
        
        # 获取用户成就统计
        stats = self._get_user_achievement_stats(user_id)
        
        # 构建邮件内容
        html_body = build_achievement_email(achievement, user, stats)
        
        # 邮件主题
        subject = f"🎉 恭喜解锁新成就：{achievement.name}"
        
        # 发送邮件
        try:
            send_email(
                to_email=user.email,
                subject=subject,
                html_body=html_body,
                from_name="Daily-News成就系统通知"
            )
            logger.info(f"成就通知邮件已发送给用户 {user.email} (成就: {achievement.name})")
        except Exception as e:
            logger.error(f"发送成就通知邮件失败: {str(e)}")
            raise


def check_and_unlock_achievements(
    user_id: int,
    trigger_type: str,
    news_id: int = None,
    db: Session = None
) -> List[Dict]:
    """
    检查并解锁成就的便捷函数
    
    Args:
        user_id: 用户ID
        trigger_type: 触发类型 ('read', 'share', 'streak')
        news_id: 新闻ID（可选）
        db: 数据库会话（可选，如果未提供则创建新的）
        
    Returns:
        解锁的成就列表
    """
    if db is None:
        db = next(get_db())
    
    checker = AchievementChecker(db)
    
    if trigger_type == 'read':
        return checker.check_reading_achievements(user_id, news_id)
    elif trigger_type == 'share':
        return checker.check_sharing_achievements(user_id, news_id)
    elif trigger_type == 'streak':
        return checker.check_streak_achievements(user_id)
    else:
        logger.error(f"未知的触发类型: {trigger_type}")
        return []
