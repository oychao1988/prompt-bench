# tests/test_optimizers.py
import pytest
from promptbench.optimizers.summarizer import EvaluationSummarizer
from promptbench.optimizers.prompt_optimizer import PromptOptimizer
from unittest.mock import Mock, patch


def test_summarizer_empty_results():
    """测试空结果的总结"""
    summarizer = EvaluationSummarizer()
    result = summarizer.summarize([])

    assert result == "暂无结果，无法给出优化建议。"


def test_summarizer_ai_dimensions():
    """测试AI维度分析"""
    summarizer = EvaluationSummarizer()

    # 模拟评估结果
    results = [
        {
            "ai_details": {
                "intro_quality": {"score": 0.4, "reason": "开头不够直接"},
                "classic_naturalness": {"score": 0.8, "reason": "引用自然"},
                "content_depth": {"score": 0.3, "reason": "内容空洞"},
                "writing_fluency": {"score": 0.7, "reason": "文笔流畅"},
                "emotional_resonance": {"score": 0.5, "reason": "情感不足"},
            }
        },
        {
            "ai_details": {
                "intro_quality": {"score": 0.5, "reason": "开头一般"},
                "classic_naturalness": {"score": 0.9, "reason": "引用很自然"},
                "content_depth": {"score": 0.4, "reason": "内容不够深入"},
                "writing_fluency": {"score": 0.8, "reason": "文笔流畅"},
                "emotional_resonance": {"score": 0.6, "reason": "情感尚可"},
            }
        },
    ]

    summary = summarizer.summarize(results)

    assert "开头质量" in summary
    assert "内容深度" in summary
    assert "情感共鸣" in summary


def test_summarizer_rule_dimensions():
    """测试规则维度分析"""
    summarizer = EvaluationSummarizer()

    results = [
        {
            "in_length_range": False,
            "para_count_reasonable": True,
            "avg_para_length_ok": False,
            "has_3_points": True,
            "has_headings": False,
        },
        {
            "in_length_range": False,
            "para_count_reasonable": True,
            "avg_para_length_ok": True,
            "has_3_points": True,
            "has_headings": False,
        },
    ]

    summary = summarizer.summarize(results, length_range=(400, 600))

    assert "字数控制" in summary
    assert "小标题结构" in summary


def test_summarizer_no_issues():
    """测试没有明显问题的情况"""
    summarizer = EvaluationSummarizer()

    # 所有评估都通过
    results = [
        {
            "ai_details": {
                "intro_quality": {"score": 0.8},
                "classic_naturalness": {"score": 0.9},
                "content_depth": {"score": 0.8},
                "writing_fluency": {"score": 0.9},
                "emotional_resonance": {"score": 0.8},
            },
            "in_length_range": True,
            "para_count_reasonable": True,
            "avg_para_length_ok": True,
            "has_3_points": True,
            "has_headings": True,
        }
    ]

    summary = summarizer.summarize(results)

    assert "当前提示词整体表现稳定" in summary


def test_optimizer_client_failure():
    """测试客户端获取失败"""
    optimizer = PromptOptimizer()

    with patch.object(optimizer, '_get_client', return_value=None):
        with pytest.raises(RuntimeError) as exc_info:
            optimizer.optimize("原始提示词", "评估总结", 2)

        assert "客户端" in str(exc_info.value)


def test_optimizer_basic():
    """测试基本优化流程"""
    optimizer = PromptOptimizer()

    with patch.object(optimizer, '_get_client') as mock_get_client:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "# 提示词版本：v2\n\n优化后的提示词内容..."
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = optimizer.optimize("原始提示词", "评估总结", 2)

        assert "提示词版本：v2" in result
        assert "优化后的提示词内容" in result
