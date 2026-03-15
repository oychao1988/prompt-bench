# CLAUDE.md

PromptBench 开发指南 - 提示词评估与优化工具。

## Project Context

**项目名称**：PromptBench

**用途**：评估和优化 LLM 提示词，通过多模型并行测试和规则引擎自动评分。

**技术栈**：Python 3.12 + OpenAI SDK

**当前状态**：✅ 核心功能已完成并验证

**已实现功能**：
- ✅ 多模型并行评估（8个模型同时测试）
- ✅ 规则评估引擎（5个维度）
- ✅ AI语义评估（5个维度，使用LLM）
- ✅ AI检测（多检测器支持，含模拟检测）
- ✅ 模型连通性测试（ping命令）
- ✅ 自动禁用失败模型（--auto-disable）
- ✅ 评估结果保存（JSON格式）
- ✅ 评估总结生成（优化建议）
- ✅ 版本管理（提示词和历史记录）

**已验证版本**：v4（胡家喜人设：60岁退休语文老师）
- 评估时间：2026-03-15
- 平均总分：8.0/10分
- 最佳模型：deepseek-v3.2-exp（9.42分）

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
├── promptbench/               # 核心包（模块化架构）
│   ├── __init__.py
│   ├── cli/                   # 命令行接口
│   │   └── main.py
│   ├── core/                  # 核心模块
│   │   ├── config.py          # 配置管理
│   │   ├── constants.py       # 常量定义
│   │   ├── entities.py        # 数据类
│   │   └── exceptions.py      # 异常体系
│   ├── evaluators/            # 评估器
│   │   ├── rule_evaluator.py  # 规则评估
│   │   └── ai_evaluator.py    # AI评估
│   ├── detectors/             # AI检测器
│   │   ├── base.py            # 基础类
│   │   └── multi_detector.py  # 多检测器聚合
│   ├── optimizers/            # 优化器
│   │   ├── summarizer.py      # 评估总结
│   │   └── prompt_optimizer.py # 提示词优化
│   ├── models/                # 模型客户端
│   │   └── client.py          # 统一模型接口
│   ├── versions/              # 版本管理
│   │   ├── prompt_manager.py  # 提示词管理
│   │   └── history_manager.py # 历史记录管理
│   └── utils/                 # 工具模块
│       ├── text.py            # 文本处理
│       ├── file.py            # 文件操作
│       └── log.py             # 日志工具
├── tests/                     # 测试套件
│   ├── test_core.py
│   ├── test_evaluators_integration.py
│   ├── test_rule_evaluator.py
│   ├── test_ai_evaluator.py
│   ├── test_detectors.py
│   ├── test_optimizers.py
│   ├── test_models_versions.py
│   ├── test_cli.py
│   └── test_utils.py
├── models.json                # 模型配置
├── prompts/                   # 提示词版本文件（评估对象）
│   └── v*.md
├── outputs/                   # 评估结果（不提交）
│   └── v*/
├── pyproject.toml             # 项目配置
├── README.md                  # 项目概述
├── USAGE.md                   # 使用说明
└── CLAUDE.md                  # 开发指南（本文件）
```

### 核心模块
- `promptbench/core/config.py`：统一配置管理和环境变量加载
- `promptbench/evaluators/rule_evaluator.py`：规则评估逻辑（字数、段落数等）
- `promptbench/evaluators/ai_evaluator.py`：AI语义评估逻辑
- `promptbench/detectors/multi_detector.py`：多检测器聚合和AI检测
- `promptbench/optimizers/`：评估总结和提示词优化
- `promptbench/models/client.py`：统一的模型调用接口
- `promptbench/versions/`：提示词版本管理和历史记录
- `promptbench/cli/main.py`：命令行接口（CLI）

### 配置文件
- `models.json`：配置哪些模型参与评估
- `.env`：API密钥和配置（不提交）
- `evaluations_history.json`：版本历史（自动生成，不提交）

## CLI Commands

```bash
# 运行评估（使用最新版本提示词）
promptbench evaluate

# 基于指定版本评估
promptbench evaluate --from-version 4

# 仅测试不优化（跳过自动生成下一版）
promptbench evaluate --skip-optimize

# 测试模型连通性
promptbench ping --all                                    # Ping 所有启用的模型
promptbench ping --provider xiaoai --model gpt-5.1-2025-11-13  # Ping 单个模型
promptbench ping --all --auto-disable                     # Ping 并自动禁用失败的模型

# 查看版本排名（占位符）
promptbench ranking

# 显示版本详情（占位符）
promptbench show 4

# 比较版本（占位符）
promptbench compare --versions 1 2 3

# 查看帮助
promptbench --help
promptbench evaluate --help
promptbench ping --help
```

## 评估流程说明

### 完整评估流程

```bash
# 1. 确保模型配置正确
python -m promptbench.cli.main ping --all

# 2. 运行评估（会自动生成下一版提示词）
python -m promptbench.cli.main evaluate --from-version 4

# 3. 查看评估结果
cat outputs/v4/evaluations.json
cat outputs/v4/summary.md

# 4. 查看各模型生成的文章
ls outputs/v4/
```

### 评估输出说明

每次评估会生成以下文件：

```
outputs/v4/
├── evaluations.json                    # 详细评估结果（JSON格式）
├── summary.md                          # 评估总结和优化建议
├── xiaoai__gpt-5.1-2025-11-13.txt     # 各模型生成的文章
├── xiaoai__deepseek-v3.2-exp.txt       # （最佳模型示例）
└── ...                                 # 其他模型输出
```

### 实际评估示例（v4版本）

**版本信息**：v4（胡家喜人设：60岁退休语文老师）

**评估结果**：
- **评估模型数**：8个
- **平均总分**：8.0/10分
- **最佳模型**：deepseek-v3.2-exp（9.42分）
- **AI评估平均分**：2.9/3分（优秀）
- **人类化程度**：平均65%

**最佳模型表现（deepseek-v3.2-exp）**：
- 规则评估：3.0/3.0分（满分）
- AI语义评估：2.94/3.0分
- AI检测：3.48/4.0分（人类率87%）
- 文章字数：1279字
- 段落数：10段

**主要优化建议**：
1. 段落数量控制（部分模型段落过多）
2. 小标题结构建议添加
3. 段落长度需要更均衡

### 开发模式运行

```bash
# 直接运行Python模块
python -m promptbench.cli.main evaluate
python -m promptbench.cli.main ranking

# 或使用旧脚本（已废弃，保留向后兼容）
python evaluate_prompts.py --evaluate
```

## Code Organization

| 模块 | 主要类/函数 | 职责 |
|------|-------------|------|
| **核心模块** | | |
| `core/config.py` | `ConfigManager` | 环境变量加载、配置管理 |
| `core/constants.py` | - | 默认权重、评分规则、常量 |
| `core/entities.py` | `EvaluationResult`, `ModelConfig` | 数据类定义 |
| `core/exceptions.py` | `PromptBenchError` 及子类 | 异常体系 |
| **评估模块** | | |
| `evaluators/rule_evaluator.py` | `RuleEvaluator` | 规则评估（字数、段落数等） |
| `evaluators/ai_evaluator.py` | `AIEvaluator` | AI语义评估 |
| **检测模块** | | |
| `detectors/base.py` | `AIDetector` | AI检测器基类 |
| `detectors/multi_detector.py` | `MultiAIDetector` | 多检测器聚合 |
| **优化模块** | | |
| `optimizers/summarizer.py` | `EvaluationSummarizer` | 评估结果总结 |
| `optimizers/prompt_optimizer.py` | `PromptOptimizer` | 提示词优化 |
| **模型模块** | | |
| `models/client.py` | `ModelClient` | 统一模型调用接口 |
| **版本管理** | | |
| `versions/prompt_manager.py` | `PromptManager` | 提示词版本管理 |
| `versions/history_manager.py` | `HistoryManager` | 评估历史管理 |
| **CLI模块** | | |
| `cli/main.py` | `CLI` | 命令行接口 |
| **工具模块** | | |
| `utils/text.py` | - | 文本处理工具 |
| `utils/file.py` | - | 文件操作工具 |
| `utils/log.py` | - | 日志工具 |

## Preferences

### ✅ 必须遵守
- 使用模块化架构，所有新功能应在相应模块中实现
- 遵循类型注解规范（`function(arg: type) -> ReturnType`）
- 遵循 Google 风格的 Docstring
- 修改代码后运行测试确保通过
- 新增 provider 必须在 `models.json` 和 `.env` 中同时配置
- 使用 `promptbench` CLI 命令或 `python -m promptbench.cli.main`

### ❌ 禁止行为
- **禁止添加文章生成功能**：本项目是评估工具，不是生成工具
- **不要提交敏感文件**：`.env`, `evaluations_history.json`, `outputs/`
- **不要硬编码 API 密钥**：必须从环境变量读取
- **不要修改 prompts/ 下的版本文件**：评估对象应保持只读
- **不要使用 f-string 中的中文引号**：会导致语法错误

### ⚠️ 注意事项
- 评估结果自动保存到 `outputs/v{N}/`
- 默认使用 `ConfigManager` 加载环境变量
- 规则评估权重在 `core/constants.py` 的 `DEFAULT_RULE_WEIGHTS` 中定义
- AI评估维度在 `evaluators/ai_evaluator.py` 的提示词中定义
- 旧脚本 `evaluate_prompts.py` 已废弃，仅保留向后兼容
- 所有配置通过环境变量或 `models.json` 管理，禁止硬编码

## Development Workflow

### 修改规则评估
编辑 `promptbench/evaluators/rule_evaluator.py` 中的 `RuleEvaluator` 类

### 修改AI评估
编辑 `promptbench/evaluators/ai_evaluator.py` 中的 `AIEvaluator` 类

### 修改优化逻辑
编辑 `promptbench/optimizers/` 目录下的相应模块

### 运行测试
```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_rule_evaluator.py -v

# 查看测试覆盖率
pytest tests/ --cov=promptbench --cov-report=html
```

### 更新文档
修改代码后必须更新：
1. `CLAUDE.md` - 开发指南
2. `USAGE.md` - 使用说明
3. `README.md` - 项目概述

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
