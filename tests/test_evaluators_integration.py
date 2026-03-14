# tests/test_evaluators_integration.py
import pytest
from promptbench.evaluators.rule_evaluator import RuleEvaluator
from promptbench.evaluators.ai_evaluator import AIEvaluator
from promptbench.core.entities import RuleEvaluation, AIEvaluation
from unittest.mock import Mock, patch


def test_full_evaluation_flow():
    """测试完整的评估流程"""
    rule_evaluator = RuleEvaluator()
    ai_evaluator = AIEvaluator()

    text = """
    退休之后，没事就来公园散散步，看见老哥拿个大毛笔蘸着水写字，
    一笔一划，稳稳当当的，写的是真好。

    看见这位老哥写字，我就觉得，这才是退休该有的样子。
    我站在旁边看着，不打扰，就觉得心里踏实、舒坦。
    这日子，平淡，却有滋味。
    """

    prompt = "写一篇关于退休生活的短文，400-600字"

    # 规则评估
    rule_result = rule_evaluator.evaluate(text)
    assert isinstance(rule_result, RuleEvaluation)
    assert 0 <= rule_result.rule_score <= 3.0

    # AI评估（需要mock）
    with patch.object(ai_evaluator, '_get_client') as mock_get_client:
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{
            "intro_quality": {"score": 0.8, "reason": "开头自然入题"},
            "classic_naturalness": {"score": 0.6, "reason": "无引用"},
            "content_depth": {"score": 0.7, "reason": "有真情实感"},
            "writing_fluency": {"score": 0.9, "reason": "文笔流畅"},
            "emotional_resonance": {"score": 0.8, "reason": "引发共鸣"}
        }'''
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        ai_result = ai_evaluator.evaluate(text, prompt)
        assert isinstance(ai_result, AIEvaluation)
        assert 0 <= ai_result.ai_score <= 3.0

    # 总分计算
    total_score = rule_result.rule_score + ai_result.ai_score
    assert 0 <= total_score <= 6.0
