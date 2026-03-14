# promptbench/versions/history_manager.py
"""
历史记录管理器

管理评估历史记录的加载、保存和计算摘要。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from promptbench.core.config import ConfigManager


class HistoryManager:
    """
    历史记录管理器

    管理评估历史记录的加载、保存和计算摘要。
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化历史记录管理器

        Args:
            config_manager: 配置管理器，None 则创建新实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.history_file = self.config_manager.config.history_file

    def load_history(self) -> Dict[str, Any]:
        """
        加载评估历史记录

        Returns:
            历史记录字典，不存在则返回空字典
        """
        if not self.history_file.exists():
            return {}

        with self.history_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_history(self, history: Dict[str, Any]) -> None:
        """
        保存评估历史记录

        Args:
            history: 历史记录字典
        """
        with self.history_file.open("w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def calculate_summary(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算单个版本的评估摘要

        Args:
            evaluations: 评估结果列表

        Returns:
            评估摘要字典
        """
        if not evaluations:
            return {
                "avg_rule_score": 0,
                "avg_ai_score": 0,
                "avg_detection_score": 0,
                "avg_total_score": 0,
                "max_total_score": 0,
                "min_total_score": 0,
                "best_model": None,
                "model_count": 0,
            }

        # 提取各维度得分
        rule_scores = [e.get("rule_score", 0) for e in evaluations]
        ai_scores = [e.get("ai_score", 0) for e in evaluations]
        detection_scores = [e.get("detection_score", 0) for e in evaluations]
        total_scores = [e.get("total_score", 0) for e in evaluations]

        # 找出最佳模型
        max_total_score = max(total_scores)
        min_total_score = min(total_scores)
        best_model = next(
            (e.get("model") for e in evaluations if e.get("total_score", 0) == max_total_score),
            None,
        )

        return {
            "avg_rule_score": round(sum(rule_scores) / len(rule_scores), 2),
            "avg_ai_score": round(sum(ai_scores) / len(ai_scores), 2),
            "avg_detection_score": round(sum(detection_scores) / len(detection_scores), 2),
            "avg_total_score": round(sum(total_scores) / len(total_scores), 2),
            "max_total_score": max_total_score,
            "min_total_score": min_total_score,
            "best_model": best_model,
            "model_count": len(evaluations),
        }

    def update_history(
        self,
        version: int,
        evaluations: List[Dict[str, Any]],
        prompt_path: str,
    ) -> None:
        """
        更新评估历史记录

        Args:
            version: 版本号
            evaluations: 评估结果列表
            prompt_path: 提示词文件路径
        """
        history = self.load_history()
        summary = self.calculate_summary(evaluations)

        history[f"v{version}"] = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "prompt_path": prompt_path,
            "summary": summary,
            "evaluations": evaluations,
        }

        self.save_history(history)

    def get_version_summary(self, version: int) -> Optional[Dict[str, Any]]:
        """
        获取指定版本的摘要信息

        Args:
            version: 版本号

        Returns:
            版本摘要字典，不存在则返回 None
        """
        history = self.load_history()
        return history.get(f"v{version}")

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """
        获取所有版本的摘要信息

        Returns:
            版本摘要列表，按版本号排序
        """
        history = self.load_history()
        summaries = []

        for key, value in history.items():
            if key.startswith("v") and "summary" in value:
                summaries.append(value)

        # 按版本号排序
        summaries.sort(key=lambda x: x.get("version", 0))

        return summaries
