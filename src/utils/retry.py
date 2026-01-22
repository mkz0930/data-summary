"""
重试装饰器模块
提供带指数退避的重试机制
"""

import time
import functools
from typing import Callable, Tuple, Type, Optional
from src.utils.logger import get_logger


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[object] = None
):
    """
    重试装饰器，支持指数退避

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型元组
        logger: 日志记录器，如果为None则使用默认logger

    Returns:
        装饰器函数

    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def fetch_data():
            # 可能失败的操作
            pass
    """
    if logger is None:
        logger = get_logger()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} 失败，已达到最大重试次数 {max_attempts}。"
                            f"最后的错误: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 第 {attempt} 次尝试失败: {str(e)}。"
                        f"{current_delay:.1f}秒后重试..."
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里，但为了类型检查
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[object] = None
):
    """
    异步重试装饰器，支持指数退避

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
        exceptions: 需要重试的异常类型元组
        logger: 日志记录器，如果为None则使用默认logger

    Returns:
        装饰器函数

    Example:
        @retry_async(max_attempts=3, delay=1.0, backoff=2.0)
        async def fetch_data():
            # 可能失败的异步操作
            pass
    """
    import asyncio

    if logger is None:
        logger = get_logger()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} 失败，已达到最大重试次数 {max_attempts}。"
                            f"最后的错误: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 第 {attempt} 次尝试失败: {str(e)}。"
                        f"{current_delay:.1f}秒后重试..."
                    )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里，但为了类型检查
            if last_exception:
                raise last_exception

        return wrapper
    return decorator


class RetryContext:
    """重试上下文管理器"""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        logger: Optional[object] = None
    ):
        """
        初始化重试上下文

        Args:
            max_attempts: 最大尝试次数
            delay: 初始延迟时间（秒）
            backoff: 退避倍数
            exceptions: 需要重试的异常类型元组
            logger: 日志记录器
        """
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.logger = logger or get_logger()

        self.attempt = 0
        self.current_delay = delay

    def __enter__(self):
        self.attempt += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return True

        if not issubclass(exc_type, self.exceptions):
            return False

        if self.attempt >= self.max_attempts:
            self.logger.error(
                f"操作失败，已达到最大重试次数 {self.max_attempts}。"
                f"最后的错误: {str(exc_val)}"
            )
            return False

        self.logger.warning(
            f"第 {self.attempt} 次尝试失败: {str(exc_val)}。"
            f"{self.current_delay:.1f}秒后重试..."
        )

        time.sleep(self.current_delay)
        self.current_delay *= self.backoff
        return True

    def should_retry(self) -> bool:
        """检查是否应该继续重试"""
        return self.attempt < self.max_attempts


def retry_with_context(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    使用上下文管理器的重试方式

    Example:
        retry_ctx = RetryContext(max_attempts=3)
        while retry_ctx.should_retry():
            with retry_ctx:
                # 可能失败的操作
                result = risky_operation()
                break
    """
    return RetryContext(
        max_attempts=max_attempts,
        delay=delay,
        backoff=backoff,
        exceptions=exceptions
    )
