# promptbench/core/__init__.py
"""核心模块 - 配置、数据模型、异常和常量"""

from .config import ConfigManager, Config
from .entities import (
    ModelConfig,
    RuleEvaluation,
    AIEvaluation,
    DetectionResult,
    EvaluationResult,
    VersionSummary,
    PromptVersion
)
from .exceptions import (
    PromptBenchError,
    ConfigError,
    ModelError,
    EvaluationError,
    VersionError
)
from .constants import (
    DEFAULT_RULE_WEIGHTS,
    DEFAULT_AI_WEIGHTS,
    SCORING_RULES
)

__all__ = [
    # Config
    "ConfigManager",
    "Config",
    # Entities
    "ModelConfig",
    "RuleEvaluation",
    "AIEvaluation",
    "DetectionResult",
    "EvaluationResult",
    "VersionSummary",
    "PromptVersion",
    # Exceptions
    "PromptBenchError",
    "ConfigError",
    "ModelError",
    "EvaluationError",
    "VersionError",
    # Constants
    "DEFAULT_RULE_WEIGHTS",
    "DEFAULT_AI_WEIGHTS",
    "SCORING_RULES"
]