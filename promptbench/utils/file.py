# promptbench/utils/file.py
"""
文件操作工具

提供文件操作辅助函数。
"""

from pathlib import Path
from typing import Optional
import json


class FileUtils:
    """文件操作工具类"""

    @staticmethod
    def ensure_dir(dir_path: Path) -> None:
        """
        确保目录存在

        Args:
            dir_path: 目录路径
        """
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def load_json(file_path: Path) -> dict:
        """
        加载 JSON 文件

        Args:
            file_path: 文件路径

        Returns:
            JSON 数据字典
        """
        if not file_path.exists():
            return {}

        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_json(data: dict, file_path: Path, ensure_dir: bool = True) -> None:
        """
        保存 JSON 文件

        Args:
            data: 数据字典
            file_path: 文件路径
            ensure_dir: 是否确保目录存在
        """
        if ensure_dir:
            FileUtils.ensure_dir(file_path.parent)

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_text(file_path: Path) -> str:
        """
        加载文本文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容字符串
        """
        with file_path.open("r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def save_text(content: str, file_path: Path, ensure_dir: bool = True) -> None:
        """
        保存文本文件

        Args:
            content: 内容字符串
            file_path: 文件路径
            ensure_dir: 是否确保目录存在
        """
        if ensure_dir:
            FileUtils.ensure_dir(file_path.parent)

        with file_path.open("w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def find_version_files(dir_path: Path) -> list:
        """
        查找目录中所有的版本文件

        Args:
            dir_path: 目录路径

        Returns:
            版本文件列表
        """
        if not dir_path.exists():
            return []

        version_files = []

        for p in dir_path.glob("v*.md"):
            stem = p.stem
            if stem.startswith("v") and stem[1:].isdigit():
                ver = int(stem[1:])
                version_files.append((ver, p))

        version_files.sort(key=lambda x: x[0])
        return version_files

    @staticmethod
    def get_output_dir(base_dir: Path, version: int) -> Path:
        """
        获取指定版本的输出目录

        Args:
            base_dir: 项目根目录
            version: 版本号

        Returns:
            输出目录路径
        """
        return base_dir / "outputs" / f"v{version}"
