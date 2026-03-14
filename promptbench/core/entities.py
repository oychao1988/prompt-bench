# promptbench/core/entities.py
"""
数据模型定义

定义所有领域实体和数据传输对象（DTO），
使用 dataclass 提供类型安全和默认值。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


# ====== 模型配置 ======

@dataclass
class ModelConfig:
    """模型配置"""
    provider: str
    name: str
    enabled: bool
    input_price: Optional[str] = None
    output_price: Optional[str] = None
    description: Optional[str] = None


# ====== 规则评估结果 ======

@dataclass
class RuleEvaluation:
    """规则评估结果"""
    rule_score: float
    in_length_range: bool
    para_count_reasonable: bool
    avg_para_length_ok: bool
    has_3_points: bool
    has_headings: bool
    chars: int
    paragraphs: int
    avg_para_length: float
    length_range: str


# ====== AI评估结果 ======

@dataclass
class AIEvaluation:
    """AI语义评估结果"""
    ai_score: float
    ai_details: Dict[str, Any]
    error: Optional[str] = None


# ====== AI检测结果 ======

@dataclass
class DetectionResult:
    """AI检测结果"""
    ai_score: float
    ai_percentage: int
    human_percentage: int
    detector_results: List[Dict[str, Any]]
    detector_count: int
    confidence: str


# ====== 完整评估结果 ======

@dataclass
class EvaluationResult:
    """单篇文章的完整评估结果"""
    provider: str
    model: str
    rule_score: float          # 0-3分
    ai_score: float            # 0-3分
    detection_score: float     # 0-4分
    total_score: float         # 0-10分
    rule_details: RuleEvaluation
    ai_details: AIEvaluation
    detection_details: DetectionResult
    chars: int
    paragraphs: int
    output_path: Optional[Path] = None


# ====== 版本总结 ======

@dataclass
class VersionSummary:
    """某个提示词版本的总结"""
    version: int
    avg_score: float
    max_score: float
    min_score: float
    model_count: int
    evaluation_time: datetime
    results: List[EvaluationResult] = field(default_factory=list)


# ====== 提示词版本 ======

@dataclass
class PromptVersion:
    """提示词版本信息"""
    version: int
    content: str
    path: Path
    created_at: datetime
