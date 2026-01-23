"""
日志工具模块
提供统一的日志记录功能，支持文件和控制台输出
增强功能：结构化日志、性能追踪、上下文管理
"""

import logging
import sys
import json
import time
import functools
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from logging.handlers import RotatingFileHandler
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'operation': self.operation,
            'duration_ms': round(self.duration * 1000, 2),
            'success': self.success,
            'error': self.error,
            'metadata': self.metadata,
            'timestamp': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
        }


class ConsoleFormatter(logging.Formatter):
    """自定义控制台格式化器，根据日志级别显示不同格式"""

    def format(self, record):
        # WARNING和ERROR显示级别标识
        if record.levelno >= logging.WARNING:
            return f"[{record.levelname}] {record.getMessage()}"
        # INFO和DEBUG只显示消息
        return record.getMessage()


class JsonFormatter(logging.Formatter):
    """JSON 格式化器，用于结构化日志"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data

        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class Logger:
    """日志管理器（增强版）"""

    def __init__(
        self,
        name: str = "data_summary",
        log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
        console_output: bool = True,
        file_output: bool = True,
        json_output: bool = False,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        初始化日志管理器

        Args:
            name: 日志记录器名称
            log_dir: 日志文件目录
            log_level: 日志级别
            console_output: 是否输出到控制台
            file_output: 是否输出到文件
            json_output: 是否输出 JSON 格式日志
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的日志文件数量
        """
        self.name = name
        self.log_level = log_level
        self.json_output = json_output

        # 性能追踪存储
        self._performance_metrics: list = []

        # 设置日志目录
        if log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            log_dir = project_root / "logs"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.logger.handlers.clear()  # 清除已有的处理器

        # 日志格式
        self.file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 使用自定义控制台格式化器
        self.console_formatter = ConsoleFormatter()

        # JSON 格式化器
        self.json_formatter = JsonFormatter()

        # 添加控制台处理器
        if console_output:
            self._add_console_handler()

        # 添加文件处理器
        if file_output:
            self._add_file_handler(max_bytes, backup_count)

        # 添加 JSON 文件处理器
        if json_output:
            self._add_json_handler(max_bytes, backup_count)

    def _add_console_handler(self) -> None:
        """添加控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(self.console_formatter)
        self.logger.addHandler(console_handler)

    def _add_file_handler(self, max_bytes: int, backup_count: int) -> None:
        """添加文件处理器（支持日志轮转）"""
        # 使用日期作为日志文件名
        log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(file_handler)

    def _add_json_handler(self, max_bytes: int, backup_count: int) -> None:
        """添加 JSON 格式文件处理器"""
        json_log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.json.log"

        json_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        json_handler.setLevel(self.log_level)
        json_handler.setFormatter(self.json_formatter)
        self.logger.addHandler(json_handler)

    def debug(self, message: str, *args, **kwargs) -> None:
        """记录DEBUG级别日志"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """记录INFO级别日志"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """记录WARNING级别日志"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """记录ERROR级别日志"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """记录CRITICAL级别日志"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """记录异常信息"""
        self.logger.exception(message, *args, **kwargs)

    def set_level(self, level: int) -> None:
        """设置日志级别"""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)

    # ==================== 结构化日志方法 ====================

    def log_with_data(
        self,
        level: int,
        message: str,
        data: Dict[str, Any]
    ) -> None:
        """
        记录带有结构化数据的日志

        Args:
            level: 日志级别
            message: 日志消息
            data: 附加数据
        """
        record = self.logger.makeRecord(
            self.name, level, "", 0, message, (), None
        )
        record.extra_data = data
        self.logger.handle(record)

    def info_with_data(self, message: str, data: Dict[str, Any]) -> None:
        """记录带数据的 INFO 日志"""
        self.log_with_data(logging.INFO, message, data)

    def warning_with_data(self, message: str, data: Dict[str, Any]) -> None:
        """记录带数据的 WARNING 日志"""
        self.log_with_data(logging.WARNING, message, data)

    def error_with_data(self, message: str, data: Dict[str, Any]) -> None:
        """记录带数据的 ERROR 日志"""
        self.log_with_data(logging.ERROR, message, data)

    # ==================== 性能追踪方法 ====================

    @contextmanager
    def track_performance(
        self,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        性能追踪上下文管理器

        Args:
            operation: 操作名称
            metadata: 附加元数据

        Yields:
            PerformanceMetrics 对象

        Example:
            with logger.track_performance("数据采集", {"keyword": "camping"}) as metrics:
                # 执行操作
                pass
            print(f"耗时: {metrics.duration}秒")
        """
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            metadata=metadata or {}
        )

        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise
        finally:
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time

            # 记录性能日志
            self._log_performance(metrics)

            # 存储指标
            self._performance_metrics.append(metrics)

    def _log_performance(self, metrics: PerformanceMetrics) -> None:
        """记录性能日志"""
        status = "成功" if metrics.success else "失败"
        duration_ms = metrics.duration * 1000

        message = f"[性能] {metrics.operation} - {status} - {duration_ms:.2f}ms"

        if metrics.metadata:
            meta_str = ", ".join(f"{k}={v}" for k, v in metrics.metadata.items())
            message += f" ({meta_str})"

        if metrics.success:
            self.info(message)
        else:
            self.error(f"{message} - 错误: {metrics.error}")

    def log_performance(
        self,
        operation: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        手动记录性能指标

        Args:
            operation: 操作名称
            duration: 持续时间（秒）
            metadata: 附加元数据
        """
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=time.time() - duration,
            end_time=time.time(),
            duration=duration,
            metadata=metadata or {}
        )
        self._log_performance(metrics)
        self._performance_metrics.append(metrics)

    def log_api_call(
        self,
        api: str,
        status: int,
        latency: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录 API 调用日志

        Args:
            api: API 名称或 URL
            status: HTTP 状态码
            latency: 延迟（秒）
            metadata: 附加元数据
        """
        success = 200 <= status < 400
        status_text = "成功" if success else "失败"

        message = f"[API] {api} - {status} {status_text} - {latency * 1000:.2f}ms"

        data = {
            'api': api,
            'status_code': status,
            'latency_ms': round(latency * 1000, 2),
            'success': success,
            **(metadata or {})
        }

        if success:
            self.info_with_data(message, data) if self.json_output else self.info(message)
        else:
            self.warning_with_data(message, data) if self.json_output else self.warning(message)

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要

        Returns:
            性能统计摘要
        """
        if not self._performance_metrics:
            return {'total_operations': 0}

        total = len(self._performance_metrics)
        successful = sum(1 for m in self._performance_metrics if m.success)
        failed = total - successful

        durations = [m.duration for m in self._performance_metrics]
        total_duration = sum(durations)
        avg_duration = total_duration / total if total > 0 else 0

        # 按操作分组统计
        by_operation = {}
        for m in self._performance_metrics:
            if m.operation not in by_operation:
                by_operation[m.operation] = {
                    'count': 0,
                    'success': 0,
                    'failed': 0,
                    'total_duration': 0,
                    'durations': []
                }
            by_operation[m.operation]['count'] += 1
            by_operation[m.operation]['total_duration'] += m.duration
            by_operation[m.operation]['durations'].append(m.duration)
            if m.success:
                by_operation[m.operation]['success'] += 1
            else:
                by_operation[m.operation]['failed'] += 1

        # 计算每个操作的平均时间
        for op, stats in by_operation.items():
            stats['avg_duration'] = stats['total_duration'] / stats['count']
            stats['min_duration'] = min(stats['durations'])
            stats['max_duration'] = max(stats['durations'])
            del stats['durations']  # 移除原始数据

        return {
            'total_operations': total,
            'successful': successful,
            'failed': failed,
            'success_rate': round(successful / total * 100, 2) if total > 0 else 0,
            'total_duration_seconds': round(total_duration, 2),
            'avg_duration_seconds': round(avg_duration, 4),
            'by_operation': by_operation
        }

    def clear_performance_metrics(self) -> None:
        """清空性能指标"""
        self._performance_metrics.clear()


def performance_tracker(operation: str = None, metadata: Dict[str, Any] = None):
    """
    性能追踪装饰器

    Args:
        operation: 操作名称（默认使用函数名）
        metadata: 附加元数据

    Example:
        @performance_tracker("数据分析")
        def analyze_data():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            logger = get_logger()

            with logger.track_performance(op_name, metadata):
                return func(*args, **kwargs)

        return wrapper
    return decorator


# 全局日志实例
_logger_instance: Optional[Logger] = None


def get_logger() -> Logger:
    """
    获取全局日志实例（单例模式）

    Returns:
        Logger实例
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance


def init_logger(
    name: str = "data_summary",
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True
) -> Logger:
    """
    初始化全局日志实例

    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        log_level: 日志级别
        console_output: 是否输出到控制台
        file_output: 是否输出到文件

    Returns:
        Logger实例
    """
    global _logger_instance
    _logger_instance = Logger(
        name=name,
        log_dir=log_dir,
        log_level=log_level,
        console_output=console_output,
        file_output=file_output
    )
    return _logger_instance


# 便捷函数
def debug(message: str, *args, **kwargs) -> None:
    """记录DEBUG级别日志"""
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs) -> None:
    """记录INFO级别日志"""
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs) -> None:
    """记录WARNING级别日志"""
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs) -> None:
    """记录ERROR级别日志"""
    get_logger().error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs) -> None:
    """记录CRITICAL级别日志"""
    get_logger().critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs) -> None:
    """记录异常信息"""
    get_logger().exception(message, *args, **kwargs)
