# promptbench/detectors/base.py
"""
基础AI检测器

支持多种第三方AI文本检测API。
"""

from typing import Dict, Any, Optional


class AIDetector:
    """
    AI检测器基类

    支持多种检测工具，包括朱雀、GPTZero、Copyleaks等。
    当前版本实现模拟检测，基于文本特征的启发式算法。
    """

    def __init__(self, detector_type: str = "mock", config: Optional[Dict[str, Any]] = None):
        """
        初始化AI检测器

        Args:
            detector_type: 检测器类型，支持 "mock"(模拟)、"zhuque"、"gptzero"、"copyleaks"
            config: 检测器配置 {"api_key": "", "endpoint": "", "enabled": True, "weight": 1.0}
        """
        self.detector_type = detector_type
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.api_endpoint = self.config.get("endpoint", "")
        self.enabled = self.config.get("enabled", True)
        self.weight = self.config.get("weight", 1.0)

    def detect(self, text: str) -> Dict[str, Any]:
        """
        检测文本的AI生成概率

        Args:
            text: 待检测的文本

        Returns:
            包含检测结果的字典：
            {
                "ai_score": 0.85,  # AI生成概率 (0-1)
                "ai_percentage": 85,  # AI百分比 (0-100)
                "human_percentage": 15,  # 人类百分比 (0-100)
                "detector": "mock",  # 使用的检测器
                "confidence": "high",  # 置信度
                "enabled": True,  # 是否启用
                "weight": 1.0  # 权重
            }
        """
        if not self.enabled:
            return self._get_disabled_result()

        if self.detector_type == "mock":
            return self._detect_mock(text)
        elif self.detector_type == "zhuque":
            return self._detect_zhuque(text)
        elif self.detector_type == "gptzero":
            return self._detect_gptzero(text)
        elif self.detector_type == "copyleaks":
            return self._detect_copyleaks(text)
        else:
            # 默认使用模拟检测
            return self._detect_mock(text)

    def _get_disabled_result(self) -> Dict[str, Any]:
        """返回未启用的结果"""
        return {
            "ai_score": 0.0,
            "ai_percentage": 0,
            "human_percentage": 100,
            "detector": self.detector_type,
            "confidence": "disabled",
            "enabled": False,
            "weight": self.weight
        }

    def _detect_mock(self, text: str) -> Dict[str, Any]:
        """
        模拟AI检测（用于测试）

        基于文本特征简单判断：
        - 段落过于整齐
        - 句子长度过于平均
        - 缺少口语化表达
        """
        # 简单启发式规则
        paragraphs = [p for p in text.split("\n") if p.strip()]
        para_lengths = [len(p) for p in paragraphs]

        # 计算段落长度的标准差（越小说明越整齐）
        if len(para_lengths) > 1:
            avg_length = sum(para_lengths) / len(para_lengths)
            variance = sum((x - avg_length) ** 2 for x in para_lengths) / len(para_lengths)
            std_dev = variance ** 0.5
            # 标准差越小，AI概率越高
            uniformity_score = max(0, min(1, 1 - std_dev / 100))
        else:
            uniformity_score = 0.5

        # 简单的关键词检测
        ai_keywords = ["首先", "其次", "最后", "总之", "综上所述", "值得注意的是"]
        keyword_count = sum(1 for kw in ai_keywords if kw in text)
        keyword_score = min(1, keyword_count / 3)

        # 计算最终的AI概率
        ai_probability = (uniformity_score * 0.6 + keyword_score * 0.4)
        ai_probability = round(ai_probability, 2)

        # 根据AI概率确定置信度
        if ai_probability > 0.7 or ai_probability < 0.3:
            confidence = "high"
        elif ai_probability > 0.5 or ai_probability < 0.4:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "ai_score": ai_probability,
            "ai_percentage": round(ai_probability * 100),
            "human_percentage": round((1 - ai_probability) * 100),
            "detector": "mock",
            "confidence": confidence,
            "enabled": self.enabled,
            "weight": self.weight
        }

    def _detect_zhuque(self, text: str) -> Dict[str, Any]:
        """
        使用朱雀AI检测（腾讯）

        API文档：https://matrix.tencent.com/ai-detect/ai_gen_txt
        注：当前版本返回模拟结果，待API接入
        """
        # TODO: 实现朱雀检测API调用
        # 当前返回模拟结果
        return self._detect_mock(text)

    def _detect_gptzero(self, text: str) -> Dict[str, Any]:
        """
        使用GPTZero检测

        API文档：https://api.gptzero.me/v2/predict/text
        注：当前版本返回模拟结果，待API接入
        """
        # TODO: 实现GPTZero API调用
        # 当前返回模拟结果
        return self._detect_mock(text)

    def _detect_copyleaks(self, text: str) -> Dict[str, Any]:
        """
        使用Copyleaks检测

        API文档：https://api.copyleaks.com
        注：当前版本返回模拟结果，待API接入
        """
        # TODO: 实现Copyleaks API调用
        # 当前返回模拟结果
        return self._detect_mock(text)
