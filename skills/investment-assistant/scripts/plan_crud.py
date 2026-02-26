#!/usr/bin/env python3
"""
投资计划 CRUD 管理工具

Usage:
  python3 plan_crud.py add --record-file /tmp/plan.json --data-dir ~/openclaw-data/investment/
  python3 plan_crud.py list --data-dir ~/openclaw-data/investment/ [--status pending]
  python3 plan_crud.py get --data-dir ~/openclaw-data/investment/ --plan-id plan_001
  python3 plan_crud.py update --data-dir ~/openclaw-data/investment/ --plan-id plan_001 --field status --value executed
  python3 plan_crud.py delete --data-dir ~/openclaw-data/investment/ --plan-id plan_001
  python3 plan_crud.py check-expiring --data-dir ~/openclaw-data/investment/ --days 7
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

PLANS_FILE = "plans.json"
VALID_STATUSES = ["pending", "triggered", "executed", "cancelled", "expired"]
VALID_DIRECTIONS = ["long", "short", "hedge"]
VALID_MARKETS = ["US", "HK", "CN", "CRYPTO"]
VALID_PRIORITIES = ["low", "medium", "high"]


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def _load_plans(data_dir):
    path = os.path.join(data_dir, PLANS_FILE)
    if not os.path.exists(path):
        return {"version": "1.0", "updated_at": _now_iso(), "plans": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_plans(data_dir, data):
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, PLANS_FILE)
    data["updated_at"] = _now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _next_id(plans):
    max_num = 0
    for p in plans:
        try:
            num = int(p["id"].split("_")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    return f"plan_{max_num + 1:03d}"


def _validate_plan(record):
    errors = []
    if not record.get("symbol"):
        errors.append("symbol 不能为空")
    if record.get("direction") not in VALID_DIRECTIONS:
        errors.append(f"direction 必须是 {VALID_DIRECTIONS} 之一")
    if record.get("market", "US") not in VALID_MARKETS:
        errors.append(f"market 必须是 {VALID_MARKETS} 之一")

    price_range = record.get("price_range")
    if not isinstance(price_range, list) or len(price_range) != 2:
        errors.append("price_range 必须是长度为 2 的数组")
    elif price_range[0] >= price_range[1]:
        errors.append("price_range[0] 必须小于 price_range[1]")

    target = record.get("target_price")
    if target is None or not isinstance(target, (int, float)):
        errors.append("target_price 必须是数字")

    if record.get("quantity") is None and record.get("amount") is None:
        errors.append("quantity 和 amount 至少填一个")

    priority = record.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        errors.append(f"priority 必须是 {VALID_PRIORITIES} 之一")

    return errors


def _normalize_record(record):
    """Normalize input: convert price_range_low/high to price_range array."""
    if "price_range" not in record and "price_range_low" in record:
        record["price_range"] = [record.pop("price_range_low"), record.pop("price_range_high")]
    return record


def cmd_add(args):
    with open(args.record_file, "r", encoding="utf-8") as f:
        record = json.load(f)

    record = _normalize_record(record)
    errors = _validate_plan(record)
    if errors:
        print(f"❌ 验证失败：")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    data = _load_plans(args.data_dir)
    now = _now_iso()
    created = datetime.now(timezone.utc).astimezone()
    expires = created + timedelta(days=90)

    plan = {
        "id": _next_id(data["plans"]),
        "created_at": now,
        "updated_at": now,
        "expires_at": expires.isoformat(),
        "status": "pending",
        "market": record.get("market", "US"),
        "symbol": record["symbol"].upper(),
        "name": record.get("name", record["symbol"]),
        "direction": record["direction"],
        "target_price": float(record["target_price"]),
        "price_range": [float(record["price_range"][0]), float(record["price_range"][1])],
        "quantity": record.get("quantity"),
        "amount": float(record["amount"]) if record.get("amount") is not None else None,
        "priority": record.get("priority", "medium"),
        "thesis": record.get("thesis", ""),
        "notes": record.get("notes", ""),
        "evaluations_count": 0,
        "last_evaluated_at": None,
    }

    data["plans"].append(plan)
    _save_plans(args.data_dir, data)

    print(f"✅ 计划已创建: {plan['id']}")
    print(f"  股票: {plan['symbol']} ({plan['name']})")
    dir_map = {'long': '做多', 'short': '做空', 'hedge': '对冲'}
    print(f"  方向: {dir_map.get(plan['direction'], plan['direction'])}")
    print(f"  目标区间: ${plan['price_range'][0]:.2f} - ${plan['price_range'][1]:.2f}")
    print(f"  优先级: {plan['priority']}")
    print(f"  有效期至: {plan['expires_at'][:10]}")
    print(json.dumps({"action": "add", "plan_id": plan["id"], "status": "success"}, ensure_ascii=False))


def cmd_list(args):
    data = _load_plans(args.data_dir)
    plans = data["plans"]

    if args.status:
        statuses = [s.strip() for s in args.status.split(",")]
        plans = [p for p in plans if p["status"] in statuses]

    if args.symbol:
        plans = [p for p in plans if p["symbol"].upper() == args.symbol.upper()]

    if not plans:
        print("📭 没有找到匹配的计划")
        print(json.dumps({"action": "list", "count": 0, "plans": []}, ensure_ascii=False))
        return

    print(f"📋 共 {len(plans)} 个计划：\n")
    for p in plans:
        direction_emoji = {"long": "🟢", "short": "🔴", "hedge": "🟡"}.get(p["direction"], "⚪")
        status_map = {
            "pending": "⏳", "triggered": "⚡", "executed": "✅",
            "cancelled": "🚫", "expired": "⏰"
        }
        priority_map = {"high": "🔴", "medium": "🟡", "low": "⚪"}
        status_emoji = status_map.get(p["status"], "❓")
        priority_emoji = priority_map.get(p.get("priority", "medium"), "🟡")

        print(f"  {status_emoji} {p['id']} | {direction_emoji} {p['symbol']} ({p['name']})")
        print(f"     目标: ${p['price_range'][0]:.2f} - ${p['price_range'][1]:.2f} | 优先级: {priority_emoji} {p.get('priority', 'medium')}")
        print(f"     状态: {p['status']} | 创建: {p['created_at'][:10]} | 过期: {p['expires_at'][:10]}")
        if p.get("thesis"):
            print(f"     逻辑: {p['thesis'][:60]}...")
        print()

    print(json.dumps({
        "action": "list",
        "count": len(plans),
        "plans": [{"id": p["id"], "symbol": p["symbol"], "status": p["status"]} for p in plans]
    }, ensure_ascii=False))


def cmd_get(args):
    data = _load_plans(args.data_dir)
    plan = next((p for p in data["plans"] if p["id"] == args.plan_id), None)
    if not plan:
        print(f"❌ 找不到计划: {args.plan_id}")
        sys.exit(1)
    print(json.dumps(plan, ensure_ascii=False, indent=2))


def cmd_update(args):
    data = _load_plans(args.data_dir)

    # Support --record-file for multi-field updates
    if args.record_file:
        with open(args.record_file, "r", encoding="utf-8") as f:
            updates = json.load(f)
        plan_id = updates.get("plan_id") or args.plan_id
        if not plan_id:
            print("❌ 必须提供 plan_id")
            sys.exit(1)
        plan = next((p for p in data["plans"] if p["id"] == plan_id), None)
        if not plan:
            print(f"❌ 找不到计划: {plan_id}")
            sys.exit(1)
        updates = _normalize_record(updates)
        skip_keys = {"action", "plan_id"}
        updated_fields = []
        for key, value in updates.items():
            if key in skip_keys:
                continue
            if key in plan:
                old = plan[key]
                plan[key] = value
                updated_fields.append(f"  {key}: {old} → {value}")
        plan["updated_at"] = _now_iso()
        _save_plans(args.data_dir, data)
        print(f"✅ 计划 {plan_id} 已更新")
        for line in updated_fields:
            print(line)
        print(json.dumps({"action": "update", "plan_id": plan_id, "status": "success"}, ensure_ascii=False))
        return

    # Single field update via --field/--value
    plan = next((p for p in data["plans"] if p["id"] == args.plan_id), None)
    if not plan:
        print(f"❌ 找不到计划: {args.plan_id}")
        sys.exit(1)

    field = args.field
    value = args.value

    # Type coercion
    if field == "status" and value not in VALID_STATUSES:
        print(f"❌ status 必须是 {VALID_STATUSES} 之一")
        sys.exit(1)
    elif field == "priority" and value not in VALID_PRIORITIES:
        print(f"❌ priority 必须是 {VALID_PRIORITIES} 之一")
        sys.exit(1)
    elif field in ("target_price", "amount"):
        value = float(value)
    elif field == "quantity":
        value = int(value) if value != "null" else None
    elif field == "price_range":
        value = json.loads(value)
    elif field == "evaluations_count":
        value = int(value)

    old_value = plan.get(field)
    plan[field] = value
    plan["updated_at"] = _now_iso()
    _save_plans(args.data_dir, data)

    print(f"✅ 计划 {args.plan_id} 已更新")
    print(f"  {field}: {old_value} → {value}")
    print(json.dumps({"action": "update", "plan_id": args.plan_id, "field": field, "status": "success"}, ensure_ascii=False))


def cmd_delete(args):
    data = _load_plans(args.data_dir)
    original_count = len(data["plans"])
    data["plans"] = [p for p in data["plans"] if p["id"] != args.plan_id]

    if len(data["plans"]) == original_count:
        print(f"❌ 找不到计划: {args.plan_id}")
        sys.exit(1)

    _save_plans(args.data_dir, data)
    print(f"✅ 计划 {args.plan_id} 已删除")
    print(json.dumps({"action": "delete", "plan_id": args.plan_id, "status": "success"}, ensure_ascii=False))


def cmd_check_expiring(args):
    data = _load_plans(args.data_dir)
    now = datetime.now(timezone.utc).astimezone()
    threshold = now + timedelta(days=args.days)

    expiring = []
    for p in data["plans"]:
        if p["status"] not in ("pending", "triggered"):
            continue
        try:
            expires = datetime.fromisoformat(p["expires_at"])
            if expires <= threshold:
                days_left = (expires - now).days
                expiring.append({"plan": p, "days_left": days_left})
        except (ValueError, KeyError):
            continue

    if not expiring:
        print(f"✅ 未来 {args.days} 天内没有计划即将过期")
        print(json.dumps({"action": "check-expiring", "count": 0, "plans": []}, ensure_ascii=False))
        return

    print(f"⏰ 有 {len(expiring)} 个计划即将过期：\n")
    for item in expiring:
        p = item["plan"]
        days = item["days_left"]
        emoji = "🔴" if days <= 3 else "🟡"
        print(f"  {emoji} {p['id']} | {p['symbol']} ({p['name']})")
        print(f"     剩余 {days} 天 | 过期时间: {p['expires_at'][:10]}")
        print(f"     目标: ${p['price_range'][0]:.2f} - ${p['price_range'][1]:.2f}")
        print()

    print(json.dumps({
        "action": "check-expiring",
        "count": len(expiring),
        "plans": [{"id": item["plan"]["id"], "symbol": item["plan"]["symbol"], "days_left": item["days_left"]} for item in expiring]
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="投资计划 CRUD 管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # add
    p_add = subparsers.add_parser("add", help="添加计划")
    p_add.add_argument("--record-file", required=True, help="JSON 文件路径")
    p_add.add_argument("--data-dir", required=True, help="数据目录")

    # list
    p_list = subparsers.add_parser("list", help="列出计划")
    p_list.add_argument("--data-dir", required=True, help="数据目录")
    p_list.add_argument("--status", help="按状态筛选")
    p_list.add_argument("--symbol", help="按股票代码筛选")

    # get
    p_get = subparsers.add_parser("get", help="获取单个计划详情")
    p_get.add_argument("--data-dir", required=True, help="数据目录")
    p_get.add_argument("--plan-id", required=True, help="计划 ID")

    # update
    p_update = subparsers.add_parser("update", help="更新计划字段")
    p_update.add_argument("--data-dir", required=True, help="数据目录")
    p_update.add_argument("--plan-id", help="计划 ID")
    p_update.add_argument("--record-file", help="JSON 文件路径（支持多字段更新）")
    p_update.add_argument("--field", help="要更新的字段名（单字段模式）")
    p_update.add_argument("--value", help="新值（单字段模式）")

    # delete
    p_delete = subparsers.add_parser("delete", help="删除计划")
    p_delete.add_argument("--data-dir", required=True, help="数据目录")
    p_delete.add_argument("--plan-id", required=True, help="计划 ID")

    # check-expiring
    p_expire = subparsers.add_parser("check-expiring", help="检查即将过期的计划")
    p_expire.add_argument("--data-dir", required=True, help="数据目录")
    p_expire.add_argument("--days", type=int, default=7, help="检查未来 N 天（默认 7）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.data_dir = os.path.expanduser(args.data_dir)
    if not hasattr(args, "record_file"):
        args.record_file = None

    cmd_map = {
        "add": cmd_add,
        "list": cmd_list,
        "get": cmd_get,
        "update": cmd_update,
        "delete": cmd_delete,
        "check-expiring": cmd_check_expiring,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
