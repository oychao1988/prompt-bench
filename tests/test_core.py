# tests/test_core.py
import pytest
from promptbench.core.exceptions import (
    PromptBenchError,
    ConfigError,
    ModelError,
    EvaluationError,
    VersionError
)
from promptbench.core.constants import (
    DEFAULT_RULE_WEIGHTS,
    DEFAULT_AI_WEIGHTS,
    SCORING_RULES
)
from promptbench.core.entities import (
    ModelConfig,
    RuleEvaluation,
    AIEvaluation
)
from promptbench.core.config import ConfigManager, Config

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

def test_default_rule_weights():
    """测试默认规则权重"""
    assert DEFAULT_RULE_WEIGHTS["in_length_range"] == 1.0
    assert DEFAULT_RULE_WEIGHTS["para_count_reasonable"] == 0.7
    assert DEFAULT_RULE_WEIGHTS["avg_para_length_ok"] == 0.3
    assert DEFAULT_RULE_WEIGHTS["has_3_points"] == 0.6
    assert DEFAULT_RULE_WEIGHTS["has_headings"] == 0.4

def test_default_ai_weights():
    """测试默认AI评估权重"""
    assert DEFAULT_AI_WEIGHTS["intro_quality"] == 0.6
    assert DEFAULT_AI_WEIGHTS["classic_naturalness"] == 0.6
    assert DEFAULT_AI_WEIGHTS["content_depth"] == 0.6
    assert DEFAULT_AI_WEIGHTS["writing_fluency"] == 0.6
    assert DEFAULT_AI_WEIGHTS["emotional_resonance"] == 0.6

def test_scoring_rules():
    """测试评分规则"""
    assert SCORING_RULES["total_score"] == 10
    assert SCORING_RULES["quality_score"] == 6
    assert SCORING_RULES["detection_score"] == 4

def test_model_config():
    """测试模型配置数据类"""
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

def test_rule_evaluation():
    """测试规则评估结果"""
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

def test_ai_evaluation():
    """测试AI评估结果"""
    result = AIEvaluation(
        ai_score=2.1,
        ai_details={}
    )
    assert result.ai_score == 2.1
    assert result.error is None

def test_config_manager_initialization():
    """测试配置管理器初始化"""
    manager = ConfigManager()
    assert manager.config is not None
    assert isinstance(manager.config, Config)