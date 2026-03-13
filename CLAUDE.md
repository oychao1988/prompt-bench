# CLAUDE.md

PromptBench 开发指南 - 提示词评估与优化工具。

## Project Context

**项目名称**：PromptBench

**用途**：评估和优化 LLM 提示词，通过多模型并行测试和规则引擎自动评分。

**技术栈**：Python 3.12 + OpenAI SDK

**核心功能**：
- 多模型并行评估（使用 models.json 配置）
- 规则引擎自动评分（8维度，12分制）
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
| 规则评估 | `evaluate_article()`, `extract_length_requirement()` | ~206-376 |
| 评估总结 | `summarize_evaluations()`, `optimize_prompt_via_llm()` | ~377-493 |
| 版本历史 | `update_evaluations_history()`, `show_version_ranking()` | ~511-627 |
| 评估流程 | `run_evaluation()` | ~708-813 |

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
- 规则评估权重在 `evaluate_article()` 的 `weights` 字典中定义

## Development Workflow

1. **修改评估规则**：编辑 `evaluate_article()`（~245-376行）
2. **添加新维度**：在 `evaluate_article()` 中添加检测逻辑和权重
3. **修改优化逻辑**：编辑 `optimize_prompt_via_llm()`（~441-493行）
4. **更新文档**：修改后必须更新 CLAUDE.md 、USAGE.md 、README.md

## Related Documentation

- **[USAGE.md](USAGE.md)**：完整使用说明
- **[README.md](README.md)**：项目概述
