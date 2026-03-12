#!/usr/bin/env python3
"""导入现有的评估结果到历史记录文件"""
import json
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
PROMPTS_DIR = BASE_DIR / "prompts"
EVALUATIONS_HISTORY_FILE = BASE_DIR / "evaluations_history.json"


def calculate_version_summary(evaluations):
    """计算单个版本的评估摘要"""
    if not evaluations:
        return {
            "avg_score": 0,
            "max_score": 0,
            "best_model": None,
            "model_count": 0,
            "dimension_scores": {
                "intro_ok": 0,
                "has_classic": 0,
                "has_3_points": 0,
                "ending_concise": 0,
                "in_length_range": 0,
            },
        }

    scores = [e["evaluation"]["score"] for e in evaluations]
    max_score = max(scores)
    best_model = next(
        (e["model"] for e in evaluations if e["evaluation"]["score"] == max_score),
        None,
    )

    dimensions = ["intro_ok", "has_classic", "has_3_points", "ending_concise", "in_length_range"]
    dimension_scores = {}
    for dim in dimensions:
        passed = sum(1 for e in evaluations if e["evaluation"].get(dim, False))
        dimension_scores[dim] = passed / len(evaluations)

    return {
        "avg_score": sum(scores) / len(scores),
        "max_score": max_score,
        "best_model": best_model,
        "model_count": len(evaluations),
        "dimension_scores": dimension_scores,
    }


def main():
    history = {}

    for eval_dir in sorted(OUTPUT_DIR.glob("v*")):
        if not eval_dir.is_dir():
            continue

        version = int(eval_dir.name[1:])  # 去掉 'v' 前缀
        eval_file = eval_dir / "evaluations.json"

        if not eval_file.exists():
            print(f"跳过 {eval_dir.name}: 未找到 evaluations.json")
            continue

        with eval_file.open("r", encoding="utf-8") as f:
            evaluations = json.load(f)

        prompt_path = PROMPTS_DIR / f"v{version}.md"
        if not prompt_path.exists():
            print(f"警告: {prompt_path} 不存在")

        summary = calculate_version_summary(evaluations)

        history[f"v{version}"] = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "prompt_path": str(prompt_path),
            "summary": summary,
            "evaluations": evaluations,
        }

        print(f"已导入 v{version}: 平均分 {summary['avg_score']:.2f}, 最高分 {summary['max_score']}")

    # 保存历史记录
    with EVALUATIONS_HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"\n已导入 {len(history)} 个版本到 {EVALUATIONS_HISTORY_FILE}")


if __name__ == "__main__":
    main()
