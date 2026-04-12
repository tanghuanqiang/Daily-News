"""Summary Task Queue — AI 摘要异步任务队列

基于数据库的轻量级任务队列，用于解耦新闻抓取和 LLM 调用。
支持优先级排序、幂等入队、失败重试和状态跟踪。
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import SummaryTask, NewsCache

logger = logging.getLogger(__name__)

# 任务类型 → 优先级映射（越小越优先）
TASK_PRIORITY = {
    "summary": 0,         # 正常摘要最优先
    "summary_roast": 1,   # 吐槽摘要次之
    "relevance": 2,       # 相关性评分最低
}

# 所有需要入队的任务类型（按执行顺序）
ALL_TASK_TYPES = ["summary", "summary_roast", "relevance"]


class SummaryTaskQueue:
    """AI 摘要任务队列"""

    def __init__(self, db: Session):
        self.db = db

    def enqueue(self, news_id: int, task_type: str = None) -> bool:
        """创建任务（幂等：同一 news_id + task_type 不会重复）

        Args:
            news_id: 关联的新闻 ID
            task_type: 任务类型，None 则创建全部三种

        Returns:
            是否成功创建（已存在则返回 False）
        """
        types = [task_type] if task_type else ALL_TASK_TYPES
        created = 0

        for tt in types:
            try:
                # 幂等检查
                existing = self.db.query(SummaryTask).filter(
                    SummaryTask.news_id == news_id,
                    SummaryTask.task_type == tt,
                    SummaryTask.status.in_(["pending", "processing"])
                ).first()

                if existing:
                    continue

                task = SummaryTask(
                    news_id=news_id,
                    task_type=tt,
                    status="pending",
                    priority=TASK_PRIORITY.get(tt, 99),
                    retry_count=0,
                    max_retries=3,
                )
                self.db.add(task)
                created += 1

            except Exception as e:
                logger.error(f"Failed to enqueue task (news_id={news_id}, type={tt}): {e}")

        if created > 0:
            try:
                self.db.commit()
                logger.info(f"Enqueued {created} tasks for news_id={news_id}")
                return True
            except Exception as e:
                self.db.rollback()
                logger.error(f"Commit failed for enqueue: {e}")
                return False

        return False

    def enqueue_batch(self, news_ids: List[int]) -> int:
        """批量入队（一篇新闻创建 3 个任务：summary, summary_roast, relevance）

        Args:
            news_ids: 新闻 ID 列表

        Returns:
            成功创建的任务数量
        """
        total = 0
        for news_id in news_ids:
            if self.enqueue(news_id):
                total += 3  # 每篇 3 个任务
        return total

    def dequeue(self, exclude_news_ids: List[int] = None) -> Optional[SummaryTask]:
        """取出一条待处理任务（按优先级排序）

        Args:
            exclude_news_ids: 排除的新闻 ID 列表（用于防止同篇新闻并发处理）

        Returns:
            SummaryTask 或 None
        """
        query = self.db.query(SummaryTask).filter(
            SummaryTask.status == "pending"
        ).order_by(
            SummaryTask.priority.asc(),
            SummaryTask.created_at.asc()
        )

        if exclude_news_ids:
            query = query.filter(SummaryTask.news_id.notin_(exclude_news_ids))

        task = query.first()

        if task:
            task.status = "processing"
            task.started_at = datetime.utcnow()
            try:
                self.db.commit()
                return task
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to dequeue task {task.id}: {e}")
                return None

        return None

    def complete(self, task_id: int, result: Any = None):
        """标记任务完成"""
        task = self.db.query(SummaryTask).filter(SummaryTask.id == task_id).first()
        if not task:
            return

        task.status = "completed"
        task.completed_at = datetime.utcnow()

        # 更新关联新闻的摘要状态
        self._update_news_summary_status(task.news_id)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to complete task {task_id}: {e}")

    def fail(self, task_id: int, error_message: str) -> bool:
        """标记任务失败，支持重试

        Returns:
            True 表示已重试（状态回退为 pending），False 表示已耗尽重试
        """
        task = self.db.query(SummaryTask).filter(SummaryTask.id == task_id).first()
        if not task:
            return False

        task.error_message = error_message[:500]  # 截断过长错误
        task.retry_count += 1

        if task.retry_count < task.max_retries:
            # 重试：回退到 pending，提高优先级
            task.status = "pending"
            task.started_at = None
            logger.warning(
                f"Task {task_id} failed (attempt {task.retry_count}/{task.max_retries}): {error_message[:100]}"
            )
            result = True
        else:
            # 重试耗尽
            task.status = "failed"
            task.completed_at = datetime.utcnow()
            logger.error(f"Task {task_id} permanently failed after {task.max_retries} retries: {error_message[:100]}")
            result = False

        # 更新关联新闻的摘要状态
        self._update_news_summary_status(task.news_id)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update task {task_id}: {e}")

        return result

    def _update_news_summary_status(self, news_id: int):
        """根据任务完成情况更新 news_cache.summary_status"""
        news = self.db.query(NewsCache).filter(NewsCache.id == news_id).first()
        if not news:
            return

        tasks = self.db.query(SummaryTask).filter(
            SummaryTask.news_id == news_id
        ).all()

        if not tasks:
            return

        completed_count = sum(1 for t in tasks if t.status == "completed")
        failed_count = sum(1 for t in tasks if t.status == "failed")
        total = len(tasks)

        # summary 已完成就算 partial
        summary_task = next((t for t in tasks if t.task_type == "summary"), None)
        if summary_task and summary_task.status == "completed":
            if completed_count == total:
                news.summary_status = "completed"
            else:
                news.summary_status = "partial"
        elif failed_count == total:
            news.summary_status = "unavailable"
        # pending/partial 保持不变

    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        from sqlalchemy import func

        stats = {}

        # 各状态数量
        status_counts = self.db.query(
            SummaryTask.status, func.count(SummaryTask.id)
        ).group_by(SummaryTask.status).all()

        for status, count in status_counts:
            stats[f"{status}_count"] = count

        stats.setdefault("pending_count", 0)
        stats.setdefault("processing_count", 0)
        stats.setdefault("completed_count", 0)
        stats.setdefault("failed_count", 0)

        stats["total"] = sum(v for k, v in stats.items() if k.endswith("_count"))

        # 各类型统计
        type_counts = self.db.query(
            SummaryTask.task_type, SummaryTask.status, func.count(SummaryTask.id)
        ).group_by(SummaryTask.task_type, SummaryTask.status).all()

        stats["by_type"] = {}
        for task_type, status, count in type_counts:
            if task_type not in stats["by_type"]:
                stats["by_type"][task_type] = {}
            stats["by_type"][task_type][status] = count

        # 处理中的任务
        processing = self.db.query(SummaryTask).filter(
            SummaryTask.status == "processing"
        ).all()
        stats["processing_tasks"] = [
            {
                "id": t.id,
                "news_id": t.news_id,
                "task_type": t.task_type,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "retry_count": t.retry_count,
            }
            for t in processing
        ]

        # 最近失败的任务
        recent_failed = self.db.query(SummaryTask).filter(
            SummaryTask.status == "failed"
        ).order_by(SummaryTask.completed_at.desc()).limit(10).all()

        stats["recent_failed"] = [
            {
                "id": t.id,
                "news_id": t.news_id,
                "task_type": t.task_type,
                "error_message": t.error_message,
                "retry_count": t.retry_count,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in recent_failed
        ]

        return stats

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理过期的已完成/失败任务

        Args:
            days: 保留最近多少天的记录

        Returns:
            清理的任务数量
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        try:
            deleted = self.db.query(SummaryTask).filter(
                SummaryTask.status.in_(["completed", "failed"]),
                SummaryTask.completed_at < cutoff
            ).delete(synchronize_session="fetch")

            self.db.commit()
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old summary tasks (older than {days} days)")
            return deleted
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0

    def requeue_failed(self, news_id: int = None) -> int:
        """重新入队失败的任务

        Args:
            news_id: 指定新闻 ID，None 则重试所有失败任务

        Returns:
            重新入队的任务数
        """
        query = self.db.query(SummaryTask).filter(
            SummaryTask.status == "failed"
        )

        if news_id:
            query = query.filter(SummaryTask.news_id == news_id)

        tasks = query.all()
        count = 0

        for task in tasks:
            task.status = "pending"
            task.retry_count = 0
            task.error_message = None
            task.started_at = None
            task.completed_at = None
            count += 1

        if count > 0:
            try:
                self.db.commit()
                logger.info(f"Requeued {count} failed tasks")
            except Exception as e:
                self.db.rollback()
                logger.error(f"Failed to requeue tasks: {e}")
                return 0

        return count
