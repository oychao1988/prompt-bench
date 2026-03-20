# promptbench/optimizers/summarizer.py
"""
评估总结器

分析评估结果，生成优化建议。
"""

from typing import List, Dict, Any, Optional, Tuple
from promptbench.versions.prompt_template import PromptTemplate


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
        lines.append("请根据以下建议，只更新对应的章节内容，其他章节保持不变。")
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
            if r.get("ai_details", {}).get("ai_details", {}).get("intro_quality", {}).get("score", 1) < self.ai_threshold
        )
        if intro_bad > 0:
            suggestions.append(
                f"- 开头质量（{intro_bad}个模型不佳）：首段必须在2-3句内直接切入主题，用具体场景而非抽象陈述。"
            )

        # 2. 经典引用恰当性
        classic_unnatural = sum(
            1 for r in results
            if r.get("ai_details", {}).get("ai_details", {}).get("classic_naturalness", {}).get("score", 1) < self.ai_threshold
        )
        if classic_unnatural > 0:
            suggestions.append(
                f"- 经典引用（{classic_unnatural}个模型不自然）：引用经典时要自然，避免生硬堆砌。"
            )

        # 3. 内容深度与思想性
        content_shallow = sum(
            1 for r in results
            if r.get("ai_details", {}).get("ai_details", {}).get("content_depth", {}).get("score", 1) < self.ai_threshold
        )
        if content_shallow > 0:
            suggestions.append(
                f"- 内容深度（{content_shallow}个模型不足）：每个观点都要有具体的故事或细节支撑，避免空泛的道理说教。"
            )

        # 4. 文笔流畅度与可读性
        writing_choppy = sum(
            1 for r in results
            if r.get("ai_details", {}).get("ai_details", {}).get("writing_fluency", {}).get("score", 1) < self.ai_threshold
        )
        if writing_choppy > 0:
            suggestions.append(
                f"- 文笔流畅度（{writing_choppy}个模型不佳）：多使用短句和口语化表达，语言要有节奏感。"
            )

        # 5. 情感共鸣
        low_emotion = sum(
            1 for r in results
            if r.get("ai_details", {}).get("ai_details", {}).get("emotional_resonance", {}).get("score", 1) < self.ai_threshold
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
        wrong_length = sum(1 for r in results if not r.get("rule_details", {}).get("in_length_range", True))
        if wrong_length > 0 and length_range:
            params = PromptTemplate.format_length_requirement(length_range[0], length_range[1])
            suggestion = PromptTemplate.build_suggestion(
                "in_length_range",
                wrong_length,
                f"明确要求总字数严格控制在 {length_range[0]}-{length_range[1]} 字之间，"
                f"低于 {params['min_lower']} 字或高于 {params['max_upper']} 字将视为不合格"
            )
            suggestions.append(suggestion)

        # 2. 一级标题
        no_title = sum(1 for r in results if not r.get("rule_details", {}).get("has_title", True))
        if no_title > 0:
            suggestions.append(
                PromptTemplate.build_suggestion(
                    "has_title",
                    no_title,
                    "添加 '必须使用一级标题 (# 标题) 作为文章开头' 的要求"
                )
            )

        # 3. 小标题
        no_subtitles = sum(1 for r in results if not r.get("rule_details", {}).get("has_subtitles", True))
        if no_subtitles > 0:
            suggestions.append(
                PromptTemplate.build_suggestion(
                    "has_subtitles",
                    no_subtitles,
                    "添加 '必须使用二级标题 (## 标题) 划分观点段落' 的要求，每个观点一段"
                )
            )

        # 4. 加粗内容
        no_bold = sum(1 for r in results if not r.get("rule_details", {}).get("has_bold_content", True))
        if no_bold > 0:
            suggestions.append(
                PromptTemplate.build_suggestion(
                    "has_bold_content",
                    no_bold,
                    "添加 '重点关键词和金句必须使用 **加粗** 标记' 的要求"
                )
            )

        # 5. 图片占位符
        no_images = sum(1 for r in results if not r.get("rule_details", {}).get("has_images", True))
        if no_images > 0:
            suggestions.append(
                PromptTemplate.build_suggestion(
                    "has_images",
                    no_images,
                    "添加 '每个观点段落后插入图片占位符，格式：![图片描述](https://...)' 的要求"
                )
            )

        return suggestions
