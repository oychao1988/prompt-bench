# promptbench/utils/log.py
"""
日志工具

提供日志记录功能。
"""

import logging
from typing import Optional
from pathlib import Path


class LogUtils:
    """日志工具类"""

    _logger: Optional[logging.Logger] = None
    _initialized = False

    @classmethod
    def init_logger(
        cls,
        name: str = "promptbench",
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
    ) -> logging.Logger:
        """
        初始化日志记录器

        Args:
            name: 日志记录器名称
            level: 日志级别
            log_file: 日志文件路径（可选）

        Returns:
            日志记录器实例
        """
        if cls._initialized:
            return cls._logger

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 文件输出（如果指定）
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        cls._logger = logger
        cls._initialized = True

        return logger

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """
        获取日志记录器实例

        Returns:
            日志记录器实例
        """
        if cls._logger is None:
            cls.init_logger()
        return cls._logger

    @classmethod
    def info(cls, message: str) -> None:
        """
        记录 INFO 级别日志

        Args:
            message: 日志消息
        """
        cls.get_logger().info(message)

    @classmethod
    def warning(cls, message: str) -> None:
        """
        记录 WARNING 级别日志

        Args:
            message: 日志消息
        """
        cls.get_logger().warning(message)

    @classmethod
    def error(cls, message: str) -> None:
        """
        记录 ERROR 级别日志

        Args:
            message: 日志消息
        """
        cls.get_logger().error(message)

    @classmethod
    def debug(cls, message: str) -> None:
        """
        记录 DEBUG 级别日志

        Args:
            message: 日志消息
        """
        cls.get_logger().debug(message)
