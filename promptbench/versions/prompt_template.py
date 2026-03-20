# promptbench/versions/prompt_template.py
"""
提示词结构模板

定义提示词的标准结构，支持模块化更新。
"""

from typing import Dict, List, Optional


class PromptTemplate:
    """
    提示词结构模板类

    定义提示词的标准章节结构，使优化器能够精准定位和更新特定章节。
    """

    # 主章节定义
    SECTIONS = {
        "persona": "一、人设设定",
        "topic": "二、主题方向",
        "writing_rules": "三、写作规则",
        "content_structure": "四、内容结构",
        "notes": "五、注意事项",
    }

    # 子章节定义
    SUBSECTIONS = {
        "writing_rules": {
            "length": "3.1 字数要求",
            "format": "3.2 格式要求",
            "style": "3.3 语言风格",
        }
    }

    # 规则评估指标与章节的映射
    RULE_SECTION_MAPPING = {
        "in_length_range": ("writing_rules", "length"),
        "has_title": ("writing_rules", "format"),
        "has_subtitles": ("writing_rules", "format"),
        "has_bold_content": ("writing_rules", "format"),
        "has_images": ("writing_rules", "format"),
    }

    @classmethod
    def get_section_path(cls, rule_key: str) -> Optional[str]:
        """
        获取规则评估指标对应的章节路径

        Args:
            rule_key: 规则评估指标名称

        Returns:
            章节路径字符串，如 "三、写作规则 > 3.2 格式要求"
        """
        if rule_key not in cls.RULE_SECTION_MAPPING:
            return None

        section_key, subsection_key = cls.RULE_SECTION_MAPPING[rule_key]
        section_name = cls.SECTIONS.get(section_key, "")
        subsection_name = cls.SUBSECTIONS.get(section_key, {}).get(subsection_key, "")

        if subsection_name:
            return f"{section_name} > {subsection_name}"
        return section_name

    @classmethod
    def get_default_content(cls, section: str, subsection: Optional[str] = None) -> Optional[str]:
        """
        获取章节的默认内容模板

        Args:
            section: 主章节key
            subsection: 子章节key

        Returns:
            默认内容字符串
        """
        # 写作规则章节的默认内容
        if section == "writing_rules":
            if subsection == "length":
                return """### 3.1 字数要求
- 总字数严格控制在 {min}-{max} 字之间
- 低于 {min_lower} 字或高于 {max_upper} 字将被视为不合格
- 建议完成后检查字数，确保符合要求"""

            elif subsection == "format":
                return """### 3.2 格式要求
- 必须使用一级标题 (# 标题) 作为文章开头
- 必须使用二级标题 (## 标题) 划分观点段落
- 重点关键词和金句必须使用 **加粗** 标记
- 每个观点段落后插入图片占位符，格式：![图片描述](https://...)
- 使用 Markdown 格式输出"""

            elif subsection == "style":
                return """### 3.3 语言风格
- 句子以短句为主，尽量口语化，但有分寸
- 关键处可以自然拉长一句，形成散文式的缓慢长句
- 整体口吻平和、克制、含蓄，有一点自嘲的幽默感
- 多通过具体意象唤起读者记忆，增强画面感"""

        return None

    @classmethod
    def format_length_requirement(cls, min_length: int, max_length: int) -> Dict[str, str]:
        """
        格式化字数要求的内容

        Args:
            min_length: 最小字数
            max_length: 最大字数

        Returns:
            字数要求参数字典
        """
        return {
            "min": min_length,
            "max": max_length,
            "min_lower": int(min_length * 0.5),
            "max_upper": int(max_length * 1.5),
        }

    @classmethod
    def parse_prompt_sections(cls, prompt: str) -> Dict[str, str]:
        """
        解析提示词，提取各章节内容

        Args:
            prompt: 提示词文本

        Returns:
            章节key到内容的映射
        """
        sections = {}
        lines = prompt.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            # 检测是否是章节标题（如 "## 一、人设设定"）
            if line.strip().startswith("##") and any(
                section_name in line for section_name in cls.SECTIONS.values()
            ):
                # 保存上一个章节
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # 开始新章节
                for key, name in cls.SECTIONS.items():
                    if name in line:
                        current_section = key
                        current_content = []
                        break
            elif current_section is not None:
                current_content.append(line)

        # 保存最后一个章节
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    @classmethod
    def build_suggestion(cls, rule_key: str, issue_count: int, suggestion: str) -> str:
        """
        构建结构化的优化建议

        Args:
            rule_key: 规则评估指标
            issue_count: 有问题的模型数量
            suggestion: 具体建议内容

        Returns:
            格式化的建议字符串
        """
        section_path = cls.get_section_path(rule_key)
        if not section_path:
            return f"- {suggestion}（{issue_count}个模型）"

        return f"""【{section_path}】
- 问题：{issue_count}个模型不符合要求
- 建议：{suggestion}"""
