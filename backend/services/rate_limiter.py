"""Token Bucket Rate Limiter — 控制 NVIDIA API 调用频率

设计目标:
  - 30 RPM 稳态速率（留 10 RPM 余量给其他请求）
  - 最多 burst 30 个令牌（应对短时积压）
  - 线程安全（APScheduler 线程池可能并发）
"""
import threading
import time
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """令牌桶限速器

    Args:
        rate: 每秒填充的令牌数 (e.g. 0.5 = 30/min)
        capacity: 桶容量 (最大突发量)
    """

    def __init__(self, rate: float = 0.5, capacity: int = 30):
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)  # 初始满桶
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        """补充令牌"""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def acquire(self, tokens: int = 1, blocking: bool = True, timeout: float = 10.0) -> bool:
        """获取令牌

        Args:
            tokens: 需要的令牌数
            blocking: 是否阻塞等待
            timeout: 最大等待秒数

        Returns:
            True 获取成功, False 超时
        """
        deadline = time.monotonic() + timeout if blocking else 0

        while True:
            with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True
                if not blocking:
                    return False
                if time.monotonic() > deadline:
                    return False

            # 等待一小段时间再试
            time.sleep(0.5)

    def get_available(self) -> float:
        """获取当前可用令牌数"""
        with self._lock:
            self._refill()
            return self._tokens

    def get_wait_seconds(self, tokens: int = 1) -> float:
        """获取需要等待多少秒才能获取指定数量的令牌"""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            needed = tokens - self._tokens
            return needed / self.rate

    def reset(self):
        """重置令牌桶（用于测试）"""
        with self._lock:
            self._tokens = float(self.capacity)
            self._last_refill = time.monotonic()


# 全局限速器单例
_rate_limiter: TokenBucket | None = None


def get_rate_limiter(rpm: int = 30, burst: int = 30) -> TokenBucket:
    """获取全局限速器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        rate_per_second = rpm / 60.0
        _rate_limiter = TokenBucket(rate=rate_per_second, capacity=burst)
        logger.info(f"Rate limiter initialized: {rpm} RPM, burst={burst}")
    return _rate_limiter
