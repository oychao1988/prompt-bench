# promptbench/cli/main.py
"""
PromptBench CLI 主入口

提供命令行访问入口。
"""

import argparse
import json
import sys
from typing import Optional, Dict, List, Any
from pathlib import Path
from promptbench.core.config import ConfigManager
from promptbench.models.client import ModelClient


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

        # 连通性测试命令
        ping_parser = subparsers.add_parser(
            "ping", help="测试模型连通性（像网络 ping 一样）"
        )
        ping_parser.add_argument(
            "--provider", "-p", type=str,
            help="指定提供商（如 xiaoai）"
        )
        ping_parser.add_argument(
            "--model", "-m", type=str,
            help="指定模型名称"
        )
        ping_parser.add_argument(
            "--all", "-a", action="store_true",
            help="测试所有启用的模型"
        )
        ping_parser.add_argument(
            "--auto-disable", "-d", action="store_true",
            help="自动禁用测试失败的模型"
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
        elif args.command == "ping":
            CLI.ping_models(config_manager, args)
        else:
            print("未知命令，请使用 --help 查看帮助")
            sys.exit(1)

    @staticmethod
    def run_evaluation(config_manager, args):
        """
        运行多模型评估流程

        Args:
            config_manager: 配置管理器
            args: 命令行参数
        """
        from promptbench.versions.prompt_manager import PromptManager
        from promptbench.evaluators.rule_evaluator import RuleEvaluator
        from promptbench.evaluators.ai_evaluator import AIEvaluator
        from promptbench.detectors.multi_detector import MultiAIDetector
        from promptbench.models.client import ModelClient
        from promptbench.optimizers.prompt_optimizer import PromptOptimizer
        from promptbench.optimizers.summarizer import EvaluationSummarizer
        from promptbench.versions.history_manager import HistoryManager
        from promptbench.core.entities import EvaluationResult
        from promptbench.core.config import ConfigManager
        from pathlib import Path
        import json
        import concurrent.futures
        from datetime import datetime

        print("正在运行多模型评估...")

        # 1. 加载提示词
        prompt_manager = PromptManager(config_manager)

        if args.from_version:
            prompt_path = prompt_manager.get_prompt_path(args.from_version)
            prompt = prompt_path.read_text(encoding="utf-8")
            version = args.from_version
            print(f"使用版本 {version} 的提示词")
        else:
            prompt_path, version = prompt_manager.get_latest_version()
            prompt = prompt_path.read_text(encoding="utf-8")
            print(f"使用最新版本 {version} 的提示词")

        # 2. 创建输出目录
        output_dir = config_manager.config.outputs_dir / f"v{version}"
        output_dir.mkdir(exist_ok=True)

        # 3. 加载模型配置
        with open(config_manager.config.models_file, "r", encoding="utf-8") as f:
            models_config = json.load(f)

        enabled_models = []
        for category, models in models_config.items():
            for model in models:
                if model.get("enabled", False):
                    enabled_models.append((model["provider"], model["name"]))

        print(f"启用 {len(enabled_models)} 个模型")

        # 4. 评估结果列表
        all_results = []

        # 5. 并行评估
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_model = {}

            for provider, model_name in enabled_models:
                print(f"正在调用 {provider}/{model_name}...")

                future = executor.submit(
                    CLI._evaluate_single_model,
                    provider, model_name, prompt, version
                )
                future_to_model[future] = (provider, model_name)

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_model):
                provider, model_name = future_to_model[future]

                try:
                    result = future.result()
                    if result:
                        all_results.append(result)
                        print(f"✅ {provider}/{model_name} 完成")
                    else:
                        print(f"❌ {provider}/{model_name} 失败")

                except Exception as e:
                    print(f"❌ {provider}/{model_name} 出错: {e}")

        # 6. 转换并保存评估结果
        if all_results:
            # 将 EvaluationResult 对象转换为字典格式
            results_dict = []
            for result in all_results:
                result_dict = {
                    "provider": result.provider,
                    "model": result.model,
                    "rule_score": result.rule_score,
                    "ai_score": result.ai_score,
                    "detection_score": result.detection_score,
                    "total_score": result.total_score,
                    "rule_details": result.rule_details.to_dict(),
                    "ai_details": result.ai_details.to_dict(),
                    "detection_details": result.detection_details,
                    "chars": result.chars,
                    "paragraphs": result.paragraphs,
                    "output_path": str(result.output_path) if result.output_path else None
                }
                results_dict.append(result_dict)

            # 保存到 JSON 文件
            evaluations_file = output_dir / "evaluations.json"
            with open(evaluations_file, "w", encoding="utf-8") as f:
                json.dump(results_dict, f, ensure_ascii=False, indent=2, default=str)

            print(f"结果已保存到 {evaluations_file}")

            # 7. 生成评估总结
            summarizer = EvaluationSummarizer()
            summary = summarizer.summarize(results_dict)

            summary_file = output_dir / "summary.md"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(summary)

            print(f"评估总结已生成: {summary_file}")

            # 8. 自动优化提示词（如果未跳过）
            if not args.skip_optimize:
                print("正在优化提示词...")

                optimizer = PromptOptimizer()
                new_prompt = optimizer.optimize(prompt, summary, version + 1)

                # 保存新提示词
                new_version = version + 1
                new_prompt_path = prompt_manager.save_prompt(new_prompt, new_version)
                print(f"新提示词已生成: {new_prompt_path}")

            # 9. 更新历史记录
            history_manager = HistoryManager(config_manager)
            history_manager.update_history(
                version,
                results_dict,
                str(prompt_path)
            )
            print("历史记录已更新")

        print(f"评估完成！共评估 {len(all_results)}/{len(enabled_models)} 个模型")

    @staticmethod
    def _evaluate_single_model(provider, model_name, prompt, version):
        """
        评估单个模型

        Args:
            provider: 提供商名称
            model_name: 模型名称
            prompt: 提示词
            version: 版本号

        Returns:
            EvaluationResult 或 None
        """
        from promptbench.models.client import ModelClient
        from promptbench.evaluators.rule_evaluator import RuleEvaluator
        from promptbench.evaluators.ai_evaluator import AIEvaluator
        from promptbench.detectors.multi_detector import MultiAIDetector
        from promptbench.core.entities import EvaluationResult
        from pathlib import Path

        try:
            # 调用模型
            client = ModelClient(provider)
            content = client.call(model_name, prompt)

            if not content:
                return None

            # 保存模型输出
            output_dir = Path("outputs") / f"v{version}"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{provider}__{model_name}.txt"
            output_file.write_text(content, encoding="utf-8")

            # 执行评估
            rule_evaluator = RuleEvaluator()
            rule_eval = rule_evaluator.evaluate(content)

            ai_evaluator = AIEvaluator()
            ai_eval = ai_evaluator.evaluate(content, prompt)

            detector = MultiAIDetector()
            detection_result = detector.detect(content)

            # 计算总分
            quality_score = rule_eval.rule_score + ai_eval.ai_score
            detection_score = (1 - detection_result["ai_score"]) * 4
            total_score = quality_score + detection_score

            # 创建结果
            result = EvaluationResult(
                provider=provider,
                model=model_name,
                rule_score=rule_eval.rule_score,
                ai_score=ai_eval.ai_score,
                detection_score=detection_score,
                total_score=total_score,
                rule_details=rule_eval,
                ai_details=ai_eval,
                detection_details=detection_result,
                chars=len(content),
                paragraphs=len([p for p in content.split("\n") if p.strip()]),
                output_path=output_file
            )

            return result

        except Exception as e:
            print(f"❌ 评估失败 {provider}/{model_name}: {e}")
            return None

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

    @staticmethod
    def load_models_config(config_manager: ConfigManager) -> Dict[str, List[Dict[str, Any]]]:
        """
        加载模型配置

        Args:
            config_manager: 配置管理器

        Returns:
            模型配置字典
        """
        models_file = config_manager.config.models_file

        if not models_file.exists():
            print(f"❌ 模型配置文件不存在: {models_file}")
            sys.exit(1)

        with open(models_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def ping_single_model(provider: str, model_name: str) -> None:
        """
        测试单个模型的连通性

        Args:
            provider: 提供商名称
            model_name: 模型名称
        """
        client = ModelClient(provider)
        result = client.test_connection(model_name)

        if result["success"]:
            print(f"✅ {provider}/{model_name}")
            print(f"   Base URL: {result.get('base_url', 'N/A')}")
            print(f"   Response: {result.get('response', 'N/A')[:50]}...")
        else:
            print(f"❌ {provider}/{model_name}")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    @staticmethod
    def ping_models(config_manager: ConfigManager, args) -> None:
        """
        测试模型连通性

        Args:
            config_manager: 配置管理器
            args: 命令行参数
        """
        # 如果指定了单个模型
        if args.provider and args.model:
            print(f"Ping 模型: {args.provider}/{args.model}")
            print("-" * 60)
            CLI.ping_single_model(args.provider, args.model)
            return

        # 测试所有启用的模型
        if args.all:
            models_config = CLI.load_models_config(config_manager)

            print("Ping 所有启用的模型...")
            print("=" * 60)

            total_count = 0
            success_count = 0
            failed_models = []
            failed_models_full = []  # 存储完整信息用于自动禁用

            # 遍历所有模型分类
            for category, models in models_config.items():
                for idx, model_config in enumerate(models):
                    if not model_config.get("enabled", False):
                        continue

                    total_count += 1
                    provider = model_config["provider"]
                    model_name = model_config["name"]

                    result = CLI.ping_model_connection(provider, model_name)

                    if result["success"]:
                        success_count += 1
                        print(f"✅ {provider}/{model_name}")
                    else:
                        error_msg = result.get("error", "Unknown error")
                        failed_models.append((provider, model_name, error_msg))
                        failed_models_full.append((category, idx, provider, model_name, error_msg))
                        print(f"❌ {provider}/{model_name}")
                        print(f"   Error: {error_msg}")

            print("=" * 60)
            print(f"Ping 完成: {success_count}/{total_count} 个模型可用")

            if failed_models:
                print(f"\n失败的模型 ({len(failed_models)}):")
                for provider, model_name, error in failed_models:
                    print(f"  - {provider}/{model_name}: {error}")

            # 如果指定了 --auto-disable，则禁用失败的模型
            if args.auto_disable and failed_models_full:
                print("\n" + "=" * 60)
                print("自动禁用失败的模型...")

                for category, idx, provider, model_name, error in failed_models_full:
                    models_config[category][idx]["enabled"] = False
                    print(f"   禁用: {provider}/{model_name}")

                # 保存更新后的配置
                models_file = config_manager.config.models_file
                with open(models_file, "w", encoding="utf-8") as f:
                    json.dump(models_config, f, indent=4, ensure_ascii=False)

                print(f"\n已更新配置文件: {models_file}")

            return

        # 如果没有指定任何选项，显示帮助
        print("请指定 ping 选项：")
        print("  --provider <name> --model <name>  Ping 指定模型")
        print("  --all                               Ping 所有启用的模型")
        print("\n示例:")
        print("  promptbench ping --provider xiaoai --model gpt-4")
        print("  promptbench ping --all")

    @staticmethod
    def ping_model_connection(provider: str, model_name: str) -> Dict[str, Any]:
        """
        Ping 模型连接（内部方法）

        Args:
            provider: 提供商名称
            model_name: 模型名称

        Returns:
            测试结果字典
        """
        client = ModelClient(provider)
        return client.test_connection(model_name)


if __name__ == "__main__":
    try:
        CLI.main()
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
