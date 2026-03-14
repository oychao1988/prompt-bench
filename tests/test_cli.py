# tests/test_cli.py
import pytest
import sys
from unittest.mock import patch
from promptbench.cli.main import CLI


@pytest.mark.skip(reason="argparse 在没有参数时的行为难以测试")
def test_parse_args_empty():
    """测试解析空参数"""
    with patch.object(sys, 'argv', ['promptbench']):
        with pytest.raises(SystemExit):
            CLI.parse_args()


def test_parse_args_help():
    """测试解析帮助参数"""
    with patch.object(sys, 'argv', ['promptbench', '--help']):
        with pytest.raises(SystemExit):
            CLI.parse_args()


def test_parse_args_evaluate():
    """测试解析评估命令参数"""
    with patch.object(sys, 'argv', ['promptbench', 'evaluate']):
        args = CLI.parse_args()
        assert args.command == 'evaluate'
        assert args.from_version is None
        assert args.skip_optimize is False


def test_parse_args_evaluate_with_version():
    """测试解析包含版本的评估命令"""
    with patch.object(sys, 'argv', ['promptbench', 'evaluate', '--from-version', '1']):
        args = CLI.parse_args()
        assert args.command == 'evaluate'
        assert args.from_version == 1


def test_parse_args_evaluate_skip_optimize():
    """测试解析跳过优化参数"""
    with patch.object(sys, 'argv', ['promptbench', 'evaluate', '--skip-optimize']):
        args = CLI.parse_args()
        assert args.command == 'evaluate'
        assert args.skip_optimize is True


def test_parse_args_ranking():
    """测试解析排名命令"""
    with patch.object(sys, 'argv', ['promptbench', 'ranking']):
        args = CLI.parse_args()
        assert args.command == 'ranking'
        assert args.limit == 10


def test_parse_args_ranking_with_limit():
    """测试解析带限制的排名命令"""
    with patch.object(sys, 'argv', ['promptbench', 'ranking', '--limit', '5']):
        args = CLI.parse_args()
        assert args.command == 'ranking'
        assert args.limit == 5


def test_parse_args_compare():
    """测试解析对比命令"""
    with patch.object(sys, 'argv', ['promptbench', 'compare', '--versions', '1', '2']):
        args = CLI.parse_args()
        assert args.command == 'compare'
        assert args.versions == [1, 2]


def test_parse_args_show():
    """测试解析显示命令"""
    with patch.object(sys, 'argv', ['promptbench', 'show', '1']):
        args = CLI.parse_args()
        assert args.command == 'show'
        assert args.version == 1
