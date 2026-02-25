# 每日汇总规范

## 触发条件

- 定时任务：每天东八区早上 7:00 自动触发（通过 openclaw cron 配置）
- 用户手动请求："今日英语汇总"、"daily English summary"

## 推送渠道

Discord `#english-learning` 频道

## 数据来源

读取指定日期的 CSV 记录，按 date 字段过滤。

## 汇总结构

### 1. 当日新学表达

以表格形式展示当天所有记录：

```
📚 每日英语汇总 | 2026-03-01（共 8 个表达）

| # | 你的问题 | 推荐表达 | 音标 | 词性 | 例句 |
|---|---------|---------|------|------|------|
| 1 | 故意冷落别人 | cold shoulder | /koʊld ˈʃoʊl.dɚ/ | phrase | She gave me the cold shoulder. |
| 2 | 拖延 | procrastinate | /prəˈkræs.tɪ.neɪt/ | verb | Stop procrastinating and start now. |
```

### 2. 复习回顾（可选）

从过去 30 天的记录中，按以下规则挑选 2-3 个进行复习：

- **高频查询**：同一表达被多次查询（不同日期），优先复习
- **随机抽取**：若无高频词，则从过去 30 天中随机抽取

```
🔁 复习回顾（来自过去 30 天）

| # | 表达 | 音标 | 含义 | 出现次数 |
|---|------|------|------|---------|
| 1 | get the hang of | /ɡɛt ðə hæŋ ʌv/ | 掌握窍门 | 3 次 |
| 2 | burning out | /ˈbɜːr.nɪŋ aʊt/ | 精疲力竭 | 2 次 |
```

### 3. 无记录时的处理

若当天没有任何记录：

```
📚 每日英语汇总 | 2026-03-01

今天还没有新的学习记录哦！来问我一个英语表达吧 💪

🔁 复习一下之前学过的：
...（照常从历史记录中抽取复习内容）
```

## generate_daily_summary.py 调用规范

```bash
python3 scripts/generate_daily_summary.py \
  --data-dir ~/openclaw-data/english/ \
  --username john_doe \
  --date 2026-03-01 \
  --include-review \
  --output ~/openclaw-data/english/summaries/daily_2026-03-01.md
```

- `--include-review`：启用复习回顾功能（从过去 30 天抽取）
- `--output`：可选，不指定则打印到 stdout
- 输出为 Markdown 格式
