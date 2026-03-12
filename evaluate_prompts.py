import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import textwrap

from openai import OpenAI


BASE_DIR = Path(__file__).parent
MODELS_FILE = BASE_DIR / "models.json"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
EVALUATIONS_HISTORY_FILE = BASE_DIR / "evaluations_history.json"

# 新增：模块化提示词文件路径
BASE_PROMPT_FILE = PROMPTS_DIR / "v5_base.md"
STRUCTURES_LIBRARY_FILE = PROMPTS_DIR / "structures_library.md"
TITLES_LIBRARY_FILE = PROMPTS_DIR / "titles_library.md"


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


def get_client(provider: str):
    """
    按 provider 读取对应的 base_url 和 api_key；
    若未配置该 provider，则使用通用 llm_base_url / llm_api_key 兜底。
    若仍无 api_key，返回 None（调用方应跳过该 provider）。
    """
    key_prefix = provider.lower().replace("-", "_")
    base_url = (
        os.getenv(f"{key_prefix}_base_url")
        or os.getenv(f"{key_prefix.upper()}_BASE_URL")
        or os.getenv("llm_base_url")
        or os.getenv("LLM_BASE_URL")
    )
    api_key = (
        os.getenv(f"{key_prefix}_api_key")
        or os.getenv(f"{key_prefix.upper()}_API_KEY")
        or os.getenv("llm_api_key")
        or os.getenv("LLM_API_KEY")
    )
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=base_url or "https://api.openai.com/v1",
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


def get_prompt_file_by_version(version: int) -> Path:
    """
    根据版本号获取提示词文件路径。
    """
    prompt_path = PROMPTS_DIR / f"v{version}.md"
    if not prompt_path.exists():
        raise RuntimeError(f"未找到提示词文件：{prompt_path}")
    return prompt_path


def load_base_prompt() -> str:
    """加载基础提示词（人设+风格+方向）"""
    if not BASE_PROMPT_FILE.exists():
        raise RuntimeError(f"未找到基础提示词文件：{BASE_PROMPT_FILE}")
    return BASE_PROMPT_FILE.read_text(encoding="utf-8")


def load_structure(structure_type: str = "场景感悟式") -> str:
    """
    从结构库中加载指定结构。

    Args:
        structure_type: 结构类型，如 "场景感悟式" / "今昔对比式" / "对话展开式"

    Returns:
        结构要求文本
    """
    if not STRUCTURES_LIBRARY_FILE.exists():
        # 如果结构库不存在，返回默认结构
        return get_default_structure(structure_type)

    structures_text = STRUCTURES_LIBRARY_FILE.read_text(encoding="utf-8")
    structure = extract_structure_from_text(structures_text, structure_type)

    if structure:
        return structure
    else:
        return get_default_structure(structure_type)


def extract_structure_from_text(text: str, structure_type: str) -> Optional[str]:
    """从结构库文本中提取指定结构"""
    import re

    # 匹配从 "## 结构X：XXX" 到下一个 "##" 之前的内容
    patterns = [
        rf'(## 结构[一二三四五六七八九十]+[：:]\s*{re.escape(structure_type)}.*?)(?=## 结构|$)',
        rf'(## 结构\d+[：:]\s*{re.escape(structure_type)}.*?)(?=## 结构|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 提取模板部分（从"结构模板"开始）
            template_match = re.search(r'(结构模板|模板).*?\n(.*?)(?=$|\n##|\n\*\*)', content, re.DOTALL)
            if template_match:
                return template_match.group(1).strip() + "\n" + template_match.group(2).strip()
            return content

    return None


def get_default_structure(structure_type: str) -> str:
    """返回默认结构（当结构库不存在时）"""
    defaults = {
        "场景感悟式": """
## 结构要求：场景感悟式

**开头**：一个具体场景（3-5句）
- 直接入题，不拖沓，可从一个具体画面切入
- 明确点出"人过六十 / 老了才明白 / 老了才发现"等主题

**中间**：3-4个观点段落
- 每个段落从一个细节/故事出发，顺出一层道理
- 段落间空一行，方便阅读
- 每段控制在3-5句
- 分别围绕：和自己相处、和家人相处、和世界相处

**结尾**：1-2句升华收束
- 简短有力，像写给同龄人的一小段慢慢的叮嘱
- 不开启新故事或论证
""",
        "对话展开式": """
## 结构要求：对话展开式

**开头**：一句对话/一个提问（3-5句引入）

**中间**：对话展开 + 我的反应 + 事后的感悟
- 完整叙述对话场景
- 描述我当时的反应（说了什么/没说什么）
- 事后的反思和感悟

**结尾**：一句劝慰
- 像对同龄人的轻轻叮嘱
- 不开启新话题
""",
        "今昔对比式": """
## 结构要求：今昔对比式

**开头**：一句话点出对比
- "以前...现在..."
- "年轻时...老了才..."

**中间**：3个对比场景
- 每个场景都是"当年的我 vs 现在的我"
- 通过具体事件展现观念/心态的变化

**结尾**：一句感悟
- 总结变化的核心
""",
    }

    return defaults.get(structure_type, defaults["场景感悟式"])


def load_prompt(prompt_path: Path) -> str:
    """保留向后兼容：加载旧版完整提示词"""
    return prompt_path.read_text(encoding="utf-8")


# ====== 2. 提示词构建函数 ======


def build_prompt(
    topic: str,
    structure_type: str = "场景感悟式",
    custom_title: str = None,
    custom_structure: str = None,
    use_base_prompt: bool = True,
) -> str:
    """
    构建完整的写作提示词。

    Args:
        topic: 选题，如 "和老伴吵了一辈子，老了才发现"
        structure_type: 结构类型，如 "场景感悟式" / "今昔对比式" / "对话展开式"
        custom_title: 自定义标题（可选）
        custom_structure: 自定义结构（可选），用于仿写爆文
        use_base_prompt: 是否使用模块化提示词（True）还是旧版提示词（False）

    Returns:
        完整的写作提示词
    """
    if use_base_prompt:
        # 新版：使用模块化系统
        base = load_base_prompt()
        structure = custom_structure or load_structure(structure_type)
        title = custom_title or f"《{topic}》"

        full_prompt = f"""{base}

## 标题
{title}

{structure}

## 选题
{topic}

## 字数要求
1000-1200字（微感悟/对话体/日记体可放宽至500-800字）

请根据以上要求，写一篇完整的文章。"""
    else:
        # 旧版：加载完整提示词（向后兼容）
        prompt_path, _ = get_latest_prompt_file()
        base = load_prompt(prompt_path)
        title = custom_title or f"《{topic}》"

        full_prompt = f"""{base}

## 标题
{title}

## 选题
{topic}

请根据以上要求，写一篇完整的文章。"""

    return full_prompt


def generate_title_from_topic(topic: str, title_type: str = None) -> str:
    """
    根据选题生成标题。

    Args:
        topic: 选题
        title_type: 标题类型（可选），如 "感悟发现型" / "对话引用型" / "场景细节型"

    Returns:
        生成的标题
    """
    if title_type == "对话引用型":
        # 尝试提取对话
        if "女儿" in topic:
            return f"《女儿说"挺好的"，我知道她在硬撑》"
        elif "老伴" in topic:
            return f"《老伴说"你退休了别管我"》"
        elif "母亲" in topic or "妈妈" in topic:
            return f"《老母亲说"你别回来了"》"
    elif title_type == "场景细节型":
        # 提取场景关键词
        if "老伴" in topic:
            return f"《老伴炖的那碗汤，我喝了一辈子》"
        elif "女儿" in topic:
            return f"《视频挂了之后，我常常对着手机发呆》"
    elif title_type == "今昔对比型":
        return f"《以前总觉得{topic.split('，')[0]}，现在{topic.split('，')[1] if '，' in topic else '才明白'}》"

    # 默认使用感悟发现型
    return f"《老了才发现，{topic}》"


# ====== 3. 统一的模型调用函数（兼容你提供的所有 model name）======


def call_llm(
    client: OpenAI,
    model_name: str,
    prompt: str,
    topic: str = None,
    keywords: List[str] = None,
) -> str:
    """
    通过 OpenAI 兼容接口调用任意模型。
    使用传入的 client（按 provider 已配置好 base_url / api_key）。

    Args:
        client: OpenAI 客户端
        model_name: 模型名称
        prompt: 系统提示词
        topic: 选题（可选），如果提供且 keywords 为空，则使用选题作为用户消息
        keywords: 关键词列表（可选），用于旧版兼容

    Returns:
        生成的文章文本
    """
    # 构建用户消息
    if keywords:
        user_content = "请围绕以下关键词写一篇公众号文章：\n\n" + ",".join(keywords)
    elif topic:
        user_content = f"请根据以上要求，围绕选题「{topic}」写一篇完整的公众号文章。"
    else:
        user_content = "请根据以上要求，写一篇完整的公众号文章。"

    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        temperature=0.8,
    )
    return resp.choices[0].message.content or ""


def generate_with_model(
    provider: str,
    model_name: str,
    prompt: str,
    topic: str = None,
    keywords: List[str] = None,
) -> str:
    """
    使用该 provider 对应的 base_url / api_key 创建客户端并调用。
    若该 provider 未配置 api_key，抛出 RuntimeError。

    Args:
        provider: provider 名称
        model_name: 模型名称
        prompt: 完整提示词
        topic: 选题（可选）
        keywords: 关键词列表（可选，旧版兼容）

    Returns:
        生成的文章文本
    """
    client = get_client(provider)
    if client is None:
        raise RuntimeError(
            f"未配置 {provider} 的 API Key，请在 .env 中设置 "
            f"{provider.lower()}_api_key 或 llm_api_key"
        )
    return call_llm(client, model_name, prompt, topic=topic, keywords=keywords)


# ====== 3. 简单可实现的自动评价指标 ======


def extract_length_requirement(prompt: str) -> Tuple[int, int]:
    """
    从提示词中提取字数要求。
    返回 (min_length, max_length)，如果未找到则返回默认值 (400, 1500)。
    """
    import re

    # 尝试匹配 "X-Y字" 格式
    pattern1 = r"(\d+)\s*[-~至到]\s*(\d+)\s*[字字符]"
    match1 = re.search(pattern1, prompt)
    if match1:
        return int(match1.group(1)), int(match1.group(2))

    # 尝试匹配 "约X字" 或 "X字左右" 格式
    pattern2 = r"(?:约|左右|大约|大概)?(\d{3,4})\s*[字字符]"
    match2 = re.search(pattern2, prompt)
    if match2:
        length = int(match2.group(1))
        # 允许 ±20% 的浮动
        return int(length * 0.8), int(length * 1.2)

    # 尝试匹配 "至少X字" 格式
    pattern3 = r"(?:至少|最少|不低于)(\d+)\s*[字字符]"
    match3 = re.search(pattern3, prompt)
    if match3:
        min_length = int(match3.group(1))
        return min_length, min_length * 2

    # 尝试匹配 "不超过X字" 格式
    pattern4 = r"(?:不超过|最多|不高于)(\d+)\s*[字字符]"
    match4 = re.search(pattern4, prompt)
    if match4:
        max_length = int(match4.group(1))
        return 0, max_length

    # 默认范围
    return 400, 1500


def evaluate_article(text: str, length_range: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
    """
    不调用别的模型，只做一些"规则+统计"型评分，
    简单、无成本，但能看出结构是否对齐。

    评分体系（总分 12 分）：
    - intro_ok: 2分 - 开头是否直接入题
    - has_classic: 2分 - 是否引用经典（诗词、古人名言）
    - has_headings: 1分 - 是否有小标题结构
    - para_count_reasonable: 1分 - 段落数是否合理（5-20段）
    - has_3_points: 1分 - 是否有 3 个明显观点段落
    - ending_good: 2分 - 结尾是否简短有力或有总结词
    - in_length_range: 2分 - 字数是否达标
    - avg_para_length_ok: 1分 - 平均段落长度是否合理（30-150字）

    Args:
        text: 待评估的文章文本
        length_range: 字数范围 (min, max)，None 则使用默认值 (400, 1500)
    """
    if length_range is None:
        length_range = (400, 1500)

    min_length, max_length = length_range

    # 基础统计
    chars = len(text)
    paragraphs = [p for p in text.split("\n") if p.strip()]
    para_count = len(paragraphs)

    # 1. 是否直接入题（首段是否很快出现核心话题关键词）
    first_line = paragraphs[0].strip() if paragraphs else ""
    intro_ok = any(kw in first_line for kw in ["老了", "人过六十", "退休", "这一生", "人到老年", "花甲", "古稀"])

    # 2. 经典引用检测（改进版）
    # 检测书名号
    has_book_marks = "《" in text and "》" in text
    # 检测古人名/诗人名/现代作家
    classic_authors = [
        "孔子", "孟子", "庄子", "老子", "荀子",
        "陶渊明", "苏轼", "杜甫", "李白", "白居易",
        "王维", "李商隐", "杜牧", "陆游", "辛弃疾",
        "诗经", "楚辞", "论语", "道德经", "战国策",
        "汪曾祺", "龙应台", "史铁生", "杨绛", "季羡林",
    ]
    has_author = any(author in text for author in classic_authors)
    # 检测引用标记词
    quote_patterns = ["诗云", "诗曰", "曰", "曾经说过", "有诗为证", "写道", "说"]
    has_quote = any(pattern in text for pattern in quote_patterns)
    has_classic = has_book_marks or has_author or has_quote

    # 3. 是否有小标题结构（改进版）
    import re
    heading_patterns = [
        "^##\\s",  # Markdown 标题
        "^#\\s",   # Markdown 一级标题
        "^\\d+\\s*[、.．]",  # 数字序号：1. 1、 1．
        "^[一二三四五六七八九十]+\\s*[、.．]",  # 中文数字
        "^[其第]?[一二三四五六七八九十]+[个项]",  # 其一、第二、三项
        "^首先\\s", "^其次\\s", "^最后\\s",  # 顺序词
        "^第一\\s", "^第二\\s", "^第三\\s",  # 序数词
    ]
    has_headings = False
    for para in paragraphs:
        para_stripped = para.strip()
        for pattern in heading_patterns:
            if re.match(pattern, para_stripped, re.MULTILINE):
                has_headings = True
                break
        if has_headings:
            break

    # 4. 段落数是否合理（避免过度碎片化或过于冗长）
    para_count_reasonable = 5 <= para_count <= 20

    # 5. 结构检测（中间是否有 3 个明显分段）
    middle_para_count = max(0, para_count - 2)
    has_3_points = middle_para_count >= 3

    # 6. 结尾是否简短有力或有总结词（改进版）
    last_para = paragraphs[-1].strip() if paragraphs else ""
    ending_short = len(last_para) <= 80
    # 检测总结词
    ending_patterns = ["总之", "所以", "因此", "综上", "真的，", "也就够了", "这才"]
    has_ending_word = any(pattern in last_para for pattern in ending_patterns)
    ending_good = ending_short or has_ending_word

    # 7. 字数是否在指定范围内
    in_length_range = min_length <= chars <= max_length

    # 8. 平均段落长度是否合理（避免碎片化）
    avg_para_length = chars / para_count if para_count > 0 else 0
    avg_para_length_ok = 30 <= avg_para_length <= 150

    # 计算得分
    score = 0
    weights = {
        "intro_ok": 2,
        "has_classic": 2,
        "has_headings": 1,
        "para_count_reasonable": 1,
        "has_3_points": 1,
        "ending_good": 2,
        "in_length_range": 2,
        "avg_para_length_ok": 1,
    }

    details = {
        "intro_ok": intro_ok,
        "has_classic": has_classic,
        "has_headings": has_headings,
        "para_count_reasonable": para_count_reasonable,
        "has_3_points": has_3_points,
        "ending_good": ending_good,
        "in_length_range": in_length_range,
        "avg_para_length_ok": avg_para_length_ok,
        "chars": chars,
        "paragraphs": para_count,
        "avg_para_length": round(avg_para_length, 1),
        "length_range": f"{min_length}-{max_length}",
    }

    for k, w in weights.items():
        if details[k]:
            score += w

    details["score"] = score
    return details


# ====== 4. 基于多模型结果，自动生成“提示词优化建议” ======


def summarize_evaluations(results: List[Dict[str, Any]], length_range: Optional[Tuple[int, int]] = None) -> str:
    """
    这里不用再调模型，直接基于规则结果给一点通用建议。
    你后续也可以改成再调一个大模型，专门做 meta-分析。
    """
    if not results:
        return "暂无结果，无法给出优化建议。"

    # 统计常见问题
    intro_bad = sum(1 for r in results if not r["evaluation"]["intro_ok"])
    no_classic = sum(1 for r in results if not r["evaluation"]["has_classic"])
    no_headings = sum(1 for r in results if not r["evaluation"]["has_headings"])
    para_count_bad = sum(1 for r in results if not r["evaluation"]["para_count_reasonable"])
    not_3_points = sum(1 for r in results if not r["evaluation"]["has_3_points"])
    ending_bad = sum(1 for r in results if not r["evaluation"]["ending_good"])
    wrong_length = sum(1 for r in results if not r["evaluation"]["in_length_range"])
    avg_para_length_bad = sum(1 for r in results if not r["evaluation"]["avg_para_length_ok"])

    lines = []
    lines.append("优化建议（基于多模型输出的共性表现）：")

    if intro_bad > 0:
        lines.append(
            "- 开头要求可以更具体，比如限制首段在 2-3 句内直接点明「人过六十 / 老了才明白 / 花甲之年」的主题。"
        )
    if no_classic > 0:
        lines.append(
            "- 可以在提示词中补充：至少自然引用 1-2 句古诗词或经典名句（如《诗经》、论语、古人名言等），并与观点紧密相关。"
        )
    if no_headings > 0:
        lines.append(
            "- 建议添加小标题结构，使用「一、」「二、」「三、」或「1.」「2.」「3.」「其一、」「其二、」等形式标注观点段落。"
        )
    if para_count_bad > 0:
        lines.append(
            "- 文章段落数建议控制在 5-20 段之间，避免过度碎片化（每段 1-2 句）或过于冗长（整段不分）。"
        )
    if avg_para_length_bad > 0:
        lines.append(
            "- 每段平均长度建议在 30-150 字之间，避免过度碎片化或段落过长。"
        )
    if not_3_points > 0:
        lines.append(
            "- 强调中间必须拆成 3 个观点段落，每个观点 2-3 句，并用空行分隔，方便在公众号中阅读。"
        )
    if ending_bad > 0:
        lines.append(
            "- 对结尾加一句约束：用 1-2 句完成收束，不要在结尾开启新的故事或论证。可以使用「真的，够了」「这才...」等总结性表达。"
        )
    if wrong_length > 0:
        # 使用实际的字数要求
        if length_range:
            lines.append(f"- 明确要求文章总字数控制在 {length_range[0]}-{length_range[1]} 字之间，避免过长或过短。")
        else:
            lines.append("- 明确要求文章总字数控制在指定范围内，避免过长或过短。")

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
    meta_client = get_client(os.getenv("PROMPT_OPTIMIZER_PROVIDER") or "openai")
    if meta_client is None:
        raise RuntimeError(
            "提示词自动优化需要 OpenAI 客户端，请在 .env 中配置 openai_api_key 或 llm_api_key"
        )

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

    resp = meta_client.chat.completions.create(
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
) -> Optional[str]:
    """
    对外暴露的构建函数：使用 LLM 做自动优化。
    若出现异常则返回 None，调用方可决定是否跳过生成。
    """
    try:
        return optimize_prompt_via_llm(original_prompt, eval_summary, new_version)
    except Exception as e:
        print(f"提示词自动优化失败，跳过生成新版本：{e}")
        return None


# ====== 5. 评估历史记录 ======


def load_evaluations_history() -> Dict[str, Any]:
    """
    加载评估历史记录，如果不存在则返回空字典。
    """
    if not EVALUATIONS_HISTORY_FILE.exists():
        return {}
    with EVALUATIONS_HISTORY_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_evaluations_history(history: Dict[str, Any]) -> None:
    """
    保存评估历史记录。
    """
    with EVALUATIONS_HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def calculate_version_summary(evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算单个版本的评估摘要。
    """
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

    # 计算各维度通过率
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


def update_evaluations_history(
    version: int, evaluations: List[Dict[str, Any]], prompt_path: str
) -> None:
    """
    更新评估历史记录。
    """
    history = load_evaluations_history()
    summary = calculate_version_summary(evaluations)

    history[f"v{version}"] = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "prompt_path": prompt_path,
        "summary": summary,
        "evaluations": evaluations,
    }

    save_evaluations_history(history)


def show_version_ranking(limit: int = 10) -> None:
    """
    展示版本排名列表。
    """
    history = load_evaluations_history()
    if not history:
        print("暂无评估历史记录。")
        return

    # 按平均分排序
    versions = []
    for ver, data in history.items():
        versions.append(
            (
                ver,
                data["summary"]["avg_score"],
                data["summary"]["max_score"],
                data["summary"]["model_count"],
                data["timestamp"],
            )
        )

    versions.sort(key=lambda x: x[1], reverse=True)

    print(f"\n{'版本':<8} {'平均分':<8} {'最高分':<8} {'模型数':<8} {'时间'}")
    print("-" * 70)
    for ver, avg, max_score, count, timestamp in versions[:limit]:
        # 只显示日期部分
        date = timestamp.split("T")[0]
        print(f"{ver:<8} {avg:<8.2f} {max_score:<8} {count:<8} {date}")

    # 找出历史最佳版本
    if versions:
        best_ver, best_avg, best_max, _, _ = versions[0]
        print(f"\n历史最佳版本: {best_ver}（平均分: {best_avg:.2f}，最高分: {best_max}）")


def compare_with_best(version: int) -> None:
    """
    将当前版本与历史最佳版本进行对比。
    """
    history = load_evaluations_history()
    if not history or len(history) < 2:
        return

    # 找出历史最佳版本（排除当前版本）
    best_ver = None
    best_avg = -1
    for ver, data in history.items():
        if ver != f"v{version}":
            avg = data["summary"]["avg_score"]
            if avg > best_avg:
                best_avg = avg
                best_ver = ver

    if best_ver is None:
        return

    current_key = f"v{version}"
    if current_key not in history:
        return

    current_avg = history[current_key]["summary"]["avg_score"]
    diff = current_avg - best_avg

    print(f"\n版本对比: v{version} vs {best_ver}")
    print(f"  当前版本平均分: {current_avg:.2f}")
    print(f"  历史最佳平均分: {best_avg:.2f}")
    if diff > 0:
        print(f"  差异: +{diff:.2f} (当前版本更好)")
    elif diff < 0:
        print(f"  差异: {diff:.2f} (历史版本更好)")
    else:
        print(f"  差异: 0 (持平)")


# ====== 6. 版本创建 ======


def create_new_version(base_version: int, new_version: Optional[int] = None) -> Path:
    """
    基于指定版本创建新版本（复制内容）。

    Args:
        base_version: 基础版本号
        new_version: 新版本号，None 则自动递增

    Returns:
        新版本提示词文件路径
    """
    base_path = get_prompt_file_by_version(base_version)
    base_content = base_path.read_text(encoding="utf-8")

    # 确定新版本号
    if new_version is None:
        # 获取当前最大版本号 + 1
        _, latest_ver = get_latest_prompt_file()
        new_version = latest_ver + 1

    new_path = PROMPTS_DIR / f"v{new_version}.md"

    if new_path.exists():
        raise RuntimeError(f"目标版本已存在：{new_path}")

    # 复制内容
    new_path.write_text(base_content, encoding="utf-8")

    print(f"已创建新版本 v{new_version}，基于 v{base_version}")
    print(f"  新版本路径: {new_path}")
    print(f"  提示: 请手动编辑 {new_path.name} 后再运行评估")

    return new_path


# ====== 7. 主流程 ======


def run_single_generation(
    topic: str,
    structure_type: str = "场景感悟式",
    provider: str = None,
    model_name: str = None,
    custom_title: str = None,
    custom_structure: str = None,
    output_file: str = None,
) -> None:
    """
    单篇文章生成模式（使用新模块化系统）。

    Args:
        topic: 选题
        structure_type: 结构类型
        provider: 指定 provider（可选），不指定则使用第一个启用的模型
        model_name: 指定模型名称（可选）
        custom_title: 自定义标题（可选）
        custom_structure: 自定义结构（可选），用于仿写爆文
        output_file: 输出文件路径（可选）
    """
    print(f"== 使用模块化提示词系统 ==")
    print(f"选题: {topic}")
    print(f"结构: {structure_type}")

    # 构建提示词
    prompt = build_prompt(
        topic=topic,
        structure_type=structure_type,
        custom_title=custom_title,
        custom_structure=custom_structure,
        use_base_prompt=True,
    )

    # 确定使用的模型
    models_cfg = load_models()

    if provider and model_name:
        # 使用指定的模型
        providers_to_try = [(provider, model_name)]
    else:
        # 使用第一个启用的模型
        for provider_name, models_key in [
            ("openai", "openai_models"),
            ("anthropic", "anthropic_models"),
            ("google", "google_models"),
            ("deepseek", "deepseek_models"),
        ]:
            models = models_cfg.get(models_key, [])
            for m in models:
                if m.get("enabled", True):
                    providers_to_try = [(provider_name, m["name"])]
                    break
            if providers_to_try:
                break
        else:
            print("错误：未找到启用的模型，请在 models.json 中配置")
            return

    # 调用模型
    for prov, mdl in providers_to_try:
        print(f"\n== 调用 {prov} / {mdl} ==")
        try:
            article = generate_with_model(prov, mdl, prompt, topic=topic)
        except Exception as e:
            print(f"  调用失败：{e}")
            continue

        # 保存或输出
        if output_file:
            out_path = Path(output_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(article, encoding="utf-8")
            print(f"\n已保存到: {out_path}")
        else:
            print("\n" + "=" * 50)
            print(article)
            print("=" * 50)

        # 评估文章
        length_range = (1000, 1200)
        evaluation = evaluate_article(article, length_range)
        print(f"\n评估结果:")
        print(f"  得分: {evaluation['score']}/12")
        print(f"  字数: {evaluation['chars']}")
        print(f"  段落数: {evaluation['paragraphs']}")
        print(f"  是否在字数范围内: {'是' if evaluation['in_length_range'] else '否'}")
        print(f"  是否引用经典: {'是' if evaluation['has_classic'] else '否'}")
        print(f"  开头是否直接: {'是' if evaluation['intro_ok'] else '否'}")
        print(f"  结尾是否简洁: {'是' if evaluation['ending_good'] else '否'}")

        return

    print("\n错误：所有模型调用失败")


def run_batch_generation(
    topics: List[str],
    structure_types: List[str] = None,
    provider: str = None,
    model_name: str = None,
    output_dir: str = None,
) -> None:
    """
    批量生成模式（用于日更）。

    Args:
        topics: 选题列表
        structure_types: 结构类型列表（可选），不指定则循环使用默认结构
        provider: 指定 provider（可选）
        model_name: 指定模型名称（可选）
        output_dir: 输出目录（可选），默认为 outputs/batch/
    """
    if structure_types is None:
        structure_types = ["场景感悟式", "对话展开式", "今昔对比式", "一事一议式"]

    if output_dir is None:
        output_dir = OUTPUT_DIR / "batch"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"== 批量生成模式 ==")
    print(f"选题数: {len(topics)}")
    print(f"结构类型: {', '.join(structure_types)}")
    print(f"输出目录: {output_dir}\n")

    models_cfg = load_models()

    # 确定使用的模型
    if provider and model_name:
        providers_to_try = [(provider, model_name)]
    else:
        for provider_name, models_key in [
            ("openai", "openai_models"),
            ("anthropic", "anthropic_models"),
            ("google", "google_models"),
            ("deepseek", "deepseek_models"),
        ]:
            models = models_cfg.get(models_key, [])
            for m in models:
                if m.get("enabled", True):
                    providers_to_try = [(provider_name, m["name"])]
                    break
            if providers_to_try:
                break

    if not providers_to_try:
        print("错误：未找到启用的模型")
        return

    prov, mdl = providers_to_try[0]
    print(f"使用模型: {prov} / {mdl}\n")

    results = []
    for i, topic in enumerate(topics, 1):
        # 循环使用结构类型
        structure_type = structure_types[(i - 1) % len(structure_types)]

        print(f"[{i}/{len(topics)}] 选题: {topic} ({structure_type})")

        try:
            prompt = build_prompt(
                topic=topic,
                structure_type=structure_type,
                use_base_prompt=True,
            )
            article = generate_with_model(prov, mdl, prompt, topic=topic)

            # 保存
            safe_topic = topic.replace(" ", "_").replace("，", "_")[:30]
            out_file = output_dir / f"{i:02d}_{safe_topic}.md"
            out_file.write_text(article, encoding="utf-8")

            # 评估
            evaluation = evaluate_article(article, (1000, 1200))

            results.append({
                "topic": topic,
                "structure": structure_type,
                "file": str(out_file),
                "score": evaluation["score"],
                "chars": evaluation["chars"],
            })

            print(f"  ✓ 得分: {evaluation['score']}/12, 字数: {evaluation['chars']}, 已保存: {out_file.name}")

        except Exception as e:
            print(f"  ✗ 失败: {e}")
            continue

    # 汇总
    print(f"\n== 批量生成完成 ==")
    print(f"成功: {len(results)}/{len(topics)}")
    if results:
        avg_score = sum(r["score"] for r in results) / len(results)
        print(f"平均分: {avg_score:.2f}")
        print(f"\n最佳文章:")
        best = max(results, key=lambda x: x["score"])
        print(f"  {best['topic']} - {best['score']}/12 ({best['structure']})")


def run_evaluation(base_version: Optional[int] = None, skip_optimize: bool = False) -> None:
    """
    运行评估流程。

    Args:
        base_version: 基线提示词版本号，None 表示使用最新版本
        skip_optimize: 是否跳过生成新版本提示词
    """
    models_cfg = load_models()

    # 确定基线提示词版本
    if base_version is None:
        prompt_path, current_version = get_latest_prompt_file()
    else:
        prompt_path = get_prompt_file_by_version(base_version)
        current_version = base_version
    prompt = load_prompt(prompt_path)

    print(f"使用基线提示词: v{current_version} ({prompt_path.name})")

    # 从提示词中提取字数要求
    length_range = extract_length_requirement(prompt)
    print(f"检测到字数要求: {length_range[0]}-{length_range[1]} 字")

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
            if not m.get("enabled", True):
                print(f"== 跳过（未启用）{provider} / {m['name']} ==")
                continue
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

            # 自动评价（使用从提示词中提取的字数要求）
            evaluation = evaluate_article(article, length_range)
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

    # 更新评估历史记录
    if all_results:
        update_evaluations_history(current_version, all_results, str(prompt_path))
        print(f"已更新评估历史记录: {EVALUATIONS_HISTORY_FILE}")

        # 显示版本对比
        compare_with_best(current_version)

        # 给出基于规则的整体优化建议
        summary = summarize_evaluations(all_results, length_range)
        print("\n" + summary)

        # 生成下一版提示词（除非跳过）
        if not skip_optimize:
            next_version = current_version + 1
            optimized_prompt = build_optimized_prompt(prompt, summary, next_version)
            if optimized_prompt:
                optimized_file = PROMPTS_DIR / f"v{next_version}.md"
                optimized_file.write_text(optimized_prompt, encoding="utf-8")
                print(
                    f"\n已生成优化版提示词 v{next_version}，文件路径: {optimized_file}（后续请直接使用该版本提示词生成文章）"
                )
            else:
                print("\n跳过生成新版本提示词。")
        else:
            print("\n已跳过生成新版本提示词（--skip-optimize）。")
    else:
        print("\n暂无模型调用结果（可能是接口调用失败）。")


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。
    """
    parser = argparse.ArgumentParser(
        description="提示词评估与优化工具（支持模块化提示词系统）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单篇生成模式（新模块化系统）
  %(prog)s --generate "和老伴吵了一辈子，老了才发现"
  %(prog)s --generate "女儿说挺好的" --structure 对话展开式
  %(prog)s --generate "和老伴吵了一辈子" --title 《老伴炖的那碗汤》 --output article.md

  # 批量生成模式（日更）
  %(prog)s --batch "和老伴吵了一辈子" "女儿说挺好的" "半夜醒来才承认老了"
  %(prog)s --batch topic1 topic2 topic3 --structures 场景感悟式 对话展开式

  # 旧版评估模式（向后兼容）
  %(prog)s --evaluate                          # 使用最新版提示词运行评估并生成新版本
  %(prog)s --evaluate --from-version 3         # 基于 v3 版本运行评估
  %(prog)s --evaluate --skip-optimize          # 运行评估但不生成新版本提示词
  %(prog)s --ranking                           # 显示历史版本排名

  # 版本创建
  %(prog)s --create-version 1                  # 基于 v1 创建新版本（自动递增版本号）
  %(prog)s --create-version 1 --to 7           # 基于 v1 创建 v7 版本

可用结构类型:
  场景感悟式, 今昔对比式, 对话展开式, 三段递进式,
  一事一议式, 问答体, 书信体, 日记体
        """,
    )

    # 模式选择（互斥）
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--generate",
        type=str,
        metavar="TOPIC",
        help="单篇生成模式：生成一篇文章（使用模块化系统）",
    )
    mode_group.add_argument(
        "--batch",
        nargs="+",
        metavar="TOPIC",
        help="批量生成模式：生成多篇文章（日更用）",
    )
    mode_group.add_argument(
        "--evaluate",
        action="store_true",
        help="评估模式：运行多模型评估（旧版，向后兼容）",
    )
    mode_group.add_argument(
        "--ranking",
        action="store_true",
        help="显示历史版本排名并退出",
    )
    mode_group.add_argument(
        "--create-version",
        type=int,
        metavar="N",
        help="基于指定版本创建新版本（复制内容）",
    )

    # 单篇生成选项
    parser.add_argument(
        "--structure",
        type=str,
        default="场景感悟式",
        help="结构类型（默认：场景感悟式）",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="自定义标题（可选）",
    )
    parser.add_argument(
        "--custom-structure",
        type=str,
        help="自定义结构文本（可选，用于仿写爆文）",
    )
    parser.add_argument(
        "--output",
        type=str,
        metavar="FILE",
        help="输出文件路径（可选）",
    )

    # 批量生成选项
    parser.add_argument(
        "--structures",
        nargs="+",
        metavar="TYPE",
        help="批量生成时使用的结构类型列表（可选）",
    )
    parser.add_argument(
        "--batch-output",
        type=str,
        metavar="DIR",
        help="批量生成输出目录（默认：outputs/batch/）",
    )

    # 评估模式选项
    parser.add_argument(
        "--from-version",
        type=int,
        metavar="N",
        help="基于指定版本的提示词运行评估（评估模式）",
    )
    parser.add_argument(
        "--skip-optimize",
        action="store_true",
        help="跳过生成新版本提示词（评估模式）",
    )

    # 模型选择
    parser.add_argument(
        "--provider",
        type=str,
        metavar="NAME",
        help="指定 provider（如 openai、anthropic、google、deepseek）",
    )
    parser.add_argument(
        "--model",
        type=str,
        metavar="NAME",
        help="指定模型名称",
    )

    # 版本创建选项
    parser.add_argument(
        "--to",
        type=int,
        metavar="N",
        help="指定新版本号（与 --create-version 配合使用）",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.ranking:
        # 显示排名
        show_version_ranking()
    elif args.create_version is not None:
        # 创建新版本模式
        create_new_version(args.create_version, args.to)
    elif args.generate:
        # 单篇生成模式（新）
        run_single_generation(
            topic=args.generate,
            structure_type=args.structure,
            provider=args.provider,
            model_name=args.model,
            custom_title=args.title,
            custom_structure=args.custom_structure,
            output_file=args.output,
        )
    elif args.batch:
        # 批量生成模式（新）
        run_batch_generation(
            topics=args.batch,
            structure_types=args.structures,
            provider=args.provider,
            model_name=args.model,
            output_dir=args.batch_output,
        )
    elif args.evaluate:
        # 评估模式（向后兼容）
        run_evaluation(base_version=args.from_version, skip_optimize=args.skip_optimize)
    else:
        # 默认：单篇生成示例
        parser.print_help()
        print("\n提示：使用 --generate 或 --batch 开始生成文章，或使用 --evaluate 运行评估")

