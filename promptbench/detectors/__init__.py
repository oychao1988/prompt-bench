# promptbench/detectors/__init__.py
"""
AI检测模块

提供多种AI文本检测器和多检测器聚合功能。
"""

from promptbench.detectors.base import AIDetector
from promptbench.detectors.multi_detector import MultiAIDetector

__all__ = ["AIDetector", "MultiAIDetector"]
