# PromptBench 代码重构设计文档

**日期**: 2026-03-14
**项目**: PromptBench - 提示词评估与优化工具
**设计目标**: 全面优化，提高可维护性、可测试性，并为未来功能扩展做准备

---

## 1. 重构目标

| 目标 | 说明 |
|------|------|
| 提高可维护性 | 拆分大文件，让代码更容易理解和修改 |
| 增加可测试性 | 解耦代码，方便编写单元测试 |
| 添加新功能准备 | 为添加新功能做架构准备 |
| 配置管理 | 将配置集中管理 |
| 类型注解 | 完善类型提示，提高代码可维护性 |
| 错误处理 | 统一异常处理和错误信息 |
| 单元测试 | 为核心模块添加测试用例 |

---

## 2. 技术选型

- **保持现状**: 继续使用 OpenAI SDK，保持简单
- **向后兼容性**: 可以打破兼容性，重新设计更优的接口
- **功能保留**: 完全保留现有功能

---

## 3. 目录结构设计

```
promptbench/
├── __init__.py              # 包入口，包含版本信息
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── config.py            # 配置管理（环境变量、.env解析）
│   ├── entities.py          # 数据模型（领域实体、数据传输对象）
│   ├── exceptions.py        # 异常定义
│   └── constants.py         # 常量定义（评分标准、默认配置）
├── evaluators/              # 评估引擎模块
│   ├── __init__.py
│   ├── base.py              # 评估器基类
│   ├── rule_evaluator.py    # 规则评估（长度、段落、结构）
│   └── ai_evaluator.py      # AI语义评估（开头、引用、深度、流畅、情感）
├── detectors/               # AI检测模块
│   ├── __init__.py
│   ├── base.py              # 检测器基类
│   ├── zhuque.py            # 朱雀检测
│   ├── gptzero.py           # GPTZero检测
│   ├── copyleaks.py         # Copyleaks检测
│   └── multi_detector.py    # 多检测器管理
├── models/                  # LLM模型管理模块
│   ├── __init__.py
│   ├── client.py            # 统一模型调用接口
│   ├── provider.py          # 模型提供方配置
│   └── connectivity.py      # 连通性测试
├── versions/                # 版本管理模块
│   ├── __init__.py
│   ├── prompt_manager.py    # 提示词文件管理
│   └── history_manager.py   # 评估历史追踪
├── cli/                     # 命令行界面
│   ├── __init__.py
│   ├── main.py              # 主CLI入口
│   └── commands/            # 各子命令实现
│       ├── __init__.py
│       ├── evaluate.py
│       ├── ranking.py
│       ├── create_version.py
├── optimizers/             # 优化器模块
│   ├── __init__.py
│   ├── base.py              # 优化器基类
│   ├── llm_optimizer.py     # LLM提示词优化
│   └── summarizer.py        # 评估总结生成
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── text.py              # 文本处理工具（字数统计、段落分析、引用检测等）
│   ├── file.py              # 文件操作工具（读取/写入文件、目录操作等）
│   └── log.py               # 日志管理（统一日志配置和管理）
└── tests/                   # 单元测试
    ├── __init__.py
    ├── test_core.py
    ├── test_evaluators.py
    ├── test_detectors.py
    ├── test_models.py
    ├── test_versions.py
    └── test_optimizers.py
```

---

## 4. 核心数据模型

### 4.1 数据模型定义（core/entities.py）

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class ModelConfig:
    """模型配置"""
    provider: str
    name: str
    enabled: bool
    input_price: Optional[str] = None
    output_price: Optional[str] = None
    description: Optional[str] = None

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

@dataclass
class AIEvaluation:
    """AI评估结果"""
    ai_score: float
    ai_details: Dict[str, Any]
    error: Optional[str] = None

@dataclass
class DetectionResult:
    """AI检测结果"""
    ai_score: float
    ai_percentage: int
    human_percentage: int
    detector_results: List[Dict[str, Any]]
    detector_count: int
    confidence: str

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
    output_path: Path

@dataclass
class VersionSummary:
    """某个提示词版本的总结"""
    version: int
    avg_score: float
    max_score: float
    min_score: float
    model_count: int
    evaluation_time: datetime
    results: List[EvaluationResult]

@dataclass
class PromptVersion:
    """提示词版本信息"""
    version: int
    content: str
    path: Path
    created_at: datetime
```

### 4.2 模块职责说明

| 模块 | 职责 | 主要类/函数 |
|------|------|------------|
| `core/config.py` | 配置管理，统一的配置访问接口 | `ConfigManager` |
| `core/entities.py` | 数据模型定义，类型注解 | `EvaluationResult` 等 |
| `core/exceptions.py` | 异常体系定义 | `PromptBenchError` 等 |
| `evaluators/rule_evaluator.py` | 规则评估引擎 | `RuleEvaluator.evaluate()` |
| `evaluators/ai_evaluator.py` | AI语义评估引擎 | `AIEvaluator.evaluate()` |
| `detectors/multi_detector.py` | 多AI检测管理 | `MultiAIDetector.detect()` |
| `optimizers/llm_optimizer.py` | LLM提示词优化 | `LLMOptimizer.optimize()` |
| `optimizers/summarizer.py` | 评估总结生成 | `Summarizer.summarize()` |
| `models/client.py` | 统一的模型调用接口 | `LLMClient.generate()` |
| `versions/prompt_manager.py` | 提示词版本管理 | `PromptManager.get_latest()` |
| `utils/text.py` | 文本处理工具 | `count_chars()`, `analyze_paragraphs()`, `detect_quotes()` 等 |
| `utils/file.py` | 文件操作工具 | `read_file()`, `write_file()`, `create_dir()` 等 |
| `utils/log.py` | 日志管理 | `get_logger()`, 统一的日志配置 |
| `cli/main.py` | 命令行入口 | `main()` |

---

## 5. API 设计

### 5.1 优化器基类（optimizers/base.py）

```python
# optimizers/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseOptimizer(ABC):
    """优化器基类，定义优化器的核心接口"""

    @abstractmethod
    def optimize(
        self,
        prompt: str,
        eval_summary: str,
        version: int,
        **kwargs
    ) -> str:
        """
        优化提示词的核心方法

        Args:
            prompt: 原始提示词
            eval_summary: 评估总结
            version: 新的版本号
            **kwargs: 其他参数

        Returns:
            优化后的提示词
        """
        pass

    @abstractmethod
    def validate_prompt(self, prompt: str) -> List[str]:
        """
        验证提示词的格式和内容

        Args:
            prompt: 待验证的提示词

        Returns:
            验证错误列表，空列表表示验证通过
        """
        pass

class BaseSummarizer(ABC):
    """总结器基类，定义评估总结的接口"""

    @abstractmethod
    def summarize(self, results: List[Dict[str, Any]]) -> str:
        """
        生成评估总结

        Args:
            results: 评估结果列表

        Returns:
            格式化的评估总结
        """
        pass

    @abstractmethod
    def get_common_issues(self, results: List[Dict[str, Any]]) -> List[str]:
        """
        获取常见问题列表

        Args:
            results: 评估结果列表

        Returns:
            常见问题列表
        """
        pass
```

### 5.2 模型提供方管理（models/provider.py）

```python
# models/provider.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class ProviderConfig:
    """模型提供方配置"""
    name: str
    base_url: str
    api_key: str
    enabled: bool = True
    description: Optional[str] = None
    default_model: Optional[str] = None
    supported_models: List[str] = field(default_factory=list)

class ProviderManager:
    """模型提供方管理器"""

    def __init__(self):
        self.providers: Dict[str, ProviderConfig] = {}
        self._load_providers_from_config()

    def _load_providers_from_config(self):
        """从配置中加载提供方信息"""
        from core.config import ConfigManager

        config = ConfigManager()

        # 支持的默认提供方
        default_providers = [
            {
                "name": "openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": config.get_env("OPENAI_API_KEY"),
                "default_model": "gpt-4o",
                "supported_models": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]
            },
            {
                "name": "anthropic",
                "base_url": "https://api.anthropic.com/v1",
                "api_key": config.get_env("ANTHROPIC_API_KEY"),
                "default_model": "claude-3-opus-20240229",
                "supported_models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
            }
        ]

        for provider_info in default_providers:
            self.providers[provider_info["name"]] = ProviderConfig(
                **provider_info
            )

    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """获取提供方配置"""
        return self.providers.get(name)

    def list_enabled_providers(self) -> List[ProviderConfig]:
        """获取所有启用的提供方"""
        return [
            config for config in self.providers.values() if config.enabled
        ]

    def get_default_provider(self) -> Optional[ProviderConfig]:
        """获取默认提供方"""
        return next(
            (p for p in self.providers.values() if p.enabled),
            None
        )
```

### 5.3 模型连通性测试（models/connectivity.py）

```python
# models/connectivity.py
import time
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ConnectivityTestResult:
    """模型连通性测试结果"""
    provider: str
    model: str
    success: bool
    response_time: float
    error: str = ""
    timestamp: str = ""

class ConnectivityTester:
    """模型连通性测试器"""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    def test_model_connectivity(
        self,
        provider: str,
        model: str
    ) -> ConnectivityTestResult:
        """
        测试单个模型的连通性

        Args:
            provider: 模型提供方
            model: 模型名称

        Returns:
            测试结果
        """
        start_time = time.time()
        result = ConnectivityTestResult(
            provider=provider,
            model=model,
            success=False,
            response_time=0.0,
            error="",
            timestamp=""
        )

        try:
            from models.client import LLMClient

            # 使用简单的连通性测试
            client = LLMClient.get_client(provider)
            response = client.generate(
                prompt="Hello, world!",
                model=model,
                max_tokens=10
            )

            result.success = True
            result.response_time = time.time() - start_time
            result.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        except Exception as e:
            result.success = False
            result.response_time = time.time() - start_time
            result.error = str(e)
            result.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        return result

    def test_all_models(self) -> List[ConnectivityTestResult]:
        """
        测试所有启用的模型的连通性

        Returns:
            所有模型的测试结果列表
        """
        from core.config import ConfigManager
        from models.client import LLMClient

        results = []

        for model_config in ConfigManager().get_model_configs():
            if model_config.enabled:
                result = self.test_model_connectivity(
                    model_config.provider,
                    model_config.name
                )
                results.append(result)

        return results

    def print_summary(self, results: List[ConnectivityTestResult]):
        """打印测试结果摘要"""
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)

        print(f"\n📊 连通性测试摘要:")
        print(f"✅ 成功: {success_count}/{total_count}")
        print(f"❌ 失败: {total_count - success_count}/{total_count}")

        if total_count > 0:
            avg_response_time = sum(r.response_time for r in results) / total_count
            print(f"⏱️  平均响应时间: {avg_response_time:.2f} 秒")

        print("\n详细结果:")
        for result in results:
            status = "✅" if result.success else "❌"
            response_time = f"{result.response_time:.2f} 秒"
            print(f"{status} {result.provider}/{result.model}: {response_time}")
            if result.error:
                print(f"   错误: {result.error}")
```

### 5.4 主要 API 接口

```python
# core/config.py - 配置管理
class ConfigManager:
    """统一配置管理器"""
    def get_model_configs() -> List[ModelConfig]
    def get_env(key: str, default: Any = None) -> Any
    def get_provider_config(provider: str) -> Dict[str, str]

# evaluators/rule_evaluator.py - 规则评估
class RuleEvaluator:
    def evaluate(text: str, length_range: Tuple[int, int] = None) -> RuleEvaluation

# evaluators/ai_evaluator.py - AI评估
class AIEvaluator:
    def evaluate(text: str, prompt: str) -> AIEvaluation

# detectors/multi_detector.py - AI检测
class MultiAIDetector:
    def detect(text: str) -> DetectionResult

# models/client.py - 模型调用
class LLMClient:
    def generate(prompt: str, model: str, topic: str = None) -> str
    def test_connectivity(model: str) -> bool

# versions/prompt_manager.py - 提示词管理
class PromptManager:
    def get_latest() -> PromptVersion
    def get_by_version(version: int) -> PromptVersion
    def create_new(from_version: int, content: str = None) -> PromptVersion

# versions/history_manager.py - 历史管理
class HistoryManager:
    def add_evaluation(version: int, result: EvaluationResult)
    def get_summary(version: int) -> VersionSummary
    def get_ranking() -> List[VersionSummary]

# optimizers/llm_optimizer.py - LLM提示词优化
class LLMOptimizer:
    def optimize(original_prompt: str, eval_summary: str, new_version: int) -> str
    def validate_prompt(prompt: str) -> List[str]

# optimizers/summarizer.py - 评估总结
class Summarizer:
    def summarize(results: List[EvaluationResult]) -> str
    def get_common_issues(results: List[EvaluationResult]) -> List[str]
```

### 5.4 日志系统设计（新增）

```python
# utils/log.py
import logging
import sys
from pathlib import Path
from typing import Optional

class LogManager:
    """统一日志管理器"""

    @staticmethod
    def get_logger(name: str = "promptbench", level: int = logging.INFO) -> logging.Logger:
        """获取配置好的 logger 对象"""
        logger = logging.getLogger(name)

        if logger.hasHandlers():
            return logger

        logger.setLevel(level)

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # 文件输出
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "promptbench.log")
        file_handler.setLevel(logging.WARNING)

        # 格式配置
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

# 便捷的 log 工具函数
logger = LogManager.get_logger()

def debug(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)

def exception(msg: str, *args, **kwargs):
    logger.exception(msg, *args, **kwargs)
```

### 5.3 配置管理设计

```python
# core/config.py
from pathlib import Path
import os
from typing import Any, Dict, List, Optional
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
    """统一配置管理"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent.parent
        self.config = self._load_config()

    def _load_config(self) -> Config:
        """从 .env 和默认路径加载配置"""
        return Config(
            base_dir=self.base_dir,
            models_file=self.base_dir / "models.json",
            prompts_dir=self.base_dir / "prompts",
            outputs_dir=self.base_dir / "outputs",
            history_file=self.base_dir / "evaluations_history.json"
        )

    def get_env(self, key: str, default: Any = None) -> Any:
        """获取环境变量"""
        return os.getenv(key, default)

    def get_provider_config(self, provider: str) -> Dict[str, str]:
        """获取指定 provider 的配置（base_url, api_key）"""
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

---

## 6. 错误处理策略

### 6.1 异常体系（core/exceptions.py）

```python
class PromptBenchError(Exception):
    """项目所有异常的基类"""
    pass

class ConfigError(PromptBenchError):
    """配置错误（缺少 API key、无效配置等）"""
    pass

class ModelError(PromptBenchError):
    """模型调用错误（API 失败、模型不存在等）"""
    pass

class EvaluationError(PromptBenchError):
    """评估过程错误"""
    pass

class VersionError(PromptBenchError):
    """版本管理错误（版本不存在、文件找不到等）"""
    pass

# 错误处理装饰器
def handle_errors(default_return=None, reraise=False):
    """统一错误处理装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__name__} 失败: {e}")
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator
```

---

## 7. CLI 设计

### 7.1 新的 CLI 接口

```bash
# 新的 CLI 接口（更清晰的命令结构）
promptbench evaluate            # 运行评估（替代 --evaluate）
promptbench evaluate --version 5  # 评估指定版本
promptbench evaluate --skip-optimize  # 仅测试不优化
promptbench ranking             # 查看版本排名（替代 --ranking）
promptbench create 5            # 创建新版本（替代 --create-version）
promptbench create 5 --to 7     # 创建 v7 基于 v5
promptbench test-models         # 测试模型连通性

### 7.2 CLI 向后兼容性设计

为了保持与旧接口的兼容性，我们将实现兼容层：

```python
# cli/compat.py
import argparse
import warnings
from typing import List, Dict, Any
from .main import main as new_main

# 弃用警告装饰器
def deprecated(new_command: str):
    """标记旧命令的装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"命令已弃用，请使用新命令: {new_command}",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

def map_old_arguments(old_args: argparse.Namespace) -> Dict[str, Any]:
    """
    将旧版参数映射到新版参数

    旧版:
      --evaluate → promptbench evaluate
      --from-version N → promptbench evaluate --version N
      --ranking → promptbench ranking
      --create-version N → promptbench create N
      --create-version N --to M → promptbench create N --to M
    """
    new_args = {}

    if old_args.evaluate:
        new_args["command"] = "evaluate"
        if old_args.from_version:
            new_args["version"] = old_args.from_version
        if old_args.skip_optimize:
            new_args["skip_optimize"] = True

    if old_args.ranking:
        new_args["command"] = "ranking"

    if old_args.create_version:
        new_args["command"] = "create"
        new_args["from_version"] = old_args.create_version
        if old_args.to:
            new_args["to_version"] = old_args.to

    return new_args

def run_compat_mode():
    """
    兼容模式入口，处理旧版参数
    """
    parser = argparse.ArgumentParser(
        description="PromptBench - 提示词评估与优化工具 (兼容模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # 旧版参数
    parser.add_argument("--evaluate", action="store_true", help="运行评估")
    parser.add_argument("--from-version", type=int, help="从指定版本评估")
    parser.add_argument("--skip-optimize", action="store_true", help="跳过优化步骤")
    parser.add_argument("--ranking", action="store_true", help="查看版本排名")
    parser.add_argument("--create-version", type=int, help="创建新版本")
    parser.add_argument("--to", type=int, help="目标版本号")

    args = parser.parse_args()

    # 映射参数
    mapped = map_old_arguments(args)

    if "command" not in mapped:
        parser.print_help()
        return

    # 调用新的 CLI
    import sys

    # 构建新命令的参数
    sys.argv = ["promptbench", mapped["command"]]

    if mapped["command"] == "evaluate":
        if "version" in mapped:
            sys.argv.extend(["--version", str(mapped["version"])])
        if "skip_optimize" in mapped:
            sys.argv.extend(["--skip-optimize"])

    elif mapped["command"] == "create":
        sys.argv.extend([str(mapped["from_version"])])
        if "to_version" in mapped:
            sys.argv.extend(["--to", str(mapped["to_version"])])

    # 运行新命令
    new_main()
```

---

### 7.3 models.json 迁移策略

```python
# 保持现有 models.json 格式完全不变
# 新代码会继续读取和解析相同的格式

# 新增版本检查
def check_models_json_format():
    """检查 models.json 格式是否正确"""
    from pathlib import Path
    import json

    models_file = Path("models.json")

    if not models_file.exists():
        raise VersionError("models.json 文件不存在")

    try:
        with models_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

            # 检查必要的字段
            required_keys = ["openai_models", "anthropic_models", "google_models", "deepseek_models"]

            for key in required_keys:
                if key not in data:
                    logger.warning(f"models.json 中缺少 {key} 键")

            return True

    except json.JSONDecodeError as e:
        raise ConfigError(f"models.json JSON 解析失败: {e}")

    return False
```

---

## 8. 实施阶段计划

### 第一阶段：核心基础设施
- 创建 `core/` 模块
- 实现 `config.py` - 配置管理
- 实现 `entities.py` - 数据模型
- 实现 `exceptions.py` - 异常体系
- 实现 `constants.py` - 常量定义

### 第二阶段：评估模块
- 创建 `evaluators/` 模块
- 实现 `base.py` - 优化器基类
- 实现 `rule_evaluator.py` - 规则评估
- 实现 `ai_evaluator.py` - AI语义评估
- 创建 `detectors/` 模块
- 实现各检测器（zhuque, gptzero, copyleaks）
- 实现 `multi_detector.py` - 多检测器管理

### 第三阶段：优化器模块
- 创建 `optimizers/` 模块
- 实现 `base.py` - 优化器基类
- 实现 `llm_optimizer.py` - LLM提示词优化
- 实现 `summarizer.py` - 评估总结生成

### 第四阶段：模型和版本管理
- 创建 `models/` 模块
- 实现 `client.py` - 统一模型调用接口
- 实现 `provider.py` - 模型提供方管理
- 实现 `connectivity.py` - 连通性测试
- 创建 `versions/` 模块
- 实现 `prompt_manager.py` - 提示词文件管理
- 实现 `history_manager.py` - 评估历史追踪

### 第五阶段：CLI 接口
- 创建 `cli/` 模块
- 实现新的命令结构
- 实现 `compat.py` - 向后兼容层（带 deprecation 警告）
- 实现各子命令（evaluate, ranking, create）

### 第六阶段：测试和文档
- 创建 `tests/` 目录
- 为核心模块添加单元测试
- 更新 `README.md`
- 更新 `USAGE.md`
- 更新 `CLAUDE.md`

---

## 10. 数据迁移策略

### 10.1 evaluations_history.json 迁移

```python
# 迁移脚本示例（migrations/v1_to_v2.py）
def migrate_history_file(old_path: Path, new_path: Path):
    """
    迁移旧版本的 evaluations_history.json 到新版本格式
    """
    with old_path.open("r", encoding="utf-8") as f:
        old_data = json.load(f)

    new_data = []
    for entry in old_data:
        # 确保所有字段都存在
        if "version" in entry and "avg_score" in entry:
            # 补充缺失的字段
            entry.setdefault("max_score", 0.0)
            entry.setdefault("min_score", 0.0)
            entry.setdefault("model_count", 0)
            entry.setdefault("evaluation_time", str(datetime.now()))
            new_data.append(entry)

    with new_path.open("w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False, default=str)

def check_and_migrate():
    """检查并执行必要的数据迁移"""
    history_file = ConfigManager().config.history_file

    if history_file.exists():
        temp_path = history_file.with_suffix(".json.backup")
        history_file.rename(temp_path)

        try:
            migrate_history_file(temp_path, history_file)
            print("✅ 历史数据迁移成功")
        except Exception as e:
            temp_path.rename(history_file)
            print(f"❌ 数据迁移失败: {e}")
            raise
```

### 10.2 向后兼容性保障

```python
# 在启动时检查并执行迁移
check_and_migrate()
```

---


## 9. 评分体系（保持不变）

### 总分：10分（质量6分 + AI检测4分）

#### 质量评估（6分）
##### 规则评估（3分）
| 维度 | 分值 | 检测规则 |
|------|------|----------|
| `in_length_range` | 1.0分 | 字数是否在提示词要求范围内 |
| `para_count_reasonable` | 0.7分 | 段落数是否合理（5-20段） |
| `avg_para_length_ok` | 0.3分 | 平均段落长度是否合理（30-150字） |
| `has_3_points` | 0.6分 | 中间是否有≥3个观点段落 |
| `has_headings` | 0.4分 | 是否有小标题结构 |

##### AI语义评估（3分）
| 维度 | 分值 | 评估标准 |
|------|------|----------|
| `intro_quality` | 0.6分 | 开头是否直接入题，有吸引力，符合人设 |
| `classic_naturalness` | 0.6分 | 经典引用是否自然恰当，与观点紧密相关 |
| `content_depth` | 0.6分 | 内容是否有深度，观点是否有启发性 |
| `writing_fluency` | 0.6分 | 文笔是否流畅自然，语言是否有节奏感 |
| `emotional_resonance` | 0.6分 | 是否能引发情感共鸣，打动人心 |

#### AI检测（4分）
**评分公式**：`检测分 = (1 - AI率) × 4`，保留2位小数

## 10. 数据迁移策略

- 完全保留现有功能，只是重构架构
- 保持技术栈不变（OpenAI SDK）
- 允许打破向后兼容性，设计更优的 CLI 接口
- 完善类型注解
- 添加单元测试
- 统一错误处理
- 集中配置管理
- 性能优化：并发执行、缓存机制、增量更新
- 数据迁移：保留历史数据并提供迁移策略

---

**设计完成日期**: 2026-03-14
**设计状态**: ✅ 已批准，准备进入实施阶段
