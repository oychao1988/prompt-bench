# 使用说明：evaluate_prompts.py 模块化提示词系统

## 📁 新的文档结构

```
prompts/
├── v5_base.md              # 基础提示词（人设+风格+方向）
├── structures_library.md   # 结构库（8种文章结构）
└── titles_library.md       # 标题库（10种标题类型）
```

---

## 🚀 快速开始

### 1. 单篇生成模式

**基础用法**：
```bash
python evaluate_prompts.py --generate "和老伴吵了一辈子，老了才发现"
```

**指定结构**：
```bash
python evaluate_prompts.py --generate "女儿说挺好的" --structure 对话展开式
```

**自定义标题和输出文件**：
```bash
python evaluate_prompts.py --generate "和老伴吵了一辈子" \
  --title "《老伴炖的那碗汤，我喝了一辈子》" \
  --output outputs/article.md
```

**指定模型**：
```bash
python evaluate_prompts.py --generate "半夜醒来才承认老了" \
  --provider deepseek \
  --model deepseek-v3.1
```

---

### 2. 批量生成模式（日更用）

**基础用法**：
```bash
python evaluate_prompts.py --batch \
  "和老伴吵了一辈子，老了才发现" \
  "女儿说挺好的，我知道她在硬撑" \
  "半夜醒来，我才真正承认自己老了"
```

**指定结构循环**：
```bash
python evaluate_prompts.py --batch topic1 topic2 topic3 \
  --structures 场景感悟式 对话展开式 今昔对比式
```

**指定输出目录**：
```bash
python evaluate_prompts.py --batch topic1 topic2 topic3 \
  --batch-output outputs/week1/
```

---

### 3. 仿写爆文模式

```bash
python evaluate_prompts.py --generate "老伴住院那周，我才明白了一个道理" \
  --custom-structure '开头：老伴住院那周，我一个人在家
中间：三个场景
  - 场景1：一个人做饭，不知道做什么
  - 场景2：晚上家里太安静，睡不着
  - 场景3：想打电话给女儿，又怕她担心
结尾：一句劝慰'
```

---

## 📋 可用结构类型

| 结构类型 | 适用场景 | 示例 |
|---------|---------|------|
| 场景感悟式 | 人生感悟、处世智慧、独处安宁 | 《半夜醒来，我才真正承认自己老了》 |
| 今昔对比式 | 衰老反思、观念变化、时代记忆 | 《以前总觉得时间慢，现在觉得快》 |
| 对话展开式 | 子女关系、老伴相处、朋友交往 | 《女儿说"挺好的"》 |
| 三段递进式 | 深度思考、价值观反思 | 《退休半年，我才慢慢懂了》 |
| 一事一议式 | 具体事件、当天见闻、短篇随笔 | 《河边那对老夫妻》 |
| 问答体 | 问答回信、读者互动 | 《有读者问我"怎么和老伴相处"》 |
| 书信体 | 写给特定对象、情感倾诉 | 《写给在外地的女儿》 |
| 日记体 | 当天记录、碎片串联 | 《今天的三件小事》 |

---

## 🎯 命令行参数说明

### 模式选择（互斥，选一个）

| 参数 | 说明 |
|------|------|
| `--generate TOPIC` | 单篇生成模式 |
| `--batch TOPIC...` | 批量生成模式 |
| `--evaluate` | 评估模式（旧版，向后兼容） |
| `--ranking` | 显示历史版本排名 |
| `--create-version N` | 基于指定版本创建新版本 |

### 单篇生成选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--structure TYPE` | 结构类型 | 场景感悟式 |
| `--title TITLE` | 自定义标题 | 自动生成 |
| `--custom-structure TEXT` | 自定义结构（仿写爆文） | - |
| `--output FILE` | 输出文件路径 | 打印到终端 |

### 批量生成选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--structures TYPE...` | 结构类型列表 | 自动循环使用 |
| `--batch-output DIR` | 输出目录 | outputs/batch/ |

### 通用选项

| 参数 | 说明 |
|------|------|
| `--provider NAME` | 指定 provider（openai/anthropic/google/deepseek） |
| `--model NAME` | 指定模型名称 |

---

## 📊 输出示例

### 单篇生成输出

```
== 使用模块化提示词系统 ==
选题: 和老伴吵了一辈子，老了才发现
结构: 对话展开式

== 调用 deepseek / deepseek-v3.1 ==

==================================================
[生成的文章内容...]
==================================================

评估结果:
  得分: 10/12
  字数: 1156
  段落数: 8
  是否在字数范围内: 是
  是否引用经典: 是
  开头是否直接: 是
  结尾是否简洁: 是

已保存到: outputs/article.md
```

### 批量生成输出

```
== 批量生成模式 ==
选题数: 7
结构类型: 场景感悟式, 对话展开式, 今昔对比式, 一事一议式
输出目录: outputs/batch

使用模型: deepseek / deepseek-v3.1

[1/7] 选题: 和老伴吵了一辈子，老了才发现 (场景感悟式)
  ✓ 得分: 10/12, 字数: 1156, 已保存: 01_和老伴吵了一辈子，老了才发现.md

[2/7] 选题: 女儿说挺好的，我知道她在硬撑 (对话展开式)
  ✓ 得分: 9/12, 字数: 1089, 已保存: 02_女儿说挺好的，我知道她在硬撑.md

...

== 批量生成完成 ==
成功: 7/7
平均分: 9.57

最佳文章:
  和老伴吵了一辈子，老了才发现 - 11/12 (场景感悟式)
```

---

## 🔄 旧版兼容性

原有的评估模式仍然可用：

```bash
# 使用最新版提示词运行评估
python evaluate_prompts.py --evaluate

# 基于 v3 版本运行评估
python evaluate_prompts.py --evaluate --from-version 3

# 运行评估但不生成新版本
python evaluate_prompts.py --evaluate --skip-optimize

# 显示历史版本排名
python evaluate_prompts.py --ranking
```

---

## 💡 使用场景

### 场景1：日常单篇生成

```bash
# 每天生成一篇文章
python evaluate_prompts.py --generate "选题" --structure 结构 --output article.md
```

### 场景2：批量生成一周内容

```bash
# 周一晚上批量生成下周7篇
python evaluate_prompts.py --batch \
  "周一选题" "周二选题" "周三选题" "周四选题" \
  "周五选题" "周六选题" "周日选题" \
  --batch-output outputs/week2/
```

### 场景3：仿写爆文

```bash
# 分析爆文结构，用喜生口吻重写
python evaluate_prompts.py --generate "老伴住院那周，我才明白了一个道理" \
  --custom-structure '[爆文结构]'
```

### 场景4：A/B测试不同结构

```bash
# 同一选题，测试不同结构的效果
python evaluate_prompts.py --generate "和老伴吵了一辈子" \
  --structure 场景感悟式 --output test1.md

python evaluate_prompts.py --generate "和老伴吵了一辈子" \
  --structure 对话展开式 --output test2.md

# 对比两篇文章的数据
```

---

## ⚙️ 配置说明

### .env 文件

```bash
# 通用配置（所有 provider 兜底）
llm_base_url=https://api.example.com/v1
llm_api_key=your-api-key

# 或按 provider 分别配置
deepseek_base_url=https://api.deepseek.com
deepseek_api_key=your-deepseek-key
```

### models.json

```json
{
  "deepseek_models": [
    {
      "provider": "deepseek",
      "name": "deepseek-v3.1",
      "enabled": true
    }
  ]
}
```

---

## 🐛 故障排除

### 问题：未找到基础提示词文件

```
RuntimeError: 未找到基础提示词文件：prompts/v5_base.md
```

**解决**：确认 `prompts/v5_base.md`、`structures_library.md`、`titles_library.md` 三个文件存在。

---

### 问题：未找到启用的模型

```
错误：未找到启用的模型，请在 models.json 中配置
```

**解决**：检查 `models.json`，确保至少有一个模型的 `"enabled": true`。

---

### 问题：API 调用失败

```
调用失败：Incorrect API key provided
```

**解决**：检查 `.env` 文件，确认 API 密钥配置正确。

---

## 📚 进阶：自定义结构

### 1. 编辑 structures_library.md

在 `prompts/structures_library.md` 中添加新结构：

```markdown
## 结构九：我的自定义结构

**适用场景**：XXX

**结构模板**：
开头：...
中间：...
结尾：...
```

### 2. 使用自定义结构

```bash
python evaluate_prompts.py --generate "选题" --structure 我的自定义结构
```

---

## 🎉 总结

新系统的核心优势：

| 优势 | 说明 |
|------|------|
| **模块化** | 人设、结构、标题分离，便于维护 |
| **灵活性** | 支持指定结构、自定义结构、仿写爆文 |
| **可扩展** | 新增结构只需修改 structures_library.md |
| **可测试** | 同一选题可测试不同结构效果 |
| **向后兼容** | 保留旧版评估模式 |

---

如有问题，请查看帮助：

```bash
python evaluate_prompts.py --help
```
