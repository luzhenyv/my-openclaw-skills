---
name: investment-assistant
description: |
  个人投资计划管理 + 智能盘后评估系统。
  核心功能：① 投资计划 CRUD 管理（备忘录）② 每日盘后自动多维度评估。
  触发词：添加计划、新建计划、投资计划、查看计划、评估、盘后分析、今日分析、
  周报、投资周报、plan、evaluate、analysis、weekly review。
---

# Investment Assistant

投资计划管理 → 自动获取市场数据 → 技术/消息/基本面三维分析 → 多空辩论 → 综合评估 → 推送报告。

改编自 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 的核心分析框架，采用单 Agent 顺序扮演多角色完成完整评估链。

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

## 二、每日盘后评估

### 触发方式

- **自动（Cron）**：每个交易日美东 16:30（`30 20 * * 1-5` UTC）
- **手动**：用户说"评估 TSLA"、"今日盘后分析"、"分析一下我的计划"

### 评估对象

所有 `status = pending` 或 `status = triggered` 的计划。手动触发时也可指定单只股票。

### 完整评估流程

对**每只股票**（按 symbol 去重）执行以下完整流程：

#### Step 1：获取市场数据

```bash
# 1a. OHLCV 数据
python3 <SKILL_DIR>/scripts/fetch_stock_data.py \
  --symbol {SYMBOL} --days 60 \
  --output /tmp/{symbol}_ohlcv.csv

# 1b. 技术指标
python3 <SKILL_DIR>/scripts/fetch_indicators.py \
  --symbol {SYMBOL} --all --lookback 60 \
  --output /tmp/{symbol}_indicators.json

# 1c. K线图（每日用daily，周报用weekly）
python3 <SKILL_DIR>/scripts/generate_chart.py \
  --symbol {SYMBOL} --period daily --days 60 \
  --output /tmp/{symbol}_chart.png

# 1d. 公司新闻
python3 <SKILL_DIR>/scripts/fetch_news.py \
  --mode company --symbol {SYMBOL} --days 7 \
  --output /tmp/{symbol}_company_news.json

# 1e. 全球宏观新闻
python3 <SKILL_DIR>/scripts/fetch_news.py \
  --mode global --days 3 \
  --output /tmp/global_news.json

# 1f. 基本面数据（带季度缓存）
python3 <SKILL_DIR>/scripts/fetch_fundamentals.py \
  --symbol {SYMBOL} \
  --data-dir ~/openclaw-data/investment \
  --output /tmp/{symbol}_fundamentals.json
```

#### Step 2：技术面分析（Market Analyst 角色）

读取 `references/market_analyst_prompt.md` 作为分析框架。

将以下数据填入模板变量：
- `{stock_data_csv}`：Step 1a 的 OHLCV 数据
- `{indicators_json}`：Step 1b 的技术指标
- `{chart_image_path}`：Step 1c 的 K 线图（使用 Vision 能力分析图像）
- `{ticker}`、`{current_date}`、`{period}`

执行分析，产出：**技术面分析报告** + **技术面评分 (0-100)**

#### Step 3：消息面分析（News Analyst 角色）

读取 `references/news_analyst_prompt.md` 作为分析框架。

将以下数据填入模板变量：
- `{company_news_json}`：Step 1d 的公司新闻
- `{global_news_json}`：Step 1e 的全球新闻
- `{ticker}`、`{current_date}`

执行分析，产出：**消息面分析报告** + **消息面评分 (0-100)** + **重要新闻列表（如有）**

#### Step 4：基本面分析（Fundamentals Analyst 角色）

读取 `references/fundamentals_analyst_prompt.md` 作为分析框架。

将以下数据填入模板变量：
- `{fundamentals_json}`：Step 1f 的基本面数据
- `{cached_memo}`：季度缓存 Markdown 备忘录（如有）
- `{ticker}`、`{current_date}`

执行分析，产出：**基本面分析报告** + **基本面评分 (0-100)**

#### Step 5：多空辩论

**看多方**：读取 `references/bull_researcher_prompt.md`，输入三份分析报告 + 计划信息，产出看多论点。

**看空方**：读取 `references/bear_researcher_prompt.md`，输入三份分析报告 + 计划信息，产出看空论点。

#### Step 6：综合评估与最终决策

读取 `references/risk_evaluator_prompt.md` 作为评估框架。

输入：三份分析报告 + 多空论点 + 完整计划信息。

产出：
- **加权综合评分**（技术面 30% + 消息面 30% + 基本面 40%）
- **最终决策**：`recommend_execute` / `wait` / `recommend_cancel`
- **信心度**（0-100%）
- **可操作建议**

#### Step 7：记录评估结果

```bash
# 写入评估记录
cat > /tmp/eval_record.json << 'JSONEOF'
[
  {
    "date": "{YYYY-MM-DD}",
    "symbol": "{SYMBOL}",
    "market": "{MARKET}",
    "direction": "{DIRECTION}",
    "plan_id": "{PLAN_ID}",
    "target_price": {TARGET_PRICE},
    "current_price": {CURRENT_CLOSE},
    "price_in_range": "{true/false}",
    "technical_score": {TECH_SCORE},
    "news_score": {NEWS_SCORE},
    "fundamentals_score": {FUND_SCORE},
    "verdict": "{recommend_execute/wait/recommend_cancel}",
    "confidence": {CONFIDENCE},
    "reason": "{简要原因}"
  }
]
JSONEOF

python3 <SKILL_DIR>/scripts/write_evaluation.py \
  --data-dir ~/openclaw-data/investment \
  --records-file /tmp/eval_record.json
```

#### Step 8：归档重要新闻（如有）

如果 Step 3 识别出重要新闻，归档保存：

```bash
cat > /tmp/news_records.json << 'JSONEOF'
[
  {
    "date": "{YYYY-MM-DD}",
    "symbol": "{SYMBOL}",
    "headline": "Tesla Q4 deliveries beat expectations",
    "source": "Reuters",
    "summary": "特斯拉Q4交付量超出市场预期...",
    "sentiment": "positive",
    "is_significant": "true"
  }
]
JSONEOF

python3 <SKILL_DIR>/scripts/write_news_archive.py \
  --data-dir ~/openclaw-data/investment \
  --records-file /tmp/news_records.json
```

#### Step 9：推送评估报告

将最终结果以 Telegram 消息格式输出，格式参见 `references/report_format_spec.md`。

单只股票格式：
```
📊 盘后评估 - {SYMBOL} ({DATE})

💰 当前: ${PRICE} | 目标: ${TARGET} ({DIRECTION})
📈 区间: ${LOW} - ${HIGH} {IN_RANGE_EMOJI}

🔧 技术面: {TECH}/100 ({SIGNAL})
📰 消息面: {NEWS}/100 ({SIGNAL})
📊 基本面: {FUND}/100 ({SIGNAL})
📈 综合: {WEIGHTED}/100

🎯 决策: {VERDICT_EMOJI} {VERDICT_TEXT}
🔒 信心: {CONFIDENCE}%
💡 {REASON}
```

多只股票汇总：
```
📋 盘后评估汇总 ({DATE})
━━━━━━━━━━━━━━━━━━
1️⃣ {SYMBOL} | {SCORE}/100 | {VERDICT_EMOJI} | {CONFIDENCE}%
   {REASON_SHORT}
...
━━━━━━━━━━━━━━━━━━
📊 活跃计划: {N} | 今日评估: {M}
```

---

## 三、周报

### 触发方式

- **自动（Cron）**：每周六美东 10:00（`0 14 * * 6` UTC）
- **手动**：用户说"投资周报"、"本周总结"、"weekly review"

### 周报差异

| 项目 | 每日评估 | 周报 |
|------|---------|------|
| K 线图 | 日线 60 天 | 周线 120 天 |
| 新闻范围 | 7 天 | 14 天 |
| 额外内容 | 无 | 本周评分趋势 + 到期提醒 |

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
| yfinance 数据获取失败 | 跳过该计划，报告中注明"数据获取失败" |
| K 线图生成失败 | 跳过视觉分析，仅用数值数据 |
| 无新闻数据 | 消息面评分标记为"数据不足"，其他维度正常评估 |
| 非交易日手动触发 | 正常执行，使用最近交易日数据 |
| 多个计划关注同一股票 | 数据获取只执行一次，分析复用，评估按计划分别记录 |
| 港股/A股代码格式 | 港股用 `.HK` 后缀（如 `0700.HK`），A股用 `.SS`/`.SZ` 后缀 |
| 用户未提供完整信息 | 引导用户补全必填字段，可选字段使用默认值 |
| 基本面季度缓存 | 同一季度内复用缓存，避免重复获取和分析 |
| 评估过程中某步骤出错 | 使用已有数据继续后续步骤，最终报告中注明缺失部分 |
