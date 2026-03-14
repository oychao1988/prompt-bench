# promptbench/optimizers/summarizer.py
"""
评估总结器

分析评估结果，生成优化建议。
"""

from typing import List, Dict, Any, Optional, Tuple


class EvaluationSummarizer:
    """
    评估总结器

    基于多模型输出的共性表现，生成针对性的优化建议。
    结合规则评估和AI评估的结果，给出全面的提示词优化建议。
    """

    def __init__(self, ai_threshold: float = 0.6):
        """
        初始化评估总结器

        Args:
            ai_threshold: AI评估维度的不及格阈值（默认0.6分）
        """
        self.ai_threshold = ai_threshold

    def summarize(self, results: List[Dict[str, Any]], length_range: Optional[Tuple[int, int]] = None) -> str:
        """
        生成评估总结和优化建议

        Args:
            results: 评估结果列表
            length_range: 字数范围（用于规则评估建议）

        Returns:
            优化建议文本
        """
        if not results:
            return "暂无结果，无法给出优化建议。"

        lines = []
        lines.append("优化建议（基于多模型输出的共性表现）：")
        lines.append("")

        # 分析AI评估维度
        ai_suggestions = self._analyze_ai_dimensions(results)

        # 分析规则评估维度
        rule_suggestions = self._analyze_rule_dimensions(results, length_range)

        # 输出建议
        if ai_suggestions:
            lines.append("【AI评估维度建议】")
            lines.extend(ai_suggestions)
            lines.append("")

        if rule_suggestions:
            lines.append("【规则评估维度建议】")
            lines.extend(rule_suggestions)
            lines.append("")

        # 如果没有明显问题
        if not ai_suggestions and not rule_suggestions:
            lines.append("- 当前提示词整体表现稳定，可以在不改变结构的前提下，增加少量语气上的温度与画面感描述要求。")
            lines.append("- 建议尝试微调：让经典引用更自然、让故事细节更具体、让情感表达更克制温暖。")

        return "\n".join(lines)

    def _analyze_ai_dimensions(self, results: List[Dict[str, Any]]) -> List[str]:
        """分析AI评估维度"""
        suggestions = []

        # 1. 开头质量
        intro_bad = sum(
            1 for r in results
            if r.get("ai_details", {}).get("intro_quality", {}).get("score", 1) < self.ai_threshold
        )
        if intro_bad > 0:
            suggestions.append(
                f"- 开头质量（{intro_bad}个模型不佳）：首段必须在2-3句内直接切入主题，用具体场景而非抽象陈述。"
            )

        # 2. 经典引用恰当性
        classic_unnatural = sum(
            1 for r in results
            if r.get("ai_details", {}).get("classic_naturalness", {}).get("score", 1) < self.ai_threshold
        )
        if classic_unnatural > 0:
            suggestions.append(
                f"- 经典引用（{classic_unnatural}个模型不自然）：引用经典时要自然，避免生硬堆砌。"
            )

        # 3. 内容深度与思想性
        content_shallow = sum(
            1 for r in results
            if r.get("ai_details", {}).get("content_depth", {}).get("score", 1) < self.ai_threshold
        )
        if content_shallow > 0:
            suggestions.append(
                f"- 内容深度（{content_shallow}个模型不足）：每个观点都要有具体的故事或细节支撑，避免空泛的道理说教。"
            )

        # 4. 文笔流畅度与可读性
        writing_choppy = sum(
            1 for r in results
            if r.get("ai_details", {}).get("writing_fluency", {}).get("score", 1) < self.ai_threshold
        )
        if writing_choppy > 0:
            suggestions.append(
                f"- 文笔流畅度（{writing_choppy}个模型不佳）：多使用短句和口语化表达，语言要有节奏感。"
            )

        # 5. 情感共鸣
        low_emotion = sum(
            1 for r in results
            if r.get("ai_details", {}).get("emotional_resonance", {}).get("score", 1) < self.ai_threshold
        )
        if low_emotion > 0:
            suggestions.append(
                f"- 情感共鸣（{low_emotion}个模型不足）：写出真实的生活细节和内心感受，用克制而温暖的基调。"
            )

        return suggestions

    def _analyze_rule_dimensions(
        self, results: List[Dict[str, Any]], length_range: Optional[Tuple[int, int]]
    ) -> List[str]:
        """分析规则评估维度"""
        suggestions = []

        # 1. 字数要求
        wrong_length = sum(1 for r in results if not r.get("in_length_range", True))
        if wrong_length > 0 and length_range:
            suggestions.append(
                f"- 字数控制（{wrong_length}个模型不符合）：明确要求文章总字数控制在 {length_range[0]}-{length_range[1]} 字之间。"
            )

        # 2. 段落数量
        para_count_bad = sum(1 for r in results if not r.get("para_count_reasonable", True))
        if para_count_bad > 0:
            suggestions.append(
                f"- 段落数量（{para_count_bad}个模型不合理）：文章段落数建议控制在 5-20 段之间。"
            )

        # 3. 段落长度
        avg_para_length_bad = sum(1 for r in results if not r.get("avg_para_length_ok", True))
        if avg_para_length_bad > 0:
            suggestions.append(
                f"- 段落长度（{avg_para_length_bad}个模型不合理）：每段平均长度建议在 30-150 字之间。"
            )

        # 4. 结构完整性
        not_3_points = sum(1 for r in results if not r.get("has_3_points", True))
        if not_3_points > 0:
            suggestions.append(
                f"- 结构完整性（{not_3_points}个模型不符合）：中间必须拆成 3 个观点段落，每个观点 2-3 句。"
            )

        # 5. 小标题结构
        no_headings = sum(1 for r in results if not r.get("has_headings", True))
        if no_headings > 0:
            suggestions.append(
                f"- 小标题结构（{no_headings}个模型缺失）：建议添加小标题结构，使用序号形式标注观点段落。"
            )

        return suggestions
