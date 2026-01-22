"""
日志工具模块
提供统一的日志记录功能，支持文件和控制台输出
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime


class Logger:
    """日志管理器"""

    def __init__(
        self,
        name: str = "data_summary",
        log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
        console_output: bool = True,
        file_output: bool = True,
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
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的日志文件数量
        """
        self.name = name
        self.log_level = log_level

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

        self.console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # 添加控制台处理器
        if console_output:
            self._add_console_handler()

        # 添加文件处理器
        if file_output:
            self._add_file_handler(max_bytes, backup_count)

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
