```markdown
# 每日评估工作流规范

## 概述

每日盘后评估（Daily Post-Market Evaluation）是本系统的核心功能。每个交易日收盘后（美东16:30），自动对所有 `pending` 和 `triggered` 状态的投资计划进行多维度分析和评估。

## 触发方式

- **自动触发**：OpenClaw Cron 每个交易日（周一至周五）美东 16:30 触发
- **手动触发**：用户可以随时说"评估一下 TSLA"或"今天的盘后分析"
- **周报触发**：每周六美东 10:00 触发，使用周线级别分析

## 工作流步骤

### Phase 1: 数据准备

对每个待评估的计划，按以下顺序获取数据：

```
1. 读取投资计划
   └─ python3 <SKILL_DIR>/scripts/plan_crud.py list --data-dir ~/openclaw-data/investment --status pending,triggered

2. 对每个计划的 symbol:
   ├─ 2a. 获取 OHLCV 数据
   │   └─ python3 <SKILL_DIR>/scripts/fetch_stock_data.py --symbol {SYMBOL} --days 60
   │
   ├─ 2b. 计算技术指标
   │   └─ python3 <SKILL_DIR>/scripts/fetch_indicators.py --symbol {SYMBOL} --all --lookback 60
   │
   ├─ 2c. 生成 K 线图
   │   └─ python3 <SKILL_DIR>/scripts/generate_chart.py --symbol {SYMBOL} --period daily --days 60
   │   （周报模式用 --period weekly --days 120）
   │
   ├─ 2d. 获取新闻
   │   ├─ python3 <SKILL_DIR>/scripts/fetch_news.py --mode company --symbol {SYMBOL} --days 7
   │   └─ python3 <SKILL_DIR>/scripts/fetch_news.py --mode global --days 3
   │
   └─ 2e. 获取基本面（使用缓存）
       └─ python3 <SKILL_DIR>/scripts/fetch_fundamentals.py --symbol {SYMBOL} --data-dir ~/openclaw-data/investment
```

### Phase 2: 分析

按以下顺序执行分析（每步读取对应的 prompt 模板）：

```
3. 技术面分析
   └─ 读取 references/market_analyst_prompt.md
   └─ 填充变量 → 执行分析 → 得到技术面报告 + 评分

4. 消息面分析
   └─ 读取 references/news_analyst_prompt.md
   └─ 填充变量 → 执行分析 → 得到消息面报告 + 评分

5. 基本面分析
   └─ 读取 references/fundamentals_analyst_prompt.md
   └─ 填充变量 → 执行分析 → 得到基本面报告 + 评分
```

### Phase 3: 辩论

```
6. 看多辩论
   └─ 读取 references/bull_researcher_prompt.md
   └─ 输入：三份分析报告 + 计划信息 → 得到看多论点

7. 看空辩论
   └─ 读取 references/bear_researcher_prompt.md
   └─ 输入：三份分析报告 + 计划信息 → 得到看空论点
```

### Phase 4: 综合评估

```
8. 风险评估与最终决策
   └─ 读取 references/risk_evaluator_prompt.md
   └─ 输入：三份分析报告 + 多空论点 + 计划信息
   └─ 输出：最终决策（recommend_execute / wait / recommend_cancel）
          + 综合评分 + 信心度 + 建议
```

### Phase 5: 记录与通知

```
9. 写入评估记录
   └─ python3 <SKILL_DIR>/scripts/write_evaluation.py \
        --data-dir ~/openclaw-data/investment \
        --records-file /tmp/eval_record.json

10. 归档重要新闻（如有）
    └─ python3 <SKILL_DIR>/scripts/write_news_archive.py \
         --data-dir ~/openclaw-data/investment \
         --records-file /tmp/news_records.json

11. 生成并发送评估报告（Telegram 消息）
```

## 周报模式差异

| 项目 | 每日评估 | 周报评估 |
|------|---------|---------|
| K 线图 | 日线 60 天 | 周线 120 天 |
| 新闻范围 | 7 天 | 14 天 |
| 分析深度 | 常规 | 加入周线级别趋势判断 |
| 额外内容 | 无 | 本周评估回顾 + 趋势变化 |

## 错误处理

- 如果 yfinance 获取数据失败：跳过该计划，在报告中注明
- 如果图表生成失败：跳过视觉分析，仅使用数值数据
- 如果某个分析步骤失败：使用已有数据继续后续步骤
- 所有错误都应在最终报告中述明

## 性能考虑

- 按 symbol 去重：如果多个计划关注同一只股票，数据获取只执行一次
- 基本面使用季度缓存，避免重复获取
- 每个计划的完整评估流程约需 3-5 分钟（取决于 LLM 响应速度）
```
