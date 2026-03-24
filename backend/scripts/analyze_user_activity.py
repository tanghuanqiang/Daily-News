#!/usr/bin/env python3
"""
用户活跃时间分析脚本
分析用户行为日志，计算最佳推送时间窗口
"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import SessionLocal
from models import UserActivityLog, User
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PushTimingAnalyzer:
    """推送时机分析器"""
    
    def __init__(self, db):
        self.db = db
        self.analysis_days = 7  # 分析过去7天的数据
        self.optimal_hour = 9   # 默认最佳时间（上午9点）
    
    def analyze_user_activity(self, user_id: int) -> Optional[int]:
        """
        分析指定用户的活跃时间，返回最佳推送小时
        
        Args:
            user_id: 用户ID
            
        Returns:
            最佳推送小时（0-23），如果数据不足返回None
        """
        try:
            # 计算分析的时间范围（过去N天）
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=self.analysis_days)
            
            # 查询用户的行为日志
            activity_logs = self.db.query(UserActivityLog).filter(
                UserActivityLog.user_id == user_id,
                UserActivityLog.activity_time >= start_time,
                UserActivityLog.activity_time <= end_time
            ).all()
            
            if not activity_logs:
                logger.info(f"用户 {user_id} 在过去 {self.analysis_days} 天没有活动记录")
                return None
            
            logger.info(f"用户 {user_id} 共有 {len(activity_logs)} 条活动记录")
            
            # 统计每小时的活动次数
            hour_counts = Counter()
            for log in activity_logs:
                hour = log.hour_of_day
                hour_counts[hour] += 1
            
            # 找出最活跃的小时
            if hour_counts:
                most_active_hour = hour_counts.most_common(1)[0][0]
                activity_count = hour_counts.most_common(1)[0][1]
                
                logger.info(f"用户 {user_id} 最活跃时间: {most_active_hour}:00 (活动次数: {activity_count})")
                
                # 打印详细统计（调试用）
                if len(activity_logs) < 5:
                    logger.debug(f"用户 {user_id} 活动详情:")
                    for log in activity_logs:
                        logger.debug(f"  - {log.activity_type} at {log.activity_time}")
                
                return most_active_hour
            else:
                logger.warning(f"用户 {user_id} 没有有效的小时数据")
                return None
                
        except Exception as e:
            logger.error(f"分析用户活跃时间失败 (用户ID: {user_id}): {str(e)}")
            return None
    
    def analyze_all_users(self) -> Dict[int, int]:
        """
        分析所有用户，返回每个用户的最佳推送时间
        
        Returns:
            字典：{user_id: optimal_hour}
        """
        logger.info(f"开始分析所有用户的活跃时间（分析过去 {self.analysis_days} 天）...")
        
        # 查询所有有活动记录的用户
        users = self.db.query(UserActivityLog.user_id).distinct().all()
        
        if not users:
            logger.warning("数据库中没有用户活动记录")
            return {}
        
        logger.info(f"找到 {len(users)} 个有活动记录的用户")
        
        user_optimal_times = {}
        analyzed_count = 0
        skipped_count = 0
        
        for user_tuple in users:
            user_id = user_tuple[0]
            optimal_hour = self.analyze_user_activity(user_id)
            
            if optimal_hour is not None:
                user_optimal_times[user_id] = optimal_hour
                analyzed_count += 1
            else:
                skipped_count += 1
        
        logger.info(f"分析完成：成功分析 {analyzed_count} 个用户，跳过 {skipped_count} 个用户")
        
        return user_optimal_times
    
    def save_push_time_to_preferences(self, user_id: int, optimal_hour: int) -> bool:
        """
        将最佳推送时间保存到用户设置
        
        Args:
            user_id: 用户ID
            optimal_hour: 最佳推送小时
            
        Returns:
            是否保存成功
        """
        try:
            # 查询用户
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.error(f"用户不存在: {user_id}")
                return False
            
            # 更新推送时间（默认启用个性化推送）
            user.email_schedule_enabled = True
            user.email_schedule_type = "daily"
            user.email_schedule_hour = optimal_hour
            user.email_schedule_minute = 0
            
            self.db.commit()
            
            logger.info(f"已保存用户 {user_id} 的最佳推送时间: {optimal_hour}:00")
            return True
            
        except Exception as e:
            logger.error(f"保存推送时间失败 (用户ID: {user_id}): {str(e)}")
            self.db.rollback()
            return False
    
    def analyze_and_save_all(self) -> Tuple[int, int]:
        """
        分析所有用户并保存最佳推送时间
        
        Returns:
            (成功分析的用户数, 成功保存的用户数)
        """
        logger.info("=== 开始分析并保存所有用户的最佳推送时间 ===")
        
        # 分析所有用户
        user_optimal_times = self.analyze_all_users()
        
        if not user_optimal_times:
            logger.warning("没有可保存的分析结果")
            return 0, 0
        
        logger.info(f"正在保存 {len(user_optimal_times)} 个用户的推送时间...")
        
        # 保存到用户偏好设置
        saved_count = 0
        for user_id, optimal_hour in user_optimal_times.items():
            if self.save_push_time_to_preferences(user_id, optimal_hour):
                saved_count += 1
        
        logger.info(f"=== 分析完成 ===")
        logger.info(f"分析用户数: {len(user_optimal_times)}")
        logger.info(f"保存成功数: {saved_count}")
        
        return len(user_optimal_times), saved_count
    
    def generate_report(self, user_optimal_times: Dict[int, int]):
        """
        生成分析报告
        
        Args:
            user_optimal_times: 用户最佳推送时间字典
        """
        if not user_optimal_times:
            logger.info("没有数据可生成报告")
            return
        
        logger.info("\n=== 推送时间分析报告 ===")
        
        # 统计各时间段的用户分布
        hour_distribution = Counter(user_optimal_times.values())
        
        logger.info("用户最佳推送时间分布：")
        for hour in range(24):
            count = hour_distribution.get(hour, 0)
            if count > 0:
                percentage = (count / len(user_optimal_times)) * 100
                bar = "█" * int(percentage / 2)
                logger.info(f"  {hour:02d}:00 - {count:3d} 个用户 ({percentage:5.1f}%) {bar}")
        
        # 最热门的时间段
        most_popular_hour = hour_distribution.most_common(1)[0]
        logger.info(f"\n最热门推送时间: {most_popular_hour[0]:02d}:00 ({most_popular_hour[1]} 个用户)")
        
        # 统计摘要
        logger.info(f"\n统计摘要：")
        logger.info(f"  总用户数: {len(user_optimal_times)}")
        logger.info(f"  平均推送时间: {sum(user_optimal_times.values()) / len(user_optimal_times):.1f}:00")
        logger.info(f"  推送时间标准差: {self._calculate_std_dev(list(user_optimal_times.values())):.1f} 小时")
    
    def _calculate_std_dev(self, values: List[int]) -> float:
        """计算标准差"""
        if not values:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5


def main():
    """主函数"""
    db = SessionLocal()
    
    try:
        analyzer = PushTimingAnalyzer(db)
        
        # 分析所有用户并保存
        analyzed_count, saved_count = analyzer.analyze_and_save_all()
        
        # 生成报告
        if analyzed_count > 0:
            # 重新查询已保存的数据生成报告
            user_optimal_times = {}
            users = db.query(User).filter(
                User.email_schedule_enabled == True
            ).all()
            
            for user in users:
                if user.email_schedule_hour is not None:
                    user_optimal_times[user.id] = user.email_schedule_hour
            
            analyzer.generate_report(user_optimal_times)
        
        logger.info(f"\n任务完成！成功分析 {analyzed_count} 个用户，保存 {saved_count} 个用户的推送时间")
        
    except Exception as e:
        logger.error(f"分析过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
