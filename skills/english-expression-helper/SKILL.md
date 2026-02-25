---
name: english-expression-helper
description: |
  英语表达助手：帮用户找到最地道的英语表达方式，并生成每日学习汇总。
  触发词：怎么说、英语怎么表达、how to say、English expression、每日英语汇总、daily English summary。
---

# English Expression Helper

用户描述想表达的意思 → 推荐最地道的英语表达 → 记录到本地 → 每日汇总推送。

---

## 记录字段

| 字段 | 格式 | 说明 |
|------|------|------|
| id | string | UUID，自动生成 |
| date | `YYYY-MM-DD` | 记录日期 |
| username | string | 用户名，无法获取时填 `unknown` |
| query | string | 用户的原始提问（中文或英文） |
| expression | string | 推荐的英语表达 |
| phonetic | string | 音标（IPA） |
| pos | string | 词性（noun / verb / phrase / adj / adv 等） |
| example_sentence | string | 一个例句 |
| context | string | 适用场景说明（可选，简短） |
| tags | string | 逗号分隔关键词（话题、场景等） |

---

## 即时问答规范

### 核心原则

1. **只推荐高频表达**：推荐的单词/短语必须是日常高频使用的，高中生甚至小学生也能理解
2. **生僻词不推荐**：如果某个表达过于书面或生僻，跳过或换一个更常见的
3. **回复简洁**：直接给出推荐表达 + 音标 + 词性 + 一个例句即可
4. **正式/非正式**：仅当两者差异大且都高频时才分别列出，否则只给最常用的那一个
5. **支持多轮对话**：用户追问时继续提供帮助，必要时主动请用户补充上下文

### 回复格式

```
📝 推荐表达

**cold shoulder** /koʊld ˈʃoʊl.dɚ/ (phrase)
故意冷落、不理睬某人

> She gave me the cold shoulder after the argument.
> 吵架之后她就不理我了。

💡 场景：日常口语，非正式
```

若用户的提问有多种不同含义，先确认语境：

```
🤔 "打发时间"可以有几种理解：
1. 无聊时消磨时间
2. 有效利用空闲时间

你指的是哪种？我好推荐最合适的表达。
```

### 多轮对话

- 用户追问 "有没有更口语的说法" / "正式场合怎么说" → 继续推荐
- 用户追问 "能再给个例句吗" → 补充例句
- 用户提供更多上下文 → 据此调整推荐
- 每轮推荐的表达都会**自动记录**到本地存储

---

## 工作流程

### Step 1：理解用户意图

1. 用户用中文或英文描述想表达的意思
2. 若意图模糊或有多种理解，**先询问用户以确认语境**
3. 从对话上下文获取 username，无法获取 → 填 `unknown`

### Step 2：推荐表达

遵循以下规则：

1. **高频优先**：只推荐母语者日常使用的高频表达
2. **简单优先**：若有同义的简单词和复杂词，优先推荐简单词
3. **提供音标**：使用 IPA 音标
4. **提供词性**：noun / verb / phrase / adj / adv / idiom 等
5. **提供例句**：一个自然的例句 + 中文翻译
6. **场景标注**（可选）：仅在需要时标注（如"仅用于口语"、"偏正式"）

### Step 3：记录表达

每次推荐后，将记录写入本地存储。

**使用 `--records-file` 方式调用**（避免 shell 转义问题）：

```bash
# 1. 写入临时 JSON 文件
cat > /tmp/expression_records.json << 'JSONEOF'
[
  {
    "date": "2026-03-01",
    "username": "john_doe",
    "query": "故意冷落别人怎么说",
    "expression": "cold shoulder",
    "phonetic": "/koʊld ˈʃoʊl.dɚ/",
    "pos": "phrase",
    "example_sentence": "She gave me the cold shoulder after the argument.",
    "context": "日常口语，非正式",
    "tags": "社交,情绪,非正式"
  }
]
JSONEOF

# 2. 调用写入脚本
python3 <SKILL_DIR>/scripts/write_expression.py \
  --records-file /tmp/expression_records.json \
  --data-dir ~/openclaw-data/english/
```

> **重要**：`<SKILL_DIR>` = 此 SKILL.md 文件所在目录的绝对路径。
>
> 详细存储规范见 `references/expression_db_spec.md`。

### Step 4：确认反馈

```
✅ 已记录！今日累计学习 5 个表达。
```

---

## 每日汇总

### 触发方式

- 定时任务（通过 openclaw cron 配置）：每天东八区早上 7:00 自动生成并推送到 Discord `#english-learning` 频道
- 用户手动请求："今日英语汇总"、"daily English summary"

### 生成命令

```bash
python3 <SKILL_DIR>/scripts/generate_daily_summary.py \
  --data-dir ~/openclaw-data/english/ \
  --username <USERNAME> \
  --date <YYYY-MM-DD> \
  --include-review \
  --output ~/openclaw-data/english/summaries/daily_<YYYY-MM-DD>.md
```

- `--include-review`：从过去 30 天的高频错词/重点词中随机抽取 2-3 个混入推送
- 详细规范见 `references/daily_summary_spec.md`

### 推送格式

```
📚 每日英语汇总 | 2026-03-01（共 8 个表达）

| # | 你的问题 | 推荐表达 | 音标 | 词性 | 例句 |
|---|---------|---------|------|------|------|
| 1 | 故意冷落别人 | cold shoulder | /koʊld ˈʃoʊl.dɚ/ | phrase | She gave me the cold shoulder. |
| 2 | 拖延 | procrastinate | /prəˈkræs.tɪ.neɪt/ | verb | Stop procrastinating and start now. |
| ... | | | | | |

🔁 复习回顾（来自过去 30 天）

| # | 表达 | 音标 | 含义 | 出现次数 |
|---|------|------|------|---------|
| 1 | get the hang of | /ɡɛt ðə hæŋ ʌv/ | 掌握窍门 | 3 次 |
| 2 | burning out | /ˈbɜːr.nɪŋ aʊt/ | 精疲力竭 | 2 次 |
```

---

## 历史查询

用户可以请求查看过去的学习记录：

- "我上周学了哪些表达" → 读取最近 7 天的记录并列出
- "这个月的英语汇总" → 读取本月所有记录

数据保留**至少 30 天**供复习和汇总使用。

---

## 特殊场景处理

| 场景 | 处理方式 |
|------|---------|
| 用户描述模糊 | 先确认语境，提供选项让用户选择 |
| 用户问的是语法而非表达 | 简要解释语法点，但核心仍聚焦于推荐表达 |
| 同一表达重复提问 | 正常回答，记录时自动去重（同 date+username+expression） |
| 用户要求更多例句 | 补充 1-2 个例句，不重复记录同一表达 |
| 用户用英文提问 | 同样支持，帮助润色或推荐更地道的替代表达 |
| 生僻/过度书面的表达 | 不推荐，换一个更常见的高频表达 |
