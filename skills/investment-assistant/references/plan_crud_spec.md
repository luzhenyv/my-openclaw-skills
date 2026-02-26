# 投资计划 CRUD 操作规范

所有命令中 `<SKILL_DIR>` = SKILL.md 文件所在目录的绝对路径。

## 创建计划

用户说"添加计划"、"新建一个投资计划"等 → **必须完成以下 4 步后才能写入**。

### Step 1：收集基本信息

引导用户提供：市场、代码、方向、目标价、区间、数量/金额、优先级。未提供的可选字段用合理默认值。

### Step 2：讨论交易逻辑（⚠️ 必须执行，不可跳过）

**每个计划都必须有清晰的内在交易逻辑**，而非情绪化表达（如"感觉要涨"、"别人都在买"）。

1. **引导用户明确 `logic_type`**：询问用户这笔交易属于哪种逻辑类型（见 `plan_spec.md` 中的交易逻辑类型表），常见选项：

   | 买入逻辑 | 卖出逻辑 |
   |---------|---------|
   | 回调买入（pullback_buy） | 止盈卖出（take_profit） |
   | 突破追涨（breakout_long） | 止损卖出（stop_loss） |
   | 左侧建仓（left_side_entry） | 减仓（reduce_position） |
   | 右侧建仓（right_side_entry） | |
   | 支撑反弹（support_bounce） | |
   | 均值回归（mean_reversion） | |

2. **引导用户阐述 `thesis`**：要求用户用 1-3 句话说明具体理由，必须包含：
   - **为什么是这个价格/区间？**（技术位、估值、事件驱动？）
   - **核心假设是什么？**（什么条件成立才值得买入/卖出？）
   - 示例：
     - ✅ "400 是 200 日均线支撑位，FSD V13 推送是催化剂，跌到支撑区间左侧建仓"
     - ✅ "突破 200 后追涨，成交量放大确认突破有效，上方无明显阻力"
     - ❌ "感觉 TSLA 要涨"（缺乏逻辑依据）
     - ❌ "朋友推荐的"（非独立判断）

3. **助手给出逻辑评估**：根据用户的 `logic_type` + `thesis` + `price_range`，**主动给出建议**：
   - `logic_type` 与 `direction` / `price_range` 是否自洽？
   - 逻辑是否有明显漏洞？（如"左侧建仓"但没有分批计划）
   - 价格区间是否合理？（区间太窄容易错过，太宽风险不可控）
   - 建议性改进（非强制），用户可接受或忽略

   > 示例评估输出：
   > ```
   > 📋 逻辑评估：
   > ✅ 逻辑类型「回调买入」与买入方向一致
   > ✅ 目标价 $400 在 200 日均线附近，技术支撑合理
   > ⚠️ 建议：区间 $385-$415 跨度为 7.5%，偏宽。如果是精准的支撑位交易，
   >    建议收窄至 $390-$410（5% 以内）以提高执行纪律
   > ⚠️ 建议：考虑设置止损位（如跌破 $370 则止损），可后续添加止损计划
   > ```

4. **用户确认或修改**：根据讨论结果，用户确认最终的 `logic_type` 和 `thesis`。

### Step 3：预览计划

将收集的信息格式化展示给用户确认，示例：

```
📝 计划预览：

| 字段 | 值 |
|------|-----|
| 标的 | TSLA 特斯拉 |
| 方向 | 买入 |
| 目标价 | $400 |
| 买入区间 | $385 - $415 |
| 金额 | $10,000 |
| 优先级 | 高 |
| 逻辑类型 | 回调买入 |
| 投资逻辑 | 长期看好自动驾驶，400 附近是 200 日均线支撑位，等回调到支撑区间再买入 |

确认创建？(Y/N)
```

### Step 4：写入

用户确认后执行：

```bash
cat > /tmp/plan_record.json << 'JSONEOF'
{
  "action": "add",
  "market": "US",
  "symbol": "TSLA",
  "direction": "buy",
  "target_price": 400,
  "price_range_low": 385,
  "price_range_high": 415,
  "amount": 10000,
  "priority": "high",
  "logic_type": "pullback_buy",
  "thesis": "长期看好自动驾驶，400 附近是 200 日均线支撑位，等回调到支撑区间再买入"
}
JSONEOF

python3 <SKILL_DIR>/scripts/plan_crud.py add \
  --record-file /tmp/plan_record.json \
  --data-dir ~/openclaw-data/investment
```

### 创建计划示例场景

> **用户**：帮我添加一个 AAPL 的买入计划，目标价 180。
>
> **助手**：好的，先确认几个信息：
> - 买入区间？（目标价附近你希望多大范围内买入？）
> - 买入金额或股数？
> - 你的买入逻辑是什么？比如：回调买入、突破追涨、左侧建仓、支撑反弹？
>
> **用户**：区间 170-190，投 5000 刀。等回调买入。
>
> **助手**：
> 📋 逻辑评估：
> ✅ 「回调买入」与买入方向一致
> ⚠️ 补充一下：180 附近有什么技术支撑让你选择这个价位？还是基于估值？这样我可以帮你记录更完整的 thesis。
> ⚠️ 区间 $170-$190 跨度 11%，偏宽。如果是回调到支撑位买入，建议收窄到你认为的支撑区间。
>
> **用户**：175 是前低支撑，我觉得 170-185 更合理。逻辑是 AAPL 估值已修正到合理区间，175 前低是强支撑。
>
> **助手**：
> ✅ 逻辑清晰。更新后的计划预览：
>
> | 字段 | 值 |
> |------|-----|
> | 标的 | AAPL 苹果 |
> | 方向 | 买入 |
> | 目标价 | $180 |
> | 买入区间 | $170 - $185 |
> | 金额 | $5,000 |
> | 逻辑类型 | 回调买入 |
> | 投资逻辑 | 估值修正到合理区间，175 前低是强支撑位，等回调到支撑区间买入 |
>
> 确认创建？

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
