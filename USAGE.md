# PromptBench 使用说明

提示词评估与优化工具 - 通过多模型并行测试、规则引擎评分、自动迭代优化，帮助您找到最佳提示词版本。

## 📖 项目简介

**PromptBench** 是一个专业的提示词评估与优化工具，通过多模型并行测试、规则引擎评分、自动迭代优化，帮助您找到最佳提示词版本。

**适用场景**：
- 测试不同版本的提示词效果
- 对比不同模型对同一提示词的响应
- 基于评估结果自动优化提示词
- 追踪提示词版本历史和性能变化

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加 API 配置
# vim .env
```

### 2. 安装依赖

```bash
# 使用 pip
pip install openai python-dotenv

# 或使用 uv（推荐）
uv pip install openai python-dotenv
```

### 3. 运行第一次评估

```bash
# 使用最新版提示词运行评估
uv run evaluate_prompts.py --evaluate
```

---

## 📋 核心命令

### 运行评估

```bash
# 使用最新版提示词运行评估
uv run evaluate_prompts.py --evaluate

# 基于指定版本运行评估（如 v3）
uv run evaluate_prompts.py --evaluate --from-version 3

# 运行评估但不生成新版本（仅测试）
uv run evaluate_prompts.py --evaluate --skip-optimize
```

### 查看排名

```bash
# 显示所有历史版本的排名
uv run evaluate_prompts.py --ranking
```

### 版本管理

```bash
# 基于现有版本创建新版本（复制内容）
uv run evaluate_prompts.py --create-version 4

# 基于现有版本创建指定版本号
uv run evaluate_prompts.py --create-version 4 --to 7
```

---

## 🔄 评估工作流程

```
┌─────────────────────┐
│  1. 准备提示词版本    │
│  prompts/v{N}.md    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  2. 运行评估         │
│  --evaluate         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  3. 多模型并行测试   │
│  (根据 models.json) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  4. 规则引擎评分     │
│  (8维度自动评估)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  5. 生成评估报告     │
│  outputs/v{N}/      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  6. 自动优化建议     │
│  (生成下一版提示词)   │
└─────────────────────┘
```

---

## 📊 评估结果说明

### 输出目录结构

```
outputs/
└── v5/                              # 版本 5 的评估结果
    ├── deepseek__deepseek-v3.1.txt  # 各模型生成的文章
    ├── anthropic__claude-opus-4-5-20251101.txt
    ├── google__gemini-3.1-pro-preview.txt
    └── evaluations.json             # 评估报告（JSON 格式）
```

### evaluations.json 格式

```json
[
  {
    "provider": "google",
    "model": "gemini-3.1-pro-preview",
    "evaluation": {
      "rule_score": 5,
      "ai_score": 3.5,
      "total_score": 8.5,
      "in_length_range": false,
      "para_count_reasonable": true,
      "avg_para_length_ok": false,
      "has_3_points": true,
      "has_headings": false,
      "chars": 1420,
      "paragraphs": 9,
      "avg_para_length": 157.8,
      "length_range": "1000-1200",
      "ai_details": {
        "intro_quality": {"score": 1.0, "reason": "..."},
        "classic_naturalness": {"score": 0.5, "reason": "..."},
        "content_depth": {"score": 0.75, "reason": "..."},
        "writing_fluency": {"score": 0.5, "reason": "..."},
        "emotional_resonance": {"score": 0.5, "reason": "..."},
        "human_like": {"score": 0.25, "reason": "..."}
      }
    },
    "output_path": "outputs/v5/google__gemini-3.1-pro-preview.txt"
  }
]
```

### 评分维度说明

#### 总分：10分（规则5分 + AI评估5分）

#### 规则评估（5分） - 客观指标

| 维度 | 权重 | 检测规则 |
|------|------|----------|
| `in_length_range` | 1.5分 | 字数是否在提示词要求范围内 |
| `para_count_reasonable` | 1分 | 段落数是否合理（5-20段） |
| `avg_para_length_ok` | 0.5分 | 平均段落长度是否合理（30-150字） |
| `has_3_points` | 1分 | 中间是否有≥3个观点段落 |
| `has_headings` | 1分 | 是否有小标题结构 |

#### AI评估（5分） - 语义指标

| 维度 | 权重 | 评估标准 |
|------|------|----------|
| `intro_quality` | 1分 | 开头是否直接入题，有吸引力，符合人设 |
| `classic_naturalness` | 1分 | 经典引用是否自然恰当，与观点紧密相关 |
| `content_depth` | 1分 | 内容是否有深度，观点是否有启发性 |
| `writing_fluency` | 1分 | 文笔是否流畅自然，语言是否有节奏感，有人味儿 |
| `emotional_resonance` | 1分 | 是否能引发情感共鸣，打动人心 |

---

## 🎯 使用场景

### 场景1：测试新提示词

```bash
# 1. 创建新的提示词版本
cp prompts/v4.md prompts/v5.md
# 编辑 v5.md，优化提示词内容

# 2. 运行评估
uv run evaluate_prompts.py --evaluate --from-version 5

# 3. 查看结果
cat outputs/v5/evaluations.json
```

### 场景2：对比历史版本

```bash
# 1. 查看版本排名
uv run evaluate_prompts.py --ranking

# 输出示例：
# 版本     平均分   最高分   模型数   时间
# v4       9.50     11       5       2026-03-12
# v3       8.75     10       5       2026-03-11
# v1       8.20     10       5       2026-03-10
```

### 场景3：基于历史版本重新优化

```bash
# 基于 v3 重新开始评估（跳过 v4）
uv run evaluate_prompts.py --evaluate --from-version 3

# 这将：
# 1. 使用 v3 提示词运行评估
# 2. 自动生成 v4（新的优化版本）
```

### 场景4：仅测试不优化

```bash
# 测试提示词效果，但不生成下一版
uv run evaluate_prompts.py --evaluate --skip-optimize
```

---

## ⚙️ 配置说明

### models.json

控制哪些模型参与评估：

```json
{
  "openai_models": [
    {
      "provider": "xiaoai",
      "name": "gpt-5.1-2025-11-13",
      "enabled": true
    }
  ],
  "anthropic_models": [
    {
      "provider": "xiaoai",
      "name": "claude-opus-4-5-20251101",
      "enabled": true
    }
  ],
  "deepseek_models": [
    {
      "provider": "xiaoai",
      "name": "deepseek-v3.1",
      "enabled": false  # 暂时禁用
    }
  ]
}
```

### .env 配置

```bash
# 通用配置（所有 provider 兜底）
llm_base_url=https://api.example.com/v1
llm_api_key=your-api-key

# 或按 provider 分别配置
xiaoai_base_url=https://api.xiaoai.com/v1
xiaoai_api_key=your-xiaoai-key
```

---

## 📝 提示词版本管理

### 创建新版本

**方式1：自动生成**
```bash
uv run evaluate_prompts.py --evaluate
# 评估完成后自动生成 v{N+1}.md
```

**方式2：手动创建**
```bash
uv run evaluate_prompts.py --create-version 4
# 基于 v4 创建 v5（自动递增）

uv run evaluate_prompts.py --create-version 4 --to 7
# 基于 v4 创建 v7（指定版本号）
```

### 版本命名规范

- 文件名：`v{数字}.md`
- 数字递增：v1.md → v2.md → v3.md ...
- 保持连续：避免跳号（除非有意为之）

---

## 🛠️ 故障排除

### 问题1：未找到提示词文件

```
RuntimeError: 未找到提示词文件：prompts/v5.md
```

**解决**：
- 检查版本号是否正确
- 确认文件存在于 `prompts/` 目录

### 问题2：未找到启用的模型

```
错误：未找到启用的模型，请在 models.json 中配置
```

**解决**：
- 检查 `models.json`
- 确保至少有一个模型的 `"enabled": true`

### 问题3：API 调用失败

```
调用失败：Incorrect API key provided
```

**解决**：
- 检查 `.env` 文件中的 API 密钥配置
- 确认 provider 名称与 `models.json` 一致

### 问题4：评估历史为空

```
暂无评估历史记录。
```

**解决**：
- 至少运行一次 `--evaluate` 才能生成历史记录
- 检查 `evaluations_history.json` 文件是否存在

---

## 💡 最佳实践

### 1. 版本迭代策略

```
v1 (初始版本)
  ↓
v2-v3 (快速迭代，每天1-2版)
  ↓
v4-v10 (精细优化，每天1版)
  ↓
v11+ (成熟版本，按需迭代)
```

### 2. 评估频率建议

- **开发阶段**：每天评估 1-2 次
- **稳定阶段**：每周评估 1 次
- **A/B测试**：同时评估多个版本

### 3. 优化建议处理

评估完成后会输出优化建议，例如：

```
优化建议（基于多模型输出的共性表现）：
- 开头要求可以更具体，比如限制首段在 2-3 句内直接点明主题
- 可以在提示词中补充：至少自然引用 1-2 句古诗词或经典名句
- 建议添加小标题结构，使用「一、」「二、」「三、」等形式
```

**处理方式**：
1. 查看自动生成的下一版提示词
2. 手动调整优化建议
3. 运行下一轮评估验证效果

---

## 📚 高级用法

### 非线性迭代

```bash
# 跳过某些版本，基于历史版本重新开始
uv run evaluate_prompts.py --evaluate --from-version 3

# 这将创建新的 v4，覆盖现有的 v4（如有）
```

### 版本分支

```bash
# 基于 v3 创建 v7（保留 v4-v6）
uv run evaluate_prompts.py --create-version 3 --to 7

# 手动编辑 v7.md
vim prompts/v7.md

# 评估 v7
uv run evaluate_prompts.py --evaluate --from-version 7
```

---

## 🎓 总结

本工具的核心价值：

| 特性 | 说明 |
|------|------|
| **多模型并行** | 一次评估测试多个模型 |
| **规则引擎** | 无需人工评分，自动8维度评估 |
| **版本管理** | 追踪所有历史版本和性能变化 |
| **自动优化** | 基于评估结果生成下一版提示词 |
| **灵活迭代** | 支持线性迭代和非线性分支 |

---

如有疑问，查看帮助：

```bash
uv run evaluate_prompts.py --help
```
