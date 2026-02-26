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

## ⚠️ 关键规则（MANDATORY — 每次评估必须严格执行）

> **下面的规则是强制性的，不允许跳过任何一步或"自己发挥"。**

1. **必须使用 `read` 工具读取 `references/subagent_*_task.md` 模板文件** → 将模板中的 `{变量}` 替换为实际值 → 将替换后的完整文本传入 `sessions_spawn` 的 `task` 参数。  
   ❌ **禁止自己编写简化版的 task**。模板中包含关键的 Python 脚本命令、分析框架指引和输出格式要求，缺少这些 Sub-Agent 无法正确执行！

2. **必须使用项目內的 Python 脚本（`<SKILL_DIR>/scripts/`）获取数据**。所有数据获取通过脚本完成——不要让 Sub-Agent 用 `web_search`/`web_fetch` 替代。

3. **必须走完 Phase 1 → Phase 2 → Phase 3 全流程**：
   - Phase 1: Spawn 3 个分析师 Sub-Agent（技术面 + 消息面 + 基本面）
   - Phase 2: 等 3 个 Sub-Agent 全部完成后，**必须 Spawn 投资评估师 Sub-Agent**（读取 `references/subagent_evaluator_task.md` 模板，填充后 spawn）
   - Phase 3: 投资评估师完成后，**必须执行** `write_evaluation.py` 记录结果 + 格式化 Telegram 报告

4. **`<SKILL_DIR>` = 此 SKILL.md 文件所在目录的绝对路径**（即 `{baseDir}` 的值）。所有引用的脚本和文件都相对于此目录。

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

---

## 一、投资计划管理

用户说"添加计划"、"查看计划"、"更新计划"等 → 进入计划 CRUD 流程。

- **计划字段定义**：详见 `references/plan_spec.md`
- **CRUD 操作命令**：详见 `references/plan_crud_spec.md`

支持的操作：`add` / `list` / `get` / `update` / `delete`，全部通过 `scripts/plan_crud.py` 执行。

---

## 二、每日盘后评估（Multi-Agent 流程）

### 触发方式

- **自动（Cron）**：每个交易日美东 16:30（`30 20 * * 1-5` UTC）
- **手动**：用户说"评估 TSLA"、"今日盘后分析"、"分析一下我的计划"

### 评估对象

所有 `status = pending` 或 `status = triggered` 的计划。手动触发时也可指定单只股票。

### 完整工作流

详见 `references/evaluation_workflow_spec.md`，包含：
- Phase 0 准备 → Phase 1 三维分析 → Phase 2 辩论评估 → Phase 3 记录报告
- 每个 Sub-Agent 的变量替换表
- Phase 3 记录/归档/推送的操作命令
- 错误处理与特殊场景

### 流程要点（快速参考）

**Phase 0**：用 `plan_crud.py list --status pending,triggered` 获取活跃计划，按 symbol 去重。

**Phase 1**：对每个 symbol，`read` 模板 → 替换变量 → `sessions_spawn` 三个分析师（非阻塞并行）。

**Phase 1→2 过渡**：追踪 announce 结果，3/3 收齐后进入 Phase 2。状态追踪格式：
```
📊 {SYMBOL} 评估进度:
  ✅ 技术面分析师 - 完成 (score: 62)
  ✅ 消息面分析师 - 完成 (score: 55)
  ⏳ 基本面分析师 - 进行中...
  收集进度: 2/3
```

**Phase 2**：`read` `subagent_evaluator_task.md` → 填充三份报告 + 计划信息 → spawn 投资评估师。同一股票多个计划时：分析复用，评估按计划分别 spawn。

**Phase 3**：执行 `write_evaluation.py` 记录 + `write_news_archive.py` 归档 + 格式化 Telegram 报告（格式见 `references/report_format_spec.md`）。

---

## 三、周报

- **自动（Cron）**：每周六美东 10:00（`0 14 * * 6` UTC）
- **手动**：用户说"投资周报"、"本周总结"、"weekly review"

使用与每日评估相同的 Multi-Agent 流程，参数差异：

| 变量 | 每日评估 | 周报 |
|------|---------|------|
| `{lookback_days}` | 60 | 120 |
| `{period}` | daily | weekly |
| `{chart_days}` | 60 | 120 |
| `{news_days}` | 7 | 14 |

周报额外包含：本周评分趋势（读取本周评估 CSV）+ 到期提醒（`check_expiring_plans.py --days 14`）。格式见 `references/report_format_spec.md`。

---

## 四、计划到期检查

- **自动（Cron）**：每周一美东 09:00（`0 13 * * 1` UTC）
- 操作命令与提醒格式见 `references/plan_crud_spec.md`

---

## 五、历史查询

用户可查询历史评估记录和新闻归档：

- 评估数据：`~/openclaw-data/investment/evaluations_YYYY-MM.csv`
- 新闻归档：`~/openclaw-data/investment/news_archive_YYYY-MM.csv`

---

## 六、参考资料索引

| 文件 | 内容 |
|------|------|
| `references/plan_spec.md` | 计划字段定义、状态流转、数据结构 |
| `references/plan_crud_spec.md` | 计划 CRUD 操作命令、到期检查 |
| `references/evaluation_workflow_spec.md` | 评估全流程、变量替换表、Phase 3 命令、错误处理、特殊场景 |
| `references/report_format_spec.md` | Telegram 报告格式（每日/汇总/周报） |
| `references/technical_indicators_spec.md` | 13 个技术指标详细说明 |
| `references/subagent_*_task.md` | Sub-Agent 任务模板（4 个） |
| `references/*_prompt.md` | Sub-Agent 分析框架提示词（5 个） |
| `config/settings.json` | 全局配置（数据源、指标、评估参数等） |
