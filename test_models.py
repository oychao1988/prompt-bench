#!/usr/bin/env python3
"""
模型实时连通性测试脚本
- 测试 models.json 中配置的模型的实时连通性
- 只做简单的连通测试，不做复杂的评估
- 可以单独运行，也可以在评估前自动运行
- 失败的模型可以自动禁用
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from evaluate_prompts import load_env_from_dotenv, load_models, get_client, call_llm

MODELS_FILE = BASE_DIR / "models.json"


def test_model_connection(
    provider: str,
    model_name: str,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    测试单个模型的连通性

    Args:
        provider: 提供商名称
        model_name: 模型名称
        verbose: 是否显示详细信息

    Returns:
        (是否成功, 消息)
    """
    try:
        if verbose:
            print(f"  测试 {provider}/{model_name}...", end=" ")

        # 测试环境变量和API密钥
        client = get_client(provider)
        if client is None:
            msg = "API 密钥未配置"
            if verbose:
                print(f"❌ {msg}")
            return False, msg

        # 测试简单请求
        response = call_llm(
            client=client,
            prompt="你好，这是一个测试。",
            model_name=model_name,
            max_tokens=50,
        )

        if response and len(response.strip()) > 0:
            if verbose:
                print("✅ 成功")
            return True, "成功"
        else:
            msg = "无响应"
            if verbose:
                print(f"❌ {msg}")
            return False, msg

    except Exception as e:
        msg = str(e)[:100]
        if verbose:
            print(f"❌ 失败: {msg}")
        return False, msg


def test_all_models(
    models_cfg: Dict[str, Any],
    verbose: bool = True,
    test_all: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """
    测试模型的连通性

    Args:
        models_cfg: 模型配置
        verbose: 是否显示详细信息
        test_all: 是否测试所有模型（包括未启用的）

    Returns:
        测试结果字典: {provider: {model_name: {success: bool, message: str, was_enabled: bool}}}
    """
    results = {}

    if verbose:
        print("=" * 70)
        print("模型实时连通性测试")
        if test_all:
            print("(强制测试所有模型，包括未启用的)")
        print("=" * 70)

    total = 0
    success_count = 0
    failed_count = 0

    for provider_group in ['openai_models', 'anthropic_models', 'google_models', 'deepseek_models']:
        provider = provider_group.replace('_models', '')
        models = models_cfg.get(provider_group, [])

        if not models:
            continue

        results[provider] = {}

        if verbose:
            print(f"\n【{provider.capitalize()}】")

        for model in models:
            model_name = model['name']
            enabled = model.get('enabled', False)

            if not test_all and not enabled:
                if verbose:
                    print(f"  ⏭️  跳过（未启用）: {model_name}")
                continue

            total += 1
            if verbose:
                status_marker = "[已启用]" if enabled else "[未启用]"
                print(f"  测试 {provider}/{model_name} {status_marker}...", end=" ")

            success, msg = test_model_connection(provider, model_name, verbose=False)

            if verbose:
                if success:
                    print("✅ 成功")
                else:
                    print(f"❌ 失败: {msg}")

            results[provider][model_name] = {
                'success': success,
                'message': msg,
                'was_enabled': enabled,
            }

            if success:
                success_count += 1
            else:
                failed_count += 1

    if verbose:
        print("\n" + "=" * 70)
        if test_all:
            print(f"测试完成: {total} 个模型（所有模型）")
        else:
            print(f"测试完成: {total} 个启用的模型")
        print(f"  ✅ 成功: {success_count}")
        print(f"  ❌ 失败: {failed_count}")
        print("=" * 70)

    return results


def update_models_config(
    models_cfg: Dict[str, Any],
    test_results: Dict[str, Dict[str, Any]],
    auto_disable: bool = False,
    auto_enable: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    更新模型配置

    Args:
        models_cfg: 原始模型配置
        test_results: 测试结果
        auto_disable: 是否自动禁用失败的模型
        auto_enable: 是否自动启用成功的模型
        verbose: 是否显示详细信息

    Returns:
        更新后的模型配置
    """
    updated_cfg = json.loads(json.dumps(models_cfg))  # 深拷贝

    changes_made = []

    for provider_group in ['openai_models', 'anthropic_models', 'google_models', 'deepseek_models']:
        provider = provider_group.replace('_models', '')
        provider_results = test_results.get(provider, {})

        for model in updated_cfg.get(provider_group, []):
            model_name = model['name']
            result = provider_results.get(model_name)

            if not result:
                continue

            success = result['success']
            was_enabled = result['was_enabled']

            if not success and (auto_disable or was_enabled):
                if model.get('enabled', False):
                    model['enabled'] = False
                    changes_made.append(f"禁用 {provider}/{model_name}")
            elif success and auto_enable and not was_enabled:
                if not model.get('enabled', False):
                    model['enabled'] = True
                    changes_made.append(f"启用 {provider}/{model_name}")

    if verbose and changes_made:
        print("\n已更新配置:")
        for change in changes_made:
            print(f"  - {change}")

    return updated_cfg


def show_available_models(
    models_cfg: Dict[str, Any],
    test_results: Dict[str, Dict[str, Any]],
) -> None:
    """
    显示可用模型列表
    """
    print("\n" + "=" * 70)
    print("可用模型列表")
    print("=" * 70)

    print("\n✅ 可正常调用:")
    for provider, models in test_results.items():
        available = [name for name, res in models.items() if res['success']]
        if available:
            print(f"\n  {provider.capitalize()}:")
            for name in available:
                print(f"    - {name}")

    print("\n❌ 调用失败:")
    for provider, models in test_results.items():
        failed = [name for name, res in models.items() if not res['success']]
        if failed:
            print(f"\n  {provider.capitalize()}:")
            for name in failed:
                print(f"    - {name} ({test_results[provider][name]['message']})")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="模型实时连通性测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试所有启用的模型（默认行为）
  %(prog)s

  # 强制测试所有模型（包括未启用的），成功者开启、失败则关闭
  %(prog)s --force-test

  # 静默模式，只输出结果
  %(prog)s --quiet

  # 测试启用的模型并禁用失败的
  %(prog)s --auto-disable

  # 测试启用的模型并启用成功的（如果之前未启用）
  %(prog)s --auto-enable

  # 只显示可用模型列表（不测试）
  %(prog)s --list

  # 测试后不更新配置
  %(prog)s --no-update
        """,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="测试所有模型（包括未启用的）",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，不显示详细输出",
    )
    parser.add_argument(
        "--auto-disable",
        action="store_true",
        help="自动禁用失败的模型（默认行为）",
    )
    parser.add_argument(
        "--auto-enable",
        action="store_true",
        help="自动启用成功的模型（用于强制测试模式）",
    )
    parser.add_argument(
        "--force-test",
        action="store_true",
        help="强制测试所有模型（包括未启用的），成功者开启、失败则关闭",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="只显示可用模型列表",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="不更新 models.json 配置",
    )

    args = parser.parse_args()

    # 加载环境变量
    load_env_from_dotenv()

    # 加载模型配置
    models_cfg = {}
    if MODELS_FILE.exists():
        with MODELS_FILE.open("r", encoding="utf-8") as f:
            models_cfg = json.load(f)

    if args.list:
        # 只显示启用的模型列表（不进行实际测试）
        print("=" * 70)
        print("当前启用的模型（配置文件状态）")
        print("=" * 70)
        for provider_group in ['openai_models', 'anthropic_models', 'google_models', 'deepseek_models']:
            provider = provider_group.replace('_models', '')
            models = models_cfg.get(provider_group, [])
            if models:
                print(f"\n【{provider.capitalize()}】")
                for model in models:
                    if model.get('enabled', False):
                        print(f"  - {model['name']}")
        return 0

    # 处理强制测试模式
    test_all = args.force_test
    auto_enable = args.auto_enable or args.force_test
    auto_disable = args.auto_disable or args.force_test

    # 测试模型
    test_results = test_all_models(
        models_cfg,
        verbose=not args.quiet,
        test_all=test_all,
    )

    # 显示结果
    if not args.quiet:
        show_available_models(models_cfg, test_results)

    # 更新配置
    if not args.no_update:
        updated_cfg = update_models_config(
            models_cfg=models_cfg,
            test_results=test_results,
            auto_disable=auto_disable,
            auto_enable=auto_enable,
            verbose=not args.quiet,
        )

        if updated_cfg != models_cfg:
            with MODELS_FILE.open("w", encoding="utf-8") as f:
                json.dump(updated_cfg, f, ensure_ascii=False, indent=4)
            if not args.quiet:
                print(f"\n已更新: {MODELS_FILE}")

    # 返回状态码
    any_failed = any(
        not result['success']
        for provider_results in test_results.values()
        for result in provider_results.values()
    )

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
