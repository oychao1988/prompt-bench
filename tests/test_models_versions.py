# tests/test_models_versions.py
import pytest
from pathlib import Path
from promptbench.models.client import ModelClient
from promptbench.versions.prompt_manager import PromptManager
from promptbench.versions.history_manager import HistoryManager
from promptbench.core.exceptions import VersionError
from unittest.mock import Mock, patch
import json
import tempfile


def test_model_client_init():
    """测试模型客户端初始化"""
    client = ModelClient("openai")
    assert client.provider == "openai"


def test_model_client_no_api_key():
    """测试没有 API key 的情况"""
    client = ModelClient("openai")

    with patch.object(client.config_manager, 'get_provider_config', return_value={"base_url": "https://api.openai.com/v1", "api_key": ""}):
        result = client.get_client()
        assert result is None


def test_prompt_manager_latest_version(tmp_path):
    """测试获取最新版本"""
    # 创建临时提示词文件
    (tmp_path / "v1.md").write_text("# Version 1")
    (tmp_path / "v3.md").write_text("# Version 3")
    (tmp_path / "v2.md").write_text("# Version 2")

    # 创建配置管理器并设置 prompts_dir
    from promptbench.core.config import Config
    config = Config(
        base_dir=tmp_path,
        models_file=tmp_path / "models.json",
        prompts_dir=tmp_path,
        outputs_dir=tmp_path / "outputs",
        history_file=tmp_path / "history.json"
    )
    manager = PromptManager(config_manager=Mock(config=config))

    path, version = manager.get_latest_version()

    assert version == 3
    assert path.name == "v3.md"


def test_prompt_manager_load_by_version(tmp_path):
    """测试按版本号加载"""
    (tmp_path / "v5.md").write_text("# Test Prompt")

    from promptbench.core.config import Config
    config = Config(
        base_dir=tmp_path,
        models_file=tmp_path / "models.json",
        prompts_dir=tmp_path,
        outputs_dir=tmp_path / "outputs",
        history_file=tmp_path / "history.json"
    )
    manager = PromptManager(config_manager=Mock(config=config))

    content, version = manager.load_prompt(5)

    assert version == 5
    assert content == "# Test Prompt"


def test_prompt_manager_version_not_found(tmp_path):
    """测试版本不存在"""
    from promptbench.core.config import Config
    config = Config(
        base_dir=tmp_path,
        models_file=tmp_path / "models.json",
        prompts_dir=tmp_path,
        outputs_dir=tmp_path / "outputs",
        history_file=tmp_path / "history.json"
    )
    manager = PromptManager(config_manager=Mock(config=config))

    with pytest.raises(VersionError) as exc_info:
        manager.get_prompt_path(999)

    assert "999" in str(exc_info.value)


def test_history_manager_calculate_summary():
    """测试计算摘要"""
    manager = HistoryManager()

    evaluations = [
        {
            "rule_score": 2.5,
            "ai_score": 2.0,
            "detection_score": 3.0,
            "total_score": 7.5,
            "model": "gpt-4"
        },
        {
            "rule_score": 2.8,
            "ai_score": 2.2,
            "detection_score": 3.2,
            "total_score": 8.2,
            "model": "gpt-4o"
        },
    ]

    summary = manager.calculate_summary(evaluations)

    assert summary["avg_total_score"] == 7.85  # (7.5 + 8.2) / 2
    assert summary["max_total_score"] == 8.2
    assert summary["min_total_score"] == 7.5
    assert summary["best_model"] == "gpt-4o"
    assert summary["model_count"] == 2


def test_history_manager_empty_evaluations():
    """测试空评估列表"""
    manager = HistoryManager()

    summary = manager.calculate_summary([])

    assert summary["avg_total_score"] == 0
    assert summary["model_count"] == 0
    assert summary["best_model"] is None


def test_history_manager_save_and_load(tmp_path):
    """测试保存和加载历史"""
    from promptbench.core.config import Config
    config = Config(
        base_dir=tmp_path,
        models_file=tmp_path / "models.json",
        prompts_dir=tmp_path,
        outputs_dir=tmp_path / "outputs",
        history_file=tmp_path / "history.json"
    )
    manager = HistoryManager(config_manager=Mock(config=config))

    evaluations = [
        {
            "rule_score": 2.5,
            "ai_score": 2.0,
            "detection_score": 3.0,
            "total_score": 7.5,
            "model": "gpt-4"
        }
    ]

    manager.update_history(1, evaluations, "/path/to/v1.md")

    # 验证保存的文件
    assert (tmp_path / "history.json").exists()

    # 加载并验证
    history = manager.load_history()
    assert "v1" in history
    assert history["v1"]["version"] == 1
    assert history["v1"]["summary"]["model_count"] == 1
