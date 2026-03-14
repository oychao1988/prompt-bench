# promptbench/optimizers/prompt_optimizer.py
"""
提示词优化器

使用LLM自动优化提示词。
"""

import textwrap
from typing import Optional
from promptbench.core.config import ConfigManager


class PromptOptimizer:
    """
    提示词优化器

    使用LLM基于原始提示词和评估总结，自动生成优化后的新版本提示词。
    """

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        """
        初始化提示词优化器

        Args:
            model: 优化模型名称，None 使用默认模型
            provider: 模型提供商，None 使用默认提供商
        """
        self.config_manager = ConfigManager()
        self.model = model or self.config_manager.get_env("PROMPT_OPTIMIZER_MODEL", "gpt-5.4")
        self.provider = provider or self.config_manager.get_env("PROMPT_OPTIMIZER_PROVIDER", "openai")

    def optimize(self, original_prompt: str, eval_summary: str, new_version: int) -> str:
        """
        使用LLM自动优化提示词

        Args:
            original_prompt: 原始提示词
            eval_summary: 评估总结
            new_version: 新版本号

        Returns:
            优化后的提示词

        Raises:
            RuntimeError: 如果无法获取LLM客户端
        """
        client = self._get_client()

        if client is None:
            raise RuntimeError(
                f"提示词自动优化需要 {self.provider} 客户端，"
                f"请在 .env 中配置 {self.provider}_api_key 或 llm_api_key"
            )

        return self._optimize_via_llm(client, original_prompt, eval_summary, new_version)

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

    def _optimize_via_llm(
        self, client, original_prompt: str, eval_summary: str, new_version: int
    ) -> str:
        """
        调用LLM进行提示词优化

        Args:
            client: OpenAI客户端
            original_prompt: 原始提示词
            eval_summary: 评估总结
            new_version: 新版本号

        Returns:
            优化后的提示词
        """
        system_msg = (
            "你是一名专业的提示词工程师，擅长为大模型生成结构清晰、可执行性强的中文提示词。"
            "你的任务是：在保留原有意图和人设的前提下，根据评估总结对提示词进行迭代优化，"
            "输出一个新的完整提示词。"
        )

        user_msg = textwrap.dedent(f"""
            这是当前使用的提示词（版本号将升级为 v{new_version}）：

            --- 原始提示词开始 ---
            {original_prompt.strip()}
            --- 原始提示词结束 ---

            这是根据多模型生成结果得到的评估总结（包含常见问题与优化方向）：

            --- 评估总结开始 ---
            {eval_summary.strip()}
            --- 评估总结结束 ---

            请在充分消化以上内容的基础上，生成一份新的完整提示词文本，要求：
            1. 新提示词开头显式注明"提示词版本：v{new_version}"。
            2. 明确写清：人设、写作风格、文章结构、内容方向、注意事项等关键信息。
            3. 必须针对评估总结中提到的问题给出对应的约束。
            4. 用 Markdown 结构化书写，便于在文件中直接保存使用。
            5. 只输出提示词正文，不要任何额外解释。
            """)

        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
        )

        content = resp.choices[0].message.content or ""
        return content.strip()
