#!/usr/bin/env python3
"""
检查即将过期的投资计划（独立脚本，供 Cron 调用）

Usage:
  python3 check_expiring_plans.py --data-dir ~/openclaw-data/investment/ --days 7
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

PLANS_FILE = "plans.json"


def check_expiring(data_dir, days):
    path = os.path.join(data_dir, PLANS_FILE)
    if not os.path.exists(path):
        print("📭 没有找到计划文件")
        print(json.dumps({"action": "check-expiring", "count": 0, "plans": []}, ensure_ascii=False))
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now(timezone.utc).astimezone()
    threshold = now + timedelta(days=days)

    expiring = []
    for p in data.get("plans", []):
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
        print(f"✅ 未来 {days} 天内没有计划即将过期")
        print(json.dumps({"action": "check-expiring", "count": 0, "plans": []}, ensure_ascii=False))
        return

    print(f"⏰ 有 {len(expiring)} 个计划即将过期：\n")
    for item in sorted(expiring, key=lambda x: x["days_left"]):
        p = item["plan"]
        d = item["days_left"]
        emoji = "🔴" if d <= 3 else "🟡" if d <= 7 else "⚪"
        direction_cn = {"long": "做多", "short": "做空", "hedge": "对冲"}.get(p["direction"], p["direction"])
        print(f"  {emoji} {p['id']} | {p['symbol']} ({p['name']})")
        print(f"     方向: {direction_cn} | 目标: ${p['price_range'][0]:.2f} - ${p['price_range'][1]:.2f}")
        print(f"     剩余 {d} 天 | 过期: {p['expires_at'][:10]}")
        if p.get("thesis"):
            print(f"     逻辑: {p['thesis'][:50]}")
        print()

    print(json.dumps({
        "action": "check-expiring",
        "count": len(expiring),
        "plans": [{"id": item["plan"]["id"], "symbol": item["plan"]["symbol"], "days_left": item["days_left"]} for item in expiring]
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="检查即将过期的计划")
    parser.add_argument("--data-dir", required=True, help="数据目录")
    parser.add_argument("--days", type=int, default=7, help="检查未来 N 天（默认 7）")
    args = parser.parse_args()
    args.data_dir = os.path.expanduser(args.data_dir)
    check_expiring(args.data_dir, args.days)


if __name__ == "__main__":
    main()
