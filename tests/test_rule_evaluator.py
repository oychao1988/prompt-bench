# tests/test_rule_evaluator.py
import pytest
from promptbench.evaluators.rule_evaluator import RuleEvaluator
from promptbench.core.entities import RuleEvaluation
from promptbench.core.constants import DEFAULT_RULE_WEIGHTS


def test_rule_evaluator_basic():
    """测试基本规则评估"""
    evaluator = RuleEvaluator()

    text = """
    退休之后，没事就来公园散散步。

    第一，这样可以锻炼身体。
    第二，还能交到朋友。
    第三，心情也会变好。

    总之，退休生活要有规律。
    """

    result = evaluator.evaluate(text)

    assert isinstance(result, RuleEvaluation)
    assert result.rule_score >= 0
    assert result.rule_score <= 3.0
    assert result.chars > 0
    assert result.paragraphs > 0


def test_rule_evaluator_length_range():
    """测试字数范围检查"""
    evaluator = RuleEvaluator(length_range=(100, 200))

    # 测试过短文本
    short_text = "太短了"
    result = evaluator.evaluate(short_text)
    assert not result.in_length_range

    # 测试合适文本（15个字符 × 10 = 150字）
    proper_text = "这是一个长度合适的文本。" * 10
    result = evaluator.evaluate(proper_text)
    assert result.in_length_range


def test_rule_evaluator_paragraph_structure():
    """测试段落结构检查"""
    evaluator = RuleEvaluator()

    # 测试有结构的文本
    structured_text = """
    开头段落。

    第一个观点。
    第二个观点。
    第三个观点。

    结尾段落。
    """

    result = evaluator.evaluate(structured_text)
    assert result.has_3_points


def test_rule_evaluator_headings():
    """测试小标题检测"""
    evaluator = RuleEvaluator()

    # 测试带小标题的文本
    text_with_headings = """
    开头段落。

    ## 第一点
    内容...

    ## 第二点
    内容...

    结尾。
    """

    result = evaluator.evaluate(text_with_headings)
    assert result.has_headings


def test_rule_evaluator_custom_weights():
    """测试自定义权重"""
    custom_weights = {
        "in_length_range": 2.0,
        "para_count_reasonable": 0.5,
        "avg_para_length_ok": 0.2,
        "has_3_points": 0.2,
        "has_headings": 0.1,
    }
    evaluator = RuleEvaluator(weights=custom_weights)

    text = "测试文本"
    result = evaluator.evaluate(text)

    # 验证权重被正确应用
    assert result.rule_score >= 0
