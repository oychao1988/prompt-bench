import json
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import textwrap

from openai import OpenAI


BASE_DIR = Path(__file__).parent
MODELS_FILE = BASE_DIR / "models.json"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


# ====== 0. 读取 .env，初始化客户端 ======

def load_env_from_dotenv():
    """
    简单解析当前项目下的 .env 文件，把里面的 key=value 写入环境变量。
    避免强依赖 python-dotenv，保证脚本开箱即用。
    """
    dotenv_path = BASE_DIR / ".env"
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


load_env_from_dotenv()

LLM_BASE_URL = os.getenv("llm_base_url") or os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("llm_api_key") or os.getenv("LLM_API_KEY")

if not LLM_API_KEY:
    raise RuntimeError("未找到 llm_api_key / LLM_API_KEY，请在 .env 或环境变量中配置。")

client = OpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL or "https://api.openai.com/v1",
)


# ====== 1. 加载配置 & 版本管理 ======


def load_models() -> Dict[str, List[Dict[str, Any]]]:
    with MODELS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_latest_prompt_file() -> Tuple[Path, int]:
    """
    在 prompts 目录下查找形如 v1.md、v2.md 的文件，取版本号最大的作为当前版本。
    """
    if not PROMPTS_DIR.exists():
        raise RuntimeError(f"未找到 prompts 目录：{PROMPTS_DIR}")

    candidates: List[Tuple[int, Path]] = []
    for p in PROMPTS_DIR.glob("v*.md"):
        stem = p.stem  # 例如 v1
        if stem.startswith("v") and stem[1:].isdigit():
            ver = int(stem[1:])
            candidates.append((ver, p))

    if not candidates:
        raise RuntimeError("prompts 目录下未找到任何 v*.md 提示词文件。")

    version, path = max(candidates, key=lambda x: x[0])
    return path, version


def load_prompt(prompt_path: Path) -> str:
    return prompt_path.read_text(encoding="utf-8")


# ====== 2. 统一的模型调用函数（兼容你提供的所有 model name）======


def call_llm(model_name: str, prompt: str) -> str:
    """
    通过 OpenAI 兼容接口调用任意模型。
    你的网关（llm_base_url）只要支持 /chat/completions，就可以直接用。
    """
    keywords = [
        "老了才明白", "儿女"
    ]
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": "请围绕以下关键词写一篇公众号文章：\n\n" + ",".join(keywords),
            },
        ],
        temperature=0.8,
    )
    return resp.choices[0].message.content or ""


def generate_with_model(provider: str, model_name: str, prompt: str) -> str:
    """
    目前所有 provider 都通过同一个网关调用，
    这里保留 provider 只是为了输出结果时区分来源。
    """
    return call_llm(model_name, prompt)


# ====== 3. 简单可实现的自动评价指标 ======


def evaluate_article(text: str) -> Dict[str, Any]:
    """
    不调用别的模型，只做一些“规则+统计”型评分，
    简单、无成本，但能看出结构是否对齐。
    """
    # 基础统计
    chars = len(text)
    paragraphs = [p for p in text.split("\n") if p.strip()]
    para_count = len(paragraphs)

    # 是否直接入题（首段是否很快出现核心话题关键词）
    first_line = paragraphs[0].strip() if paragraphs else ""
    intro_ok = any(kw in first_line for kw in ["老了", "人过六十", "退休", "这一生"])

    # 经典引用粗略检测
    classic_keywords = [
        "《",
        "》",
        "孔子",
        "孟子",
        "庄子",
        "陶渊明",
        "苏轼",
        "杜甫",
        "李白",
        "诗经",
    ]
    has_classic = any(kw in text for kw in classic_keywords)

    # 结构检测（中间是否有 3 个明显分段）
    # 简单判断：除开头和结尾，中间段落数 >= 3
    middle_para_count = max(0, para_count - 2)
    has_3_points = middle_para_count >= 3

    # 结尾是否简短有力：最后一段字数 < 80
    last_para = paragraphs[-1].strip() if paragraphs else ""
    ending_concise = len(last_para) <= 80

    # 字数是否在 1000-1200 之间（按字符近似）
    in_length_range = 1000 <= chars <= 1200

    score = 0
    weights = {
        "intro_ok": 2,
        "has_classic": 2,
        "has_3_points": 3,
        "ending_concise": 2,
        "in_length_range": 1,
    }

    details = {
        "intro_ok": intro_ok,
        "has_classic": has_classic,
        "has_3_points": has_3_points,
        "ending_concise": ending_concise,
        "in_length_range": in_length_range,
        "chars": chars,
        "paragraphs": para_count,
    }

    for k, w in weights.items():
        if details[k]:
            score += w

    details["score"] = score
    return details


# ====== 4. 基于多模型结果，自动生成“提示词优化建议” ======


def summarize_evaluations(results: List[Dict[str, Any]]) -> str:
    """
    这里不用再调模型，直接基于规则结果给一点通用建议。
    你后续也可以改成再调一个大模型，专门做 meta-分析。
    """
    if not results:
        return "暂无结果，无法给出优化建议。"

    # 统计常见问题
    intro_bad = sum(1 for r in results if not r["evaluation"]["intro_ok"])
    no_classic = sum(1 for r in results if not r["evaluation"]["has_classic"])
    wrong_length = sum(1 for r in results if not r["evaluation"]["in_length_range"])
    not_3_points = sum(1 for r in results if not r["evaluation"]["has_3_points"])
    ending_not_concise = sum(
        1 for r in results if not r["evaluation"]["ending_concise"]
    )

    lines = []
    lines.append("优化建议（基于多模型输出的共性表现）：")

    if intro_bad > 0:
        lines.append(
            "- 开头要求可以更具体，比如限制首段在 2-3 句内直接点明“人过六十 / 老了才明白”的主题。"
        )
    if no_classic > 0:
        lines.append(
            "- 可以在提示词中补充：至少自然引用 1-2 句古诗词或经典名句，并与观点紧密相关。"
        )
    if wrong_length > 0:
        lines.append("- 明确要求文章总字数控制在 1000-1200 字之间，避免过长或过短。")
    if not_3_points > 0:
        lines.append(
            "- 强调中间必须拆成 3 个小标题式观点，每个观点 2-3 句，并用空行分隔，方便在公众号中阅读。"
        )
    if ending_not_concise > 0:
        lines.append(
            "- 对结尾加一句约束：用 1-2 句完成收束，不要在结尾开启新的故事或论证。"
        )

    if len(lines) == 1:
        lines.append(
            "- 当前提示词整体表现稳定，可以在不改变结构的前提下，增加少量语气上的温度与画面感描述要求。"
        )

    return "\n".join(lines)


def optimize_prompt_via_llm(
    original_prompt: str, eval_summary: str, new_version: int
) -> str:
    """
    使用一个指定模型，基于原始提示词和本次评估总结，自动生成“下一版”完整提示词。
    这样就不依赖硬编码的模板，而是走真正的“内容驱动优化”流程。
    """
    meta_model = os.getenv("PROMPT_OPTIMIZER_MODEL") or "gpt-5.4"

    system_msg = (
        "你是一名专业的提示词工程师，擅长为大模型生成结构清晰、可执行性强的中文提示词。"
        "你的任务是：在保留原有意图和人设的前提下，根据评估总结对提示词进行迭代优化，输出一个新的完整提示词。"
    )
    user_msg = textwrap.dedent(
        f"""
        这是当前使用的提示词（版本号将升级为 v{new_version}）：

        --- 原始提示词开始 ---
        {original_prompt.strip()}
        --- 原始提示词结束 ---

        这是根据多模型生成结果得到的评估总结（包含常见问题与优化方向），当前希望生成的文章长度控制在 1000-1200 字左右：

        --- 评估总结开始 ---
        {eval_summary.strip()}
        --- 评估总结结束 ---

        请在充分消化以上内容的基础上，生成一份新的完整提示词文本，要求：
        1. 新提示词开头显式注明“提示词版本：v{new_version}”。
        2. 明确写清：人设、写作风格、文章结构（含开头/中间3个观点/结尾）、内容方向、注意事项等关键信息。
        3. 必须针对评估总结中提到的问题给出对应的约束（例如：字数区间、是否引用经典、结构是否清晰等）。
        4. 用 Markdown 结构化书写，便于在文件中直接保存使用。
        5. 只输出提示词正文，不要任何额外解释。
        """
    )

    resp = client.chat.completions.create(
        model=meta_model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.4,
    )
    content = resp.choices[0].message.content or ""
    return content.strip()


def build_optimized_prompt(
    original_prompt: str, eval_summary: str, new_version: int
) -> str:
    """
    对外暴露的构建函数：优先使用 LLM 做自动优化，
    若出现异常则退回到原始提示词 + 评估总结的简单拼接，避免整个流程失败。
    """
    try:
        return optimize_prompt_via_llm(original_prompt, eval_summary, new_version)
    except Exception as e:
        # 回退策略：至少保证有可用的新版本提示词
        fallback = (
            f"（提示词版本：v{new_version}，LLM 自动优化失败，以下为原始提示词 + 评估总结的整合版本）\n\n"
        )
        fallback += original_prompt.strip()
        fallback += "\n\n---\n\n"
        fallback += "## 本次自动评估总结（供人工参考，可据此手动继续优化）\n\n"
        fallback += eval_summary.strip()
        print(f"提示词自动优化失败，已使用回退方案：{e}")
        return fallback.strip()


# ====== 5. 主流程 ======


def main():
    models_cfg = load_models()

    # 使用当前 prompts 目录下版本号最大的 vN.md 作为基线提示词
    prompt_path, current_version = get_latest_prompt_file()
    prompt = load_prompt(prompt_path)

    # 本次生成结果与评估，按提示词版本号归档到 outputs/v{current_version}/ 下
    run_output_dir = OUTPUT_DIR / f"v{current_version}"
    run_output_dir.mkdir(parents=True, exist_ok=True)

    # 根据你的 models.json，按 provider 分组
    provider_map = {
        "openai": models_cfg.get("openai_models", []),
        "anthropic": models_cfg.get("anthropic_models", []),
        "google": models_cfg.get("google_models", []),
        "deepseek": models_cfg.get("deepseek_models", []),
    }

    all_results: List[Dict[str, Any]] = []

    for provider, models in provider_map.items():
        for m in models:
            model_name = m["name"]
            print(f"== 调用 {provider} / {model_name} ==")
            try:
                article = generate_with_model(provider, model_name, prompt)
            except Exception as e:
                print(f"  调用失败，跳过 {provider}/{model_name}：{e}")
                continue

            # 保存原文到对应版本目录下
            safe_model_name = model_name.replace(":", "_").replace("/", "_")
            out_file = run_output_dir / f"{provider}__{safe_model_name}.txt"
            out_file.write_text(article, encoding="utf-8")

            # 自动评价
            evaluation = evaluate_article(article)
            all_results.append(
                {
                    "provider": provider,
                    "model": model_name,
                    "evaluation": evaluation,
                    "output_path": str(out_file),
                }
            )
            print(
                f"  得分: {evaluation['score']}, 字数: {evaluation['chars']}, 段落数: {evaluation['paragraphs']}"
            )

    # 汇总评价并输出为 JSON（同样放到当前版本目录下）
    eval_file = run_output_dir / "evaluations.json"
    with eval_file.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n已保存评价结果到: {eval_file}")

    # 给出基于规则的整体优化建议
    if all_results:
        summary = summarize_evaluations(all_results)
        print("\n" + summary)

        # 基于当前版本生成下一个版本的完整提示词（版本号递增，且由 LLM 自动优化）
        next_version = current_version + 1
        optimized_prompt = build_optimized_prompt(prompt, summary, next_version)
        optimized_file = PROMPTS_DIR / f"v{next_version}.md"
        optimized_file.write_text(optimized_prompt, encoding="utf-8")
        print(
            f"\n已生成优化版提示词 v{next_version}，文件路径: {optimized_file}（后续请直接使用该版本提示词生成文章）"
        )
    else:
        print("\n暂无模型调用结果（可能是接口调用失败）。")


if __name__ == "__main__":
    main()

