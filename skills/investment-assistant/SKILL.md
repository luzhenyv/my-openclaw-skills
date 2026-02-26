---
name: investment-assistant
description: |
  个人投资计划管理 + 智能盘后评估系统（Multi-Agent 架构）。
  核心功能：① 投资计划 CRUD 管理（备忘录）② 每日盘后自动多维度评估。
  触发词：添加计划、新建计划、投资计划、查看计划、评估、盘后分析、今日分析、
  周报、投资周报、plan、evaluate、analysis、weekly review。
---

# Investment Assistant

投资计划管理 → 自动获取市场数据 → 技术/消息/基本面三维分析 → 多空辩论 → 综合评估 → 推送报告。

改编自 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 的核心分析框架，使用 **OpenClaw Sub-Agents** 实现多 Agent 并行评估。

## 系统架构

```
investment-assistant (Orchestrator 主协调者)
│
├── 计划管理 ──── 直接处理，不需要 Sub-Agent
│
├── 评估 Phase 1: 三维分析（3 个 Sub-Agent 并行）
│   ├── 📈 技术面分析师  ── sessions_spawn → 获取数据 + 技术分析
│   ├── 📰 消息面分析师  ── sessions_spawn → 获取新闻 + 消息分析
│   └── 📊 基本面分析师  ── sessions_spawn → 获取财报 + 基本面分析
│
├── 评估 Phase 2: 辩论与决策（1 个 Sub-Agent，等 Phase 1 全部完成后触发）
│   └── 🎯 投资评估师   ── sessions_spawn → 多空辩论 + 综合评估 + 最终决策
│
└── 评估 Phase 3: 记录与报告 ── 直接处理
    ├── 写入评估 CSV
    ├── 归档重要新闻
    └── 格式化并推送 Telegram 报告
```

**并行优势**：Phase 1 的三个分析师 Sub-Agent 同时执行，评估耗时减少约 60%。

---

## 一、投资计划管理

### 计划字段

| 字段 | 格式 | 说明 |
|------|------|------|
| id | string | `plan_XXX` 格式，自动生成 |
| status | string | `pending` / `triggered` / `executed` / `cancelled` / `expired` |
| market | string | `US` / `HK` / `CN` |
| symbol | string | 股票代码，如 `TSLA`、`0700.HK` |
| direction | string | `long`（做多）/ `short`（做空）/ `hedge`（对冲） |
| target_price | number | 目标价格 |
| price_range | object | `{"low": 380, "high": 420}` 理想入场/出场区间 |
| quantity | string | 数量或金额描述，如 "100股" / "$5000" |
| priority | string | `high` / `medium` / `low` |
| thesis | string | 投资论点（核心逻辑） |
| created_at | string | 创建日期 `YYYY-MM-DD` |
| updated_at | string | 最近更新日期 |
| expires_at | string | 到期日期（创建后 3 个月） |
| notes | string | 备注 |

详细规范见 `references/plan_spec.md`。

### 计划管理指令

用户说"添加计划"、"新建一个投资计划"等 → 进入计划创建流程：

1. 引导用户提供：市场、代码、方向、目标价、区间、数量、优先级、论点
2. 对于用户未提供的可选字段，使用合理默认值
3. 预览 → 用户确认 → 写入

#### 创建计划

```bash
cat > /tmp/plan_record.json << 'JSONEOF'
{
  "action": "add",
  "market": "US",
  "symbol": "TSLA",
  "direction": "long",
  "target_price": 450,
  "price_range_low": 380,
  "price_range_high": 420,
  "quantity": "100股",
  "priority": "high",
  "thesis": "FSD V13 全面推送将大幅提升订阅收入"
}
JSONEOF

python3 <SKILL_DIR>/scripts/plan_crud.py add \
  --record-file /tmp/plan_record.json \
  --data-dir ~/openclaw-data/investment
```

#### 查看计划

```bash
# 列出所有活跃计划
python3 <SKILL_DIR>/scripts/plan_crud.py list \
  --data-dir ~/openclaw-data/investment \
  --status pending,triggered

# 查看特定计划
python3 <SKILL_DIR>/scripts/plan_crud.py get \
  --data-dir ~/openclaw-data/investment \
  --plan-id plan_001
```

#### 更新计划

```bash
cat > /tmp/plan_update.json << 'JSONEOF'
{
  "action": "update",
  "plan_id": "plan_001",
  "target_price": 460,
  "notes": "上调目标价，FSD进展超预期"
}
JSONEOF

python3 <SKILL_DIR>/scripts/plan_crud.py update \
  --record-file /tmp/plan_update.json \
  --data-dir ~/openclaw-data/investment
```

#### 删除/取消计划

```bash
python3 <SKILL_DIR>/scripts/plan_crud.py delete \
  --data-dir ~/openclaw-data/investment \
  --plan-id plan_001
```

> **重要**：`<SKILL_DIR>` = 此 SKILL.md 文件所在目录的绝对路径。

---

## 二、每日盘后评估（Multi-Agent 流程）

### 触发方式

- **自动（Cron）**：每个交易日美东 16:30（`30 20 * * 1-5` UTC）
- **手动**：用户说"评估 TSLA"、"今日盘后分析"、"分析一下我的计划"

### 评估对象

所有 `status = pending` 或 `status = triggered` 的计划。手动触发时也可指定单只股票。

### Phase 0：准备工作（Orchestrator 直接执行）

```bash
# 读取所有活跃计划
python3 <SKILL_DIR>/scripts/plan_crud.py list \
  --data-dir ~/openclaw-data/investment \
  --status pending,triggered
```

解析输出，按 symbol 去重，确定本次需要评估的股票列表。

### Phase 1：三维分析（3 个 Sub-Agent 并行）

对**每个 symbol**，同时 spawn 三个 Sub-Agent。使用 `sessions_spawn` 工具：

> **Sub-Agent 成本提示**：建议在 OpenClaw 配置中为 sub-agent 设置较低成本的 model：
> `agents.defaults.subagents.model` 或 per-agent `agents.list[].subagents.model`

#### 1a. Spawn 技术面分析师

读取 `references/subagent_market_analyst_task.md` 模板，填充以下变量后作为 `task` 参数：

| 变量 | 值 | 说明 |
|------|-----|------|
| `{ticker}` | 如 `TSLA` | 股票代码 |
| `{symbol_lower}` | 如 `tsla` | 小写，用于文件名 |
| `{SKILL_DIR}` | 此 SKILL.md 所在目录的绝对路径 | 脚本路径前缀 |
| `{current_date}` | 如 `2026-02-26` | 当前日期 |
| `{lookback_days}` | `60`（日常）/ `120`（周报） | 数据回溯天数 |
| `{period}` | `daily`（日常）/ `weekly`（周报） | K 线周期 |
| `{chart_days}` | `60`（日常）/ `120`（周报） | K 线图天数 |

```
sessions_spawn:
  task: "（填充后的 subagent_market_analyst_task.md 内容）"
  label: "market-analyst-{SYMBOL}"
```

#### 1b. Spawn 消息面分析师

读取 `references/subagent_news_analyst_task.md` 模板，填充以下变量：

| 变量 | 值 |
|------|-----|
| `{ticker}` | 股票代码 |
| `{symbol_lower}` | 小写 |
| `{SKILL_DIR}` | 脚本路径前缀 |
| `{current_date}` | 当前日期 |
| `{news_days}` | `7`（日常）/ `14`（周报） |

```
sessions_spawn:
  task: "（填充后的 subagent_news_analyst_task.md 内容）"
  label: "news-analyst-{SYMBOL}"
```

#### 1c. Spawn 基本面分析师

读取 `references/subagent_fundamentals_analyst_task.md` 模板，填充以下变量：

| 变量 | 值 |
|------|-----|
| `{ticker}` | 股票代码 |
| `{symbol_lower}` | 小写 |
| `{SKILL_DIR}` | 脚本路径前缀 |
| `{current_date}` | 当前日期 |

```
sessions_spawn:
  task: "（填充后的 subagent_fundamentals_analyst_task.md 内容）"
  label: "fundamentals-analyst-{SYMBOL}"
```

#### Phase 1 并行执行说明

三个 `sessions_spawn` 调用是**非阻塞**的，立即返回 `runId`。Orchestrator 的本轮处理结束。

当每个 Sub-Agent 完成后，会通过 **announce** 机制向 Orchestrator 发送一条系统消息，内容为该 Sub-Agent 的 JSON 结果。

### Phase 1→2 过渡：收集分析结果

Orchestrator 需要追踪三个 Sub-Agent 的 announce 结果。

**收到每条 announce 时的处理逻辑**：

1. 解析 announce 消息中的 JSON（从 ```json 代码块提取）
2. 根据 `agent` 字段（`market_analyst` / `news_analyst` / `fundamentals_analyst`）和 `ticker` 字段分类存储
3. 检查该 symbol 的三份分析报告是否已全部收集完毕
4. **如果三份都已收齐** → 进入 Phase 2，spawn 投资评估师
5. **如果尚未收齐** → 等待下一个 announce

**状态追踪**（在回复中维护）：
```
📊 {SYMBOL} 评估进度:
  ✅ 技术面分析师 - 完成 (score: 62)
  ✅ 消息面分析师 - 完成 (score: 55)
  ⏳ 基本面分析师 - 进行中...
  收集进度: 2/3
```

### Phase 2：辩论与综合评估（1 个 Sub-Agent）

三份分析报告收齐后，spawn 投资评估师。

读取 `references/subagent_evaluator_task.md` 模板，填充以下变量：

| 变量 | 值 |
|------|-----|
| `{ticker}` | 股票代码 |
| `{current_date}` | 当前日期 |
| `{SKILL_DIR}` | 脚本路径前缀 |
| `{plan_id}` | 计划 ID |
| `{plan_info}` | 完整的计划 JSON 信息 |
| `{market_analysis}` | Phase 1a 收到的技术面分析报告（`report` 字段） |
| `{news_analysis}` | Phase 1b 收到的消息面分析报告（`report` 字段） |
| `{fundamentals_analysis}` | Phase 1c 收到的基本面分析报告（`report` 字段） |

```
sessions_spawn:
  task: "（填充后的 subagent_evaluator_task.md 内容）"
  label: "evaluator-{SYMBOL}"
```

> **同一只股票有多个计划**时：分析报告复用，但为每个 plan 分别 spawn 一个评估师（因为计划的方向、目标价不同会影响评估结果）。

### Phase 3：记录与报告（Orchestrator 直接执行）

收到投资评估师的 announce 后，解析 JSON 结果，执行以下操作：

#### 3a. 记录评估结果

```bash
cat > /tmp/eval_record.json << 'JSONEOF'
[
  {
    "date": "{date}",
    "symbol": "{ticker}",
    "market": "{market}",
    "direction": "{direction}",
    "plan_id": "{plan_id}",
    "target_price": {target_price},
    "current_price": {current_price},
    "price_in_range": "{true/false}",
    "technical_score": {technical_score},
    "news_score": {news_score},
    "fundamentals_score": {fundamentals_score},
    "verdict": "{verdict}",
    "confidence": {confidence},
    "reason": "{reason}"
  }
]
JSONEOF

python3 <SKILL_DIR>/scripts/write_evaluation.py \
  --data-dir ~/openclaw-data/investment \
  --records-file /tmp/eval_record.json
```

其中各字段值直接从 evaluator 的 JSON 结果中提取。

#### 3b. 归档重要新闻（如有）

如果 Phase 1b 消息面分析师返回的 `significant_news` 非空：

```bash
cat > /tmp/news_records.json << 'JSONEOF'
[
  {
    "date": "{date}",
    "symbol": "{ticker}",
    "headline": "{headline}",
    "source": "{source}",
    "summary": "{summary}",
    "sentiment": "{sentiment}",
    "is_significant": "true"
  }
]
JSONEOF

python3 <SKILL_DIR>/scripts/write_news_archive.py \
  --data-dir ~/openclaw-data/investment \
  --records-file /tmp/news_records.json
```

#### 3c. 推送评估报告

将 evaluator 结果格式化为 Telegram 消息，格式参见 `references/report_format_spec.md`。

单只股票格式：
```
📊 盘后评估 - {SYMBOL} ({DATE})

💰 当前: ${PRICE} | 目标: ${TARGET} ({DIRECTION})
📈 区间: ${LOW} - ${HIGH} {IN_RANGE_EMOJI}

🔧 技术面: {TECH}/100 ({SIGNAL})
📰 消息面: {NEWS}/100 ({SIGNAL})
📊 基本面: {FUND}/100 ({SIGNAL})
📈 综合: {WEIGHTED}/100

🐂 看多: {BULL_SUMMARY}
🐻 看空: {BEAR_SUMMARY}

🎯 决策: {VERDICT_EMOJI} {VERDICT_TEXT}
🔒 信心: {CONFIDENCE}%
💡 {REASON}

📌 关注: {ACTION_ITEMS}
```

多只股票汇总（所有 symbol 的评估都完成后）：
```
📋 盘后评估汇总 ({DATE})
━━━━━━━━━━━━━━━━━━
1️⃣ {SYMBOL} | {SCORE}/100 | {VERDICT_EMOJI} | {CONFIDENCE}%
   {REASON_SHORT}
...
━━━━━━━━━━━━━━━━━━
📊 活跃计划: {N} | 今日评估: {M}
```

### Sub-Agent 超时与错误处理

| 场景 | 处理方式 |
|------|---------|
| Sub-Agent 超时 | announce 中 `Status: timeout`，该维度评分标记为 N/A，继续其余流程 |
| Sub-Agent 失败 | announce 中 `Status: error`，该维度评分标记为 N/A，在报告中注明 |
| 部分分析缺失 | 评估师仅使用可用报告进行评估，调整权重 |
| 全部 Sub-Agent 失败 | 跳过该 symbol，报告中注明"评估失败" |

建议在 OpenClaw 配置中设置合理超时：
```jsonc
{
  "agents": {
    "defaults": {
      "subagents": {
        "runTimeoutSeconds": 300,  // 每个 sub-agent 最多 5 分钟
        "maxConcurrent": 8,
        "maxChildrenPerAgent": 5
      }
    }
  }
}
```

> **重要**：`<SKILL_DIR>` = 此 SKILL.md 文件所在目录的绝对路径。

---

## 三、周报

### 触发方式

- **自动（Cron）**：每周六美东 10:00（`0 14 * * 6` UTC）
- **手动**：用户说"投资周报"、"本周总结"、"weekly review"

### 周报差异（Sub-Agent 参数调整）

周报使用与每日评估相同的 Multi-Agent 流程，但 spawn Sub-Agent 时调整以下参数：

| 变量 | 每日评估 | 周报 |
|------|---------|------|
| `{lookback_days}` | 60 | 120 |
| `{period}` | daily | weekly |
| `{chart_days}` | 60 | 120 |
| `{news_days}` | 7 | 14 |

### 周报额外内容

在 Phase 3 报告阶段，周报额外包含：
1. **本周评分趋势**：读取本周的评估 CSV，展示每日评分变化
2. **到期提醒**：调用 `check_expiring_plans.py --days 14` 检查即将到期的计划

### 周报格式

见 `references/report_format_spec.md` 中的周报模板。

---

## 四、计划到期检查

### 触发方式

- **自动（Cron）**：每周一美东 09:00（`0 13 * * 1` UTC）

```bash
python3 <SKILL_DIR>/scripts/check_expiring_plans.py \
  --data-dir ~/openclaw-data/investment \
  --days 14
```

如有即将到期的计划，推送提醒：
```
⚠️ 投资计划到期提醒

🔴 已过期:
  plan_003 AAPL 做多→$200 (过期2天)

🟡 即将到期 (14天内):
  plan_001 TSLA 做多→$450 (剩余8天)

请及时处理：执行、续期或取消。
```

---

## 五、历史查询

用户可以查询历史评估记录：

- "TSLA 上周的评估结果" → 读取评估 CSV，筛选对应日期和 symbol
- "最近一个月的评估趋势" → 读取 CSV 汇总评分变化
- "有什么重要新闻" → 读取新闻归档 CSV

评估数据存储在 `~/openclaw-data/investment/evaluations_YYYY-MM.csv`。
新闻归档存储在 `~/openclaw-data/investment/news_archive_YYYY-MM.csv`。

---

## 六、技术指标参考

本系统支持 13 个技术指标，详见 `references/technical_indicators_spec.md`：

- 均线系统：SMA50、SMA200、EMA10
- MACD 系统：MACD、Signal、Histogram
- 动量：RSI (14)、MFI
- 布林带：Upper、Middle、Lower
- 波动性：ATR
- 成交量：VWMA

---

## 七、配置

全局配置文件：`config/settings.json`

可配置项包括：数据源、默认指标列表、评估参数、计划过期时间等。

---

## 特殊场景处理

| 场景 | 处理方式 |
|------|---------|
| yfinance 数据获取失败 | Sub-Agent 返回 `status: "error"`，跳过该维度，报告中注明 |
| K 线图生成失败 | Sub-Agent 返回 `status: "partial"` + `data_issues`，跳过视觉分析 |
| 无新闻数据 | 消息面 Sub-Agent 评分标记为"数据不足"，其他维度正常评估 |
| 非交易日手动触发 | 正常执行，使用最近交易日数据 |
| 多个计划关注同一股票 | Phase 1 数据获取/分析只 spawn 一组 Sub-Agent，Phase 2 评估按计划分别 spawn |
| 港股/A股代码格式 | 港股用 `.HK` 后缀（如 `0700.HK`），A股用 `.SS`/`.SZ` 后缀 |
| 用户未提供完整信息 | 引导用户补全必填字段，可选字段使用默认值 |
| 基本面季度缓存 | 基本面 Sub-Agent 内部处理缓存逻辑 |
| Sub-Agent 超时 | 标记该维度为 N/A，用可用数据继续评估 |
| Sub-Agent announce 失败 | Gateway 自动重试，最终失败则标记为 N/A |
| 并发控制 | 由 OpenClaw `maxConcurrent` 配置控制，默认 8 |
