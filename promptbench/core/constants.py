# promptbench/core/constants.py
"""
常量定义

包含评分标准、默认配置和系统常量。
"""

from typing import Dict, Final

# ====== 规则评估权重 ======
DEFAULT_RULE_WEIGHTS: Final[Dict[str, float]] = {
    "in_length_range": 1.0,
    "para_count_reasonable": 0.7,
    "avg_para_length_ok": 0.3,
    "has_3_points": 0.6,
    "has_headings": 0.4,
}

# ====== AI语义评估权重 ======
DEFAULT_AI_WEIGHTS: Final[Dict[str, float]] = {
    "intro_quality": 0.6,
    "classic_naturalness": 0.6,
    "content_depth": 0.6,
    "writing_fluency": 0.6,
    "emotional_resonance": 0.6,
}

# ====== 评分规则总览 ======
SCORING_RULES: Final[Dict[str, float]] = {
    "total_score": 10.0,        # 总分
    "quality_score": 6.0,        # 质量评估（规则3分 + AI评估3分）
    "rule_score": 3.0,           # 规则评估
    "ai_score": 3.0,             # AI语义评估
    "detection_score": 4.0,      # AI检测
}

# ====== 文本长度默认范围 ======
DEFAULT_LENGTH_RANGE: Final[tuple[int, int]] = (400, 1500)

# ====== 段落数量合理范围 ======
REASONABLE_PARAGRAPH_COUNT: Final[tuple[int, int]] = (5, 20)

# ====== 段落长度合理范围 ======
REASONABLE_PARAGRAPH_LENGTH: Final[tuple[int, int]] = (30, 150)

# ====== 最小观点段落数 ======
MIN_POINT_PARAGRAPHS: Final[int] = 3

# ====== AI检测评分 ======
AI_DETECTION_MAX_SCORE: Final[float] = 4.0

# ====== 小标题正则模式 ======
HEADING_PATTERNS: Final[list[str]] = [
    r"^##\s",       # Markdown 标题
    r"^#\s",        # Markdown 一级标题
    r"^\d+\s*[、.．]",  # 数字序号：1. 1、 1．
    r"^[一二三四五六七八九十]+\\s*[、.．]",  # 中文数字
    r"^[其第]?[一二三四五六七八九十]+[个项]",  # 其一、第二、三项
    r"^首先\\s", "^其次\\s", "^最后\\s",  # 顺序词
    r"^第一\\s", "^第二\\s", "^第三\\s",  # 序数词
]

# ====== 默认模型配置 ======
DEFAULT_EVALUATION_MODEL: Final[str] = "gpt-5.4"
DEFAULT_OPTIMIZER_MODEL: Final[str] = "gpt-5.4"

# ====== 文件路径常量 ======
MODELS_FILE: Final[str] = "models.json"
PROMPTS_DIR: Final[str] = "prompts"
OUTPUTS_DIR: Final[str] = "outputs"
HISTORY_FILE: Final[str] = "evaluations_history.json"
