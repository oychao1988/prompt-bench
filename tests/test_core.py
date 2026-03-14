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