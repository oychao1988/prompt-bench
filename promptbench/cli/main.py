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
    def get_api_format_from_category(category_name: str) -> str:
        """
        根据模型分类名称确定 API 格式

        直接根据 models.json 中的分类键名判断，不依赖 provider 名称。

        Args:
            category_name: models.json 中的分类名称（如 "openai_models", "anthropic_models"）

        Returns:
            API 格式字符串（"openai" 或 "anthropic"）

        分类映射规则：
        - anthropic_models → anthropic
        - 其他所有分类（openai_models、google_models、deepseek_models等）→ openai
        """
        # 提取分类基础名称（移除 _models 后缀）
        if category_name.endswith("_models"):
            base_name = category_name[:-7]  # 移除 "_models" 后缀
        else:
            base_name = category_name

        # 根据分类名称确定 API 格式
        # 只有 anthropic 使用 Anthropic API 格式
        # 其他所有分类（openai、google、deepseek 等）都使用 OpenAI 兼容格式
        if base_name == "anthropic":
            return "anthropic"
        else:
            return "openai"

    @staticmethod
    def find_model_category(models_config: Dict, provider: str, model_name: str) -> str:
        """
        在 models_config 中查找指定模型所属的分类
        
        Args:
            models_config: 模型配置字典
            provider: 提供商名称
            model_name: 模型名称
            
        Returns:
            分类名称
        """
        for category, models in models_config.items():
            for model in models:
                if model.get("provider") == provider and model.get("name") == model_name:
                    return category
        return "unknown"

    @staticmethod
    def parse_args():
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

        # 对比命令
        compare_parser = subparsers.add_parser(
            "compare", help="对比评估结果"
        )
        compare_parser.add_argument(
            "--type", "-t", type=str, choices=["horizontal", "vertical"],
            help="对比类型：horizontal（横向对比）或 vertical（纵向对比）"
        )
        compare_parser.add_argument(
            "--version", "-v", type=int,
            help="指定版本号（用于横向对比）"
        )
        compare_parser.add_argument(
            "--model", "-m", type=str,
            help="指定模型名称（用于纵向对比）"
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
        elif args.command == "show":
            CLI.show_version(config_manager, args)
        elif args.command == "ping":
            CLI.ping_models(config_manager, args)
        elif args.command == "compare":
            CLI.compare_results(config_manager, args)
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

        # 5. 并行评估（带智能重试）
        import time

        retry_candidates = []

        # 第一轮：并发执行所有评估
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_model = {}

            for provider, model_name in enabled_models:
                print(f"正在调用 {provider}/{model_name}...")

                future = executor.submit(
                    CLI._evaluate_single_model,
                    provider, model_name, prompt, version, models_config
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
                        # 添加到重试列表
                        retry_candidates.append((provider, model_name))

                except Exception as e:
                    error_msg = str(e)
                    print(f"❌ {provider}/{model_name} 出错: {error_msg}")

                    # 检查是否可重试
                    if CLI.is_retryable_error(error_msg):
                        print(f"   ⏳ 检测到并发限制，将重试")
                        retry_candidates.append((provider, model_name))

        # 第二轮：重试失败的模型（顺序执行）
        if retry_candidates:
            print(f"\n⏳ 正在重试 {len(retry_candidates)} 个失败的模型...")
            print("-" * 60)

            for provider, model_name in retry_candidates:
                print(f"🔄 重试 {provider}/{model_name}...")

                # 等待一段时间再重试
                time.sleep(2)

                try:
                    result = CLI._evaluate_single_model(
                        provider, model_name, prompt, version, models_config
                    )

                    if result:
                        all_results.append(result)
                        print(f"✅ {provider}/{model_name} (重试成功)")
                    else:
                        print(f"❌ {provider}/{model_name} (重试失败)")

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
    def _evaluate_single_model(provider, model_name, prompt, version, models_config=None):
        """
        评估单个模型

        Args:
            provider: 提供商名称
            model_name: 模型名称
            prompt: 提示词
            version: 版本号
            models_config: 模型配置字典（用于确定 API 格式）

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
            # 确定 API 格式
            api_format = "openai"  # 默认格式
            if models_config:
                category = CLI.find_model_category(models_config, provider, model_name)
                api_format = CLI.get_api_format_from_category(category)
            
            # 调用模型
            client = ModelClient(provider, api_format)

            # 设置默认 topic（如果没有提供，使用通用主题）
            # 这里使用一个通用的家庭/婚姻主题作为默认值
            default_topic = "一个35岁全职妈妈在婚姻中感到孤独和委屈，丈夫长期缺席家庭责任"

            # 设置 max_tokens 限制（约等于 1500-1800 中文字符）
            # 1 token ≈ 0.75-1 个中文字符，所以 2000 tokens ≈ 1500-2000 字
            max_tokens = 2000

            content = client.call(
                model_name=model_name,
                prompt=prompt,
                topic=default_topic,
                max_tokens=max_tokens,
                temperature=0.8
            )

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
        显示版本排名

        Args:
            config_manager: 配置管理器
            args: 命令行参数
        """
        from pathlib import Path

        history_file = Path("evaluations_history.json")

        if not history_file.exists():
            print("❌ 未找到评估历史记录")
            print("   请先运行评估: promptbench evaluate")
            return

        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

        if not history:
            print("❌ 评估历史记录为空")
            return

        # 提取版本信息并按平均分排序
        version_rankings = []
        for version_key, version_data in history.items():
            summary = version_data.get("summary", {})
            version_rankings.append({
                "version": version_data.get("version", int(version_key[1:])),
                "avg_total_score": summary.get("avg_total_score", 0),
                "avg_rule_score": summary.get("avg_rule_score", 0),
                "avg_ai_score": summary.get("avg_ai_score", 0),
                "avg_detection_score": summary.get("avg_detection_score", 0),
                "best_model": summary.get("best_model", "N/A"),
                "model_count": summary.get("model_count", 0),
                "timestamp": version_data.get("timestamp", "")
            })

        # 按平均总分降序排序
        version_rankings.sort(key=lambda x: x["avg_total_score"], reverse=True)

        # 显示排名
        limit = min(args.limit, len(version_rankings))

        print(f"\n{'='*100}")
        print(f"提示词版本排名（前 {limit} 个）")
        print(f"{'='*100}\n")

        print(f"{'排名':<6} {'版本':<8} {'平均总分':<12} {'规则分':<10} {'AI分':<10} {'检测分':<10} {'最佳模型':<25} {'模型数':<8}")
        print("-" * 100)

        for idx, version_info in enumerate(version_rankings[:limit], 1):
            print(f"{idx:<6} v{version_info['version']:<7} "
                  f"{version_info['avg_total_score']:<12.2f} "
                  f"{version_info['avg_rule_score']:<10.2f} "
                  f"{version_info['avg_ai_score']:<10.2f} "
                  f"{version_info['avg_detection_score']:<10.2f} "
                  f"{version_info['best_model']:<25} "
                  f"{version_info['model_count']:<8}")

        print(f"\n总计：{len(version_rankings)} 个版本")

        # 统计信息
        if version_rankings:
            best_version = version_rankings[0]
            worst_version = version_rankings[-1]
            avg_score = sum(v["avg_total_score"] for v in version_rankings) / len(version_rankings)

            print(f"\n统计信息：")
            print(f"  最佳版本：v{best_version['version']} ({best_version['avg_total_score']:.2f}分)")
            print(f"  最差版本：v{worst_version['version']} ({worst_version['avg_total_score']:.2f}分)")
            print(f"  整体平均：{avg_score:.2f}分")
            print(f"  版本跨度：v{min(v['version'] for v in version_rankings)} → v{max(v['version'] for v in version_rankings)}")

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

        Args:
            config_manager: 配置管理器
            args: 命令行参数
        """
        from pathlib import Path
        from datetime import datetime

        version = args.version
        history_file = Path("evaluations_history.json")

        if not history_file.exists():
            print("❌ 未找到评估历史记录")
            print("   请先运行评估: promptbench evaluate")
            return

        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

        version_key = f"v{version}"
        if version_key not in history:
            print(f"❌ 未找到版本 v{version} 的评估记录")
            print(f"   可用版本：{', '.join(sorted([k for k in history.keys() if k.startswith('v')]))}")
            return

        version_data = history[version_key]
        summary = version_data.get("summary", {})
        evaluations = version_data.get("evaluations", [])

        print(f"\n{'='*100}")
        print(f"版本 v{version} 详细信息")
        print(f"{'='*100}\n")

        # 基本信息
        print(f"📁 提示词文件：{version_data.get('prompt_path', 'N/A')}")
        timestamp = version_data.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                print(f"🕐 评估时间：{dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except:
                print(f"🕐 评估时间：{timestamp}")
        print()

        # 评估摘要
        print(f"📊 评估摘要：")
        print("-" * 60)
        print(f"  评估模型数：{summary.get('model_count', 0)} 个")
        print(f"  平均总分：{summary.get('avg_total_score', 0):.2f}/10")
        print(f"  平均规则分：{summary.get('avg_rule_score', 0):.2f}/3")
        print(f"  平均 AI 分：{summary.get('avg_ai_score', 0):.2f}/3")
        print(f"  平均检测分：{summary.get('avg_detection_score', 0):.2f}/4")
        print(f"  最高分：{summary.get('max_total_score', 0):.2f}")
        print(f"  最低分：{summary.get('min_total_score', 0):.2f}")
        print(f"  最佳模型：{summary.get('best_model', 'N/A')}")
        print()

        # 模型表现排名
        if evaluations:
            # 按总分排序
            sorted_evals = sorted(evaluations, key=lambda x: x.get("total_score", 0), reverse=True)

            print(f"🏆 模型表现排名：")
            print("-" * 100)
            print(f"{'排名':<6} {'模型':<35} {'总分':<10} {'规则分':<10} {'AI分':<10} {'检测分':<10} {'字数':<10}")
            print("-" * 100)

            for idx, eval_data in enumerate(sorted_evals, 1):
                provider = eval_data.get("provider", "")
                model = eval_data.get("model", "Unknown")
                model_name = f"{provider}/{model}" if provider else model
                total_score = eval_data.get("total_score", 0)
                rule_score = eval_data.get("rule_score", 0)
                ai_score = eval_data.get("ai_score", 0)
                detection_score = eval_data.get("detection_score", 0)
                chars = eval_data.get("chars", 0)

                print(f"{idx:<6} {model_name:<35} {total_score:<10.2f} {rule_score:<10.2f} "
                      f"{ai_score:<10.2f} {detection_score:<10.2f} {chars:<10}")

            print()

        # 输出文件
        output_dir = Path(f"outputs/v{version}")
        if output_dir.exists():
            output_files = list(output_dir.glob("*.txt"))
            print(f"📄 输出文件（{len(output_files)} 个）：")
            for file in sorted(output_files):
                file_size = file.stat().st_size
                print(f"  - {file.name} ({file_size} 字节)")
        else:
            print(f"📄 输出目录不存在：{output_dir}")

        print(f"\n{'='*100}\n")

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
    def ping_single_model(provider: str, model_name: str, models_config: Dict = None) -> None:
        """
        测试单个模型的连通性

        Args:
            provider: 提供商名称
            model_name: 模型名称
            models_config: 模型配置字典（用于确定 API 格式）
        """
        # 确定 API 格式
        api_format = "openai"  # 默认格式
        if models_config:
            category = CLI.find_model_category(models_config, provider, model_name)
            api_format = CLI.get_api_format_from_category(category)
        
        client = ModelClient(provider, api_format)
        result = client.test_connection(model_name)

        if result["success"]:
            print(f"✅ {provider}/{model_name}")
            print(f"   Base URL: {result.get('base_url', 'N/A')}")
            print(f"   Response: {result.get('response', 'N/A')[:50]}...")
        else:
            print(f"❌ {provider}/{model_name}")
            print(f"   Error: {result.get('error', 'Unknown error')}")

    @staticmethod
    def is_retryable_error(error_msg: str) -> bool:
        """
        判断错误是否可重试

        Args:
            error_msg: 错误信息

        Returns:
            是否可重试
        """
        retryable_patterns = [
            "429",  # HTTP 429 Too Many Requests
            "Concurrent request limit",
            "并发",
            "rate limit",
            "too many requests",
            "overload",
        ]
        error_lower = error_msg.lower()
        return any(pattern.lower() in error_lower for pattern in retryable_patterns)

    @staticmethod
    def ping_models(config_manager: ConfigManager, args) -> None:
        """
        测试模型连通性（支持并发和智能重试）

        Args:
            config_manager: 配置管理器
            args: 命令行参数
        """
        import time
        import concurrent.futures

        # 如果指定了单个模型
        if args.provider and args.model:
            print(f"Ping 模型: {args.provider}/{args.model}")
            print("-" * 60)
            # 加载模型配置以确定 API 格式
            models_config = CLI.load_models_config(config_manager)
            CLI.ping_single_model(args.provider, args.model, models_config)
            return

        # 测试所有启用的模型
        if args.all:
            models_config = CLI.load_models_config(config_manager)

            print("Ping 所有启用的模型...")
            print("=" * 60)

            # 收集所有启用的模型
            models_to_ping = []
            for category, models in models_config.items():
                for idx, model_config in enumerate(models):
                    if model_config.get("enabled", False):
                        models_to_ping.append({
                            "category": category,
                            "idx": idx,
                            "provider": model_config["provider"],
                            "name": model_config["name"]
                        })

            total_count = len(models_to_ping)
            success_count = 0
            failed_models = []
            failed_models_full = []

            # 第一轮：并发执行所有 ping
            retry_candidates = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                future_to_model = {}

                for model_info in models_to_ping:
                    future = executor.submit(
                        CLI.ping_model_connection,
                        model_info["provider"],
                        model_info["name"],
                        models_config
                    )
                    future_to_model[future] = model_info

                for future in concurrent.futures.as_completed(future_to_model):
                    model_info = future_to_model[future]
                    provider = model_info["provider"]
                    model_name = model_info["name"]

                    try:
                        result = future.result()
                        if result["success"]:
                            success_count += 1
                            print(f"✅ {provider}/{model_name}")
                        else:
                            error_msg = result.get("error", "Unknown error")
                            print(f"❌ {provider}/{model_name}")

                            # 检查是否可重试
                            if CLI.is_retryable_error(error_msg):
                                print(f"   ⏳ {error_msg} (将重试)")
                                retry_candidates.append({
                                    "category": model_info["category"],
                                    "idx": model_info["idx"],
                                    "provider": provider,
                                    "name": model_name,
                                    "error": error_msg
                                })
                            else:
                                print(f"   Error: {error_msg}")
                                failed_models.append((provider, model_name, error_msg))
                                failed_models_full.append((
                                    model_info["category"],
                                    model_info["idx"],
                                    provider,
                                    model_name,
                                    error_msg
                                ))

                    except Exception as e:
                        error_msg = str(e)
                        print(f"❌ {provider}/{model_name}")
                        print(f"   Error: {error_msg}")
                        failed_models.append((provider, model_name, error_msg))
                        failed_models_full.append((
                            model_info["category"],
                            model_info["idx"],
                            provider,
                            model_name,
                            error_msg
                        ))

            # 第二轮：重试可重试的模型（顺序执行以避免并发冲突）
            if retry_candidates:
                print(f"\n⏳ 正在重试 {len(retry_candidates)} 个因并发限制失败的模型...")
                print("-" * 60)

                for retry_info in retry_candidates:
                    provider = retry_info["provider"]
                    model_name = retry_info["name"]
                    error_msg = retry_info["error"]

                    print(f"🔄 重试 {provider}/{model_name}...")

                    # 等待一段时间再重试
                    time.sleep(2)

                    result = CLI.ping_model_connection(provider, model_name, models_config)

                    if result["success"]:
                        success_count += 1
                        print(f"✅ {provider}/{model_name} (重试成功)")
                    else:
                        new_error = result.get("error", "Unknown error")
                        print(f"❌ {provider}/{model_name}")
                        print(f"   Error: {new_error}")
                        failed_models.append((provider, model_name, new_error))
                        failed_models_full.append((
                            retry_info["category"],
                            retry_info["idx"],
                            provider,
                            model_name,
                            new_error
                        ))

            print("=" * 60)
            print(f"Ping 完成: {success_count}/{total_count} 个模型可用")

            if failed_models:
                print(f"\n失败的模型 ({len(failed_models)}):")
                for provider, model_name, error in failed_models:
                    # 只显示错误信息的前100个字符
                    error_short = error[:100] + "..." if len(error) > 100 else error
                    print(f"  - {provider}/{model_name}: {error_short}")

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
    def ping_model_connection(provider: str, model_name: str, models_config: Dict = None) -> Dict[str, Any]:
        """
        Ping 模型连接（内部方法）

        Args:
            provider: 提供商名称
            model_name: 模型名称
            models_config: 模型配置字典（用于确定 API 格式）

        Returns:
            测试结果字典
        """
        # 确定 API 格式
        api_format = "openai"  # 默认格式
        if models_config:
            category = CLI.find_model_category(models_config, provider, model_name)
            api_format = CLI.get_api_format_from_category(category)
        
        client = ModelClient(provider, api_format)
        return client.test_connection(model_name)

    @staticmethod
    def compare_results(config_manager, args) -> None:
        """
        对比评估结果

        Args:
            config_manager: 配置管理器
            args: 命令行参数
        """
        import json
        from pathlib import Path

        if args.type == "horizontal":
            # 横向对比：同一版本的不同模型
            if not args.version:
                print("错误：横向对比需要指定 --version 参数")
                print("示例：promptbench compare --type horizontal --version 4")
                return

            version = args.version
            eval_file = config_manager.config.outputs_dir / f"v{version}" / "evaluations.json"

            if not eval_file.exists():
                print(f"错误：未找到版本 {version} 的评估结果：{eval_file}")
                return

            with open(eval_file, "r", encoding="utf-8") as f:
                results = json.load(f)

            CLI._show_horizontal_comparison(results, version)

        elif args.type == "vertical":
            # 纵向对比：同一模型的不同版本
            if not args.model:
                print("错误：纵向对比需要指定 --model 参数")
                print("示例：promptbench compare --type vertical --model deepseek-v3.2-exp")
                return

            model = args.model
            outputs_dir = config_manager.config.outputs_dir

            # 收集所有版本的评估结果
            version_results = {}

            for version_dir in sorted(outputs_dir.iterdir()):
                if version_dir.name.startswith("v"):
                    version = int(version_dir.name[1:])
                    eval_file = version_dir / "evaluations.json"

                    if eval_file.exists():
                        with open(eval_file, "r", encoding="utf-8") as f:
                            results = json.load(f)

                        # 查找指定模型的结果
                        found = False
                        for result in results:
                            # 兼容新旧格式
                            result_model = result.get("model", "")
                            provider = result.get("provider", "")

                            # 检查是否在顶层
                            if model in result_model:
                                version_results[version] = result
                                found = True
                                break

                            # 检查是否嵌套在 evaluation 中（旧格式）
                            if not found:
                                evaluation = result.get("evaluation", {})
                                eval_model = evaluation.get("model", "")
                                if model in eval_model:
                                    version_results[version] = result
                                    found = True
                                    break

            if not version_results:
                print(f"错误：未找到模型 '{model}' 的任何评估结果")
                return

            CLI._show_vertical_comparison(version_results, model)

        else:
            print("请指定对比类型：")
            print("  --type horizontal  横向对比（同一版本的不同模型）")
            print("  --type vertical    纵向对比（同一模型的不同版本）")
            print("\n示例：")
            print("  promptbench compare --type horizontal --version 4")
            print("  promptbench compare --type vertical --model deepseek-v3.2-exp")

    @staticmethod
    def _show_horizontal_comparison(results: list, version: int) -> None:
        """
        显示横向对比结果

        Args:
            results: 评估结果列表
            version: 版本号
        """
        print(f"\n{'='*80}")
        print(f"版本 {version} - 横向对比（不同模型的表现）")
        print(f"{'='*80}\n")

        # 按总分排序
        sorted_results = sorted(results, key=lambda x: x.get("total_score", 0), reverse=True)

        # 表头
        print(f"{'排名':<4} {'模型':<35} {'总分':<8} {'规则分':<8} {'AI分':<8} {'检测分':<8} {'字数':<8} {'人类率':<8}")
        print("-" * 100)

        for idx, result in enumerate(sorted_results, 1):
            model = result.get("model", "Unknown")
            provider = result.get("provider", "")
            total_score = result.get("total_score", 0)
            rule_score = result.get("rule_score", 0)
            ai_score = result.get("ai_score", 0)
            detection_score = result.get("detection_score", 0)
            chars = result.get("chars", 0)
            human_pct = result.get("detection_details", {}).get("human_percentage", 0)

            model_name = f"{provider}/{model}" if provider else model

            print(f"{idx:<4} {model_name:<35} {total_score:<8.2f} {rule_score:<8.2f} {ai_score:<8.2f} {detection_score:<8.2f} {chars:<8} {human_pct:<8}%")

        print(f"\n总计：{len(results)} 个模型")

        # 统计信息
        avg_total = sum(r.get("total_score", 0) for r in results) / len(results)
        max_total = max(r.get("total_score", 0) for r in results)
        min_total = min(r.get("total_score", 0) for r in results)

        print(f"平均分：{avg_total:.2f}")
        print(f"最高分：{max_total:.2f}")
        print(f"最低分：{min_total:.2f}")

    @staticmethod
    def _show_vertical_comparison(version_results: dict, model: str) -> None:
        """
        显示纵向对比结果

        Args:
            version_results: 版本号到评估结果的映射
            model: 模型名称
        """
        print(f"\n{'='*80}")
        print(f"模型 {model} - 纵向对比（不同版本的表现）")
        print(f"{'='*80}\n")

        if not version_results:
            return

        # 按版本号排序
        sorted_versions = sorted(version_results.items())

        # 表头
        print(f"{'版本':<8} {'总分':<8} {'规则分':<8} {'AI分':<8} {'检测分':<8} {'字数':<8} {'人类率':<8} {'段落数':<8}")
        print("-" * 100)

        for version, result in sorted_versions:
            # 兼容新旧格式
            if "total_score" in result:
                # 新格式
                total_score = result.get("total_score", 0)
                rule_score = result.get("rule_score", 0)
                ai_score = result.get("ai_score", 0)
                detection_score = result.get("detection_score", 0)
                chars = result.get("chars", 0)
                detection_details = result.get("detection_details", {})
                human_pct = detection_details.get("human_percentage", 0)
                paragraphs = result.get("paragraphs", 0)
            else:
                # 旧格式（嵌套在 evaluation 中）
                evaluation = result.get("evaluation", {})
                total_score = evaluation.get("total_score", 0)
                rule_score = evaluation.get("rule_score", 0)
                ai_score = evaluation.get("ai_score", 0)
                detection_score = evaluation.get("detection_score", 0)
                chars = evaluation.get("chars", 0)
                detection_result = result.get("detection_result", {})
                human_pct = detection_result.get("human_percentage", 0)
                paragraphs = evaluation.get("paragraphs", 0)

            print(f"v{version:<7} {total_score:<8.2f} {rule_score:<8.2f} {ai_score:<8.2f} {detection_score:<8.2f} {chars:<8} {human_pct:<8}% {paragraphs:<8}")

        # 统计信息
        scores = [r.get("total_score", 0) for r in version_results.values()]
        if scores:
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            best_version = max(version_results.items(), key=lambda x: x[1].get("total_score", 0))[0]

            print(f"\n平均分：{avg_score:.2f}")
            print(f"最高分：{max_score:.2f} (v{best_version})")
            print(f"最低分：{min_score:.2f}")
            print(f"版本跨度：v{min(version_results.keys())} → v{max(version_results.keys())}")


if __name__ == "__main__":
    try:
        CLI.main()
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
