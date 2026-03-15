# promptbench/models/client.py
"""
模型客户端

统一的模型调用接口。
"""

from typing import Optional, List, Dict, Any
from promptbench.core.config import ConfigManager


class ModelClient:
    """
    模型客户端

    提供统一的模型调用接口，支持多种提供商。
    """

    def __init__(self, provider: str):
        """
        初始化模型客户端

        Args:
            provider: 提供商名称（如 "openai", "deepseek"）
        """
        self.provider = provider
        self.config_manager = ConfigManager()
        self._client = None
        self._base_url = None

    def get_client(self):
        """
        获取 OpenAI 客户端实例

        Returns:
            OpenAI 客户端或 None（如果配置无效）
        """
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI

            provider_config = self.config_manager.get_provider_config(self.provider)

            if not provider_config.get("api_key"):
                return None

            self._client = OpenAI(
                base_url=provider_config["base_url"],
                api_key=provider_config["api_key"]
            )
            self._base_url = provider_config["base_url"]
            return self._client

        except Exception:
            return None

    def call(
        self,
        model_name: str,
        prompt: str,
        topic: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.8,
    ) -> Optional[str]:
        """
        调用模型生成文本

        Args:
            model_name: 模型名称
            prompt: 系统提示词
            topic: 选题（可选）
            keywords: 关键词列表（可选）
            max_tokens: 最大生成 token 数（可选）
            temperature: 温度参数

        Returns:
            生成的文本，失败返回 None
        """
        client = self.get_client()

        if client is None:
            return None

        try:
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
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
            }

            if max_tokens is not None:
                api_params["max_tokens"] = max_tokens

            # 调用 API
            response = client.chat.completions.create(**api_params)
            content = response.choices[0].message.content or ""

            return content

        except Exception as e:
            print(f"❌ 模型调用失败 ({self.provider}/{model_name}): {e}")
            return None

    def test_connection(self, model_name: str) -> Dict[str, Any]:
        """
        测试模型连接性

        Args:
            model_name: 模型名称

        Returns:
            包含测试结果的字典
        """
        client = self.get_client()

        if client is None:
            return {
                "success": False,
                "error": "无法创建客户端（请检查 API Key 配置）",
                "provider": self.provider,
                "model": model_name
            }

        try:
            # 发送一个简单的测试请求
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": "Hi"}
                ],
                max_tokens=10
            )

            return {
                "success": True,
                "provider": self.provider,
                "model": model_name,
                "base_url": self._base_url,
                "response": response.choices[0].message.content if response.choices else None
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider,
                "model": model_name
            }
