# promptbench/core/config.py
"""
配置管理

统一的配置访问接口，管理环境变量、.env 文件和路径配置。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class Config:
    """配置容器"""
    base_dir: Path
    models_file: Path
    prompts_dir: Path
    outputs_dir: Path
    history_file: Path


class ConfigManager:
    """统一配置管理器"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            base_dir: 项目根目录，默认为当前文件的上三级目录
        """
        if base_dir is None:
            # 从当前文件向上三级目录（promptbench/core/config.py -> project_root）
            base_dir = Path(__file__).parent.parent.parent

        self.base_dir = base_dir
        self.config = self._load_config()
        self._load_env_from_dotenv()

    def _load_config(self) -> Config:
        """
        从默认路径加载配置

        Returns:
            Config: 配置对象
        """
        return Config(
            base_dir=self.base_dir,
            models_file=self.base_dir / "models.json",
            prompts_dir=self.base_dir / "prompts",
            outputs_dir=self.base_dir / "outputs",
            history_file=self.base_dir / "evaluations_history.json"
        )

    def _load_env_from_dotenv(self):
        """
        简单解析当前项目下的 .env 文件，把里面的 key=value 写入环境变量。
        避免强依赖 python-dotenv，保证脚本开箱即用。
        """
        dotenv_path = self.base_dir / ".env"
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

    def get_env(self, key: str, default: Any = None) -> Any:
        """
        获取环境变量

        Args:
            key: 环境变量键
            default: 默认值（可选）

        Returns:
            环境变量的值，或默认值
        """
        return os.getenv(key, default)

    def get_provider_config(self, provider: str) -> Dict[str, str]:
        """
        获取指定 provider 的配置（base_url, api_key）

        Args:
            provider: provider 名称

        Returns:
            包含 base_url 和 api_key 的字典
        """
        prefix = provider.lower().replace("-", "_")
        base_url = (
            self.get_env(f"{prefix}_base_url")
            or self.get_env(f"{prefix.upper()}_BASE_URL")
            or self.get_env("llm_base_url")
            or self.get_env("LLM_BASE_URL")
        )
        api_key = (
            self.get_env(f"{prefix}_api_key")
            or self.get_env(f"{prefix.upper()}_API_KEY")
            or self.get_env("llm_api_key")
            or self.get_env("LLM_API_KEY")
        )

        return {
            "base_url": base_url or "https://api.openai.com/v1",
            "api_key": api_key
        }
