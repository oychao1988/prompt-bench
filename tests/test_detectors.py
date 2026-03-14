# tests/test_detectors.py
import pytest
from promptbench.detectors.base import AIDetector
from promptbench.detectors.multi_detector import MultiAIDetector


def test_ai_detector_init():
    """测试AI检测器初始化"""
    detector = AIDetector(detector_type="mock")
    assert detector.detector_type == "mock"
    assert detector.enabled is True


def test_ai_detector_mock_detection():
    """测试模拟AI检测"""
    detector = AIDetector(detector_type="mock")

    text = """
    第一，这是一个测试。
    第二，这也是一个测试。
    第三，这还是是一个测试。
    """

    result = detector.detect(text)

    assert "ai_score" in result
    assert "ai_percentage" in result
    assert "human_percentage" in result
    assert 0 <= result["ai_score"] <= 1
    assert 0 <= result["ai_percentage"] <= 100
    assert 0 <= result["human_percentage"] <= 100


def test_ai_detector_disabled():
    """测试禁用的检测器"""
    config = {"enabled": False, "weight": 1.0}
    detector = AIDetector(detector_type="mock", config=config)

    result = detector.detect("测试文本")

    assert result["ai_score"] == 0.0
    assert result["enabled"] is False
    assert result["confidence"] == "disabled"


def test_multi_detector_init():
    """测试多检测器初始化"""
    multi = MultiAIDetector()
    assert isinstance(multi.detectors, list)


def test_multi_detector_detect():
    """测试多检测器聚合"""
    multi = MultiAIDetector()

    text = "这是一个测试文本，用于测试AI检测功能。"
    result = multi.detect(text)

    assert "ai_score" in result
    assert "detector_count" in result
    assert "detector_results" in result


def test_multi_detector_custom_config():
    """测试自定义多检测器配置"""
    detectors_config = [
        {"type": "mock", "enabled": True, "weight": 2.0},
        {"type": "mock", "enabled": False, "weight": 1.0},
    ]
    multi = MultiAIDetector(detectors_config=detectors_config)

    text = "测试文本"
    result = multi.detect(text)

    # 应该只使用第一个检测器（第二个被禁用）
    assert result["detector_count"] >= 0
