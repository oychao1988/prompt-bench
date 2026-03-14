# promptbench/cli/main.py
"""
PromptBench CLI 主入口

提供命令行访问入口。
"""

import argparse
import sys
from typing import Optional
from promptbench.core.config import ConfigManager


class CLI:
    """PromptBench 命令行接口"""

    @staticmethod
    def parse_args():
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="PromptBench - 提示词评估与优化工具"
        )

        subparsers = parser.add_subparsers(title="命令", dest="command")

        # 评估命令
        evaluate_parser = subparsers.add_parser(
            "evaluate", help="运行评估"
        )
        evaluate_parser.add_argument(
            "--from-version", "-f", type=int,
            help="从指定版本开始评估"
        )
        evaluate_parser.add_argument(
            "--skip-optimize", "-s", action="store_true",
            help="跳过提示词优化"
        )

        # 排名命令
        ranking_parser = subparsers.add_parser(
            "ranking", help="查看版本排名"
        )
        ranking_parser.add_argument(
            "--limit", "-l", type=int, default=10,
            help="显示数量限制（默认10）"
        )

        # 比较命令
        compare_parser = subparsers.add_parser(
            "compare", help="版本对比"
        )
        compare_parser.add_argument(
            "--versions", "-v", nargs="+", type=int,
            help="要比较的版本号"
        )

        # 查看命令
        show_parser = subparsers.add_parser(
            "show", help="显示版本详情"
        )
        show_parser.add_argument(
            "version", type=int, help="版本号"
        )

        return parser.parse_args()

    @staticmethod
    def main():
        """主入口函数"""
        args = CLI.parse_args()

        # 初始化配置管理器
        config_manager = ConfigManager()

        # 根据命令执行相应操作
        if args.command == "evaluate":
            CLI.run_evaluation(config_manager, args)
        elif args.command == "ranking":
            CLI.show_ranking(config_manager, args)
        elif args.command == "compare":
            CLI.compare_versions(config_manager, args)
        elif args.command == "show":
            CLI.show_version(config_manager, args)
        else:
            print("未知命令，请使用 --help 查看帮助")
            sys.exit(1)

    @staticmethod
    def run_evaluation(config_manager, args):
        """
        运行评估

        说明：此方法目前是占位符，实际的评估逻辑需要进一步实现
        """
        print("正在运行评估...")
        if args.from_version:
            print(f"从版本 {args.from_version} 开始")
        if args.skip_optimize:
            print("跳过优化阶段")

    @staticmethod
    def show_ranking(config_manager, args):
        """
        显示排名

        说明：此方法目前是占位符
        """
        print(f"显示版本排名（前 {args.limit} 个）:")

    @staticmethod
    def compare_versions(config_manager, args):
        """
        比较版本

        说明：此方法目前是占位符
        """
        print(f"比较版本: {args.versions}")

    @staticmethod
    def show_version(config_manager, args):
        """
        显示版本详情

        说明：此方法目前是占位符
        """
        print(f"显示版本详情: v{args.version}")


if __name__ == "__main__":
    try:
        CLI.main()
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
