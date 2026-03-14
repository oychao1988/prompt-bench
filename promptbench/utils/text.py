# promptbench/utils/text.py
"""
文本处理工具

提供文本处理辅助函数。
"""

import re
from typing import Optional, Tuple, List


class TextUtils:
    """文本处理工具类"""

    @staticmethod
    def extract_length_requirement(text: str) -> Optional[Tuple[int, int]]:
        """
        从提示词中提取字数要求

        Args:
            text: 提示词文本

        Returns:
            (min_length, max_length) 或 None
        """
        # 匹配 "400-1500"、"400~1500"、"400到1500" 等格式
        patterns = [
            r'(\d+)\s*[-~到至]\s*(\d+)',
            r'(\d+)-(\d+)',
            r'约?(\d+)\s*字',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return (int(match.group(1)), int(match.group(2)))
                else:
                    # 单个字数，返回一个合理范围
                    target = int(match.group(1))
                    return (target - 200, target + 200)

        return None

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本，移除多余的空白字符

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 移除连续的空白行
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)

        # 移除行尾的空白
        text = '\n'.join(line.rstrip() for line in text.split('\n'))

        return text

    @staticmethod
    def count_chars(text: str) -> int:
        """
        计算文本字符数（不含空白）

        Args:
            text: 文本

        Returns:
            字符数
        """
        return len(text.replace(' ', '').replace('\n', ''))

    @staticmethod
    def count_paragraphs(text: str) -> int:
        """
        计算段落数

        Args:
            text: 文本

        Returns:
            段落数
        """
        paragraphs = [p for p in text.split('\n') if p.strip()]
        return len(paragraphs)

    @staticmethod
    def detect_headings(text: str, patterns: Optional[List[str]] = None) -> bool:
        """
        检测文本中是否包含小标题

        Args:
            text: 文本
            patterns: 小标题正则模式列表，None 使用默认模式

        Returns:
            是否检测到小标题
        """
        if patterns is None:
            from promptbench.core.constants import HEADING_PATTERNS
            patterns = HEADING_PATTERNS

        paragraphs = [p for p in text.split('\n') if p.strip()]

        for para in paragraphs:
            para_stripped = para.strip()
            for pattern in patterns:
                if re.match(pattern, para_stripped, re.MULTILINE):
                    return True

        return False
