# tests/test_ai_evaluator.py
import pytest
from promptbench.evaluators.ai_evaluator import AIEvaluator
from promptbench.core.entities import AIEvaluation
from unittest.mock import Mock, patch


def test_ai_evaluator_basic():
    """测试基本AI评估"""
    evaluator = AIEvaluator()

    text = "退休之后，没事就来公园散散步。"
    prompt = "写一篇关于退休生活的短文"

    # Mock the client
    with patch.object(evaluator, '_get_client') as mock_get_client:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{
            "intro_quality": {"score": 0.8, "reason": "开头直接入题"},
            "classic_naturalness": {"score": 0.6, "reason": "引用自然"},
            "content_depth": {"score": 0.7, "reason": "有一定深度"},
            "writing_fluency": {"score": 0.9, "reason": "文笔流畅"},
            "emotional_resonance": {"score": 0.5, "reason": "情感一般"}
        }'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = evaluator.evaluate(text, prompt)

        assert isinstance(result, AIEvaluation)
        assert 0 <= result.ai_score <= 3.0
        assert result.error is None


def test_ai_evaluator_client_failure():
    """测试客户端获取失败"""
    evaluator = AIEvaluator()

    with patch.object(evaluator, '_get_client', return_value=None):
        result = evaluator.evaluate("测试文本", "测试提示词")

        assert result.ai_score == 0
        assert result.error is not None
        assert "无法获取" in result.error


def test_ai_evaluator_json_parse_error():
    """测试JSON解析错误"""
    evaluator = AIEvaluator()

    with patch.object(evaluator, '_get_client') as mock_get_client:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "这不是有效的JSON"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = evaluator.evaluate("测试文本", "测试提示词")

        assert result.ai_score == 0
        assert result.error is not None


def test_ai_evaluator_api_error():
    """测试API调用错误"""
    evaluator = AIEvaluator()

    with patch.object(evaluator, '_get_client') as mock_get_client:
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API错误")
        mock_get_client.return_value = mock_client

        result = evaluator.evaluate("测试文本", "测试提示词")

        assert result.ai_score == 0
        assert result.error is not None
        assert "API错误" in result.error
