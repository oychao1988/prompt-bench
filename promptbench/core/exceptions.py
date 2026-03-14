# promptbench/core/exceptions.py
"""
PromptBench 异常体系

定义项目中所有异常的基类和子类，
提供清晰的错误分类和一致的错误处理。
"""

from typing import Optional, Any


class PromptBenchError(Exception):
    """
    PromptBench 项目所有异常的基类

    所有自定义异常都应该继承自此类，
    便于统一错误处理和日志记录。
    """

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """
        初始化异常

        Args:
            message: 错误消息
            details: 额外的错误详情（可选）
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigError(PromptBenchError):
    """
    配置错误（缺少 API key、无效配置等）

    当环境变量、.env 文件或 models.json 配置出现问题时抛出。
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None
    ):
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details)


class ModelError(PromptBenchError):
    """
    模型调用错误（API 失败、模型不存在等）

    当 LLM API 调用失败、模型不可用或返回错误响应时抛出。
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        details = {}
        if provider:
            details["provider"] = provider
        if model:
            details["model"] = model
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, details)


class EvaluationError(PromptBenchError):
    """
    评估过程错误

    当规则评估、AI评估或检测过程中出现错误时抛出。
    """

    def __init__(
        self,
        message: str,
        evaluation_type: Optional[str] = None,
        text_length: Optional[int] = None
    ):
        details = {}
        if evaluation_type:
            details["evaluation_type"] = evaluation_type
        if text_length is not None:
            details["text_length"] = text_length
        super().__init__(message, details)


class VersionError(PromptBenchError):
    """
    版本管理错误（版本不存在、文件找不到等）

    当提示词版本文件不存在、版本号无效或文件操作失败时抛出。
    """

    def __init__(
        self,
        message: str,
        version: Optional[int] = None,
        file_path: Optional[str] = None
    ):
        details = {}
        if version is not None:
            details["version"] = version
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, details)