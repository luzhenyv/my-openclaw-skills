```markdown
# 投资计划存储规范 (plans.json)

## 文件路径

```
~/openclaw-data/investment/plans.json
```

## 数据结构

```json
{
  "version": "1.0",
  "updated_at": "2026-02-26T10:00:00+08:00",
  "plans": [ ... ]
}
```

## 计划字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 自动 | 格式 `plan_XXX`，自增，脚本自动生成 |
| created_at | string | 自动 | ISO 8601 带时区 |
| updated_at | string | 自动 | ISO 8601 带时区 |
| expires_at | string | 自动 | `created_at` + 3 个月 |
| status | string | 自动 | `pending` / `triggered` / `executed` / `cancelled` / `expired` |
| market | string | 是 | `US` / `HK` / `CN` / `CRYPTO`（demo 阶段仅 `US`） |
| symbol | string | 是 | 股票代码，如 `TSLA`、`BABA` |
| name | string | 是 | 中文名称，如 `特斯拉` |
| direction | string | 是 | `buy` / `sell` |
| target_price | float | 是 | 目标价格（美元） |
| price_range | array | 是 | `[下限, 上限]`，由 LLM 与用户沟通后确认 |
| quantity | int\|null | 否 | 股数（与 amount 二选一） |
| amount | float\|null | 否 | 投入金额（与 quantity 二选一） |
| priority | string | 否 | `low` / `medium` / `high`，默认 `medium` |
| logic_type | string | 是 | 交易逻辑类型，见下方「交易逻辑类型」 |
| thesis | string | 是 | 用户的投资逻辑（必须与 `logic_type` 一致，经讨论确认后录入） |
| notes | string | 否 | 备注 |
| evaluations_count | int | 自动 | 已评估次数 |
| last_evaluated_at | string\|null | 自动 | 最后评估时间 |

## 交易逻辑类型（logic_type）

每个计划**必须**指定一个明确的交易逻辑类型，确保用户的每笔交易都有理性的内在逻辑而非情绪化决策。

| 值 | 中文 | 适用方向 | 说明 |
|---|------|---------|------|
| `pullback_buy` | 回调买入 | buy | 看好标的，等价格回调至支撑位附近再买入（左侧） |
| `breakout_long` | 突破追涨 | buy | 等价格突破关键阻力位后确认趋势再买入（右侧） |
| `left_side_entry` | 左侧建仓 | buy | 在下跌趋势中分批建仓，越跌越买 |
| `right_side_entry` | 右侧建仓 | buy | 等趋势确认反转后再入场 |
| `support_bounce` | 支撑反弹 | buy | 价格触及重要支撑位后的反弹买入 |
| `mean_reversion` | 均值回归 | buy/sell | 价格偏离均值过大，预期回归 |
| `take_profit` | 止盈卖出 | sell | 达到目标收益，分批或一次性止盈 |
| `stop_loss` | 止损卖出 | sell | 跌破关键位，执行纪律性止损 |
| `reduce_position` | 减仓 | sell | 降低仓位以控制风险 |
| `momentum_chase` | 追涨 | buy | 强势股顺势追入（需严格止损） |
| `other` | 其他 | buy/sell | 不属于以上类型，需在 `thesis` 中详细说明 |

> **规则**：`logic_type` 与 `direction` 应匹配。例如 `take_profit` 只能搭配 `sell`，`pullback_buy` 只能搭配 `buy`。`mean_reversion` 和 `other` 两者皆可。

## 状态流转

```
pending ──► triggered (当前价进入 price_range)
         ├──► executed  (用户确认已执行)
         ├──► cancelled (用户主动取消)
         └──► expired   (3个月到期，用户未续期)
```

- 仅 `pending` 和 `triggered` 状态的计划参与每日评估
- `triggered` 状态表示当前价已进入目标区间，需要重点关注
- 计划过期前 7 天，系统应提醒用户是否续期

## ID 分配规则

- 自增序号，格式 `plan_001`、`plan_002` ...
- 取当前所有计划中最大序号 + 1
- 已删除的 ID 不复用

## 示例数据

```json
{
  "id": "plan_001",
  "created_at": "2026-03-15T10:00:00+08:00",
  "updated_at": "2026-03-15T10:00:00+08:00",
  "expires_at": "2026-06-15T10:00:00+08:00",
  "status": "pending",
  "market": "US",
  "symbol": "TSLA",
  "name": "特斯拉",
  "direction": "buy",
  "target_price": 400.0,
  "price_range": [385.0, 415.0],
  "quantity": null,
  "amount": 10000.0,
  "priority": "high",
  "logic_type": "pullback_buy",
  "thesis": "长期看好自动驾驶，400 附近是重要支撑位，等回调到支撑区间再买入",
  "notes": "",
  "evaluations_count": 0,
  "last_evaluated_at": null
}
```

## 脚本调用

### 添加计划

```bash
cat > /tmp/plan_record.json << 'JSONEOF'
{
  "market": "US",
  "symbol": "TSLA",
  "name": "特斯拉",
  "direction": "buy",
  "target_price": 400.0,
  "price_range": [385.0, 415.0],
  "amount": 10000.0,
  "priority": "high",
  "logic_type": "pullback_buy",
  "thesis": "长期看好自动驾驶，400 附近是重要支撑位，等回调到支撑区间再买入"
}
JSONEOF

python3 <SKILL_DIR>/scripts/plan_crud.py add \
  --record-file /tmp/plan_record.json \
  --data-dir ~/openclaw-data/investment/
```

### 列出计划

```bash
python3 <SKILL_DIR>/scripts/plan_crud.py list \
  --data-dir ~/openclaw-data/investment/ \
  --status pending
```

### 更新计划

```bash
python3 <SKILL_DIR>/scripts/plan_crud.py update \
  --data-dir ~/openclaw-data/investment/ \
  --plan-id plan_001 \
  --field status \
  --value executed
```

### 删除计划

```bash
python3 <SKILL_DIR>/scripts/plan_crud.py delete \
  --data-dir ~/openclaw-data/investment/ \
  --plan-id plan_001
```

### 检查过期

```bash
python3 <SKILL_DIR>/scripts/plan_crud.py check-expiring \
  --data-dir ~/openclaw-data/investment/ \
  --days 7
```

## 验证规则

1. `symbol` 不能为空
2. `direction` 只能是 `buy` 或 `sell`
3. `price_range` 必须是长度为 2 的数组，且 `price_range[0] < price_range[1]`
4. `target_price` 应在 `price_range` 区间内
5. `quantity` 和 `amount` 至少有一个不为 null
6. `market` 必须是 `US` / `HK` / `CN` / `CRYPTO` 之一
7. `priority` 默认 `medium`，可选 `low` / `medium` / `high`
8. `logic_type` 必须是上方「交易逻辑类型」表中的合法值之一
9. `logic_type` 与 `direction` 必须匹配（如 `take_profit` 仅限 `sell`，`pullback_buy` 仅限 `buy`）
10. `thesis` 不能为空，且应与 `logic_type` 一致地描述具体的交易理由
```
