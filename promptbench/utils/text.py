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
        # 匹配各种字数要求格式
        patterns = [
            # "1000-1200字" 或 "1000～1200字" 或 "1000到1200字"
            r'(\d+)\s*[-~到至]\s*(\d+)\s*字',
            # "1000-1200" 或 "1000~1200"
            r'(\d+)\s*[-~到至]\s*(\d+)',
            # "字数控制在 1000–1200 字" 或 "1000–1200 之间"
            r'(\d+)\s*[–—-]\s*(\d+)',
            # "1000 到 1200 字之间"
            r'(\d+)\s+到\s+(\d+)\s+字',
            # "1000-1200字为主" 或 "1000-1200 字左右"
            r'(\d+)\s*[-~到至]\s*(\d+)\s*字[之主左右]+',
            # "严格控制在 1000-1200 字"
            r'控制.*?(\d+)\s*[-~到至]\s*(\d+)\s*字',
            # "不得低于 1000 字，不得超过 1300 字"
            r'(?:不低于|不少于|至少)\s*(\d+)\s*字.*?(?:不超过|低于|多于|高于)\s*(\d+)\s*字',
            # "1000字以上" 或 "1200字以下"
            r'(\d+)\s*字以上',
            r'(\d+)\s*字以下',
            # "约1000字"
            r'约?(\d+)\s*字[左右上下]+',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # 有两个数字，返回范围
                    return (int(groups[0]), int(groups[1]))
                elif len(groups) == 1:
                    # 只有一个数字
                    num = int(groups[0])
                    # 根据上下文判断是上限还是下限
                    if '以上' in text or '不少于' in text or '至少' in text:
                        return (num, num + 500)  # 下限，给一个合理上限
                    elif '以下' in text or '不超过' in text or '低于' in text:
                        return (max(100, num - 500), num)  # 上限，给一个合理下限
                    else:
                        # 约等于，返回一个合理范围
                        return (max(100, num - 100), num + 100)

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
