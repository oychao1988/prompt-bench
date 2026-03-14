import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import textwrap
import time
import requests

from openai import OpenAI


BASE_DIR = Path(__file__).parent
MODELS_FILE = BASE_DIR / "models.json"
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
EVALUATIONS_HISTORY_FILE = BASE_DIR / "evaluations_history.json"



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




def load_prompt(prompt_path: Path) -> str:
    """保留向后兼容：加载旧版完整提示词"""
    return prompt_path.read_text(encoding="utf-8")


# ====== 2. 统一的模型调用函数（兼容你提供的所有 model name）======


def call_llm(
    client: OpenAI,
    model_name: str,
    prompt: str,
    topic: str = None,
    keywords: List[str] = None,
    max_tokens: int = None,
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

    # 构建 API 参数
    api_params = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "temperature": 0.8,
    }
    if max_tokens is not None:
        api_params["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**api_params)

    # 验证响应格式
    if not hasattr(resp, 'choices'):
        raise RuntimeError(f"API 返回格式异常，期望带有 choices 属性的对象，实际收到: {type(resp)}")

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


# ====== 2.5. AI检测模块 ======


class AIDetector:
    """AI检测器基类，支持多种检测工具"""

    def __init__(self, detector_type: str = "zhuque", config: Optional[Dict[str, Any]] = None):
        """
        初始化AI检测器

        Args:
            detector_type: 检测器类型，支持 "zhuque"(朱雀)、"gptzero"、"copyleaks"、"originality"、"writer"
            config: 检测器配置 {"api_key": "", "endpoint": "", "enabled": True, "weight": 1.0}
        """
        self.detector_type = detector_type
        self.config = config or {}
        self.api_key = self.config.get("api_key", "")
        self.api_endpoint = self.config.get("endpoint", "")
        self.enabled = self.config.get("enabled", True)
        self.weight = self.config.get("weight", 1.0)

    def detect(self, text: str) -> Dict[str, Any]:
        """
        检测文本的AI生成概率

        Args:
            text: 待检测的文本

        Returns:
            包含检测结果的字典：
            {
                "ai_score": 0.85,  # AI生成概率 (0-1)
                "ai_percentage": 85,  # AI百分比 (0-100)
                "human_percentage": 15,  # 人类百分比 (0-100)
                "detector": "zhuque",  # 使用的检测器
                "confidence": "high",  # 置信度
                "enabled": true,  # 是否启用
                "weight": 1.0  # 权重
            }
        """
        if not self.enabled:
            return self._get_disabled_result()

        if self.detector_type == "zhuque":
            return self._detect_zhuque(text)
        elif self.detector_type == "gptzero":
            return self._detect_gptzero(text)
        elif self.detector_type == "copyleaks":
            return self._detect_copyleaks(text)
        elif self.detector_type == "originality":
            return self._detect_originality(text)
        elif self.detector_type == "writer":
            return self._detect_writer(text)
        else:
            # 默认返回模拟结果（用于测试）
            return self._detect_mock(text)

    def _get_disabled_result(self) -> Dict[str, Any]:
        """返回未启用的结果"""
        return {
            "ai_score": 0.0,
            "ai_percentage": 0,
            "human_percentage": 100,
            "detector": self.detector_type,
            "confidence": "disabled",
            "enabled": False,
            "weight": self.weight
        }

    def _detect_zhuque(self, text: str) -> Dict[str, Any]:
        """
        使用朱雀AI检测（腾讯）

        API文档：https://matrix.tencent.com/ai-detect/ai_gen_txt
        """
        try:
            if not self.api_endpoint or not self.api_key:
                print(f"⚠️  朱雀检测API未配置，使用模拟结果")
                return self._detect_mock(text)

            # TODO: 实现朱雀检测API调用
            # response = requests.post(
            #     self.api_endpoint,
            #     headers={"Authorization": f"Bearer {self.api_key}"},
            #     json={"text": text},
            #     timeout=30
            # )
            # result = response.json()
            # return {
            #     "ai_score": result.get("ai_probability", 0.5),
            #     "ai_percentage": round(result.get("ai_probability", 0.5) * 100),
            #     "human_percentage": round((1 - result.get("ai_probability", 0.5)) * 100),
            #     "detector": "zhuque",
            #     "confidence": result.get("confidence", "medium"),
            #     "enabled": self.enabled,
            #     "weight": self.weight
            # }

            return self._detect_mock(text)

        except Exception as e:
            print(f"❌ 朱雀检测失败: {e}")
            return self._detect_mock(text)

    def _detect_gptzero(self, text: str) -> Dict[str, Any]:
        """
        使用GPTZero检测

        API文档：https://api.gptzero.me/v2/predict/text
        """
        try:
            if not self.api_key:
                print(f"⚠️  GPTZero API key未配置，使用模拟结果")
                return self._detect_mock(text)

            # GPTZero API实现
            endpoint = self.api_endpoint or "https://api.gptzero.me/v2/predict/text"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                endpoint,
                headers=headers,
                json={"document": text},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                # GPTZero返回格式
                ai_probability = result.get("average_generated_prob", 0.5)
                return {
                    "ai_score": round(ai_probability, 2),
                    "ai_percentage": round(ai_probability * 100),
                    "human_percentage": round((1 - ai_probability) * 100),
                    "detector": "gptzero",
                    "confidence": "high" if ai_probability > 0.7 or ai_probability < 0.3 else "medium",
                    "enabled": self.enabled,
                    "weight": self.weight
                }
            else:
                print(f"❌ GPTZero API返回错误: {response.status_code}")
                return self._detect_mock(text)

        except Exception as e:
            print(f"❌ GPTZero检测失败: {e}")
            return self._detect_mock(text)

    def _detect_copyleaks(self, text: str) -> Dict[str, Any]:
        """
        使用Copyleaks检测

        API文档：https://api.copyleaks.com
        """
        try:
            if not self.api_key:
                print(f"⚠️  Copyleaks API key未配置，使用模拟结果")
                return self._detect_mock(text)

            # Copyleaks API实现
            endpoint = self.api_endpoint or "https://api.copyleaks.com/text/v4/ai-detection"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                endpoint,
                headers=headers,
                json={"text": text},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                # Copyleaks返回格式
                ai_score = result.get("averageAiScore", 0.5)
                return {
                    "ai_score": round(ai_score, 2),
                    "ai_percentage": round(ai_score * 100),
                    "human_percentage": round((1 - ai_score) * 100),
                    "detector": "copyleaks",
                    "confidence": "high",
                    "enabled": self.enabled,
                    "weight": self.weight
                }
            else:
                print(f"❌ Copyleaks API返回错误: {response.status_code}")
                return self._detect_mock(text)

        except Exception as e:
            print(f"❌ Copyleaks检测失败: {e}")
            return self._detect_mock(text)

    def _detect_originality(self, text: str) -> Dict[str, Any]:
        """使用Originality.ai检测"""
        try:
            if not self.api_key:
                print(f"⚠️  Originality.ai API key未配置，使用模拟结果")
                return self._detect_mock(text)

            # Originality.ai API实现
            # TODO: 根据官方文档实现
            return self._detect_mock(text)

        except Exception as e:
            print(f"❌ Originality.ai检测失败: {e}")
            return self._detect_mock(text)

    def _detect_writer(self, text: str) -> Dict[str, Any]:
        """使用Writer.com检测"""
        try:
            if not self.api_key:
                print(f"⚠️  Writer.com API key未配置，使用模拟结果")
                return self._detect_mock(text)

            # Writer.com API实现
            # TODO: 根据官方文档实现
            return self._detect_mock(text)

        except Exception as e:
            print(f"❌ Writer.com检测失败: {e}")
            return self._detect_mock(text)

    def _detect_mock(self, text: str) -> Dict[str, Any]:
        """
        模拟AI检测（用于测试）

        基于文本特征简单判断：
        - 段落过于整齐
        - 句子长度过于平均
        - 缺少口语化表达
        """
        # 简单启发式规则
        paragraphs = [p for p in text.split("\n") if p.strip()]
        para_lengths = [len(p) for p in paragraphs]

        # 计算段落长度的标准差（越小说明越整齐）
        if len(para_lengths) > 1:
            avg_length = sum(para_lengths) / len(para_lengths)
            variance = sum((x - avg_length) ** 2 for x in para_lengths) / len(para_lengths)
            std_dev = variance ** 0.5
            # 标准差越小，AI概率越高
            uniformity_score = max(0, min(1, 1 - std_dev / 100))
        else:
            uniformity_score = 0.5

        # 简单的关键词检测
        ai_keywords = ["首先", "其次", "最后", "总之", "综上所述", "值得注意的是"]
        keyword_count = sum(1 for kw in ai_keywords if kw in text)
        keyword_score = min(1, keyword_count / 3)

        # 综合评分
        ai_score = 0.3 + (uniformity_score * 0.4) + (keyword_score * 0.3)
        ai_score = round(min(0.99, max(0.01, ai_score)), 2)

        return {
            "ai_score": ai_score,
            "ai_percentage": round(ai_score * 100),
            "human_percentage": round((1 - ai_score) * 100),
            "detector": f"{self.detector_type}(mock)",
            "confidence": "medium",
            "enabled": self.enabled,
            "weight": self.weight
        }


class MultiAIDetector:
    """多AI检测器管理类，支持同时使用多个检测平台"""

    def __init__(self):
        """初始化多检测器，从环境变量读取配置"""
        self.detectors = self._load_detectors_from_env()

    def _load_detectors_from_env(self) -> List[AIDetector]:
        """从环境变量加载检测器配置"""
        detectors = []

        # 检测器配置映射
        detector_configs = {
            "zhuque": {
                "type": "zhuque",
                "enabled_env": "ZHUQUE_DETECTOR_ENABLED",
                "key_env": "ZHUQUE_API_KEY",
                "endpoint_env": "ZHUQUE_ENDPOINT",
                "weight_env": "ZHUQUE_WEIGHT"
            },
            "gptzero": {
                "type": "gptzero",
                "enabled_env": "GPTZERO_DETECTOR_ENABLED",
                "key_env": "GPTZERO_API_KEY",
                "endpoint_env": "GPTZERO_ENDPOINT",
                "weight_env": "GPTZERO_WEIGHT"
            },
            "copyleaks": {
                "type": "copyleaks",
                "enabled_env": "COPYLEAKS_DETECTOR_ENABLED",
                "key_env": "COPYLEAKS_API_KEY",
                "endpoint_env": "COPYLEAKS_ENDPOINT",
                "weight_env": "COPYLEAKS_WEIGHT"
            },
            "originality": {
                "type": "originality",
                "enabled_env": "ORIGINALITY_DETECTOR_ENABLED",
                "key_env": "ORIGINALITY_API_KEY",
                "endpoint_env": "ORIGINALITY_ENDPOINT",
                "weight_env": "ORIGINALITY_WEIGHT"
            },
            "writer": {
                "type": "writer",
                "enabled_env": "WRITER_DETECTOR_ENABLED",
                "key_env": "WRITER_API_KEY",
                "endpoint_env": "WRITER_ENDPOINT",
                "weight_env": "WRITER_WEIGHT"
            }
        }

        for name, config in detector_configs.items():
            # 检查是否启用
            enabled = os.getenv(config["enabled_env"], "false").lower() in ("true", "1", "yes")

            if not enabled:
                continue

            # 读取配置
            detector_config = {
                "api_key": os.getenv(config["key_env"], ""),
                "endpoint": os.getenv(config["endpoint_env"], ""),
                "enabled": True,
                "weight": float(os.getenv(config["weight_env"], "1.0"))
            }

            detectors.append(AIDetector(config["type"], detector_config))

        return detectors

    def detect(self, text: str) -> Dict[str, Any]:
        """
        使用所有启用的检测器进行检测，并综合计算结果

        Args:
            text: 待检测的文本

        Returns:
            综合检测结果：
            {
                "ai_score": 0.75,  # 加权平均AI分数
                "ai_percentage": 75,  # AI百分比
                "human_percentage": 25,  # 人类百分比
                "detector_results": [...],  # 各检测器的详细结果
                "detector_count": 3,  # 使用的检测器数量
                "confidence": "high"  # 综合置信度
            }
        """
        if not self.detectors:
            print("⚠️  未启用任何AI检测器，使用模拟检测")
            mock_detector = AIDetector("mock", {"enabled": True, "weight": 1.0})
            result = mock_detector.detect(text)
            return {
                "ai_score": result["ai_score"],
                "ai_percentage": result["ai_percentage"],
                "human_percentage": result["human_percentage"],
                "detector_results": [result],
                "detector_count": 1,
                "confidence": result["confidence"]
            }

        # 调用所有检测器
        detector_results = []
        for detector in self.detectors:
            print(f"  📊 使用 {detector.detector_type} 检测...")
            result = detector.detect(text)
            detector_results.append(result)

        # 计算加权平均
        total_weight = sum(r["weight"] for r in detector_results if r.get("enabled", True))
        if total_weight == 0:
            total_weight = 1

        weighted_ai_score = sum(
            r["ai_score"] * r["weight"]
            for r in detector_results
            if r.get("enabled", True)
        ) / total_weight

        # 计算综合置信度
        enabled_results = [r for r in detector_results if r.get("enabled", True)]
        if len(enabled_results) >= 3:
            confidence = "high"
        elif len(enabled_results) >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "ai_score": round(weighted_ai_score, 2),
            "ai_percentage": round(weighted_ai_score * 100),
            "human_percentage": round((1 - weighted_ai_score) * 100),
            "detector_results": detector_results,
            "detector_count": len(enabled_results),
            "confidence": confidence
        }

    def get_enabled_detectors(self) -> List[str]:
        """获取已启用的检测器列表"""
        return [d.detector_type for d in self.detectors if d.enabled]


def calculate_ai_detection_score(ai_percentage: float) -> float:
    """
    根据AI检测率计算得分（直接映射法）

    评分规则（4分制）：
    - 得分 = (1 - AI率) × 4
    - 保留2位小数

    示例：
    - AI率 0% → 人类率 100% → 得分 4.00
    - AI率 30% → 人类率 70% → 得分 2.80
    - AI率 50% → 人类率 50% → 得分 2.00
    - AI率 100% → 人类率 0% → 得分 0.00

    Args:
        ai_percentage: AI检测百分比 (0-100)

    Returns:
        检测得分 (0-4分，保留2位小数)
    """
    # 计算人类率并映射到4分制
    human_percentage = 1 - (ai_percentage / 100)
    score = human_percentage * 4
    return round(score, 2)


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
    规则评估函数：基于"规则+统计"型评分，简单、无成本，评估结构是否对齐。

    评分体系（规则总分 3 分）- 2026.3.14 调整：
    - in_length_range: 1.0分 - 字数是否在提示词要求范围内
    - para_count_reasonable: 0.7分 - 段落数是否合理（5-20段）
    - avg_para_length_ok: 0.3分 - 平均段落长度是否合理（30-150字）
    - has_3_points: 0.6分 - 中间是否有≥3个观点段落（结构完整性）
    - has_headings: 0.4分 - 是否有小标题结构（格式规范性）

    注意：开头质量、经典引用、内容深度、文笔、情感等维度由 AI 评估函数处理。
    AI检测得分由独立的检测模块处理。

    Args:
        text: 待评估的文章文本
        length_range: 字数范围 (min, max)，None 则使用默认值 (400, 1500)

    Returns:
        包含规则评估结果的字典，rule_score 为规则得分（0-3分）
    """
    if length_range is None:
        length_range = (400, 1500)

    min_length, max_length = length_range

    # 基础统计
    chars = len(text)
    paragraphs = [p for p in text.split("\n") if p.strip()]
    para_count = len(paragraphs)

    # 1. 段落数是否合理（避免过度碎片化或过于冗长）
    para_count_reasonable = 5 <= para_count <= 20

    # 2. 平均段落长度是否合理（避免碎片化）
    avg_para_length = chars / para_count if para_count > 0 else 0
    avg_para_length_ok = 30 <= avg_para_length <= 150

    # 3. 结构检测（中间是否有 3 个明显分段）
    middle_para_count = max(0, para_count - 2)
    has_3_points = middle_para_count >= 3

    # 4. 是否有小标题结构（改进版）
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

    # 5. 字数是否在指定范围内
    in_length_range = min_length <= chars <= max_length

    # 计算规则得分
    rule_score = 0.0
    weights = {
        "in_length_range": 1.0,
        "para_count_reasonable": 0.7,
        "avg_para_length_ok": 0.3,
        "has_3_points": 0.6,
        "has_headings": 0.4,
    }

    rule_evaluations = {
        "in_length_range": in_length_range,
        "para_count_reasonable": para_count_reasonable,
        "avg_para_length_ok": avg_para_length_ok,
        "has_3_points": has_3_points,
        "has_headings": has_headings,
    }

    for k, w in weights.items():
        if rule_evaluations[k]:
            rule_score += w

    # 返回规则评估结果
    details = {
        "rule_score": round(rule_score, 2),  # 规则评估得分（0-3）
        "ai_score": None,                    # AI评估得分（待填充，0-3）
        "detection_score": None,             # AI检测得分（待填充，0-4）
        "total_score": None,                 # 总分（待计算，0-10）
        **rule_evaluations,                  # 各维度评估结果
        "chars": chars,
        "paragraphs": para_count,
        "avg_para_length": round(avg_para_length, 1),
        "length_range": f"{min_length}-{max_length}",
    }

    return details


def evaluate_article_via_ai(text: str, prompt: str) -> Dict[str, Any]:
    """
    使用AI模型对文本进行语义层面的评估。

    评估维度（AI总分 3 分）- 2026.3.14 调整：
    - intro_quality: 0.6分 - 开头是否直接入题，有吸引力，符合人设
    - classic_naturalness: 0.6分 - 经典引用是否自然恰当，与观点紧密相关
    - content_depth: 0.6分 - 内容是否有深度，观点是否有启发性
    - writing_fluency: 0.6分 - 文笔是否流畅自然，语言是否有节奏感
    - emotional_resonance: 0.6分 - 是否能引发情感共鸣，是否打动人心（含AI痕迹检测）

    注意：AI检测由独立的检测模块处理，不再包含在语义评估中。

    Args:
        text: 待评估的文章文本
        prompt: 原始提示词（作为评估参考）

    Returns:
        包含AI评估结果的字典，ai_score 为AI评估总分（0-3分）
    """
    import json
    import os

    # 获取评估模型配置
    meta_model = os.getenv("EVALUATION_MODEL") or "gpt-5.4"
    meta_provider = os.getenv("EVALUATION_PROVIDER") or "openai"

    meta_client = get_client(meta_provider)
    if meta_client is None:
        # 如果无法获取客户端，返回默认评估结果
        return {
            "ai_score": 0,
            "ai_details": {},
            "error": f"无法获取 {meta_provider} 客户端，请检查 .env 配置"
        }

    # 构造评估提示词
    system_msg = (
        "你是一位专业的文本质量评估专家，擅长评估中文文章的内容质量、文笔水平和情感表达。"
        "你的任务是根据原始提示词的要求，对生成的文章进行客观、准确的评估。"
    )

    user_msg = textwrap.dedent(f"""
        请根据以下原始提示词的要求，对文章进行评估。

        原始提示词要求：
        --- 提示词开始 ---
        {prompt.strip()}
        --- 提示词结束 ---

        待评估文章：
        --- 文章开始 ---
        {text.strip()}
        --- 文章结束 ---

        请从以下5个维度进行评估，每个维度给出评分和理由：

        1. 开头质量（0.6分）：
           - 评分标准：开头是否直接入题，有吸引力，符合人设
           - 0分：开头拖沓，没有吸引力，不符合人设
           - 0.3分：开头尚可，但吸引力不足或人设不够明显
           - 0.6分：开头直接入题，有吸引力，符合人设

        2. 经典引用恰当性（0.6分）：
           - 评分标准：经典引用是否自然恰当，与观点紧密相关
           - 0分：没有引用或引用生硬、不相关
           - 0.3分：有引用但不够自然或相关性一般
           - 0.6分：引用自然恰当，与观点紧密相关

        3. 内容深度与思想性（0.6分）：
           - 评分标准：内容是否有深度，观点是否有启发性，避免空洞
           - 0分：内容空洞，观点老套，没有启发性
           - 0.3分：内容有一定深度，但观点不够深入
           - 0.6分：内容有深度，观点有启发性，能引发思考

        4. 文笔流畅度与可读性（0.6分）：
           - 评分标准：文笔是否流畅自然，语言是否有节奏感
           - 0分：文笔生硬，语言不流畅
           - 0.3分：文笔尚可，但流畅度不足
           - 0.6分：文笔流畅自然，语言有节奏感

        5. 情感共鸣（0.6分）：
           - 评分标准：是否能引发情感共鸣，是否打动人心
           - 0分：情感平淡，无法引发共鸣
           - 0.3分：有一定情感，但共鸣不足
           - 0.6分：能引发情感共鸣，打动人心

        请严格按照以下JSON格式返回评估结果：
        {{
          "intro_quality": {{"score": 1.0, "reason": "理由说明"}},
          "classic_naturalness": {{"score": 0.5, "reason": "理由说明"}},
          "content_depth": {{"score": 1.0, "reason": "理由说明"}},
          "writing_fluency": {{"score": 1.0, "reason": "理由说明"}},
          "emotional_resonance": {{"score": 0.5, "reason": "理由说明"}}
        }}

        注意：
        - 只返回JSON，不要包含任何其他文字说明
        - 每个维度的评分必须在规定范围内（0-1分），系统会自动转换为0-0.6分制
        - 理由说明要简明扼要，指出优点或不足
        """)

    try:
        # 调用AI模型进行评估
        resp = meta_client.chat.completions.create(
            model=meta_model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,  # 使用较低的temperature以提高稳定性
        )

        content = resp.choices[0].message.content or ""

        # 解析JSON结果
        # 尝试提取JSON部分（处理可能包含的额外文字）
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            ai_result = json.loads(json_str)

            # 计算AI评估总分（AI返回的是1分制，需要转换为0.6分制）
            # 总分从5分改为3分，所以每个维度从1分改为0.6分
            scale_factor = 0.6  # 1分制 → 0.6分制的转换系数
            ai_score = (
                ai_result.get("intro_quality", {}).get("score", 0) +
                ai_result.get("classic_naturalness", {}).get("score", 0) +
                ai_result.get("content_depth", {}).get("score", 0) +
                ai_result.get("writing_fluency", {}).get("score", 0) +
                ai_result.get("emotional_resonance", {}).get("score", 0)
            ) * scale_factor

            return {
                "ai_score": round(ai_score, 2),
                "ai_details": ai_result,
            }
        else:
            return {
                "ai_score": 0,
                "ai_details": {},
                "error": "AI返回结果无法解析为JSON"
            }

    except Exception as e:
        return {
            "ai_score": 0,
            "ai_details": {},
            "error": f"AI评估失败: {str(e)}"
        }


# ====== 4. 基于多模型结果，自动生成"提示词优化建议" ======


def summarize_evaluations(results: List[Dict[str, Any]], length_range: Optional[Tuple[int, int]] = None) -> str:
    """
    基于多模型输出的共性表现，生成针对性的优化建议。

    结合规则评估（结构、格式）和AI评估（内容、文笔、情感）的结果，
    给出全面的提示词优化建议。
    """
    if not results:
        return "暂无结果，无法给出优化建议。"

    lines = []
    lines.append("优化建议（基于多模型输出的共性表现）：")
    lines.append("")  # 空行分隔

    # ====== AI评估维度建议 ======
    ai_suggestions = []

    # 注意：AI评估现在使用0.6分制（从1分制转换），所以阈值需要相应调整
    # 1分制的0.6分 → 0.6分制的0.36分，约为0.4分

    # 1. 开头质量
    intro_bad = sum(1 for r in results if r["evaluation"].get("ai_details", {}).get("intro_quality", {}).get("score", 1) < 0.6)
    if intro_bad > 0:
        ai_suggestions.append(f"- 开头质量（{intro_bad}个模型不佳）：首段必须在2-3句内直接切入主题，用具体场景（如清晨河边散步、夜里等女儿电话）而非抽象陈述。明确点出「人过六十/老了才明白/老了才发现」等主题之一。")

    # 2. 经典引用恰当性
    classic_unnatural = sum(1 for r in results if r["evaluation"].get("ai_details", {}).get("classic_naturalness", {}).get("score", 1) < 0.6)
    if classic_unnatural > 0:
        ai_suggestions.append(f"- 经典引用（{classic_unnatural}个模型不自然）：引用经典时要像老教师随口而出的感慨，避免生硬堆砌。引用后要立即关联到观点，比如「古人说XXX，我想起来年轻时候...」。不要用「某某曾说过」的讲课腔。")

    # 3. 内容深度与思想性
    content_shallow = sum(1 for r in results if r["evaluation"].get("ai_details", {}).get("content_depth", {}).get("score", 1) < 0.6)
    if content_shallow > 0:
        ai_suggestions.append(f"- 内容深度（{content_shallow}个模型不足）：每个观点都要有具体的故事或细节支撑，避免空泛的道理说教。要写出个人独特体验，比如具体的一件事、一个场景、一个细节，而不是泛泛而谈。")

    # 4. 文笔流畅度与可读性
    writing_choppy = sum(1 for r in results if r["evaluation"].get("ai_details", {}).get("writing_fluency", {}).get("score", 1) < 0.6)
    if writing_choppy > 0:
        ai_suggestions.append(f"- 文笔流畅度（{writing_choppy}个模型不佳）：多使用短句和口语化表达，关键处可拉长形成散文式缓慢长句。语言要有节奏感，像老教师在老屋藤椅上聊天，不要用书面语和工整的排比句。")

    # 5. 情感共鸣
    low_emotion = sum(1 for r in results if r["evaluation"].get("ai_details", {}).get("emotional_resonance", {}).get("score", 1) < 0.6)
    if low_emotion > 0:
        ai_suggestions.append(f"- 情感共鸣（{low_emotion}个模型不足）：写出真实的生活细节和内心感受，用克制而温暖的基调。像对同龄朋友慢慢说话，不要端着、不要煽情、不要讲大道理。适当带点自嘲和温柔幽默。")

    # 6. AI痕迹
    ai_like = sum(1 for r in results if r["evaluation"].get("ai_details", {}).get("human_like", {}).get("score", 0.5) < 0.3)
    if ai_like > 0:
        ai_suggestions.append(f"- AI痕迹（{ai_like}个模型较重）：避免使用过于工整的排比、比喻等修辞手法，不要使用「首先...其次...最后...」「总之」「因此」等AI常用词。语言要朴素、真诚、有人味儿。")

    # ====== 规则评估维度建议 ======
    rule_suggestions = []

    # 1. 字数要求
    wrong_length = sum(1 for r in results if not r["evaluation"].get("in_length_range", True))
    if wrong_length > 0:
        if length_range:
            rule_suggestions.append(f"- 字数控制（{wrong_length}个模型不符合）：明确要求文章总字数控制在 {length_range[0]}-{length_range[1]} 字之间，避免过长或过短。")

    # 2. 段落数量
    para_count_bad = sum(1 for r in results if not r["evaluation"].get("para_count_reasonable", True))
    if para_count_bad > 0:
        rule_suggestions.append(f"- 段落数量（{para_count_bad}个模型不合理）：文章段落数建议控制在 5-20 段之间，避免过度碎片化（每段1-2句）或过于冗长（整段不分）。")

    # 3. 段落长度
    avg_para_length_bad = sum(1 for r in results if not r["evaluation"].get("avg_para_length_ok", True))
    if avg_para_length_bad > 0:
        rule_suggestions.append(f"- 段落长度（{avg_para_length_bad}个模型不合理）：每段平均长度建议在 30-150 字之间，避免过度碎片化或段落过长。")

    # 4. 结构完整性
    not_3_points = sum(1 for r in results if not r["evaluation"].get("has_3_points", True))
    if not_3_points > 0:
        rule_suggestions.append(f"- 结构完整性（{not_3_points}个模型不符合）：中间必须拆成 3 个观点段落（和自己相处、和家人相处、和世界相处），每个观点 2-3 句，并用空行分隔。")

    # 5. 小标题结构
    no_headings = sum(1 for r in results if not r["evaluation"].get("has_headings", True))
    if no_headings > 0:
        rule_suggestions.append(f"- 小标题结构（{no_headings}个模型缺失）：建议添加小标题结构，使用「一、」「二、」「三、」或「1.」「2.」「3.」「其一、」「其二、」等形式标注观点段落。")

    # ====== 输出建议 ======
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


def optimize_prompt_via_llm(
    original_prompt: str, eval_summary: str, new_version: int
) -> str:
    """
    使用一个指定模型，基于原始提示词和本次评估总结，自动生成"下一版"完整提示词。
    这样就不依赖硬编码的模板，而是走真正的"内容驱动优化"流程。
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
        1. 新提示词开头显式注明"提示词版本：v{new_version}"。
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

    基于新的混合评分体系（规则+AI+检测），计算各维度的平均值。
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
    rule_scores = [e["evaluation"].get("rule_score", 0) for e in evaluations]
    ai_scores = [e["evaluation"].get("ai_score", 0) for e in evaluations]
    detection_scores = [e["evaluation"].get("detection_score", 0) for e in evaluations]
    total_scores = [e["evaluation"].get("total_score", 0) for e in evaluations]

    # 找出最佳模型
    max_total_score = max(total_scores)
    min_total_score = min(total_scores)
    best_model = next(
        (e["model"] for e in evaluations if e["evaluation"].get("total_score", 0) == max_total_score),
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

    显示每个版本的总分、规则分、AI分、最高分、模型数和时间。
    """
    history = load_evaluations_history()
    if not history:
        print("暂无评估历史记录。")
        return

    # 按平均总分排序
    versions = []
    for ver, data in history.items():
        summary = data["summary"]
        versions.append(
            (
                ver,
                summary.get("avg_total_score", 0),
                summary.get("avg_rule_score", 0),
                summary.get("avg_ai_score", 0),
                summary.get("max_total_score", 0),
                summary.get("model_count", 0),
                data["timestamp"],
            )
        )

    versions.sort(key=lambda x: x[1], reverse=True)

    print(f"\n{'版本':<8} {'总分':<8} {'规则分':<8} {'AI分':<8} {'最高分':<8} {'模型数':<8} {'时间'}")
    print("-" * 90)
    for ver, total, rule, ai, max_score, count, timestamp in versions[:limit]:
        # 只显示日期部分
        date = timestamp.split("T")[0]
        print(f"{ver:<8} {total:<8.2f} {rule:<8.2f} {ai:<8.2f} {max_score:<8} {count:<8} {date}")

    # 找出历史最佳版本
    if versions:
        best_ver, best_total, best_rule, best_ai, best_max, _, _ = versions[0]
        print(f"\n历史最佳版本: {best_ver}（总分: {best_total:.2f}，规则分: {best_rule:.2f}，AI分: {best_ai:.2f}，最高分: {best_max}）")


def compare_with_best(version: int) -> None:
    """
    将当前版本与历史最佳版本进行对比。

    对比总分、规则分、AI分三个维度。
    """
    history = load_evaluations_history()
    if not history or len(history) < 2:
        return

    # 找出历史最佳版本（排除当前版本）
    best_ver = None
    best_total = -1
    for ver, data in history.items():
        if ver != f"v{version}":
            total = data["summary"].get("avg_total_score", 0)
            if total > best_total:
                best_total = total
                best_ver = ver

    if best_ver is None:
        return

    current_key = f"v{version}"
    if current_key not in history:
        return

    current_summary = history[current_key]["summary"]
    best_summary = history[best_ver]["summary"]

    current_total = current_summary.get("avg_total_score", 0)
    current_rule = current_summary.get("avg_rule_score", 0)
    current_ai = current_summary.get("avg_ai_score", 0)

    best_total_val = best_summary.get("avg_total_score", 0)
    best_rule = best_summary.get("avg_rule_score", 0)
    best_ai = best_summary.get("avg_ai_score", 0)

    diff = current_total - best_total_val

    print(f"\n版本对比: v{version} vs {best_ver}")
    print(f"  当前版本 - 总分: {current_total:.2f}, 规则分: {current_rule:.2f}, AI分: {current_ai:.2f}")
    print(f"  历史最佳 - 总分: {best_total_val:.2f}, 规则分: {best_rule:.2f}, AI分: {best_ai:.2f}")
    if diff > 0:
        print(f"  总分差异: +{diff:.2f} (当前版本更好)")
    elif diff < 0:
        print(f"  总分差异: {diff:.2f} (历史版本更好)")
    else:
        print(f"  总分差异: 0 (持平)")


def compare_models(version: Optional[int] = None) -> None:
    """
    横向对比：展示同一提示词版本下不同模型的表现。

    Args:
        version: 提示词版本号，None 表示使用最新版本
    """
    # 确定版本
    if version is None:
        _, version = get_latest_prompt_file()

    eval_file = OUTPUT_DIR / f"v{version}" / "evaluations.json"
    if not eval_file.exists():
        print(f"错误：未找到版本 v{version} 的评估结果文件")
        return

    with eval_file.open("r", encoding="utf-8") as f:
        results = json.load(f)

    if not results:
        print(f"版本 v{version} 没有评估结果")
        return

    # 按总分排序
    results_sorted = sorted(results, key=lambda x: x["evaluation"]["total_score"], reverse=True)

    print(f"\n{'='*100}")
    print(f"横向对比：提示词版本 v{version} - 各模型表现对比")
    print(f"{'='*100}")

    # 表格头部
    print(f"\n{'排名':<6} {'模型':<35} {'总分':<10} {'规则分':<10} {'AI分':<10} {'字数':<10} {'段落数':<10}")
    print("-" * 100)

    # 表格内容
    for idx, result in enumerate(results_sorted, 1):
        model_name = f"{result['provider']}/{result['model']}"
        eval_data = result["evaluation"]

        total_score = eval_data.get("total_score", 0)
        rule_score = eval_data.get("rule_score", 0)
        ai_score = eval_data.get("ai_score", 0)
        chars = eval_data.get("chars", 0)
        paragraphs = eval_data.get("paragraphs", 0)

        # 标记最佳表现
        rank_marker = f"{idx}."
        if idx == 1:
            rank_marker = "🥇"
        elif idx == 2:
            rank_marker = "🥈"
        elif idx == 3:
            rank_marker = "🥉"

        print(f"{rank_marker:<6} {model_name:<35} {total_score:<10.2f} {rule_score:<10.2f} {ai_score:<10.2f} {chars:<10} {paragraphs:<10}")

    # 统计摘要
    print("\n" + "=" * 100)
    print("统计摘要:")
    avg_total = sum(r["evaluation"]["total_score"] for r in results) / len(results)
    avg_rule = sum(r["evaluation"]["rule_score"] for r in results) / len(results)
    avg_ai = sum(r["evaluation"]["ai_score"] for r in results) / len(results)
    max_score = max(r["evaluation"]["total_score"] for r in results)
    min_score = min(r["evaluation"]["total_score"] for r in results)

    print(f"  平均总分: {avg_total:.2f}/10")
    print(f"  平均规则分: {avg_rule:.2f}/5")
    print(f"  平均AI分: {avg_ai:.2f}/5")
    print(f"  最高分: {max_score:.2f}/10")
    print(f"  最低分: {min_score:.2f}/10")
    print(f"  极差: {max_score - min_score:.2f}")
    print("=" * 100)


def compare_versions(model_filter: Optional[str] = None, limit: int = 10) -> None:
    """
    纵向对比：展示不同提示词版本在同一模型（或平均）下的表现。

    Args:
        model_filter: 模型名称过滤（如 "deepseek-v3.1"），None 表示对比所有模型的平均表现
        limit: 显示的版本数量限制
    """
    history = load_evaluations_history()
    if not history:
        print("暂无评估历史记录")
        return

    # 按版本号排序
    versions = sorted(history.keys(), key=lambda x: int(x.replace("v", "")) if x.replace("v", "").isdigit() else 0)

    print(f"\n{'='*120}")
    if model_filter:
        print(f"纵向对比：模型 '{model_filter}' 在不同提示词版本下的表现")
    else:
        print(f"纵向对比：各提示词版本的平均表现（所有模型）")
    print(f"{'='*120}")

    # 收集数据
    version_data = []
    for ver in versions[:limit]:
        summary = history[ver]["summary"]
        evaluations = history[ver].get("evaluations", [])

        if model_filter:
            # 找到指定模型的数据
            model_eval = next((e for e in evaluations if e["model"] == model_filter), None)
            if model_eval:
                version_data.append({
                    "version": ver,
                    "total_score": model_eval["evaluation"]["total_score"],
                    "rule_score": model_eval["evaluation"]["rule_score"],
                    "ai_score": model_eval["evaluation"]["ai_score"],
                    "model_count": 1,
                })
        else:
            # 使用平均数据
            if summary.get("avg_total_score") is not None:
                version_data.append({
                    "version": ver,
                    "total_score": summary["avg_total_score"],
                    "rule_score": summary["avg_rule_score"],
                    "ai_score": summary["avg_ai_score"],
                    "model_count": summary["model_count"],
                })

    if not version_data:
        print(f"未找到相关数据（模型过滤: {model_filter}）")
        return

    # 表格头部
    print(f"\n{'版本':<8} {'总分':<10} {'规则分':<10} {'AI分':<10} {'模型数':<10} {'时间'}")
    print("-" * 120)

    # 表格内容
    for data in version_data:
        ver = data["version"]
        total = data["total_score"]
        rule = data["rule_score"]
        ai = data["ai_score"]
        count = data["model_count"]
        timestamp = history[ver]["timestamp"].split("T")[0]

        print(f"{ver:<8} {total:<10.2f} {rule:<10.2f} {ai:<10.2f} {count:<10} {timestamp}")

    # 趋势分析
    if len(version_data) >= 2:
        print("\n" + "=" * 120)
        print("趋势分析:")
        first = version_data[0]
        last = version_data[-1]

        total_change = last["total_score"] - first["total_score"]
        rule_change = last["rule_score"] - first["rule_score"]
        ai_change = last["ai_score"] - first["ai_score"]

        print(f"  从 {first['version']} 到 {last['version']}:")
        print(f"    总分变化: {total_change:+.2f}")
        print(f"    规则分变化: {rule_change:+.2f}")
        print(f"    AI分变化: {ai_change:+.2f}")

        if total_change > 0:
            print(f"    结论: 提示词整体表现提升 ✅")
        elif total_change < 0:
            print(f"    结论: 提示词整体表现下降 ⚠️")
        else:
            print(f"    结论: 提示词整体表现持平 ➡️")

    print("=" * 120)


def show_evaluation_details(version: int, model: Optional[str] = None) -> None:
    """
    显示详细的评估结果，包括AI评估理由和规则评估详情。

    Args:
        version: 提示词版本号
        model: 模型名称（如 "deepseek-v3.1"），None 表示显示该版本所有模型的摘要
    """
    eval_file = OUTPUT_DIR / f"v{version}" / "evaluations.json"
    if not eval_file.exists():
        print(f"错误：未找到版本 v{version} 的评估结果文件")
        return

    with eval_file.open("r", encoding="utf-8") as f:
        results = json.load(f)

    if not results:
        print(f"版本 v{version} 没有评估结果")
        return

    if model:
        # 显示特定模型的详细信息
        result = next((r for r in results if r["model"] == model), None)
        if not result:
            print(f"未找到模型 '{model}' 在版本 v{version} 中的评估结果")
            return

        print(f"\n{'='*120}")
        print(f"详细评估结果：v{version} - {result['provider']}/{result['model']}")
        print(f"{'='*120}")

        eval_data = result["evaluation"]

        # 总体评分
        print(f"\n【总体评分】")
        print(f"  总分: {eval_data.get('total_score', 0):.2f}/10")
        print(f"  规则分: {eval_data.get('rule_score', 0):.2f}/5")
        print(f"  AI分: {eval_data.get('ai_score', 0):.2f}/5")

        # 规则评估详情
        print(f"\n【规则评估详情】")
        print(f"  字数: {eval_data.get('chars', 0)} 字（要求范围: {eval_data.get('length_range', 'N/A')}）")
        print(f"  字数达标: {'✅' if eval_data.get('in_length_range') else '❌'}")
        print(f"  段落数: {eval_data.get('paragraphs', 0)} 段")
        print(f"  段落数合理: {'✅' if eval_data.get('para_count_reasonable') else '❌'}")
        print(f"  平均段落长度: {eval_data.get('avg_para_length', 0):.1f} 字")
        print(f"  段落长度合理: {'✅' if eval_data.get('avg_para_length_ok') else '❌'}")
        print(f"  结构完整性（≥3个观点段落）: {'✅' if eval_data.get('has_3_points') else '❌'}")
        print(f"  小标题结构: {'✅' if eval_data.get('has_headings') else '❌'}")

        # AI评估详情
        print(f"\n【AI评估详情】")
        ai_details = eval_data.get("ai_details", {})
        if ai_details:
            for dim, data in ai_details.items():
                dim_names = {
                    "intro_quality": "开头质量",
                    "classic_naturalness": "经典引用恰当性",
                    "content_depth": "内容深度与思想性",
                    "writing_fluency": "文笔流畅度与可读性",
                    "emotional_resonance": "情感共鸣",
                    "human_like": "AI痕迹（人味儿）",
                }
                dim_name = dim_names.get(dim, dim)
                score = data.get("score", 0)
                reason = data.get("reason", "无理由")

                # 评分可视化
                if score >= 1.0:
                    status = "✅ 优秀"
                elif score >= 0.6:
                    status = "🟡 良好"
                elif score >= 0.3:
                    status = "🟠 及格"
                else:
                    status = "🔴 需改进"

                print(f"\n  {dim_name}（{score}/1.0 或 1.5）{status}")
                print(f"    理由: {reason}")
        else:
            print("  无AI评估详情")

        print(f"\n{'='*120}")

    else:
        # 显示该版本所有模型的摘要
        print(f"\n{'='*120}")
        print(f"版本 v{version} - 所有模型评估摘要")
        print(f"{'='*120}")

        for result in results:
            eval_data = result["evaluation"]
            print(f"\n【{result['provider']}/{result['model']}】")
            print(f"  总分: {eval_data.get('total_score', 0):.2f}/10 (规则: {eval_data.get('rule_score', 0):.2f}/5, AI: {eval_data.get('ai_score', 0):.2f}/5)")
            print(f"  字数: {eval_data.get('chars', 0)} 字, 段落数: {eval_data.get('paragraphs', 0)}")

            # 显示主要问题
            issues = []
            if not eval_data.get('in_length_range'):
                issues.append("字数不符合要求")
            if not eval_data.get('has_headings'):
                issues.append("缺少小标题结构")

            ai_details = eval_data.get('ai_details', {})
            if ai_details:
                low_score_dims = [
                    dim for dim, data in ai_details.items()
                    if data.get('score', 0) < 0.6
                ]
                if low_score_dims:
                    dim_names = {
                        "intro_quality": "开头质量",
                        "classic_naturalness": "经典引用",
                        "content_depth": "内容深度",
                        "writing_fluency": "文笔流畅度",
                        "emotional_resonance": "情感共鸣",
                        "human_like": "人味儿",
                    }
                    issues.extend([dim_names.get(dim, dim) for dim in low_score_dims])

            if issues:
                print(f"  需改进: {', '.join(issues)}")
            else:
                print(f"  表现良好 ✅")

        print(f"\n{'='*120}")


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


# ====== 6. 主流程 ======


def run_evaluation(base_version: Optional[int] = None, skip_optimize: bool = False, test_models: bool = False, auto_disable: bool = False) -> None:
    """
    运行评估流程。

    Args:
        base_version: 基线提示词版本号，None 表示使用最新版本
        skip_optimize: 是否跳过生成新版本提示词
        test_models: 是否先测试模型连通性
        auto_disable: 是否自动禁用失败的模型
    """
    models_cfg = load_models()

    # 测试模型连通性（如果启用）
    if test_models:
        print("\n" + "=" * 70)
        print("正在测试模型连通性...")
        print("=" * 70)

        # 调用独立的测试脚本
        try:
            import subprocess
            cmd = [sys.executable, str(BASE_DIR / "test_models.py")]
            if auto_disable:
                cmd.append("--auto-disable")
            result = subprocess.run(cmd, cwd=str(BASE_DIR), check=True)
            if result.returncode == 0:
                print("\n模型测试完成，无失败的模型")
            else:
                print("\n注意：有模型测试失败")
        except Exception as e:
            print(f"\n模型测试脚本执行失败: {e}")
            print("跳过模型连通性测试，继续评估...")

        print("=" * 70)

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

            # 1. 规则评估（使用从提示词中提取的字数要求）
            rule_evaluation = evaluate_article(article, length_range)

            # 2. AI评估（语义层面评估）
            print(f"  正在进行AI评估...")
            ai_evaluation = evaluate_article_via_ai(article, prompt)

            # 3. AI检测（检测文本人类化程度）
            print(f"  正在进行AI检测...")
            multi_detector = MultiAIDetector()
            enabled_detectors = multi_detector.get_enabled_detectors()

            if enabled_detectors:
                print(f"  已启用检测器: {', '.join(enabled_detectors)}")
            else:
                print(f"  未启用检测器，使用模拟检测（在.env中配置检测器）")

            detection_result = multi_detector.detect(article)
            detection_score = calculate_ai_detection_score(detection_result["ai_percentage"])

            # 4. 合并评估结果
            combined_evaluation = {
                **rule_evaluation,  # 规则评估结果
                **ai_evaluation,    # AI评估结果
                "detection_score": round(detection_score, 2),  # AI检测得分
                "detection_result": detection_result,          # AI检测详情
                "total_score": round(
                    rule_evaluation["rule_score"] +
                    ai_evaluation.get("ai_score", 0) +
                    detection_score,
                    2
                ),  # 计算总分（规则3 + AI3 + 检测4 = 10分）
            }

            all_results.append(
                {
                    "provider": provider,
                    "model": model_name,
                    "evaluation": combined_evaluation,
                    "output_path": str(out_file),
                }
            )

            # 打印评分结果
            rule_score = rule_evaluation["rule_score"]
            ai_score = ai_evaluation.get("ai_score", 0)
            detection_score = combined_evaluation["detection_score"]
            total_score = combined_evaluation["total_score"]
            ai_percentage = detection_result["ai_percentage"]
            print(
                f"  规则分: {rule_score}/3, AI分: {ai_score}/3, 检测分: {detection_score}/4, 总分: {total_score}/10 | "
                f"AI率: {ai_percentage}%, 字数: {rule_evaluation['chars']}, 段落: {rule_evaluation['paragraphs']}"
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
        description="提示词评估与优化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行评估
  %(prog)s --evaluate                          # 使用最新版提示词运行评估并生成新版本
  %(prog)s --evaluate --from-version 3         # 基于 v3 版本运行评估
  %(prog)s --evaluate --skip-optimize          # 运行评估但不生成新版本提示词

  # 查看排名
  %(prog)s --ranking                           # 显示历史版本排名

  # 横向对比（同一提示词，不同模型）
  %(prog)s --compare-models                    # 对比最新版本各模型表现
  %(prog)s --compare-models --version 5        # 对比 v5 版本各模型表现

  # 纵向对比（不同提示词，同一模型）
  %(prog)s --compare-versions                  # 对比各版本平均表现
  %(prog)s --compare-versions --model deepseek-v3.1  # 对比特定模型在各版本的表现

  # 详细查看
  %(prog)s --details --version 5               # 查看 v5 版本所有模型摘要
  %(prog)s --details --version 5 --model deepseek-v3.2-exp  # 查看特定模型的详细评估

  # 版本管理
  %(prog)s --create-version 1                  # 基于 v1 创建新版本（自动递增版本号）
  %(prog)s --create-version 1 --to 7           # 基于 v1 创建 v7 版本
        """,
    )

    # 模式选择（互斥）
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--evaluate",
        action="store_true",
        help="运行多模型评估",
    )
    mode_group.add_argument(
        "--ranking",
        action="store_true",
        help="显示历史版本排名并退出",
    )
    mode_group.add_argument(
        "--compare-models",
        action="store_true",
        help="横向对比：展示同一提示词版本下不同模型的表现",
    )
    mode_group.add_argument(
        "--compare-versions",
        action="store_true",
        help="纵向对比：展示不同提示词版本的表现（平均或特定模型）",
    )
    mode_group.add_argument(
        "--details",
        action="store_true",
        help="显示详细的评估结果（AI评估理由、规则评估详情）",
    )
    mode_group.add_argument(
        "--create-version",
        type=int,
        metavar="N",
        help="基于指定版本创建新版本（复制内容）",
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
    parser.add_argument(
        "--test-models",
        action="store_true",
        help="评估前先测试模型连通性",
    )
    parser.add_argument(
        "--auto-disable",
        action="store_true",
        help="自动禁用连通性测试失败的模型（需配合 --test-models 使用）",
    )

    # 对比模式选项
    parser.add_argument(
        "--version",
        type=int,
        metavar="N",
        help="指定提示词版本号（用于 --compare-models 和 --details）",
    )
    parser.add_argument(
        "--model",
        type=str,
        metavar="NAME",
        help="指定模型名称（用于 --compare-versions 和 --details）",
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
    elif args.compare_models:
        # 横向对比模式
        compare_models(version=args.version)
    elif args.compare_versions:
        # 纵向对比模式
        compare_versions(model_filter=args.model)
    elif args.details:
        # 详细查看模式
        if args.version is None:
            print("错误：--details 需要指定 --version 参数")
            sys.exit(1)
        show_evaluation_details(version=args.version, model=args.model)
    elif args.create_version is not None:
        # 创建新版本模式
        create_new_version(args.create_version, args.to)
    elif args.evaluate:
        # 评估模式
        run_evaluation(
            base_version=args.from_version,
            skip_optimize=args.skip_optimize,
            test_models=args.test_models,
            auto_disable=args.auto_disable,
        )
    else:
        # 默认：显示帮助
        parser.print_help()
        print("\n提示：使用 --evaluate 运行评估，或使用 --ranking 查看版本排名")

