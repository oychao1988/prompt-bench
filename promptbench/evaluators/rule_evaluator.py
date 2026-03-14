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
    REASONABLE_PARAGRAPH_COUNT,
    REASONABLE_PARAGRAPH_LENGTH,
    MIN_POINT_PARAGRAPHS,
    HEADING_PATTERNS,
    DEFAULT_LENGTH_RANGE,
)


class RuleEvaluator:
    """
    规则评估器

    基于预定义规则和统计分析评估文本质量，
    包括字数范围、段落数量、段落长度、结构完整性和格式规范性。
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
            prompt_length_range: 提示词要求的字数范围（可选）

        Returns:
            RuleEvaluation: 规则评估结果
        """
        # 使用提示词要求的范围（如果提供），否则使用评估器的默认范围
        effective_range = prompt_length_range or self.length_range
        min_length, max_length = effective_range

        # 基础统计
        chars = len(text)
        paragraphs = [p for p in text.split("\n") if p.strip()]
        para_count = len(paragraphs)

        # 1. 段落数是否合理（避免过度碎片化或过于冗长）
        para_count_reasonable = REASONABLE_PARAGRAPH_COUNT[0] <= para_count <= REASONABLE_PARAGRAPH_COUNT[1]

        # 2. 平均段落长度是否合理（避免碎片化）
        avg_para_length = chars / para_count if para_count > 0 else 0
        avg_para_length_ok = REASONABLE_PARAGRAPH_LENGTH[0] <= avg_para_length <= REASONABLE_PARAGRAPH_LENGTH[1]

        # 3. 结构检测（中间是否有足够的观点段落）
        middle_para_count = max(0, para_count - 2)
        has_3_points = middle_para_count >= MIN_POINT_PARAGRAPHS

        # 4. 是否有小标题结构
        has_headings = self._detect_headings(paragraphs)

        # 5. 字数是否在指定范围内
        in_length_range = min_length <= chars <= max_length

        # 计算规则得分
        rule_score = 0.0
        rule_evaluations = {
            "in_length_range": in_length_range,
            "para_count_reasonable": para_count_reasonable,
            "avg_para_length_ok": avg_para_length_ok,
            "has_3_points": has_3_points,
            "has_headings": has_headings,
        }

        for key, passed in rule_evaluations.items():
            if passed and key in self.weights:
                rule_score += self.weights[key]

        return RuleEvaluation(
            rule_score=round(rule_score, 2),
            in_length_range=in_length_range,
            para_count_reasonable=para_count_reasonable,
            avg_para_length_ok=avg_para_length_ok,
            has_3_points=has_3_points,
            has_headings=has_headings,
            chars=chars,
            paragraphs=para_count,
            avg_para_length=round(avg_para_length, 1),
            length_range=f"{min_length}-{max_length}",
        )

    def _detect_headings(self, paragraphs: list[str]) -> bool:
        """
        检测文本中是否包含小标题

        Args:
            paragraphs: 段落列表

        Returns:
            是否检测到小标题
        """
        for para in paragraphs:
            para_stripped = para.strip()
            for pattern in HEADING_PATTERNS:
                if re.match(pattern, para_stripped, re.MULTILINE):
                    return True
        return False
