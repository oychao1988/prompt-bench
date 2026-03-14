# promptbench/__init__.py
"""
PromptBench - 提示词评估与优化工具

一个专业的提示词评估与优化工具，通过多模型并行测试、
规则引擎评分、自动迭代优化，帮助您找到最佳提示词版本。
"""

__version__ = "2.0.0"
__author__ = "PromptBench Team"

from promptbench.core.exceptions import (
    PromptBenchError,
    ConfigError,
    ModelError,
    EvaluationError,
    VersionError
)

__all__ = [
    "PromptBenchError",
    "ConfigError",
    "ModelError",
    "EvaluationError",
    "VersionError",
]