# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**模块化提示词系统与多模型评估工具**，用于生成和优化公众号文章（退休语文老师胡家喜人设）。

**核心特性**：
- 模块化提示词（人设、结构、标题分离）
- 单篇/批量生成模式
- 多模型评估与规则引擎
- 支持仿写爆文快速起号

**技术栈**：Python + OpenAI SDK + 规则引擎评估

详细使用说明见 [USAGE.md](USAGE.md)

## 快速开始

```bash
# 1. 配置环境
cp .env.example .env
# 编辑 .env 添加 API 密钥

# 2. 安装依赖
pip install openai

# 3. 生成文章
python evaluate_prompts.py --generate "和老伴吵了一辈子，老了才发现"

# 4. 批量生成（日更）
python evaluate_prompts.py --batch topic1 topic2 topic3

# 5. 查看帮助
python evaluate_prompts.py --help
```

## 架构说明

### 模块化提示词系统

**文档结构**：
```
prompts/
├── v5_base.md              # 基础提示词（人设+风格+内容方向）
├── structures_library.md   # 结构库（8种文章结构）
└── titles_library.md       # 标题库（10种标题类型）
```

**拼接逻辑**：
```
v5_base.md + structures_library.md + 选题 + 标题 → 完整提示词
```

### 关键模块

**evaluate_prompts.py**（主脚本，~1400行）

| 模块 | 关键函数 | 行号参考 |
|------|----------|----------|
| 环境加载 | `load_env_from_dotenv()`, `get_client()` | ~40-70 |
| 提示词构建 | `load_base_prompt()`, `load_structure()`, `build_prompt()` | ~116-286 |
| 标题生成 | `generate_title_from_topic()` | ~289-318 |
| 模型调用 | `call_llm()`, `generate_with_model()` | ~324-397 |
| 规则评估 | `evaluate_article()` | ~462-587 |
| 版本监控 | `update_evaluations_history()`, `show_version_ranking()` | ~707-787 |
| 单篇生成 | `run_single_generation()` | ~905-998 |
| 批量生成 | `run_batch_generation()` | ~1001-1104 |

### 目录结构

```
.
├── evaluate_prompts.py     # 主脚本
├── models.json             # 模型配置（provider + enabled）
├── CLAUDE.md               # 本文件（开发指南）
├── USAGE.md                # 完整使用说明
├── prompts/
│   ├── v5_base.md          # 基础提示词
│   ├── structures_library.md
│   └── titles_library.md
└── outputs/                # 生成结果（不提交）
```

## 配置说明

### models.json

```json
{
  "openai_models": [
    {"provider": "xiaoai", "name": "gpt-5.1-2025-11-13", "enabled": true}
  ]
}
```

- `provider`: 对应 `.env` 中的配置前缀
- `enabled`: 控制是否参与生成/评估

### .env 配置

```
# 通用配置（兜底）
llm_base_url=<网关地址>
llm_api_key=<密钥>

# 或按 provider 配置
xiaoai_base_url=<地址>
xiaoai_api_key=<密钥>
```

## 规则评估指标

| 指标 | 权重 | 检测规则 |
|------|------|----------|
| `intro_ok` | 2 | 首段含"老了"/"人过六十"/"退休" |
| `has_classic` | 2 | 含《》或古人名/诗书名 |
| `has_3_points` | 1 | 中间段落数 ≥ 3 |
| `ending_good` | 2 | 结尾 ≤ 80 字或有总结词 |
| `in_length_range` | 2 | 字数 1000-1200 |

## 开发注意事项

### 添加新结构类型
编辑 `prompts/structures_library.md`，添加新结构模板。

### 添加新标题类型
编辑 `prompts/titles_library.md`，添加新标题模板。

### 修改评估规则
编辑 `evaluate_article()` 函数（~462-587行），调整权重或新增检测维度。

### 添加新 Provider
1. 在 `.env` 添加 `{provider}_base_url` 和 `{provider}_api_key`
2. 在 `models.json` 添加 `{provider}_models` 数组

## 版本迭代

- **版本号**：`prompts/v*.md` 中的数字
- **自动递增**：评估模式自动生成下一版本
- **非线性迭代**：`--evaluate --from-version N` 基于历史版本重新开始

## 可用结构类型

| 结构类型 | 参数值 | 适用场景 |
|---------|--------|----------|
| 场景感悟式 | `场景感悟式` | 通用型 |
| 今昔对比式 | `今昔对比式` | 衰老反思 |
| 对话展开式 | `对话展开式` | 人物对话 |
| 三段递进式 | `三段递进式` | 深度思考 |
| 一事一议式 | `一事一议式` | 具体事件 |
| 问答体 | `问答体` | 问答互动 |
| 书信体 | `书信体` | 书信倾诉 |
| 日记体 | `日记体` | 日记记录 |

详细说明见 `prompts/structures_library.md`

