"""
收集器基类模块
提供所有数据收集器的公共功能和工具方法
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from functools import wraps

from src.utils.logger import get_logger

T = TypeVar('T')


class RetryStrategy(Enum):
    """重试策略枚举"""
    EXPONENTIAL = 'exponential'  # 指数退避
    LINEAR = 'linear'  # 线性退避
    CONSTANT = 'constant'  # 固定间隔


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_errors: tuple = (Exception,)
    non_retryable_status_codes: tuple = (400, 401, 403, 404)


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    cooldown_period: float = 60.0


@dataclass
class CollectorStats:
    """收集器统计信息"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    total_items_collected: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100

    @property
    def duration(self) -> float:
        """持续时间（秒）"""
        if self.end_time == 0:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    @property
    def requests_per_second(self) -> float:
        """每秒请求数"""
        duration = self.duration
        if duration == 0:
            return 0.0
        return self.total_requests / duration

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'retried_requests': self.retried_requests,
            'total_items_collected': self.total_items_collected,
            'success_rate': round(self.success_rate, 2),
            'duration_seconds': round(self.duration, 2),
            'requests_per_second': round(self.requests_per_second, 2),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses
        }


class CircuitBreaker:
    """
    断路器模式实现

    防止在服务不可用时持续发送请求
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_requests: int = 3
    ):
        """
        初始化断路器

        Args:
            failure_threshold: 触发断路的失败次数
            recovery_timeout: 恢复超时时间（秒）
            half_open_requests: 半开状态允许的请求数
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests

        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state = 'closed'  # closed, open, half_open
        self._half_open_successes = 0

    @property
    def is_open(self) -> bool:
        """断路器是否打开"""
        if self._state == 'open':
            # 检查是否可以进入半开状态
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = 'half_open'
                self._half_open_successes = 0
                return False
            return True
        return False

    def record_success(self):
        """记录成功"""
        if self._state == 'half_open':
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_requests:
                self._state = 'closed'
                self._failure_count = 0
        else:
            self._failure_count = 0

    def record_failure(self):
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = 'open'

    def reset(self):
        """重置断路器"""
        self._failure_count = 0
        self._state = 'closed'
        self._half_open_successes = 0


class RateLimiter:
    """
    速率限制器

    使用令牌桶算法控制请求速率
    """

    def __init__(self, config: RateLimitConfig):
        """
        初始化速率限制器

        Args:
            config: 速率限制配置
        """
        self.config = config
        self._tokens = config.burst_size
        self._last_update = time.time()
        self._lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None

    async def acquire(self):
        """异步获取令牌"""
        while True:
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(
                self.config.burst_size,
                self._tokens + elapsed * self.config.requests_per_second
            )
            self._last_update = now

            if self._tokens >= 1:
                self._tokens -= 1
                return

            # 等待直到有令牌可用
            wait_time = (1 - self._tokens) / self.config.requests_per_second
            await asyncio.sleep(wait_time)

    def acquire_sync(self):
        """同步获取令牌"""
        while True:
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(
                self.config.burst_size,
                self._tokens + elapsed * self.config.requests_per_second
            )
            self._last_update = now

            if self._tokens >= 1:
                self._tokens -= 1
                return

            # 等待直到有令牌可用
            wait_time = (1 - self._tokens) / self.config.requests_per_second
            time.sleep(wait_time)


class BaseCollector(ABC):
    """
    收集器基类

    提供所有数据收集器共用的功能：
    - 重试机制（指数退避）
    - 速率限制
    - 断路器模式
    - 统计信息
    - 日志记录
    """

    def __init__(
        self,
        name: str = "BaseCollector",
        retry_config: Optional[RetryConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        enable_circuit_breaker: bool = True
    ):
        """
        初始化收集器

        Args:
            name: 收集器名称
            retry_config: 重试配置
            rate_limit_config: 速率限制配置
            enable_circuit_breaker: 是否启用断路器
        """
        self.name = name
        self.logger = get_logger()

        # 配置
        self.retry_config = retry_config or RetryConfig()
        self.rate_limit_config = rate_limit_config or RateLimitConfig()

        # 组件
        self.rate_limiter = RateLimiter(self.rate_limit_config)
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None

        # 统计
        self.stats = CollectorStats()

    @abstractmethod
    def collect(self, *args, **kwargs) -> Any:
        """
        执行数据收集（子类必须实现）

        Returns:
            收集到的数据
        """
        pass

    # ==================== 重试机制 ====================

    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟

        Args:
            attempt: 当前尝试次数（从1开始）

        Returns:
            延迟时间（秒）
        """
        config = self.retry_config

        if config.strategy == RetryStrategy.EXPONENTIAL:
            # 指数退避: 1s, 2s, 4s, 8s, 16s...
            delay = config.base_delay * (2 ** (attempt - 1))
        elif config.strategy == RetryStrategy.LINEAR:
            # 线性退避: 1s, 2s, 3s, 4s...
            delay = config.base_delay * attempt
        else:
            # 固定间隔
            delay = config.base_delay

        return min(delay, config.max_delay)

    def is_retryable_error(self, error: Exception) -> bool:
        """
        判断错误是否可重试

        Args:
            error: 异常对象

        Returns:
            是否可重试
        """
        # 检查HTTP状态码
        if hasattr(error, 'status_code'):
            if error.status_code in self.retry_config.non_retryable_status_codes:
                return False
            # 429 (Too Many Requests) 和 5xx 错误可重试
            if error.status_code == 429 or error.status_code >= 500:
                return True

        # 检查错误类型
        return isinstance(error, self.retry_config.retryable_errors)

    def with_retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        重试装饰器

        Args:
            func: 要包装的函数

        Returns:
            包装后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None

            for attempt in range(1, self.retry_config.max_attempts + 1):
                try:
                    # 检查断路器
                    if self.circuit_breaker and self.circuit_breaker.is_open:
                        raise Exception("断路器已打开，服务暂时不可用")

                    # 速率限制
                    self.rate_limiter.acquire_sync()

                    # 执行请求
                    self.stats.total_requests += 1
                    result = func(*args, **kwargs)

                    # 成功
                    self.stats.successful_requests += 1
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()

                    return result

                except Exception as e:
                    last_error = e
                    self.stats.failed_requests += 1

                    if self.circuit_breaker:
                        self.circuit_breaker.record_failure()

                    # 判断是否可重试
                    if not self.is_retryable_error(e):
                        self.log_error(f"不可重试的错误: {e}")
                        raise

                    # 最后一次尝试失败
                    if attempt >= self.retry_config.max_attempts:
                        self.log_error(f"重试 {attempt} 次后仍然失败: {e}")
                        raise

                    # 计算延迟并等待
                    delay = self.calculate_delay(attempt)
                    self.log_warning(
                        f"请求失败 (尝试 {attempt}/{self.retry_config.max_attempts}), "
                        f"{delay:.1f}秒后重试: {e}"
                    )
                    self.stats.retried_requests += 1
                    time.sleep(delay)

            raise last_error

        return wrapper

    async def with_retry_async(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        异步重试执行

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值
        """
        last_error = None

        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                # 检查断路器
                if self.circuit_breaker and self.circuit_breaker.is_open:
                    raise Exception("断路器已打开，服务暂时不可用")

                # 速率限制
                await self.rate_limiter.acquire()

                # 执行请求
                self.stats.total_requests += 1
                result = await func(*args, **kwargs)

                # 成功
                self.stats.successful_requests += 1
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

                return result

            except Exception as e:
                last_error = e
                self.stats.failed_requests += 1

                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()

                # 判断是否可重试
                if not self.is_retryable_error(e):
                    self.log_error(f"不可重试的错误: {e}")
                    raise

                # 最后一次尝试失败
                if attempt >= self.retry_config.max_attempts:
                    self.log_error(f"重试 {attempt} 次后仍然失败: {e}")
                    raise

                # 计算延迟并等待
                delay = self.calculate_delay(attempt)
                self.log_warning(
                    f"请求失败 (尝试 {attempt}/{self.retry_config.max_attempts}), "
                    f"{delay:.1f}秒后重试: {e}"
                )
                self.stats.retried_requests += 1
                await asyncio.sleep(delay)

        raise last_error

    # ==================== 批量处理 ====================

    async def batch_collect_async(
        self,
        items: List[Any],
        collect_func: Callable[[Any], Any],
        batch_size: int = 10,
        max_concurrent: int = 5
    ) -> List[Any]:
        """
        异步批量收集

        Args:
            items: 要处理的项目列表
            collect_func: 收集函数
            batch_size: 批次大小
            max_concurrent: 最大并发数

        Returns:
            收集结果列表
        """
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_item(item):
            async with semaphore:
                return await self.with_retry_async(collect_func, item)

        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[process_item(item) for item in batch],
                return_exceptions=True
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    self.log_error(f"批量处理项目失败: {result}")
                    results.append(None)
                else:
                    results.append(result)

        return results

    def batch_collect_sync(
        self,
        items: List[Any],
        collect_func: Callable[[Any], Any],
        batch_size: int = 10
    ) -> List[Any]:
        """
        同步批量收集

        Args:
            items: 要处理的项目列表
            collect_func: 收集函数
            batch_size: 批次大小

        Returns:
            收集结果列表
        """
        results = []
        wrapped_func = self.with_retry(collect_func)

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            for item in batch:
                try:
                    result = wrapped_func(item)
                    results.append(result)
                except Exception as e:
                    self.log_error(f"处理项目失败: {e}")
                    results.append(None)

        return results

    # ==================== 统计方法 ====================

    def start_collection(self):
        """开始收集（重置统计）"""
        self.stats = CollectorStats()
        self.stats.start_time = time.time()
        self.log_info("开始数据收集")

    def end_collection(self):
        """结束收集"""
        self.stats.end_time = time.time()
        self.log_info(
            f"数据收集完成: "
            f"总请求 {self.stats.total_requests}, "
            f"成功 {self.stats.successful_requests}, "
            f"失败 {self.stats.failed_requests}, "
            f"重试 {self.stats.retried_requests}, "
            f"耗时 {self.stats.duration:.2f}秒"
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.to_dict()

    # ==================== 日志方法 ====================

    def log_info(self, message: str):
        """记录信息日志"""
        self.logger.info(f"[{self.name}] {message}")

    def log_warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(f"[{self.name}] {message}")

    def log_error(self, message: str):
        """记录错误日志"""
        self.logger.error(f"[{self.name}] {message}")

    def log_debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(f"[{self.name}] {message}")
