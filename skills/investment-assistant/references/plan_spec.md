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
| thesis | string | 否 | 用户的投资逻辑 |
| notes | string | 否 | 备注 |
| evaluations_count | int | 自动 | 已评估次数 |
| last_evaluated_at | string\|null | 自动 | 最后评估时间 |

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
  "thesis": "长期看好自动驾驶，400 附近是重要支撑位",
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
  "thesis": "长期看好自动驾驶，400 附近是重要支撑位"
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
```
