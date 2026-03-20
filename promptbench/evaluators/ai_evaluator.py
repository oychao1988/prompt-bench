# promptbench/evaluators/ai_evaluator.py
"""
AI语义评估器

使用LLM进行文本质量的语义层面评估。
"""

import json
import textwrap
from typing import Optional, Dict, Any
from promptbench.core.entities import AIEvaluation
from promptbench.core.constants import DEFAULT_AI_WEIGHTS
from promptbench.core.config import ConfigManager


class AIEvaluator:
    """
    AI语义评估器

    使用LLM对文本进行语义层面的质量评估，
    包括开头质量、经典引用、内容深度、文笔流畅度和情感共鸣。
    """

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        """
        初始化AI评估器

        Args:
            model: 评估模型名称，None 使用默认模型
            provider: 模型提供商，None 使用默认提供商
        """
        self.config_manager = ConfigManager()
        self.model = model or self.config_manager.get_env("EVALUATION_MODEL", "gpt-5.4")
        self.provider = provider or self.config_manager.get_env("EVALUATION_PROVIDER", "openai")
        self.scale_factor = 0.8  # 1分制 → 0.8分制的转换系数

    def evaluate(self, text: str, prompt: str) -> AIEvaluation:
        """
        使用AI评估文本质量

        Args:
            text: 待评估的文本
            prompt: 原始提示词（作为评估参考）

        Returns:
            AIEvaluation: AI评估结果
        """
        client = self._get_client()

        if client is None:
            return AIEvaluation(
                ai_score=0,
                ai_details={},
                error=f"无法获取 {self.provider} 客户端，请检查 .env 配置"
            )

        try:
            ai_result = self._call_ai_evaluation(client, text, prompt)

            if ai_result is None:
                return AIEvaluation(
                    ai_score=0,
                    ai_details={},
                    error="AI返回结果无法解析为JSON"
                )

            # 计算AI评估总分
            ai_score = (
                ai_result.get("intro_quality", {}).get("score", 0) +
                ai_result.get("classic_naturalness", {}).get("score", 0) +
                ai_result.get("content_depth", {}).get("score", 0) +
                ai_result.get("writing_fluency", {}).get("score", 0) +
                ai_result.get("emotional_resonance", {}).get("score", 0)
            ) * self.scale_factor

            return AIEvaluation(
                ai_score=round(ai_score, 2),
                ai_details=ai_result
            )

        except Exception as e:
            return AIEvaluation(
                ai_score=0,
                ai_details={},
                error=f"AI评估失败: {str(e)}"
            )

    def _get_client(self):
        """
        获取LLM客户端

        Returns:
            OpenAI客户端或None（如果获取失败）
        """
        try:
            from openai import OpenAI

            provider_config = self.config_manager.get_provider_config(self.provider)
            client = OpenAI(
                base_url=provider_config["base_url"],
                api_key=provider_config["api_key"]
            )
            return client

        except Exception:
            return None

    def _call_ai_evaluation(self, client, text: str, prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用AI进行评估

        Args:
            client: OpenAI客户端
            text: 待评估文本
            prompt: 原始提示词

        Returns:
            AI评估结果字典，None 表示解析失败
        """
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

            1. 开头质量（0.8分）：
               - 评分标准：开头是否直接入题，有吸引力，符合人设
               - 0分：开头拖沓，没有吸引力，不符合人设
               - 0.4分：开头尚可，但吸引力不足或人设不够明显
               - 0.8分：开头直接入题，有吸引力，符合人设

            2. 经典引用恰当性（0.8分）：
               - 评分标准：经典引用是否自然恰当，与观点紧密相关
               - 0分：没有引用或引用生硬、不相关
               - 0.4分：有引用但不够自然或相关性一般
               - 0.8分：引用自然恰当，与观点紧密相关

            3. 内容深度与思想性（0.8分）：
               - 评分标准：内容是否有深度，观点是否有启发性，避免空洞
               - 0分：内容空洞，观点老套，没有启发性
               - 0.4分：内容有一定深度，但观点不够深入
               - 0.8分：内容有深度，观点有启发性，能引发思考

            4. 文笔流畅度与可读性（0.8分）：
               - 评分标准：文笔是否流畅自然，语言是否有节奏感
               - 0分：文笔生硬，语言不流畅
               - 0.4分：文笔尚可，但流畅度不足
               - 0.8分：文笔流畅自然，语言有节奏感

            5. 情感共鸣（0.8分）：
               - 评分标准：是否能引发情感共鸣，是否打动人心
               - 0分：情感平淡，无法引发共鸣
               - 0.4分：有一定情感，但共鸣不足
               - 0.8分：能引发情感共鸣，打动人心

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
            - 每个维度的评分必须在规定范围内（0-1分），系统会自动转换为0-0.8分制
            - 理由说明要简明扼要，指出优点或不足
            """)

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,  # 使用较低的temperature以提高稳定性
        )

        content = resp.choices[0].message.content or ""

        # 解析JSON结果
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            return json.loads(json_str)

        return None
