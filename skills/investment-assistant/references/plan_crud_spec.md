# 投资计划 CRUD 操作规范

所有命令中 `<SKILL_DIR>` = SKILL.md 文件所在目录的绝对路径。

## 创建计划

用户说"添加计划"、"新建一个投资计划"等 → 引导用户提供信息 → 预览 → 确认 → 写入。

引导用户提供：市场、代码、方向、目标价、区间、数量、优先级、论点。未提供的可选字段用合理默认值。

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

## 查看计划

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

## 更新计划

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

## 删除/取消计划

```bash
python3 <SKILL_DIR>/scripts/plan_crud.py delete \
  --data-dir ~/openclaw-data/investment \
  --plan-id plan_001
```

## 计划到期检查

**自动触发**：每周一美东 09:00（`0 13 * * 1` UTC）

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
