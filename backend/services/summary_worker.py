"""Summary Worker — AI 摘要异步任务处理器

从 summary_tasks 队列中消费任务，调用 LLM 生成摘要，
通过令牌桶限速确保不超过 NVIDIA API 的 RPM 限制。

由 APScheduler 每 N 秒触发一次 run_cycle()。
"""
import logging
import time
from typing import Dict, Any, Optional, Optional

from sqlalchemy.orm import Session

from database import SessionLocal, settings
from models import SummaryTask, NewsCache
from summarizer import get_summarizer
from services.summary_queue import SummaryTaskQueue
from services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# Worker 配置
WORKER_CONFIG = {
    "rpm": getattr(settings, "SUMMARY_TASK_RPM", 30),          # 每分钟最大请求数
    "burst": getattr(settings, "SUMMARY_TASK_BURST", 30),       # 突发容量
    "interval_seconds": getattr(settings, "SUMMARY_WORKER_INTERVAL", 3),  # 轮询间隔
    "max_retries": getattr(settings, "SUMMARY_MAX_RETRIES", 3),
    "cleanup_days": getattr(settings, "SUMMARY_TASK_CLEANUP_DAYS", 7),
}

# 正在处理的 news_id（防止同篇新闻并发处理多个任务）
_processing_news_ids: set = set()


class SummaryWorker:
    """AI 摘要任务处理器"""

    def __init__(self):
        self.rate_limiter = get_rate_limiter(
            rpm=WORKER_CONFIG["rpm"],
            burst=WORKER_CONFIG["burst"]
        )
        self.summarizer = None  # 延迟初始化

    def _get_summarizer(self):
        """延迟初始化 summarizer（避免启动时 LLM 连接检查阻塞）"""
        if self.summarizer is None:
            self.summarizer = get_summarizer()
        return self.summarizer

    def run_cycle(self):
        """一次工作周期：取一个任务，限速处理后执行

        由 APScheduler 定时调用，每次只处理一条任务，
        确保不会突发超过 API 限制。
        """
        # 检查令牌
        if not self.rate_limiter.acquire(tokens=1, blocking=False):
            return  # 没有令牌，跳过本轮

        db = SessionLocal()
        try:
            queue = SummaryTaskQueue(db)

            # 取一条待处理任务（排除正在处理的新闻）
            exclude_list = list(_processing_news_ids)
            task = queue.dequeue(exclude_news_ids=exclude_list if exclude_list else None)

            if not task:
                return  # 队列为空

            # 加入处理集合
            _processing_news_ids.add(task.news_id)

            try:
                self._process_task(task, db)
            finally:
                _processing_news_ids.discard(task.news_id)

        except Exception as e:
            logger.error(f"Worker cycle error: {e}", exc_info=True)
        finally:
            db.close()

    def _process_task(self, task: SummaryTask, db: Session):
        """处理单个任务"""
        queue = SummaryTaskQueue(db)
        news = db.query(NewsCache).filter(NewsCache.id == task.news_id).first()

        if not news:
            logger.warning(f"News {task.news_id} not found, marking task {task.id} as failed")
            queue.fail(task.id, "News not found (deleted)")
            return

        try:
            summarizer = self._get_summarizer()

            if task.task_type == "summary":
                result = summarizer.generate_summary(
                    news.title, news.raw_content or news.summary,
                    roast_mode=False
                )
                if result and "暂不可用" not in result:
                    news.summary = result

            elif task.task_type == "summary_roast":
                result = summarizer.generate_summary(
                    news.title, news.raw_content or news.summary,
                    roast_mode=True
                )
                if result and "暂不可用" not in result:
                    news.summary_roast = result

            elif task.task_type == "relevance":
                score = summarizer.evaluate_relevance(
                    news.topic, news.title, news.raw_content or news.summary
                )
                if score is not None:
                    news.relevance_score = score

            queue.complete(task.id)
            logger.info(
                f"Task {task.id} completed: {task.task_type} for news '{news.title[:40]}...'"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task.id} error ({task.task_type}): {error_msg}")

            # 判断是否是限速错误
            should_retry = queue.fail(task.id, error_msg)

            if not should_retry:
                logger.warning(
                    f"Task {task.id} permanently failed: {task.task_type} for news '{news.title[:40]}...'"
                )
            else:
                logger.info(f"Task {task.id} will be retried (attempt {task.retry_count})")

    def get_stats(self) -> Dict[str, Any]:
        """获取 Worker 统计信息"""
        db = SessionLocal()
        try:
            queue = SummaryTaskQueue(db)
            stats = queue.get_stats()
            stats["rate_limiter"] = {
                "available_tokens": round(self.rate_limiter.get_available(), 1),
                "wait_seconds": round(self.rate_limiter.get_wait_seconds(), 1),
                "rpm": WORKER_CONFIG["rpm"],
                "burst": WORKER_CONFIG["burst"],
            }
            stats["worker"] = {
                "interval_seconds": WORKER_CONFIG["interval_seconds"],
                "processing_count": len(_processing_news_ids),
            }
            return stats
        finally:
            db.close()


# 全局 Worker 单例
_worker: Optional[SummaryWorker] = None


def get_worker() -> SummaryWorker:
    """获取全局 Worker 单例"""
    global _worker
    if _worker is None:
        _worker = SummaryWorker()
        logger.info("Summary worker initialized")
    return _worker


def worker_cycle():
    """APScheduler 定时任务入口"""
    worker = get_worker()
    worker.run_cycle()


def cleanup_old_tasks():
    """APScheduler 定时清理入口"""
    db = SessionLocal()
    try:
        queue = SummaryTaskQueue(db)
        queue.cleanup_old_tasks(days=WORKER_CONFIG["cleanup_days"])
    finally:
        db.close()
