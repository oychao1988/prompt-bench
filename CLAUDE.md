# CLAUDE.md

PromptBench 开发指南 - 提示词评估与优化工具。

## Project Context

**项目名称**：PromptBench

**用途**：评估和优化 LLM 提示词，通过多模型并行测试和规则引擎自动评分。

**技术栈**：Python 3.12 + OpenAI SDK

**核心功能**：
- 多模型并行评估（使用 models.json 配置）
- 混合评估体系（规则6分 + AI评估6分，总分12分）
- 版本管理与历史追踪
- 自动迭代优化提示词

## Style Guide

### 命名规范
- 函数名：`snake_case`（如 `run_evaluation`）
- 常量：`UPPER_SNAKE_CASE`（如 `OUTPUT_DIR`）
- 类型注解：必须使用（`function(arg: type) -> ReturnType`）

### 代码风格
- Docstring 遵循 Google 风格
- 最大行宽：100 字符
- 导入顺序：标准库 → 第三方库 → 本地模块
- 使用 `# ====== 分隔标题 ======` 标记代码区块

### 函数组织
- 每个函数只做一件事
- 函数长度不超过 50 行（复杂逻辑除外）
- 优先使用 `pathlib.Path` 而不是 `os.path`

## Project Structure

```
.
├── evaluate_prompts.py        # 主脚本（~900行）
├── models.json                # 模型配置
├── import_history.py          # 辅助工具
├── prompts/                   # 提示词版本文件（评估对象）
│   ├── v*.md
└── outputs/                   # 评估结果（不提交）
    ├── v*/
    │   ├── {provider}__{model}.txt
    │   └── evaluations.json
    └── v*/
```

### 核心文件
- `evaluate_prompts.py`：所有评估逻辑
- `models.json`：配置哪些模型参与评估
- `evaluations_history.json`：版本历史（自动生成，不提交）
- `.env`：API 密钥（不提交）

## CLI Commands

```bash
# 运行评估
uv run evaluate_prompts.py --evaluate

# 基于指定版本评估
uv run evaluate_prompts.py --evaluate --from-version 3

# 查看版本排名
uv run evaluate_prompts.py --ranking

# 创建新版本
uv run evaluate_prompts.py --create-version 4

# 仅测试不优化
uv run evaluate_prompts.py --evaluate --skip-optimize
```

## Code Organization

| 模块 | 关键函数 | 行号 |
|------|----------|------|
| 环境加载 | `load_env_from_dotenv()`, `get_client()` | ~23-74 |
| 版本管理 | `get_latest_prompt_file()`, `load_prompt()` | ~81-114 |
| 模型调用 | `call_llm()`, `generate_with_model()` | ~122-206 |
| 规则评估 | `evaluate_article()`, `extract_length_requirement()` | ~245-344 |
| AI评估 | `evaluate_article_via_ai()` | ~347-503 |
| 评估总结 | `summarize_evaluations()`, `optimize_prompt_via_llm()` | ~509-570, ~573-654 |
| 版本历史 | `calculate_version_summary()`, `show_version_ranking()` | ~692-731, ~753-787 |
| 版本对比 | `compare_with_best()` | ~790-826 |
| 评估流程 | `run_evaluation()` | ~840-944 |

## Preferences

### ✅ 必须遵守
- 使用 `uv run` 执行脚本
- 修改函数后更新 CLAUDE.md 中的行号参考
- 评估规则修改必须在 `evaluate_article()` 函数中进行
- 新增 provider 必须在 `models.json` 和 `.env` 中同时配置

### ❌ 禁止行为
- **禁止添加文章生成功能**：本项目是评估工具，不是生成工具
- **不要提交敏感文件**：`.env`, `evaluations_history.json`, `outputs/`
- **不要硬编码 API 密钥**：必须从环境变量读取
- **不要修改 prompts/ 下的版本文件**：评估对象应保持只读
- **不要使用 f-string 中的中文引号**：会导致语法错误

### ⚠️ 注意事项
- 评估结果自动保存到 `outputs/v{N}/`
- 优化器默认使用 `gpt-5.4`，可通过 `PROMPT_OPTIMIZER_MODEL` 修改
- AI评估默认使用 `gpt-5.4`，可通过 `EVALUATION_MODEL` 修改
- 规则评估权重在 `evaluate_article()` 的 `weights` 字典中定义
- AI评估维度在 `evaluate_article_via_ai()` 的提示词中定义

## Development Workflow

1. **修改规则评估**：编辑 `evaluate_article()`（~245-344行）
2. **修改AI评估**：编辑 `evaluate_article_via_ai()`（~347-503行）
3. **修改优化逻辑**：编辑 `summarize_evaluations()`（~509-570行）
4. **更新文档**：修改后必须更新 CLAUDE.md 、USAGE.md 、README.md

## 评分体系

### 总分：10分（质量6分 + AI检测4分）

#### 质量评估（6分）
##### 规则评估（3分）
| 维度 | 分值 | 检测规则 |
|------|------|----------|
| `in_length_range` | 1.0分 | 字数是否在提示词要求范围内 |
| `para_count_reasonable` | 0.7分 | 段落数是否合理（5-20段） |
| `avg_para_length_ok` | 0.3分 | 平均段落长度是否合理（30-150字） |
| `has_3_points` | 0.6分 | 中间是否有≥3个观点段落 |
| `has_headings` | 0.4分 | 是否有小标题结构 |

##### AI语义评估（3分）
| 维度 | 分值 | 评估标准 |
|------|------|----------|
| `intro_quality` | 0.6分 | 开头是否直接入题，有吸引力，符合人设 |
| `classic_naturalness` | 0.6分 | 经典引用是否自然恰当，与观点紧密相关 |
| `content_depth` | 0.6分 | 内容是否有深度，观点是否有启发性 |
| `writing_fluency` | 0.6分 | 文笔是否流畅自然，语言是否有节奏感 |
| `emotional_resonance` | 0.6分 | 是否能引发情感共鸣，打动人心 |

#### AI检测（4分）

**评分公式**：`检测分 = (1 - AI率) × 4`，保留2位小数

**评分对照表**：
| AI率 | 人类率 | 检测分 | 评级 |
|------|--------|--------|------|
| 0% | 100% | 4.00 | ⭐⭐⭐⭐⭐ 完美 |
| 10% | 90% | 3.60 | ⭐⭐⭐⭐⭐ 优秀 |
| 20% | 80% | 3.20 | ⭐⭐⭐⭐ 良好 |
| 30% | 70% | 2.80 | ⭐⭐⭐ 良好 |
| 40% | 60% | 2.40 | ⭐⭐⭐ 一般 |
| 50% | 50% | 2.00 | ⭐⭐ 一般 |
| 60% | 40% | 1.60 | ⭐⭐ 较差 |
| 70% | 30% | 1.20 | ⭐ 较差 |
| 80% | 20% | 0.80 | ⭐ 很差 |
| 90% | 10% | 0.40 | ⭐ 很差 |
| 100% | 0% | 0.00 | ⭐ 纯AI |

**多检测器支持**：可同时启用多个检测器，自动计算加权平均值
- 朱雀AI检测（腾讯）- 中文首选
- GPTZero - 准确率高
- Copyleaks - 支持中文
- Originality.ai
- Writer.com

**配置方式**：在 `.env` 中设置：
```bash
# 启用检测器（设置为 true 启用）
GPTZERO_DETECTOR_ENABLED=true
GPTZERO_API_KEY=your_key
GPTZERO_WEIGHT=1.0

COPYLEAKS_DETECTOR_ENABLED=true
COPYLEAKS_API_KEY=your_key
COPYLEAKS_WEIGHT=1.0
```

**注意**：未配置任何检测器时，系统会使用启发式模拟检测（基于文本特征）

## Related Documentation

- **[USAGE.md](USAGE.md)**：完整使用说明
- **[README.md](README.md)**：项目概述
