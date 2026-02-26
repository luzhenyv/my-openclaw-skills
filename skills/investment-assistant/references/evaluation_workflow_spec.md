```markdown
# 每日评估工作流规范（Multi-Agent 架构）

## 概述

每日盘后评估（Daily Post-Market Evaluation）是本系统的核心功能。采用 OpenClaw Sub-Agents 实现并行多 Agent 评估架构。每个交易日收盘后（美东16:30），自动对所有 `pending` 和 `triggered` 状态的投资计划进行多维度分析和评估。

## 触发方式

- **自动触发**：OpenClaw Cron 每个交易日（周一至周五）美东 16:30 触发
- **手动触发**：用户可以随时说"评估一下 TSLA"或"今天的盘后分析"
- **周报触发**：每周六美东 10:00 触发，使用周线级别分析

## Agent 角色

| Agent | 类型 | 职责 | 并行 |
|-------|------|------|------|
| **Orchestrator** | 主 Agent | 协调流程、收集结果、记录报告 | - |
| **技术面分析师** | Sub-Agent | 获取 OHLCV/指标/K线 + 技术分析 | ✅ Phase 1 |
| **消息面分析师** | Sub-Agent | 获取新闻 + 消息面分析 | ✅ Phase 1 |
| **基本面分析师** | Sub-Agent | 获取基本面 + 基本面分析 | ✅ Phase 1 |
| **投资评估师** | Sub-Agent | 多空辩论 + 综合评估 + 最终决策 | Phase 2 |

## 工作流步骤

### Phase 0: 准备（Orchestrator）

```
1. 读取投资计划
   └─ python3 <SKILL_DIR>/scripts/plan_crud.py list --status pending,triggered

2. 按 symbol 去重，确定评估列表
```

### Phase 1: 三维分析（3 个 Sub-Agent 并行）

对每个 symbol，Orchestrator 同时 spawn 三个 Sub-Agent：

```
sessions_spawn ─┬─ 📈 技术面分析师 (label: market-analyst-{SYMBOL})
                │   ├─ 获取 OHLCV、技术指标、K线图
                │   ├─ 读取 references/market_analyst_prompt.md
                │   └─ 执行分析 → announce JSON 结果
                │
                ├─ 📰 消息面分析师 (label: news-analyst-{SYMBOL})
                │   ├─ 获取公司新闻、全球新闻
                │   ├─ 读取 references/news_analyst_prompt.md
                │   └─ 执行分析 → announce JSON 结果
                │
                └─ 📊 基本面分析师 (label: fundamentals-analyst-{SYMBOL})
                    ├─ 获取基本面数据（含季度缓存）
                    ├─ 读取 references/fundamentals_analyst_prompt.md
                    └─ 执行分析 → announce JSON 结果
```

**Sub-Agent 任务模板**（位于 references/ 目录）：
- `subagent_market_analyst_task.md`
- `subagent_news_analyst_task.md`
- `subagent_fundamentals_analyst_task.md`

#### 技术面分析师变量替换表

| 变量 | 值 | 说明 |
|------|-----|------|
| `{ticker}` | 如 `TSLA` | 股票代码 |
| `{symbol_lower}` | 如 `tsla` | 小写，用于文件名 |
| `{SKILL_DIR}` | SKILL.md 所在目录的绝对路径 | 脚本路径前缀 |
| `{current_date}` | 如 `2026-02-26` | 当前日期 |
| `{lookback_days}` | `60`（日常）/ `120`（周报） | 数据回溯天数 |
| `{period}` | `daily`（日常）/ `weekly`（周报） | K 线周期 |
| `{chart_days}` | `60`（日常）/ `120`（周报） | K 线图天数 |

```
sessions_spawn:
  task: "（填充后的 subagent_market_analyst_task.md 内容）"
  label: "market-analyst-{SYMBOL}"
```

#### 消息面分析师变量替换表

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

#### 基本面分析师变量替换表

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

#### 投资评估师变量替换表（Phase 2）

| 变量 | 值 |
|------|-----|
| `{ticker}` | 股票代码 |
| `{current_date}` | 当前日期 |
| `{SKILL_DIR}` | 脚本路径前缀 |
| `{plan_id}` | 计划 ID |
| `{plan_info}` | 完整的计划 JSON 信息 |
| `{market_analysis}` | Phase 1a 技术面分析报告（`report` 字段） |
| `{news_analysis}` | Phase 1b 消息面分析报告（`report` 字段） |
| `{fundamentals_analysis}` | Phase 1c 基本面分析报告（`report` 字段） |

```
sessions_spawn:
  task: "（填充后的 subagent_evaluator_task.md 内容）"
  label: "evaluator-{SYMBOL}"
```

### Phase 1→2 过渡: 结果收集（Orchestrator）

```
3. 收到 Sub-Agent announce 消息
   ├─ 解析 JSON 结果（从 ```json 代码块提取）
   ├─ 按 agent 类型 + ticker 分类存储
   ├─ 检查该 symbol 的 3 份报告是否收齐
   └─ 3/3 收齐 → 触发 Phase 2
```

### Phase 2: 辩论与综合评估（1 个 Sub-Agent）

```
sessions_spawn ─── 🎯 投资评估师 (label: evaluator-{SYMBOL})
                    ├─ 输入：3 份分析报告 + 计划信息
                    ├─ Step 1: 看多辩论 (读取 bull_researcher_prompt.md)
                    ├─ Step 2: 看空辩论 (读取 bear_researcher_prompt.md)
                    ├─ Step 3: 综合评估 (读取 risk_evaluator_prompt.md)
                    └─ announce JSON 结果（含决策 + 评分 + 信心度）
```

**任务模板**：`subagent_evaluator_task.md`

> 同一 symbol 多个计划：分析复用，评估按计划分别 spawn。

### Phase 3: 记录与通知（Orchestrator）

```
4. 收到评估师 announce → 提取结果
5. 写入评估 CSV → write_evaluation.py
6. 归档重要新闻（如有）→ write_news_archive.py
7. 格式化 Telegram 报告 → 推送
```

## Sub-Agent 通信协议

所有 Sub-Agent 的 announce 消息必须是包含 ```json 代码块的结构化 JSON。

### 技术面分析师返回格式
```json
{
  "agent": "market_analyst",
  "ticker": "TSLA",
  "status": "success|partial|error",
  "current_price": 408.50,
  "technical_score": 62,
  "signal": "偏多",
  "report": "（Markdown 报告）",
  "data_issues": [],
  "error": null
}
```

### 消息面分析师返回格式
```json
{
  "agent": "news_analyst",
  "ticker": "TSLA",
  "status": "success|partial|error",
  "news_score": 55,
  "signal": "中性",
  "report": "（Markdown 报告）",
  "significant_news": [...],
  "data_issues": [],
  "error": null
}
```

### 基本面分析师返回格式
```json
{
  "agent": "fundamentals_analyst",
  "ticker": "TSLA",
  "status": "success|partial|error",
  "fundamentals_score": 68,
  "signal": "较好",
  "report": "（Markdown 报告）",
  "data_issues": [],
  "error": null
}
```

### 投资评估师返回格式
```json
{
  "agent": "investment_evaluator",
  "ticker": "TSLA",
  "plan_id": "plan_001",
  "status": "success|error",
  "weighted_score": 62,
  "verdict": "wait",
  "confidence": 65,
  "reason": "...",
  "bull_summary": "...",
  "bear_summary": "...",
  "action_items": [...],
  "full_evaluation": "（Markdown 报告）",
  "error": null
}
```

## 周报模式差异

| 项目 | 每日评估 | 周报评估 |
|------|---------|---------|
| K 线图 | 日线 60 天 | 周线 120 天 |
| 新闻范围 | 7 天 | 14 天 |
| 分析深度 | 常规 | 加入周线级别趋势判断 |
| 额外内容 | 无 | 本周评估回顾 + 趋势变化 |

## 错误处理

- Sub-Agent 超时（`runTimeoutSeconds`）：announce 中 Status 为 timeout，标记该维度为 N/A
- Sub-Agent 执行失败：announce 中 Status 为 error，标记该维度为 N/A
- 部分分析缺失：评估师使用可用报告评估，调整权重比例
- 全部 Sub-Agent 失败：跳过该 symbol，报告中注明"评估失败"
- 所有错误都应在最终报告中述明

## 性能考虑

- Phase 1 三个 Sub-Agent 并行执行，比顺序快约 60%
- 按 symbol 去重：同一股票只 spawn 一组分析 Sub-Agent
- 基本面 Sub-Agent 内部处理季度缓存
- 建议为 Sub-Agent 设置较低成本的 model（`agents.defaults.subagents.model`）
- 每个 symbol 的完整评估约需 2-3 分钟（并行模式）
- 推荐 `maxConcurrent: 8`，可同时评估 2 个 symbol

## 推荐的 OpenClaw 配置

```jsonc
{
  "agents": {
    "defaults": {
      "subagents": {
        "maxSpawnDepth": 1,
        "maxChildrenPerAgent": 5,
        "maxConcurrent": 8,
        "runTimeoutSeconds": 300
      }
    }
  }
}
```

## Phase 3 操作命令

### 3a. 记录评估结果

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

各字段值直接从 evaluator 的 JSON 结果中提取。

### 3b. 归档重要新闻（如有）

如果消息面分析师返回的 `significant_news` 非空：

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

### 3c. 推送评估报告

格式化为 Telegram 消息，详见 `report_format_spec.md`。

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
| Sub-Agent announce 失败 | Gateway 自动重试，最终失败则标记为 N/A |
| 并发控制 | 由 OpenClaw `maxConcurrent` 配置控制，默认 8 |
```
