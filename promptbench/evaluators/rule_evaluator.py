# promptbench/evaluators/rule_evaluator.py
"""
规则评估器

基于规则和统计的文本质量评估。
"""

import re
from typing import Optional, Tuple, Dict
from promptbench.core.entities import RuleEvaluation
from promptbench.core.constants import (
    DEFAULT_RULE_WEIGHTS,
    TITLE_PATTERN,
    SUBTITLE_PATTERN,
    BOLD_PATTERN,
    IMAGE_PATTERNS,
    DEFAULT_LENGTH_RANGE,
)


class RuleEvaluator:
    """
    规则评估器

    基于预定义规则和统计分析评估文本质量，
    包括字数范围、Markdown格式检测、结构完整性等。
    """

    def __init__(
        self,
        length_range: Optional[Tuple[int, int]] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        初始化规则评估器

        Args:
            length_range: 字数范围 (min, max)，None 使用默认值
            weights: 自定义权重字典，None 使用默认权重
        """
        self.length_range = length_range or DEFAULT_LENGTH_RANGE
        self.weights = weights or DEFAULT_RULE_WEIGHTS.copy()

    def evaluate(self, text: str, prompt_length_range: Optional[Tuple[int, int]] = None) -> RuleEvaluation:
        """
        评估文本

        Args:
            text: 待评估的文本
            prompt_length_range: 提示词要求的字数范围（优先使用）

        Returns:
            RuleEvaluation: 规则评估结果
        """
        # 优先使用提示词要求的范围，否则使用评估器的默认范围
        effective_range = prompt_length_range or self.length_range
        min_length, max_length = effective_range

        # 基础统计
        chars = len(text)
        paragraphs = [p for p in text.split("\n") if p.strip()]
        para_count = len(paragraphs)

        # 1. 计算字数得分（线性衰减）
        length_score, in_length_range = self._calculate_length_score(chars, min_length, max_length)

        # 2. 是否有一级标题 (# 标题)
        has_title = self._detect_pattern(text, TITLE_PATTERN)

        # 3. 是否有小标题 (## 二级标题)
        has_subtitles = self._detect_pattern(text, SUBTITLE_PATTERN)

        # 4. 是否有加粗内容 (**text**)
        has_bold_content = self._detect_pattern(text, BOLD_PATTERN)

        # 5. 是否有图片
        has_images = any(self._detect_pattern(text, pattern) for pattern in IMAGE_PATTERNS)

        # 计算规则得分
        rule_score = 0.0

        # 字数得分直接使用计算值
        rule_score += length_score

        # 其他指标使用布尔判定
        if has_title:
            rule_score += self.weights.get("has_title", 0)
        if has_subtitles:
            rule_score += self.weights.get("has_subtitles", 0)
        if has_bold_content:
            rule_score += self.weights.get("has_bold_content", 0)
        if has_images:
            rule_score += self.weights.get("has_images", 0)

        return RuleEvaluation(
            rule_score=round(rule_score, 2),
            in_length_range=in_length_range,
            has_title=has_title,
            has_subtitles=has_subtitles,
            has_bold_content=has_bold_content,
            has_images=has_images,
            chars=chars,
            paragraphs=para_count,
            length_range=f"{min_length}-{max_length}",
        )

    def _calculate_length_score(self, chars: int, min_length: int, max_length: int) -> Tuple[float, bool]:
        """
        计算字数得分（线性衰减）

        衰减规则：
        - 在 [min_length, max_length] 范围内：满分
        - 低于 min_length：线性衰减，低于 min_length * 0.5 时为 0 分
        - 高于 max_length：线性衰减，高于 max_length * 1.5 时为 0 分

        Args:
            chars: 实际字数
            min_length: 最小字数
            max_length: 最大字数

        Returns:
            (得分, 是否在范围内)
        """
        max_score = self.weights.get("in_length_range", 0.8)

        # 在范围内：满分
        if min_length <= chars <= max_length:
            return max_score, True

        # 低于下限
        if chars < min_length:
            zero_point = min_length * 0.5  # 下限的50%位置为0分点
            if chars <= zero_point:
                return 0.0, False
            # 线性衰减：从 zero_point(0分) 到 min_length(满分)
            ratio = (chars - zero_point) / (min_length - zero_point)
            return round(max_score * ratio, 2), False

        # 高于上限
        zero_point = max_length * 1.5  # 上限的150%位置为0分点
        if chars >= zero_point:
            return 0.0, False
        # 线性衰减：从 max_length(满分) 到 zero_point(0分)
        ratio = (zero_point - chars) / (zero_point - max_length)
        return round(max_score * ratio, 2), False

    def _detect_pattern(self, text: str, pattern: str) -> bool:
        """
        检测文本中是否匹配指定正则模式

        Args:
            text: 待检测的文本
            pattern: 正则表达式模式

        Returns:
            是否检测到匹配
        """
        return bool(re.search(pattern, text, re.MULTILINE))
