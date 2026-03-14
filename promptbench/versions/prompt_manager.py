# promptbench/versions/prompt_manager.py
"""
提示词管理器

管理提示词文件的加载、保存和版本查询。
"""

from pathlib import Path
from typing import Tuple, List, Optional
from promptbench.core.config import ConfigManager
from promptbench.core.exceptions import VersionError


class PromptManager:
    """
    提示词管理器

    管理提示词文件的加载、保存和版本查询。
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化提示词管理器

        Args:
            config_manager: 配置管理器，None 则创建新实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.prompts_dir = self.config_manager.config.prompts_dir

    def get_latest_version(self) -> Tuple[Path, int]:
        """
        获取最新的提示词版本

        Returns:
            (文件路径, 版本号)

        Raises:
            VersionError: 如果未找到提示词文件
        """
        if not self.prompts_dir.exists():
            raise VersionError(f"未找到 prompts 目录：{self.prompts_dir}", config_file=str(self.prompts_dir))

        candidates: List[Tuple[int, Path]] = []

        for p in self.prompts_dir.glob("v*.md"):
            stem = p.stem  # 例如 v1
            if stem.startswith("v") and stem[1:].isdigit():
                ver = int(stem[1:])
                candidates.append((ver, p))

        if not candidates:
            raise VersionError(
                "prompts 目录下未找到任何 v*.md 提示词文件",
                config_file=str(self.prompts_dir)
            )

        version, path = max(candidates, key=lambda x: x[0])
        return path, version

    def get_prompt_path(self, version: int) -> Path:
        """
        根据版本号获取提示词文件路径

        Args:
            version: 版本号

        Returns:
            提示词文件路径

        Raises:
            VersionError: 如果文件不存在
        """
        prompt_path = self.prompts_dir / f"v{version}.md"

        if not prompt_path.exists():
            raise VersionError(
                f"未找到提示词文件：{prompt_path}",
                version=version,
                file_path=str(prompt_path)
            )

        return prompt_path

    def load_prompt(self, version: Optional[int] = None) -> Tuple[str, int]:
        """
        加载提示词内容

        Args:
            version: 版本号，None 则加载最新版本

        Returns:
            (提示词内容, 版本号)

        Raises:
            VersionError: 如果文件不存在
        """
        if version is None:
            prompt_path, version = self.get_latest_version()
        else:
            prompt_path = self.get_prompt_path(version)

        content = prompt_path.read_text(encoding="utf-8")
        return content, version

    def save_prompt(self, content: str, version: int) -> Path:
        """
        保存提示词到文件

        Args:
            content: 提示词内容
            version: 版本号

        Returns:
            保存的文件路径
        """
        prompt_path = self.prompts_dir / f"v{version}.md"
        prompt_path.write_text(content, encoding="utf-8")
        return prompt_path
