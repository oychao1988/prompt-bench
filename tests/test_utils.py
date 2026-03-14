# tests/test_utils.py
import pytest
from pathlib import Path
from promptbench.utils.text import TextUtils
from promptbench.utils.file import FileUtils
from promptbench.utils.log import LogUtils


def test_text_utils_extract_length_requirement():
    """测试提取字数要求"""
    # 测试范围格式
    assert TextUtils.extract_length_requirement("400-1500字") == (400, 1500)
    assert TextUtils.extract_length_requirement("500~1000字") == (500, 1000)
    assert TextUtils.extract_length_requirement("600到800字") == (600, 800)

    # 测试单个字数格式
    result = TextUtils.extract_length_requirement("约800字")
    assert result is not None
    assert 500 <= result[0] <= 1000
    assert 600 <= result[1] <= 1200

    # 测试无字数要求
    assert TextUtils.extract_length_requirement("写一篇文章") is None


def test_text_utils_count_chars():
    """测试字符计数"""
    assert TextUtils.count_chars("") == 0
    assert TextUtils.count_chars("测试") == 2
    assert TextUtils.count_chars("  测试  ") == 2


def test_text_utils_count_paragraphs():
    """测试段落计数"""
    assert TextUtils.count_paragraphs("") == 0
    assert TextUtils.count_paragraphs("测试") == 1
    assert TextUtils.count_paragraphs("测试\n\n测试") == 2


def test_text_utils_clean_text():
    """测试清理文本"""
    dirty_text = "测试\n\n\n测试\n  "
    clean_text = TextUtils.clean_text(dirty_text)

    # 不应有连续的多个空行
    assert "\n\n\n" not in clean_text


def test_file_utils_load_and_save_json(tmp_path):
    """测试JSON加载和保存"""
    test_file = tmp_path / "test.json"
    test_data = {"test": "data"}

    FileUtils.save_json(test_data, test_file)
    assert test_file.exists()

    loaded_data = FileUtils.load_json(test_file)
    assert loaded_data == test_data


def test_file_utils_load_and_save_text(tmp_path):
    """测试文本加载和保存"""
    test_file = tmp_path / "test.txt"
    test_content = "测试内容"

    FileUtils.save_text(test_content, test_file)
    assert test_file.exists()

    loaded_content = FileUtils.load_text(test_file)
    assert loaded_content == test_content


def test_file_utils_ensure_dir(tmp_path):
    """测试确保目录存在"""
    new_dir = tmp_path / "new" / "dir"
    assert not new_dir.exists()

    FileUtils.ensure_dir(new_dir)
    assert new_dir.exists()


def test_file_utils_find_version_files(tmp_path):
    """测试查找版本文件"""
    (tmp_path / "v1.md").write_text("v1")
    (tmp_path / "v3.md").write_text("v3")
    (tmp_path / "v2.md").write_text("v2")
    (tmp_path / "other.txt").write_text("other")

    version_files = FileUtils.find_version_files(tmp_path)

    assert len(version_files) == 3
    assert version_files[0][0] == 1
    assert version_files[1][0] == 2
    assert version_files[2][0] == 3


def test_log_utils_init():
    """测试初始化日志记录器"""
    logger = LogUtils.init_logger(level="DEBUG")
    assert logger is not None

    # 再次获取应返回同一实例
    logger2 = LogUtils.get_logger()
    assert logger is logger2


def test_log_utils_methods():
    """测试日志记录方法"""
    # 这些方法不应抛出异常
    LogUtils.info("info test")
    LogUtils.warning("warning test")
    LogUtils.error("error test")
    LogUtils.debug("debug test")
