---
name: daily-schedule-parser
description: |
  解析日程流水账/语音转写为结构化CSV。触发词：整理日程、记录今天、写入日程、帮我记录、record my day、log schedule。也处理周报请求（周报、weekly report、时间统计）。
---

# Daily Schedule Parser

解析碎片化日程 → 结构化 CSV → 统计分析 & 周报。

---

## 记录字段

| 字段 | 格式 | 说明 |
|------|------|------|
| date | `YYYY-MM-DD` | 记录日期 |
| username | string | Telegram username，无法获取时填 `unknown` |
| start_time | `HH:MM` | 24h 制开始时间 |
| end_time | `HH:MM` | 24h 制结束时间 |
| duration_min | int | 脚本自动计算，**提交时可留空** |
| category | string | 主分类 |
| sub_category | string | 子分类 |
| content | string | **纯客观事实**（when/where/who/what/why） |
| reflection | string | **主观表达**：情绪、感想、评价（可为空） |
| tags | string | 逗号分隔关键词（人名、项目名、工具名等） |

---

## 分类体系（可灵活扩展）

| 主分类 | 常见子分类 |
|--------|-----------|
| 工作 | 写作、会议、学习、规划、开发、沟通、行政 |
| 生活 | 用餐、购物、家务、休闲、人际、理财 |
| 通勤 | 上班通勤、下班通勤 |
| 健康 | 运动、睡眠、就医、饮食 |
| 社交 | 朋友、家人、同事、职业引荐 |

> 优先选最能反映活动本质的分类。若有更贴切的名称可自行创建。

---

## 时间解析规则

所有时间**必须转为 24h 制 `HH:MM`** 存储：

| 用户输入 | 解析结果 |
|----------|----------|
| `14:30` / `09:00` | 原样保留 |
| `3pm` / `2:30pm` | `15:00` / `14:30` |
| `9am` / `11:30am` | `09:00` / `11:30` |
| `下午两点半` / `上午9点` | `14:30` / `09:00` |
| `早上`（模糊） | ≈`07:00`，content 中标注"（约）" |
| `上午`（模糊） | ≈`09:00`，content 中标注"（约）" |
| `中午`（模糊） | ≈`12:00`，content 中标注"（约）" |
| `下午`（模糊） | ≈`14:00`，content 中标注"（约）" |
| `晚上`（模糊） | ≈`19:00`，content 中标注"（约）" |
| `吃完饭后` 等推断 | 根据上下文推断，content 中标注"（约）" |

---

## 工作流程

### Step 1：确认日期 & 用户

1. 从输入中提取日期。若未提及 → 询问：`"请问这是哪天的记录？还是就是今天（YYYY-MM-DD）？"`
2. 从对话上下文获取 Telegram username。无法获取 → 填 `unknown`。

### Step 2：解析文本 → 结构化记录

逐条提取事件，应用以下规则：

1. **时间转换**：遵循上方「时间解析规则」表
2. **并行事件拆分**：同一时段多件事 → 拆成多条记录，时间相同
3. **content / reflection 分离**：
   - `content`：只写客观事实，保留地点、人物、细节
   - `reflection`：所有主观表达移入此字段
4. **tags 生成**：从内容提取关键词（人名、项目名、工具名、地点）
5. **语音容错**：忽略重复词、口语填充词（"那个"、"就是"、"然后"），推断真实含义

### Step 3：时间冲突检测

输出预览前检查所有记录。若两条**非并行**记录的时间段互相覆盖：

> ⚠️ 我注意到 XX:XX-XX:XX 有冲突：[事件A] 和 [事件B]，请问哪个时间正确？

**必须等用户确认后再继续。**

### Step 4：输出预览

展示解析结果表格，必须让用户确认后再写入：

```
📋 解析完成，共 N 条记录：

| # | 时间 | 分类 | 子分类 | 内容 | 感想 | 标签 |
|---|------|------|--------|------|------|------|
| 1 | 08:54-09:35 | 生活 | 起床准备 | 起床，准备上班 | | 起床 |
| 2 | 09:35-10:40 | 通勤 | 上班通勤 | 乘地铁去公司 | | 通勤,地铁 |
...

✅ 确认写入？需要修改哪条？
```

### Step 5：写入 CSV

用户确认后，**使用 `--records-file` 方式调用**（避免 shell 转义问题）：

```bash
# 1. 写入临时 JSON 文件
cat > /tmp/schedule_records.json << 'JSONEOF'
[
  {"date":"2026-02-25","username":"john_doe","start_time":"08:54","end_time":"09:35","category":"生活","sub_category":"起床准备","content":"起床，准备上班","reflection":"","tags":"起床"},
  {"date":"2026-02-25","username":"john_doe","start_time":"09:35","end_time":"10:40","category":"通勤","sub_category":"上班通勤","content":"乘地铁去公司","reflection":"","tags":"通勤,地铁"}
]
JSONEOF

# 2. 调用写入脚本（<SKILL_DIR> 替换为此 skill 文件所在目录的绝对路径）
python3 <SKILL_DIR>/scripts/write_csv.py \
  --records-file /tmp/schedule_records.json \
  --data-dir ~/openclaw-data/schedules/
```

> **重要**：`<SKILL_DIR>` = 此 SKILL.md 文件所在目录的绝对路径。写入前确保目录存在。
>
> 若需覆盖已有记录（同 date+username+start_time），追加 `--overwrite` 参数。
>
> 详细 CSV 格式规范见 `references/csv_spec.md`。

### Step 6：完成反馈

脚本执行成功后，告知用户：

```
✅ 已写入 N 条记录。
📊 时间分布：工作 3.5h / 生活 2h / 通勤 1.5h
```

**若脚本报错**：向用户展示错误信息，并尝试诊断（常见原因：目录不存在、Python 版本、文件权限）。

---

## 周报生成

**触发**：用户说"周报"、"本周总结"、"时间统计"、"weekly report"，或每周六/日主动提醒。

```bash
python3 <SKILL_DIR>/scripts/generate_weekly_report.py \
  --data-dir ~/openclaw-data/schedules/ \
  --username <USERNAME> \
  --week-start <MONDAY_YYYY-MM-DD> \
  --output ~/openclaw-data/reports/weekly_<MONDAY_YYYY-MM-DD>.md
```

- `--week-start` 填该周**周一**日期
- 脚本生成 Markdown 报告，包含：时间分配总览、高频事件 Top 10、情绪洞察
- 详细规范见 `references/weekly_report_spec.md`

---

## 特殊场景处理

| 场景 | 处理方式 |
|------|---------|
| 用户只输入部分时间段 | 仅记录提及的时段，不补全整天 |
| 跨午夜事件（如 23:00-01:00） | 正常记录，脚本已处理负时差 |
| 用户要求修改已写入记录 | 使用 `--overwrite` 重写对应条目 |
| 用户输入多天记录 | 按日期拆分，分别归入各月份 CSV |
| 隐私脱敏 | 默认保留所有信息；用户明确要求时才脱敏 |
| 语音转写质量差 | 容错处理，提取核心信息，不确定处标注"（约）"后请用户确认 |
