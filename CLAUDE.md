# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个**提示词迭代优化与多模型评估系统**，用于测试和优化生成公众号文章（退休语文老师胡家喜人设）的提示词质量。系统使用多个 LLM 提供商的模型生成内容，并通过规则引擎自动评估，最后生成优化后的下一版提示词。

## 常用命令

### 环境配置
```bash
# 安装依赖（使用 uv）
uv pip install openai

# 或直接运行脚本（uv 自动使用项目虚拟环境）
uv run evaluate_prompts.py
```

### 配置 API 密钥
复制 `.env.example` 为 `.env` 并配置相应的 API 密钥：
```bash
cp .env.example .env
```

`.env` 配置格式：
```
# 通用配置（所有 provider 兜底）
llm_base_url=<统一网关地址>
llm_api_key=<统一密钥>

# 或按 provider 分别配置
xiaoai_base_url=<特定provider地址>
xiaoai_api_key=<特定密钥>

# 提示词优化器配置（可选）
PROMPT_OPTIMIZER_MODEL=<优化器模型名>
PROMPT_OPTIMIZER_PROVIDER=<优化器provider>
```

### 运行评估
```bash
# 使用最新版提示词运行评估并生成新版本
uv run evaluate_prompts.py

# 基于指定版本运行评估
uv run evaluate_prompts.py --from-version 3

# 仅评估，不生成新版本提示词
uv run evaluate_prompts.py --skip-optimize

# 显示历史版本排名
uv run evaluate_prompts.py --ranking

# 重新评估某个历史版本（不生成新版本）
uv run evaluate_prompts.py --from-version 2 --skip-optimize
```

### 版本监控与对比

系统维护 `evaluations_history.json` 中央评估记录，支持：

- **版本排名**：按平均分排序，识别历史最佳版本
- **版本对比**：每次评估自动显示当前版本 vs 历史最佳版本的差异
- **回溯评估**：可基于任意历史版本重新评估，支持非线性迭代

**核心思路**：新版不一定更好，通过实际评分决定使用哪个版本。

## 架构说明

### 核心流程

```
1. 读取 models.json → 2. 加载最新版提示词 (prompts/vN.md)
                                      ↓
3. 遍历所有启用的模型 → 4. 生成文章 → 5. 保存原文 (outputs/vN/)
                                      ↓
6. 规则引擎评估 → 7. 汇总评估结果 → 8. 生成优化建议
                                      ↓
9. LLM 生成下一版提示词 → 10. 保存到 prompts/v{N+1}.md
```

### 关键模块

**evaluate_prompts.py**（主脚本）

| 模块 | 功能 | 关键函数 |
|------|------|----------|
| 环境加载 | 解析 `.env` 文件，支持 provider 特定配置和通用配置兜底 | `load_env_from_dotenv()`, `get_client()` |
| 版本管理 | 自动识别或指定 `prompts/v*.md` 版本 | `get_latest_prompt_file()`, `get_prompt_file_by_version()` |
| 模型调用 | 通过 OpenAI 兼容接口调用任意 provider 的模型 | `call_llm()`, `generate_with_model()` |
| 规则评估 | 基于关键词检测、结构分析、字数统计等规则评分 | `evaluate_article()` |
| 优化建议 | 根据多模型评估结果统计共性 | `summarize_evaluations()` |
| 提示词优化 | 使用 LLM 基于原提示词 + 评估建议生成纯净版下一版 | `optimize_prompt_via_llm()`, `build_optimized_prompt()` |
| 版本监控 | 维护评估历史、计算版本摘要、对比排名 | `update_evaluations_history()`, `show_version_ranking()`, `compare_with_best()` |

### 目录结构

```
.
├── evaluate_prompts.py     # 主脚本（~650 行）
├── import_history.py       # 历史数据导入工具
├── models.json             # 模型配置（按 provider 分类）
├── evaluations_history.json # 评估历史记录（自动生成）
├── .env                    # API 密钥配置（不提交）
├── .env.example            # 配置模板
├── prompts/                # 提示词版本库
│   ├── v1.md
│   ├── v2.md
│   └── v{N}.md             # 最新版本
└── outputs/                # 生成结果与评估报告
    ├── v1/
    │   ├── {provider}__{model}.txt
    │   └── evaluations.json
    └── v{N}/               # 最新版本输出
```

## 配置文件说明

### models.json 结构

```json
{
  "openai_models": [
    {"provider": "xiaoai", "name": "gpt-5.1-2025-11-13", "enabled": true, ...}
  ],
  "anthropic_models": [...],
  "google_models": [...],
  "deepseek_models": [...]
}
```

- `provider`: 对应 `.env` 中的配置前缀（如 `xiaoai_base_url`）
- `enabled`: 控制是否参与本次评估
- 统计价格字段可选

### 规则评估指标（evaluate_article:147-212）

| 指标 | 权重 | 检测规则 |
|------|------|----------|
| `intro_ok` | 2 | 首段含"老了"/"人过六十"/"退休"等关键词 |
| `has_classic` | 2 | 含《》或古人名/诗书名 |
| `has_3_points` | 3 | 中间段落数 ≥ 3 |
| `ending_concise` | 2 | 结尾段落 ≤ 80 字 |
| `in_length_range` | 1 | 总字数 1000-1200 |

### 提示词优化器

**默认行为**：调用 LLM 自动生成下一版提示词
- 模型：环境变量 `PROMPT_OPTIMIZER_MODEL`（默认 `gpt-5.4`）
- Provider：环境变量 `PROMPT_OPTIMIZER_PROVIDER`（默认 `openai`）
- 输出：纯净版提示词（不含优化建议或额外注释）

**失败处理**：若 LLM 调用失败，跳过生成新版本，不会添加冗余的"评估总结"内容

## 开发注意事项

### 添加新模型
在 `models.json` 对应的 provider 分类下添加对象：
```json
{
  "provider": "xiaoai",
  "name": "model-name",
  "enabled": true
}
```

### 添加新 Provider
1. 在 `.env` 中添加 `{provider}_base_url` 和 `{provider}_api_key`
2. 在 `models.json` 中添加 `{provider}_models` 数组
3. 在 `evaluate_prompts.py:355-360` 的 `provider_map` 中添加对应条目

### 修改评估规则
编辑 `evaluate_article()` 函数（第 147-212 行），规则是基于关键词和统计的，可快速调整权重阈值或新增检测维度。

### 修改测试关键词
当前硬编码关键词为 `["老了才明白", "儿女"]`（第 111 行），可根据需求修改。

## 版本迭代逻辑

1. **版本号自动递增**：基于 `prompts/` 下最大 `v*.md` 版本号 +1
2. **原提示词保护**：每次运行生成新版本，旧版本保留
3. **输出归档**：每次运行输出独立保存到 `outputs/v{N}/`，便于历史对比
4. **版本对比**：每次运行自动与历史最佳版本对比，识别是否退化
5. **非线性迭代**：通过 `--from-version` 可基于任意历史版本重新开始迭代

### 评估历史记录结构

```json
{
  "v1": {
    "version": 1,
    "timestamp": "2026-03-12T10:30:00",
    "prompt_path": "prompts/v1.md",
    "summary": {
      "avg_score": 8.09,
      "max_score": 10,
      "best_model": "claude-opus-4-6",
      "model_count": 11,
      "dimension_scores": {...}
    },
    "evaluations": [...]
  }
}
```
