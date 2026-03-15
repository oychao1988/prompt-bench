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

### 2. 安装项目

```bash
# 安装 PromptBench
pip install -e .

# 或使用开发模式安装
pip install -e .
```

---

## 📋 核心命令

### 运行评估

```bash
# 使用最新版提示词运行评估
promptbench evaluate

# 基于指定版本运行评估（如 v4）
promptbench evaluate --from-version 4

# 运行评估但不生成新版本（仅测试）
promptbench evaluate --skip-optimize
```

### 测试模型连通性

```bash
# 测试所有启用的模型
promptbench ping --all

# 测试单个模型
promptbench ping --provider xiaoai --model gpt-5.1-2025-11-13

# 测试并自动禁用失败的模型
promptbench ping --all --auto-disable
```

**实际输出示例**：
```
Ping 所有启用的模型...
============================================================
✅ xiaoai/gpt-5.1-2025-11-13
✅ xiaoai/gpt-5.2-2025-12-11
✅ xiaoai/claude-opus-4-6
✅ xiaoai/deepseek-v3.2-exp
...
Ping 完成: 8/8 个模型可用
```

### 查看排名

```bash
# 显示所有历史版本的排名
promptbench ranking
```

### 版本管理

```bash
# 显示特定版本详情
promptbench show 4

# 比较多个版本
promptbench compare --versions 1 2 3
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
      "rule_score": 2.5,
      "ai_score": 2.1,
      "detection_score": 1.5,
      "total_score": 6.1,
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
        "emotional_resonance": {"score": 0.5, "reason": "..."}
      },
      "detection_result": {
        "ai_score": 0.65,
        "ai_percentage": 65,
        "human_percentage": 35,
        "detector": "zhuque",
        "confidence": "medium"
      }
    },
    "output_path": "outputs/v5/google__gemini-3.1-pro-preview.txt"
  }
]
```

### 评分维度说明

#### 总分：10分（质量6分 + AI检测4分）

##### 质量评估（6分）

**规则评估（3分）** - 客观指标

| 维度 | 权重 | 检测规则 |
|------|------|----------|
| `in_length_range` | 1.0分 | 字数是否在提示词要求范围内 |
| `para_count_reasonable` | 0.7分 | 段落数是否合理（5-20段） |
| `avg_para_length_ok` | 0.3分 | 平均段落长度是否合理（30-150字） |
| `has_3_points` | 0.6分 | 中间是否有≥3个观点段落 |
| `has_headings` | 0.4分 | 是否有小标题结构 |

**AI语义评估（3分）** - 语义指标

| 维度 | 权重 | 评估标准 |
|------|------|----------|
| `intro_quality` | 0.6分 | 开头是否直接入题，有吸引力，符合人设 |
| `classic_naturalness` | 0.6分 | 经典引用是否自然恰当，与观点紧密相关 |
| `content_depth` | 0.6分 | 内容是否有深度，观点是否有启发性 |
| `writing_fluency` | 0.6分 | 文笔是否流畅自然，语言是否有节奏感 |
| `emotional_resonance` | 0.6分 | 是否能引发情感共鸣，打动人心 |

##### AI检测（4分）

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

**多检测器支持**：

支持同时使用多个AI检测平台，系统自动计算加权平均值：

| 检测器 | 推荐度 | 说明 |
|--------|--------|------|
| 朱雀检测 | ⭐⭐⭐⭐⭐ | 腾讯出品，中文首选 |
| GPTZero | ⭐⭐⭐⭐ | 准确率最高（~99%），API稳定 |
| Copyleaks | ⭐⭐⭐ | 支持多种模型，检测全面 |
| Originality.ai | ⭐⭐⭐ | 专门检测AI内容 |
| Writer.com | ⭐⭐⭐ | 免费额度较大 |

**配置方式**：

在 `.env` 文件中配置：

```bash
# 启用朱雀检测（中文首选）
ZHUQUE_DETECTOR_ENABLED=true
ZHUQUE_API_KEY=your_api_key
ZHUQUE_ENDPOINT=https://matrix.tencent.com/ai-detect/ai_gen_txt
ZHUQUE_WEIGHT=1.0

# 启用GPTZero
GPTZERO_DETECTOR_ENABLED=true
GPTZERO_API_KEY=your_gptzero_api_key
GPTZERO_ENDPOINT=https://api.gptzero.me/v2/predict/text
GPTZERO_WEIGHT=1.0

# 启用Copyleaks
COPYLEAKS_DETECTOR_ENABLED=true
COPYLEAKS_API_KEY=your_copyleaks_api_key
COPYLEAKS_ENDPOINT=https://api.copyleaks.com
COPYLEAKS_WEIGHT=1.0
```

**注意事项**：
- 未配置任何检测器时，系统会使用启发式模拟检测
- 权重用于调整不同检测器的重要性，默认都是1.0
- 建议至少启用一个检测器以获得准确结果
- 中文内容优先推荐朱雀检测

---

## 📈 实际评估示例（v4版本）

### 基本信息
- **提示词版本**：v4
- **人设**：胡家喜，60岁退休语文老师
- **评估模型数**：8个
- **评估时间**：2026-03-15

### 总体结果

| 维度 | 平均分 | 最高分 |
|------|--------|--------|
| **总分** | 8.0/10 | 9.42 (deepseek-v3.2-exp) |
| **规则评估** | 2.3/3 | 3.0 |
| **AI语义评估** | 2.9/3 | 3.0 |
| **AI检测** | 2.8/4 | 3.48 |

### 最佳模型：deepseek-v3.2-exp（9.42分）

**详细得分**：
- 规则评估：3.0/3.0（满分）
  - ✅ 字数：1279字（完美在范围内）
  - ✅ 段落数：10段（合理）
  - ✅ 段落长度：平均127.9字（均衡）
  - ✅ 结构：有清晰的观点段落
  - ✅ 小标题：有段落分隔

- AI语义评估：2.94/3.0（优秀）
  - 开头质量：1.0/1.0 - "从夜里守母亲打点滴的具体场景直接入题，画面感强"
  - 经典引用：1.0/1.0 - "引用《廉颇老矣》、王羲之句、'尚能饭否'及傅雷家书、汪曾祺文字等，都自然嵌入在回忆和自述中"
  - 内容深度：0.9/1.0 - "能从生活细节中生出'话要软、手要松''时间筛子'等有启发性的认识"
  - 文笔流畅：1.0/1.0 - "语言平实而有韵律，短句为主，读起来像老人缓缓叙话"
  - 情感共鸣：1.0/1.0 - "守护老母、与女儿外孙视频、老伴的小摩擦与体谅、群里人情冷暖等细节真实细腻"

- AI检测：3.48/4.0
  - 人类率：87%
  - AI率：13%
  - 置信度：high

**文章亮点**：
1. 从"母亲床前守夜"的具体场景切入，画面感强
2. 自然引用东坡、陶渊明、傅雷家书等经典
3. 情感克制而动人，细节真实细腻
4. 符合60岁退休语文老师的人设

### 优化建议（基于8个模型的共性表现）

**规则评估维度**：
- 段落数量（2个模型不合理）：文章段落数建议控制在 5-20 段之间
- 段落长度（2个模型不合理）：每段平均长度建议在 30-150 字之间
- 小标题结构（3个模型缺失）：建议添加小标题结构，使用序号形式标注观点段落

### 评估输出文件

```
outputs/v4/
├── evaluations.json                    # 详细评估结果（JSON格式）
├── summary.md                          # 评估总结和优化建议
├── xiaoai__gpt-5.1-2025-11-13.txt     # 各模型生成的文章
├── xiaoai__gpt-5.2-2025-12-11.txt
├── xiaoai__claude-opus-4-5-20251101.txt
├── xiaoai__claude-opus-4-6.txt
├── xiaoai__claude-sonnet-4-6.txt
├── xiaoai__gemini-3.1-pro-preview.txt
├── xiaoai__deepseek-v3.1.txt
└── xiaoai__deepseek-v3.2-exp.txt       # 最佳模型
```

---

## 🎯 使用场景

### 场景1：测试新提示词

```bash
# 1. 创建新的提示词版本
cp prompts/v4.md prompts/v5.md
# 编辑 v5.md，优化提示词内容

# 2. 运行评估
promptbench evaluate --from-version 5

# 3. 查看结果
cat outputs/v5/evaluations.json
```

### 场景2：对比历史版本

```bash
# 1. 查看版本排名
promptbench ranking

# 输出示例：
# 版本     平均分   最高分   模型数   时间
# v4       9.50     11       5       2026-03-12
# v3       8.75     10       5       2026-03-11
# v1       8.20     10       5       2026-03-10
```

### 场景3：基于历史版本重新优化

```bash
# 基于 v3 重新开始评估（跳过 v4）
promptbench evaluate --from-version 3

# 这将：
# 1. 使用 v3 提示词运行评估
# 2. 自动生成 v4（新的优化版本）
```

### 场景4：仅测试不优化

```bash
# 测试提示词效果，但不生成下一版
promptbench evaluate --skip-optimize
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
promptbench evaluate
# 评估完成后自动生成 v{N+1}.md
```

**方式2：手动创建**
```bash
# 手动创建新版本（复制文件）
cp prompts/v4.md prompts/v5.md
# 基于 v4 创建 v5（自动递增）

# 手动创建新版本（复制文件）
cp prompts/v4.md prompts/v5.md --to 7
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
promptbench evaluate --from-version 3

# 这将创建新的 v4，覆盖现有的 v4（如有）
```

### 版本分支

```bash
# 基于 v3 创建 v7（保留 v4-v6）
# 基于现有版本创建指定版本号（手动复制）
cp prompts/v3.md prompts/v7.md

# 手动编辑 v7.md
vim prompts/v7.md

# 评估 v7
promptbench evaluate --from-version 7
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
promptbench --help
promptbench evaluate --help
```
