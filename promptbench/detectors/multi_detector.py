# promptbench/detectors/multi_detector.py
"""
多检测器聚合

整合多个检测器的结果，计算加权平均值。
"""

from typing import List, Dict, Any, Optional
from promptbench.detectors.base import AIDetector
from promptbench.core.config import ConfigManager


class MultiAIDetector:
    """
    多检测器聚合器

    整合多个AI检测器的结果，使用加权平均计算最终的AI概率。
    支持从环境变量或配置加载检测器。
    """

    def __init__(self, detectors_config: Optional[List[Dict[str, Any]]] = None):
        """
        初始化多检测器

        Args:
            detectors_config: 检测器配置列表，None 则从环境变量加载
                [
                    {"type": "mock", "enabled": True, "weight": 1.0},
                    {"type": "zhuque", "enabled": True, "weight": 1.0, "api_key": "..."},
                ]
        """
        if detectors_config is not None:
            self.detectors = self._create_detectors_from_config(detectors_config)
        else:
            self.detectors = self._load_detectors_from_env()

    def detect(self, text: str) -> Dict[str, Any]:
        """
        使用所有启用的检测器检测文本

        Args:
            text: 待检测的文本

        Returns:
            聚合检测结果：
            {
                "ai_score": 0.65,  # 加权平均AI概率
                "ai_percentage": 65,
                "human_percentage": 35,
                "detector_count": 2,  # 使用的检测器数量
                "detector_results": [...],  # 各检测器的详细结果
                "confidence": "medium"
            }
        """
        # 过滤出启用的检测器
        enabled_detectors = [d for d in self.detectors if d.enabled]

        if not enabled_detectors:
            # 如果没有启用的检测器，返回默认结果
            return self._get_no_detector_result()

        # 使用每个检测器进行检测
        detector_results = []
        total_weight = 0
        weighted_ai_score = 0

        for detector in enabled_detectors:
            result = detector.detect(text)
            detector_results.append(result)

            weight = result.get("weight", 1.0)
            ai_score = result.get("ai_score", 0)

            weighted_ai_score += ai_score * weight
            total_weight += weight

        # 计算加权平均
        if total_weight > 0:
            average_ai_score = weighted_ai_score / total_weight
        else:
            average_ai_score = 0

        # 确定置信度
        if average_ai_score > 0.7 or average_ai_score < 0.3:
            confidence = "high"
        elif average_ai_score > 0.5 or average_ai_score < 0.4:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "ai_score": round(average_ai_score, 2),
            "ai_percentage": round(average_ai_score * 100),
            "human_percentage": round((1 - average_ai_score) * 100),
            "detector_count": len(enabled_detectors),
            "detector_results": detector_results,
            "confidence": confidence
        }

    def get_enabled_detectors(self) -> List[str]:
        """
        获取所有启用的检测器类型

        Returns:
            启用的检测器类型列表
        """
        return [d.detector_type for d in self.detectors if d.enabled]

    def _create_detectors_from_config(self, config: List[Dict[str, Any]]) -> List[AIDetector]:
        """
        从配置列表创建检测器

        Args:
            config: 检测器配置列表

        Returns:
            检测器列表
        """
        detectors = []
        for detector_config in config:
            detector_type = detector_config.get("type", "mock")
            detector = AIDetector(detector_type=detector_type, config=detector_config)
            detectors.append(detector)
        return detectors

    def _load_detectors_from_env(self) -> List[AIDetector]:
        """
        从环境变量加载检测器配置

        Returns:
            检测器列表
        """
        config_manager = ConfigManager()
        detectors = []

        # 检查各个检测器的环境变量配置
        detector_types = ["gptzero", "copyleaks", "zhuque"]

        for detector_type in detector_types:
            enabled_key = f"{detector_type.upper()}_DETECTOR_ENABLED"
            api_key_key = f"{detector_type.upper()}_API_KEY"
            weight_key = f"{detector_type.upper()}_WEIGHT"

            enabled = config_manager.get_env(enabled_key, "false").lower() == "true"
            api_key = config_manager.get_env(api_key_key, "")
            weight = float(config_manager.get_env(weight_key, "1.0"))

            if enabled:
                detector_config = {
                    "enabled": enabled,
                    "api_key": api_key,
                    "weight": weight
                }
                detector = AIDetector(detector_type=detector_type, config=detector_config)
                detectors.append(detector)

        # 如果没有配置任何检测器，添加一个默认的mock检测器
        if not detectors:
            detectors.append(AIDetector(detector_type="mock", config={"enabled": True, "weight": 1.0}))

        return detectors

    def _get_no_detector_result(self) -> Dict[str, Any]:
        """返回没有检测器时的默认结果"""
        return {
            "ai_score": 0.0,
            "ai_percentage": 0,
            "human_percentage": 100,
            "detector_count": 0,
            "detector_results": [],
            "confidence": "no_detectors"
        }
