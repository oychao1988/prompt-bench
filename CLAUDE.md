# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个**模块化提示词系统与多模型评估工具**，用于生成和优化公众号文章（退休语文老师胡家喜人设）。

**核心功能**：
1. **模块化提示词系统**：人设、结构、标题分离，支持灵活组合
2. **单篇/批量生成**：支持单篇文章生成和批量生成（日更场景）
3. **多模型评估**：使用多个 LLM 提供商的模型生成内容并自动评估
4. **仿写爆文**：支持自定义结构，便于仿写低粉爆文快速起号
5. **版本迭代**：基于评估结果自动生成优化版提示词

**技术栈**：Python + OpenAI SDK + 规则引擎评估

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

### 单篇生成（新功能）
```bash
# 基础用法：使用默认结构生成一篇文章
python evaluate_prompts.py --generate "和老伴吵了一辈子，老了才发现"

# 指定结构类型
python evaluate_prompts.py --generate "女儿说挺好的" --structure 对话展开式

# 自定义标题并保存到文件
python evaluate_prompts.py --generate "和老伴吵了一辈子" \
  --title "《老伴炖的那碗汤，我喝了一辈子》" \
  --output outputs/article.md

# 指定模型
python evaluate_prompts.py --generate "半夜醒来才承认老了" \
  --provider deepseek --model deepseek-v3.1
```

### 批量生成（日更用）
```bash
# 批量生成多篇文章
python evaluate_prompts.py --batch \
  "和老伴吵了一辈子，老了才发现" \
  "女儿说挺好的，我知道她在硬撑" \
  "半夜醒来，我才真正承认自己老了"

# 指定结构循环和输出目录
python evaluate_prompts.py --batch topic1 topic2 topic3 \
  --structures 场景感悟式 对话展开式 今昔对比式 \
  --batch-output outputs/week1/
```

### 仿写爆文
```bash
# 使用自定义结构仿写爆文
python evaluate_prompts.py --generate "老伴住院那周，我才明白了一个道理" \
  --custom-structure '开头：老伴住院那周，我一个人在家
中间：三个场景
  - 场景1：一个人做饭，不知道做什么
  - 场景2：晚上家里太安静，睡不着
  - 场景3：想打电话给女儿，又怕她担心
结尾：一句劝慰'
```

### 运行评估（旧版，向后兼容）
```bash
# 使用最新版提示词运行评估并生成新版本
python evaluate_prompts.py --evaluate

# 基于指定版本运行评估
python evaluate_prompts.py --evaluate --from-version 3

# 仅评估，不生成新版本提示词
python evaluate_prompts.py --evaluate --skip-optimize

# 显示历史版本排名
python evaluate_prompts.py --ranking

# 重新评估某个历史版本（不生成新版本）
python evaluate_prompts.py --evaluate --from-version 2 --skip-optimize
```

### 版本监控与对比

系统维护 `evaluations_history.json` 中央评估记录，支持：

- **版本排名**：按平均分排序，识别历史最佳版本
- **版本对比**：每次评估自动显示当前版本 vs 历史最佳版本的差异
- **回溯评估**：可基于任意历史版本重新评估，支持非线性迭代

**核心思路**：新版不一定更好，通过实际评分决定使用哪个版本。

## 架构说明

### 模块化提示词系统

**文档结构**：
```
prompts/
├── v5_base.md              # 基础提示词（人设+风格+内容方向）
├── structures_library.md   # 结构库（8种文章结构模板）
└── titles_library.md       # 标题库（10种标题类型模板）
```

**拼接逻辑**：
```
v5_base.md（人设+风格） + structures_library.md（结构） + 选题 + 标题 → 完整提示词
```

**优势**：
- 人设、结构、标题分离，便于独立维护
- 支持灵活组合（同一人设 × 8种结构 × 10种标题）
- 支持自定义结构（仿写爆文）
- 便于 A/B 测试不同结构效果

### 核心流程（生成模式）

```
1. 读取 models.json → 2. 加载基础提示词 (v5_base.md)
                                      ↓
3. 加载指定结构 (structures_library.md)
                                      ↓
4. 拼接完整提示词 → 5. 调用模型生成 → 6. 保存文章
                                      ↓
7. 规则引擎评估 → 8. 显示评估结果
```

### 核心流程（评估模式）

```
1. 读取 models.json → 2. 加载完整提示词 (prompts/vN.md)
                                      ↓
3. 遍历所有启用的模型 → 4. 生成文章 → 5. 保存原文 (outputs/vN/)
                                      ↓
6. 规则引擎评估 → 7. 汇总评估结果 → 8. 生成优化建议
                                      ↓
9. LLM 生成下一版提示词 → 10. 保存到 prompts/v{N+1}.md
```

### 关键模块

**evaluate_prompts.py**（主脚本，~1400行）

| 模块 | 功能 | 关键函数 |
|------|------|----------|
| 环境加载 | 解析 `.env` 文件，支持 provider 特定配置和通用配置兜底 | `load_env_from_dotenv()`, `get_client()` |
| 提示词构建 | 加载并拼接模块化提示词 | `load_base_prompt()`, `load_structure()`, `build_prompt()` |
| 标题生成 | 根据选题生成标题 | `generate_title_from_topic()` |
| 版本管理 | 自动识别或指定 `prompts/v*.md` 版本 | `get_latest_prompt_file()`, `get_prompt_file_by_version()` |
| 模型调用 | 通过 OpenAI 兼容接口调用任意 provider 的模型 | `call_llm()`, `generate_with_model()` |
| 规则评估 | 基于关键词检测、结构分析、字数统计等规则评分 | `evaluate_article()` |
| 优化建议 | 根据多模型评估结果统计共性 | `summarize_evaluations()` |
| 提示词优化 | 使用 LLM 基于原提示词 + 评估建议生成纯净版下一版 | `optimize_prompt_via_llm()`, `build_optimized_prompt()` |
| 版本监控 | 维护评估历史、计算版本摘要、对比排名 | `update_evaluations_history()`, `show_version_ranking()`, `compare_with_best()` |
| 单篇生成 | 新功能：生成单篇文章 | `run_single_generation()` |
| 批量生成 | 新功能：批量生成多篇文章（日更用） | `run_batch_generation()` |

### 目录结构

```
.
├── evaluate_prompts.py     # 主脚本（~1400行）
├── import_history.py       # 历史数据导入工具
├── models.json             # 模型配置（按 provider 分类，含 enabled 字段）
├── .env                    # API 密钥配置（不提交）
├── .env.example            # 配置模板
├── .gitignore              # 忽略 outputs/ 和评估历史
├── CLAUDE.md               # 本文件，项目开发指南
├── USAGE.md                # 完整使用说明文档
├── prompts/                # 提示词目录
│   ├── v5_base.md          # 基础提示词（人设+风格+方向）
│   ├── structures_library.md   # 结构库（8种结构）
│   ├── titles_library.md       # 标题库（10种类型）
│   ├── v1.md               # 旧版完整提示词
│   └── v{N}.md             # 其他版本
└── outputs/                # 生成结果与评估报告（不提交）
    ├── batch/              # 批量生成输出
    ├── v1/
    │   ├── {provider}__{model}.txt
    │   └── evaluations.json
    └── v{N}/               # 其他版本输出
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

## 可用结构类型

系统内置 8 种文章结构，可根据选题选择：

| 结构类型 | 适用场景 | 命令参数 |
|---------|---------|----------|
| **场景感悟式** | 人生感悟、处世智慧、独处安宁、读书笔记 | `--structure 场景感悟式` |
| **今昔对比式** | 衰老反思、观念变化、时代记忆、教书余波 | `--structure 今昔对比式` |
| **对话展开式** | 子女关系、老伴相处、朋友交往、问答互动 | `--structure 对话展开式` |
| **三段递进式** | 深度思考、价值观反思、复杂议题 | `--structure 三段递进式` |
| **一事一议式** | 具体事件、当天见闻、微感悟、短篇随笔 | `--structure 一事一议式` |
| **问答体** | 问答回信、读者互动、具体问题咨询 | `--structure 问答体` |
| **书信体** | 写给特定对象、情感倾诉、跨时空对话 | `--structure 书信体` |
| **日记体** | 当天记录、碎片串联、日常感悟 | `--structure 日记体` |

详细说明见 `prompts/structures_library.md`。

## 可用标题类型

系统内置 10 种标题类型模板，可根据选题自动生成：

| 标题类型 | 示例 | 适用场景 |
|---------|------|----------|
| 感悟发现型 | 《老了才发现，朋友越老越少》 | 通用型 |
| 时间节点型 | 《人过六十，学会体面地退场》 | 衰老相关 |
| 场景细节型 | 《半夜醒来，我才真正承认自己老了》 | 有具体画面 |
| 对话引用型 | 《女儿说"挺好的"，我知道她在硬撑》 | 有人物对话 |
| 今昔对比型 | 《以前总觉得时间慢，现在觉得快》 | 观念变化 |
| 一事一议型 | 《老伴住院那周》 | 事件型 |
| 温和劝慰型 | 《我们这个年纪的人，把家里的灯留着》 | 劝慰类 |
| 读书感悟型 | 《书里的一句话，让我想起了女儿》 | 读书类 |
| 疑问反思型 | 《一个人吃饭，我才想起老伴的好》 | 反思类 |
| 简短意境型 | 《慢慢变老》 | 极简风格 |

详细说明见 `prompts/titles_library.md`。

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

## 使用场景与最佳实践

### 场景1：日常单篇生成

```bash
# 每天生成一篇文章，指定结构和输出文件
python evaluate_prompts.py --generate "选题" \
  --structure 对话展开式 \
  --output outputs/article.md
```

### 场景2：批量生成一周内容

```bash
# 周一晚上批量生成下周7篇
python evaluate_prompts.py --batch \
  "周一选题" "周二选题" "周三选题" "周四选题" \
  "周五选题" "周六选题" "周日选题" \
  --batch-output outputs/week2/
```

### 场景3：仿写爆文快速起号

1. **分析爆文结构**（手动分析或使用工具）
2. **提取核心结构**（开头+中间场景+结尾）
3. **用喜生口吻重写**：

```bash
python evaluate_prompts.py --generate "老伴住院那周，我才明白了一个道理" \
  --custom-structure '开头：老伴住院那周，我一个人在家
中间：三个场景
  - 场景1：一个人做饭，不知道做什么
  - 场景2：晚上家里太安静，睡不着
  - 场景3：想打电话给女儿，又怕她担心
结尾：趁着她还在身边，有些软话该说就说'
```

### 场景4：A/B测试不同结构

```bash
# 同一选题，测试不同结构的效果
python evaluate_prompts.py --generate "和老伴吵了一辈子" \
  --structure 场景感悟式 --output test1.md

python evaluate_prompts.py --generate "和老伴吵了一辈子" \
  --structure 对话展开式 --output test2.md

# 对比两篇文章的评估数据
```

### 场景5：提示词优化迭代

```bash
# 1. 运行评估
python evaluate_prompts.py --evaluate

# 2. 查看排名
python evaluate_prompts.py --ranking

# 3. 如果新版本更好，继续使用
# 4. 如果退化，回退到历史最佳版本
python evaluate_prompts.py --evaluate --from-version <最佳版本号>
```

## 最佳实践

### 1. 选题策略

- **日常更新**：围绕4大内容支柱（身体与衰老、伴侣与老伴、子女与牵挂、朋友与社交）
- **热点跟进**：结合节假日、社会话题，用喜生的人设解读
- **情感共鸣**：选择让读者"一看就说在写我"的选题

### 2. 结构选择

| 选题类型 | 推荐结构 | 备选结构 |
|---------|---------|---------|
| 身体与衰老 | 场景感悟式 | 今昔对比式 |
| 伴侣与老伴 | 对话展开式 | 一事一议式 |
| 子女与牵挂 | 对话展开式 | 书信体 |
| 父母与送别 | 一事一议式 | 场景感悟式 |
| 朋友与社交 | 场景感悟式 | 今昔对比式 |
| 独处与安宁 | 场景感悟式 | 一事一议式 |
| 教书余波 | 今昔对比式 | 场景感悟式 |
| 时代记忆 | 今昔对比式 | 三段递进式 |
| 读书笔记 | 场景感悟式 | 三段递进式 |

### 3. 起号阶段策略（前4周）

- **第1-2周**：纯仿写，验证选题和结构
- **第3-4周**：选题改编，用喜生口吻
- **第5-8周**：混合模式，原创70%+仿写30%

### 4. 评估指标关注

| 指标 | 理想值 | 说明 |
|------|--------|------|
| 总分 | 10-12分 | 优秀文章 |
| 字数 | 1000-1200字 | 符合要求 |
| has_classic | True | 引用了经典 |
| intro_ok | True | 开头直接 |
| ending_good | True | 结尾简洁 |

### 5. 常见问题排查

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| 得分低（<8分） | 结构不清晰、未引用经典 | 检查中间段落数、添加经典引用 |
| 字数超标 | 段落过长、内容冗余 | 精简表达、每段控制在3-5句 |
| 未引用经典 | 忘记添加 | 在中间段落自然嵌入一句诗词 |
| 结尾不简洁 | 开启新话题 | 用1-2句完成升华，不展开 |
