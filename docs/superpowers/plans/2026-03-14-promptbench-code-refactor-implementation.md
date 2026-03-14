# PromptBench 代码重构实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 将单文件的 promptbench 评估工具（~900行）重构为模块化架构，提高可维护性、可测试性，并完善类型注解和错误处理。

**架构:** 采用功能导向拆分，创建6个核心模块（core、evaluators、detectors、optimizers、models、versions）+ CLI接口，保持现有功能完全不变。

**技术栈:** Python 3.12 + OpenAI SDK（保持不变）+ dataclasses + pathlib + concurrent.futures

---

## 文件结构映射

### 新增文件（按创建顺序）
```
promptbench/
├── __init__.py                    # 包入口
├── core/
│   ├── __init__.py
│   ├── config.py                  # 配置管理（环境变量、.env解析）
│   ├── entities.py                # 数据模型（领域实体、数据传输对象）
│   ├── exceptions.py              # 异常定义（PromptBenchError 及子类）
│   └── constants.py               # 常量定义（评分标准、默认配置）
├── evaluators/
│   ├── __init__.py
│   ├── base.py                    # 评估器基类
│   ├── rule_evaluator.py          # 规则评估（长度、段落、结构）
│   └── ai_evaluator.py            # AI语义评估（开头、引用、深度、流畅、情感）
├── detectors/
│   ├── __init__.py
│   ├── base.py                    # 检测器基类
│   ├── zhuque.py                  # 朱雀检测（腾讯）
│   ├── gptzero.py                 # GPTZero检测
│   ├── copyleaks.py               # Copyleaks检测
│   └── multi_detector.py          # 多检测器管理
├── models/
│   ├── __init__.py
│   ├── client.py                  # 统一模型调用接口
│   ├── provider.py                # 模型提供方配置
│   └── connectivity.py            # 连通性测试
├── versions/
│   ├── __init__.py
│   ├── prompt_manager.py          # 提示词文件管理
│   └── history_manager.py         # 评估历史追踪
├── optimizers/
│   ├── __init__.py
│   ├── base.py                    # 优化器基类
│   ├── llm_optimizer.py           # LLM提示词优化
│   └── summarizer.py              # 评估总结生成
├── cli/
│   ├── __init__.py
│   ├── main.py                    # 主CLI入口
│   └── commands/
│       ├── __init__.py
│       ├── evaluate.py
│       ├── ranking.py
│       └── create_version.py
├── utils/
│   ├── __init__.py
│   ├── text.py                    # 文本处理工具
│   ├── file.py                    # 文件操作工具
│   └── log.py                     # 日志管理
└── tests/
    ├── __init__.py
    ├── test_core.py
    ├── test_evaluators.py
    ├── test_detectors.py
    ├── test_models.py
    ├── test_versions.py
    └── test_optimizers.py
```

### 修改文件
- `evaluate_prompts.py` → 保留为向后兼容层（CLI兼容）
- `models.json` → 保持不变
- `.env` → 保持不变
- `prompts/*.md` → 保持不变
- `outputs/` → 保持不变

---

## Chunk 1: 核心基础设施（core/）

### Task 1: 创建包结构

**Files:**
- Create: `promptbench/__init__.py`
- Create: `promptbench/core/__init__.py`

- [ ] **Step 1: 创建包入口文件**

```python
# promptbench/__init__.py
"""
PromptBench - 提示词评估与优化工具

一个专业的提示词评估与优化工具，通过多模型并行测试、
规则引擎评分、自动迭代优化，帮助您找到最佳提示词版本。
"""

__version__ = "2.0.0"
__author__ = "PromptBench Team"

from promptbench.core import ConfigManager
from promptbench.core.entities import (
    ModelConfig,
    RuleEvaluation,
    AIEvaluation,
    DetectionResult,
    EvaluationResult,
    VersionSummary,
    PromptVersion
)

__all__ = [
    "ConfigManager",
    "ModelConfig",
    "RuleEvaluation",
    "AIEvaluation",
    "DetectionResult",
    "EvaluationResult",
    "VersionSummary",
    "PromptVersion",
]
```

- [ ] **Step 2: 创建core模块初始化文件**

```python
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
```

- [ ] **Step 3: 提交初始包结构**

```bash
git add promptbench/__init__.py promptbench/core/__init__.py
git commit -m "feat: 创建包结构和core模块初始化文件"
```

---

### Task 2: 实现异常体系

**Files:**
- Create: `promptbench/core/exceptions.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: 编写异常类的测试**

```python
# tests/test_core.py
import pytest
from promptbench.core.exceptions import (
    PromptBenchError,
    ConfigError,
    ModelError,
    EvaluationError,
    VersionError
)

def test_prompt_bench_error_base():
    """测试基础异常类"""
    error = PromptBenchError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)

def test_config_error():
    """测试配置错误"""
    error = ConfigError("Missing API key")
    assert isinstance(error, PromptBenchError)
    assert "API key" in str(error)

def test_model_error():
    """测试模型错误"""
    error = ModelError("API call failed")
    assert isinstance(error, PromptBenchError)

def test_evaluation_error():
    """测试评估错误"""
    error = EvaluationError("Invalid evaluation result")
    assert isinstance(error, PromptBenchError)

def test_version_error():
    """测试版本错误"""
    error = VersionError("Version not found")
    assert isinstance(error, PromptBenchError)
```

- [ ] **Step 2: 运行测试（预期失败）**

```bash
pytest tests/test_core.py -v
```
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现异常体系**

```python
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
```

- [ ] **Step 4: 运行测试（预期通过）**

```bash
pytest tests/test_core.py::test_prompt_bench_error_base -v
pytest tests/test_core.py::test_config_error -v
pytest tests/test_core.py::test_model_error -v
pytest tests/test_core.py::test_evaluation_error -v
pytest tests/test_core.py::test_version_error -v
```
Expected: All PASS

- [ ] **Step 5: 提交异常体系实现**

```bash
git add promptbench/core/exceptions.py tests/test_core.py
git commit -m "feat: 实现异常体系

- 添加 PromptBenchError 基类
- 实现 ConfigError、ModelError、EvaluationError、VersionError
- 所有异常支持详细错误信息
- 添加完整的单元测试"
```

---

### Task 3: 实现常量定义

**Files:**
- Create: `promptbench/core/constants.py`
- Test: `tests/test_core.py` (add tests)

- [ ] **Step 1: 添加常量测试**

```python
# tests/test_core.py (add to existing file)

def test_default_rule_weights():
    """测试默认规则权重"""
    from promptbench.core.constants import DEFAULT_RULE_WEIGHTS

    assert DEFAULT_RULE_WEIGHTS["in_length_range"] == 1.0
    assert DEFAULT_RULE_WEIGHTS["para_count_reasonable"] == 0.7
    assert DEFAULT_RULE_WEIGHTS["avg_para_length_ok"] == 0.3
    assert DEFAULT_RULE_WEIGHTS["has_3_points"] == 0.6
    assert DEFAULT_RULE_WEIGHTS["has_headings"] == 0.4

def test_default_ai_weights():
    """测试默认AI评估权重"""
    from promptbench.core.constants import DEFAULT_AI_WEIGHTS

    assert DEFAULT_AI_WEIGHTS["intro_quality"] == 0.6
    assert DEFAULT_AI_WEIGHTS["classic_naturalness"] == 0.6
    assert DEFAULT_AI_WEIGHTS["content_depth"] == 0.6
    assert DEFAULT_AI_WEIGHTS["writing_fluency"] == 0.6
    assert DEFAULT_AI_WEIGHTS["emotional_resonance"] == 0.6

def test_scoring_rules():
    """测试评分规则"""
    from promptbench.core.constants import SCORING_RULES

    assert SCORING_RULES["total_score"] == 10
    assert SCORING_RULES["quality_score"] == 6
    assert SCORING_RULES["detection_score"] == 4
```

- [ ] **Step 2: 运行测试（预期失败）**

```bash
pytest tests/test_core.py::test_default_rule_weights -v
```
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现常量定义**

```python
# promptbench/core/constants.py
"""
常量定义

包含评分标准、默认配置和系统常量。
"""

from typing import Dict, Final

# ====== 规则评估权重 ======
DEFAULT_RULE_WEIGHTS: Final[Dict[str, float]] = {
    "in_length_range": 1.0,
    "para_count_reasonable": 0.7,
    "avg_para_length_ok": 0.3,
    "has_3_points": 0.6,
    "has_headings": 0.4,
}

# ====== AI语义评估权重 ======
DEFAULT_AI_WEIGHTS: Final[Dict[str, float]] = {
    "intro_quality": 0.6,
    "classic_naturalness": 0.6,
    "content_depth": 0.6,
    "writing_fluency": 0.6,
    "emotional_resonance": 0.6,
}

# ====== 评分规则总览 ======
SCORING_RULES: Final[Dict[str, float]] = {
    "total_score": 10.0,        # 总分
    "quality_score": 6.0,        # 质量评估（规则3分 + AI评估3分）
    "rule_score": 3.0,           # 规则评估
    "ai_score": 3.0,             # AI语义评估
    "detection_score": 4.0,      # AI检测
}

# ====== 文本长度默认范围 ======
DEFAULT_LENGTH_RANGE: Final[tuple[int, int]] = (400, 1500)

# ====== 段落数量合理范围 ======
REASONABLE_PARAGRAPH_COUNT: Final[tuple[int, int]] = (5, 20)

# ====== 段落长度合理范围 ======
REASONABLE_PARAGRAPH_LENGTH: Final[tuple[int, int]] = (30, 150)

# ====== 最小观点段落数 ======
MIN_POINT_PARAGRAPHS: Final[int] = 3

# ====== AI检测评分 ======
AI_DETECTION_MAX_SCORE: Final[float] = 4.0

# ====== 小标题正则模式 ======
HEADING_PATTERNS: Final[list[str]] = [
    r"^##\s",       # Markdown 标题
    r"^#\s",        # Markdown 一级标题
    r"^\d+\s*[、.．]",  # 数字序号：1. 1、 1．
    r"^[一二三四五六七八九十]+\\s*[、.．]",  # 中文数字
    r"^[其第]?[一二三四五六七八九十]+[个项]",  # 其一、第二、三项
    r"^首先\\s", "^其次\\s", "^最后\\s",  # 顺序词
    r"^第一\\s", "^第二\\s", "^第三\\s",  # 序数词
]

# ====== 默认模型配置 ======
DEFAULT_EVALUATION_MODEL: Final[str] = "gpt-5.4"
DEFAULT_OPTIMIZER_MODEL: Final[str] = "gpt-5.4"

# ====== 文件路径常量 ======
MODELS_FILE: Final[str] = "models.json"
PROMPTS_DIR: Final[str] = "prompts"
OUTPUTS_DIR: Final[str] = "outputs"
HISTORY_FILE: Final[str] = "evaluations_history.json"
```

- [ ] **Step 4: 运行测试（预期通过）**

```bash
pytest tests/test_core.py::test_default_rule_weights -v
pytest tests/test_core.py::test_default_ai_weights -v
pytest tests/test_core.py::test_scoring_rules -v
```
Expected: All PASS

- [ ] **Step 5: 提交常量定义**

```bash
git add promptbench/core/constants.py tests/test_core.py
git commit -m "feat: 实现常量定义

- 添加规则评估和AI评估权重常量
- 定义评分规则总览
- 添加文本和段落长度范围常量
- 实现小标题检测正则模式
- 添加完整的单元测试"
```

---

### Task 4: 实现数据模型

**Files:**
- Create: `promptbench/core/entities.py`
- Test: `tests/test_core.py` (add tests)

- [ ] **Step 1: 添加数据模型测试**

```python
# tests/test_core.py (add to existing file)

def test_model_config():
    """测试模型配置数据类"""
    from promptbench.core.entities import ModelConfig

    config = ModelConfig(
        provider="openai",
        name="gpt-4o",
        enabled=True,
        input_price="$5.00/M",
        output_price="$15.00/M"
    )

    assert config.provider == "openai"
    assert config.name == "gpt-4o"
    assert config.enabled is True
    assert config.input_price == "$5.00/M"

def test_rule_evaluation():
    """测试规则评估结果"""
    from promptbench.core.entities import RuleEvaluation

    result = RuleEvaluation(
        rule_score=2.5,
        in_length_range=True,
        para_count_reasonable=True,
        avg_para_length_ok=False,
        has_3_points=True,
        has_headings=False,
        chars=1200,
        paragraphs=8,
        avg_para_length=150.0,
        length_range="1000-1500"
    )

    assert result.rule_score == 2.5
    assert result.in_length_range is True
    assert result.chars == 1200

def test_evaluation_result():
    """测试完整评估结果"""
    from promptbench.core.entities import EvaluationResult, RuleEvaluation

    rule_details = RuleEvaluation(
        rule_score=2.5,
        in_length_range=True,
        para_count_reasonable=True,
        avg_para_length_ok=True,
        has_3_points=True,
        has_headings=True,
        chars=1200,
        paragraphs=8,
        avg_para_length=150.0,
        length_range="1000-1500"
    )

    result = EvaluationResult(
        provider="openai",
        model="gpt-4o",
        rule_score=2.5,
        ai_score=2.1,
        detection_score=3.2,
        total_score=7.8,
        rule_details=rule_details,
        ai_details={"ai_score": 2.1, "ai_details": {}},
        detection_details={"ai_score": 0.2, "ai_percentage": 20},
        chars=1200,
        paragraphs=8,
        output_path=None
    )

    assert result.total_score == 7.8
    assert result.provider == "openai"
```

- [ ] **Step 2: 运行测试（预期失败）**

```bash
pytest tests/test_core.py::test_model_config -v
```
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现数据模型**

```python
# promptbench/core/entities.py
"""
数据模型定义

定义所有领域实体和数据传输对象（DTO），
使用 dataclass 提供类型安全和默认值。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


# ====== 模型配置 ======

@dataclass
class ModelConfig:
    """模型配置"""
    provider: str
    name: str
    enabled: bool
    input_price: Optional[str] = None
    output_price: Optional[str] = None
    description: Optional[str] = None


# ====== 规则评估结果 ======

@dataclass
class RuleEvaluation:
    """规则评估结果"""
    rule_score: float
    in_length_range: bool
    para_count_reasonable: bool
    avg_para_length_ok: bool
    has_3_points: bool
    has_headings: bool
    chars: int
    paragraphs: int
    avg_para_length: float
    length_range: str


# ====== AI评估结果 ======

@dataclass
class AIEvaluation:
    """AI语义评估结果"""
    ai_score: float
    ai_details: Dict[str, Any]
    error: Optional[str] = None


# ====== AI检测结果 ======

@dataclass
class DetectionResult:
    """AI检测结果"""
    ai_score: float
    ai_percentage: int
    human_percentage: int
    detector_results: List[Dict[str, Any]]
    detector_count: int
    confidence: str


# ====== 完整评估结果 ======

@dataclass
class EvaluationResult:
    """单篇文章的完整评估结果"""
    provider: str
    model: str
    rule_score: float          # 0-3分
    ai_score: float            # 0-3分
    detection_score: float     # 0-4分
    total_score: float         # 0-10分
    rule_details: RuleEvaluation
    ai_details: AIEvaluation
    detection_details: DetectionResult
    chars: int
    paragraphs: int
    output_path: Optional[Path] = None


# ====== 版本总结 ======

@dataclass
class VersionSummary:
    """某个提示词版本的总结"""
    version: int
    avg_score: float
    max_score: float
    min_score: float
    model_count: int
    evaluation_time: datetime
    results: List[EvaluationResult] = field(default_factory=list)


# ====== 提示词版本 ======

@dataclass
class PromptVersion:
    """提示词版本信息"""
    version: int
    content: str
    path: Path
    created_at: datetime
```

- [ ] **Step 4: 运行测试（预期通过）**

```bash
pytest tests/test_core.py::test_model_config -v
pytest tests/test_core.py::test_rule_evaluation -v
pytest tests/test_core.py::test_evaluation_result -v
```
Expected: All PASS

- [ ] **Step 5: 提交数据模型实现**

```bash
git add promptbench/core/entities.py tests/test_core.py
git commit -m "feat: 实现核心数据模型

- 添加 ModelConfig 数据类
- 实现 RuleEvaluation 规则评估结果
- 实现 AIEvaluation AI评估结果
- 实现 DetectionResult AI检测结果
- 实现 EvaluationResult 完整评估结果
- 实现 VersionSummary 版本总结
- 实现 PromptVersion 提示词版本
- 所有模型使用 dataclass，提供类型安全
- 添加完整的单元测试"
```

---

## Chunk 1 审查检查点

在继续之前，让我对 Chunk 1 进行自我审查：

✅ **完整性**: 包含了所有核心基础设施的实现（异常、常量、数据模型）
✅ **测试覆盖**: 每个组件都有对应的单元测试
✅ **代码质量**: 使用 dataclass、类型注解、docstring
✅ **细粒度**: 每个任务都分解为2-5分钟的步骤
✅ **可验证**: 每步都有明确的预期结果

准备继续 Chunk 2...

---

## Chunk 2: 配置管理系统

### Task 5: 实现配置管理器

**Files:**
- Create: `promptbench/core/config.py`
- Test: `tests/test_core.py` (add tests)

- [ ] **Step 1: 添加配置管理器测试**

```python
# tests/test_core.py (add to existing file)

import os
import pytest
from pathlib import Path
from promptbench.core.config import ConfigManager, Config

def test_config_manager_initialization():
    """测试配置管理器初始化"""
    manager = ConfigManager()
    assert manager.config is not None
    assert isinstance(manager.config, Config)

def test_config_manager_get_env():
    """测试获取环境变量"""
    # 设置测试环境变量
    os.environ["TEST_VAR"] = "test_value"

    manager = ConfigManager()
    value = manager.get_env("TEST_VAR")

    assert value == "test_value"

    # 清理
    del os.environ["TEST_VAR"]

def test_config_manager_get_env_with_default():
    """测试获取环境变量（带默认值）"""
    manager = ConfigManager()
    value = manager.get_env("NONEXISTENT_VAR", "default_value")

    assert value == "default_value"

def test_config_manager_provider_config():
    """测试获取提供方配置"""
    # 设置测试环境变量
    os.environ["TEST_PROVIDER_API_KEY"] = "test_key"
    os.environ["TEST_PROVIDER_BASE_URL"] = "https://api.test.com"

    manager = ConfigManager()
    config = manager.get_provider_config("test_provider")

    assert config["api_key"] == "test_key"
    assert config["base_url"] == "https://api.test.com"

    # 清理
    del os.environ["TEST_PROVIDER_API_KEY"]
    del os.environ["TEST_PROVIDER_BASE_URL"]
```

- [ ] **Step 2: 运行测试（预期失败）**

```bash
pytest tests/test_core.py::test_config_manager_initialization -v
```
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: 实现配置管理器**

```python
# promptbench/core/config.py
"""
配置管理

统一的配置访问接口，管理环境变量、.env 文件和路径配置。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class Config:
    """配置容器"""
    base_dir: Path
    models_file: Path
    prompts_dir: Path
    outputs_dir: Path
    history_file: Path


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            base_dir: 项目根目录，默认为当前文件的上三级目录
        """
        if base_dir is None:
            # 从当前文件向上三级目录（promptbench/core/config.py -> project_root）
            base_dir = Path(__file__).parent.parent.parent

        self.base_dir = base_dir
        self.config = self._load_config()
        self._load_env_from_dotenv()

    def _load_config(self) -> Config:
        """
        从默认路径加载配置

        Returns:
            Config: 配置对象
        """
        return Config(
            base_dir=self.base_dir,
            models_file=self.base_dir / "models.json",
            prompts_dir=self.base_dir / "prompts",
            outputs_dir=self.base_dir / "outputs",
            history_file=self.base_dir / "evaluations_history.json"
        )

    def _load_env_from_dotenv(self):
        """
        简单解析当前项目下的 .env 文件，把里面的 key=value 写入环境变量。
        避免强依赖 python-dotenv，保证脚本开箱即用。
        """
        dotenv_path = self.base_dir / ".env"
        if not dotenv_path.exists():
            return

        for line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if key and key not in os.environ:
                os.environ[key] = value

    def get_env(self, key: str, default: Any = None) -> Any:
        """
        获取环境变量

        Args:
            key: 环境变量键
            default: 默认值（可选）

        Returns:
            环境变量的值，或默认值
        """
        return os.getenv(key, default)

    def get_provider_config(self, provider: str) -> Dict[str, str]:
        """
        获取指定 provider 的配置（base_url, api_key）

        Args:
            provider: provider 名称

        Returns:
            包含 base_url 和 api_key 的字典
        """
        prefix = provider.lower().replace("-", "_")
        base_url = (
            self.get_env(f"{prefix}_base_url")
            or self.get_env(f"{prefix.upper()}_BASE_URL")
            or self.get_env("llm_base_url")
            or self.get_env("LLM_BASE_URL")
        )
        api_key = (
            self.get_env(f"{prefix}_api_key")
            or self.get_env(f"{prefix.upper()}_API_KEY")
            or self.get_env("llm_api_key")
            or self.get_env("LLM_API_KEY")
        )

        return {
            "base_url": base_url or "https://api.openai.com/v1",
            "api_key": api_key
        }
```

- [ ] **Step 4: 运行测试（预期通过）**

```bash
pytest tests/test_core.py::test_config_manager_initialization -v
pytest tests/test_core.py::test_config_manager_get_env -v
pytest tests/test_core.py::test_config_manager_get_env_with_default -v
pytest tests/test_core.py::test_config_manager_provider_config -v
```
Expected: All PASS

- [ ] **Step 5: 提交配置管理器实现**

```bash
git add promptbench/core/config.py tests/test_core.py
git commit -m "feat: 实现配置管理器

- 添加 Config 数据类
- 实现 ConfigManager 统一配置管理
- 支持 .env 文件自动解析
- 实现环境变量读取（支持默认值）
- 实现提供方配置获取
- 添加完整的单元测试"
```

---

## 实施计划说明

以上是 Chunk 1（核心基础设施）和 Chunk 2（配置管理系统）的完整实施计划。由于篇幅限制，我将在下一个 response 中继续创建剩余的chunk：

- Chunk 3: 评估模块（evaluators/）
- Chunk 4: AI检测模块（detectors/）
- Chunk 5: 优化器模块（optimizers/）
- Chunk 6: 模型和版本管理（models/, versions/）
- Chunk 7: CLI接口（cli/）
- Chunk 8: 工具模块和最终测试（utils/, tests/）

每个chunk都将包含：
- 完整的任务分解
- 详细的代码实现
- 单元测试
- 提交检查点

准备继续下一个chunk吗？