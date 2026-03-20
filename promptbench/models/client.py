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

    def __init__(self, provider: str, api_format: str = None):
        """
        初始化模型客户端

        Args:
            provider: 提供商名称（如 "openai", "deepseek"）
            api_format: API 格式（如 "openai", "anthropic"），如果不提供则根据 provider 推断
        """
        self.provider = provider
        self.api_format = api_format or self._infer_api_format(provider)
        self.config_manager = ConfigManager()
        self._client = None
        self._base_url = None

    def _infer_api_format(self, provider: str) -> str:
        """
        根据 provider 推断 API 格式（仅作后备方案）

        ⚠️ 注意：此方法仅作为后备方案使用。
        正确的做法是从 models.json 的分类键名判断 API 格式，
        然后在创建 ModelClient 时明确传入 api_format 参数。

        Args:
            provider: 提供商名称

        Returns:
            API 格式字符串

        推断规则（仅供参考，不准确）：
        - anthropic, minimax-cn → anthropic
        - 其他 → openai
        """
        # ⚠️ 这个推断逻辑不够准确，因为：
        # 1. provider 名称不能完全决定 API 格式
        # 2. 同一个 provider 可能使用不同的 API 格式
        # 3. 应该从 models.json 的分类键名来判断
        if provider in ["anthropic", "minimax-cn"]:
            return "anthropic"
        else:
            return "openai"

    def get_client(self):
        """
        获取客户端实例

        Returns:
            客户端实例或 None（如果配置无效）
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
        try:
            # 构建用户消息
            if keywords:
                user_content = "请围绕以下关键词写一篇公众号文章：\n\n" + ",".join(keywords)
            elif topic:
                user_content = f"请根据以上要求，围绕选题「{topic}」写一篇完整的公众号文章。"
            else:
                user_content = "请根据以上要求，写一篇完整的公众号文章。"

            # 根据不同的 provider 使用不同的 API 格式
            if self.api_format == "anthropic":
                return self._call_anthropic_format(model_name, prompt, user_content, max_tokens, temperature)
            else:
                return self._call_openai_format(model_name, prompt, user_content, max_tokens, temperature)

        except Exception as e:
            print(f"❌ 模型调用失败 ({self.provider}/{model_name}): {e}")
            return None

    def _call_openai_format(self, model_name: str, prompt: str, user_content: str, max_tokens: Optional[int], temperature: float) -> Optional[str]:
        """使用 OpenAI 格式调用"""
        client = self.get_client()
        if client is None:
            return None

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

    def _call_anthropic_format(self, model_name: str, prompt: str, user_content: str, max_tokens: Optional[int], temperature: float) -> Optional[str]:
        """使用 Anthropic 格式调用"""
        import requests
        
        provider_config = self.config_manager.get_provider_config(self.provider)
        
        if not provider_config.get("api_key"):
            print(f"❌ {self.provider}: 缺少 API Key")
            return None

        # 构建 Anthropic API 参数
        api_params = {
            "model": model_name,
            "max_tokens": max_tokens or 1000,
            "messages": [
                {"role": "user", "content": f"{prompt}\n\n{user_content}"}
            ],
            "temperature": temperature,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {provider_config['api_key']}",
            "anthropic-version": "2023-06-01"
        }

        # 调用 API
        response = requests.post(
            f"{provider_config['base_url']}/messages",
            json=api_params,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()
            
            # 处理不同的响应格式
            content = ""
            content_list = data.get("content", [])
            
            for item in content_list:
                if "text" in item:
                    content += item["text"]
                elif "thinking" in item:
                    # 跳过思考过程，只要最终输出
                    continue
            
            return content
        else:
            print(f"❌ API 调用失败 ({self.provider}/{model_name}): {response.status_code} {response.text}")
            return None

    def test_connection(self, model_name: str) -> Dict[str, Any]:
        """
        测试模型连接性

        Args:
            model_name: 模型名称

        Returns:
            包含测试结果的字典
        """
        try:
            # 根据不同的 provider 使用不同的测试方法
            if self.api_format == "anthropic":
                return self._test_anthropic_connection(model_name)
            else:
                return self._test_openai_connection(model_name)

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider,
                "model": model_name
            }

    def _test_openai_connection(self, model_name: str) -> Dict[str, Any]:
        """测试 OpenAI 格式连接"""
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

    def _test_anthropic_connection(self, model_name: str) -> Dict[str, Any]:
        """测试 Anthropic 格式连接"""
        
        provider_config = self.config_manager.get_provider_config(self.provider)
        
        if not provider_config.get("api_key"):
            return {
                "success": False,
                "error": "无法创建客户端（请检查 API Key 配置）",
                "provider": self.provider,
                "model": model_name
            }

        try:
            # 发送一个简单的测试请求
            api_params = {
                "model": model_name,
                "max_tokens": 10,
                "messages": [
                    {"role": "user", "content": "Hi"}
                ]
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider_config['api_key']}",
                "anthropic-version": "2023-06-01"
            }

            response = requests.post(
                f"{provider_config['base_url']}/messages",
                json=api_params,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "provider": self.provider,
                    "model": model_name,
                    "base_url": provider_config['base_url'],
                    "response": data.get("content", [{}])[0].get("text", "")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "provider": self.provider,
                    "model": model_name
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider,
                "model": model_name
            }
