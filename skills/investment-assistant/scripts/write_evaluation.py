#!/usr/bin/env python3
"""
写入每日评估记录到 CSV

Usage:
  python3 write_evaluation.py --records-file /tmp/eval_records.json --data-dir ~/openclaw-data/investment/evaluations/
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

FIELDNAMES = [
    "date", "symbol", "market", "direction", "plan_id",
    "target_price", "current_price", "price_in_range",
    "technical_score", "news_score", "fundamentals_score",
    "verdict", "confidence", "reason",
]
BOM = "\ufeff"


def write_evaluations(records, data_dir):
    os.makedirs(data_dir, exist_ok=True)

    # Group by month
    by_month = {}
    for r in records:
        month_key = r["date"][:7]  # YYYY-MM
        if month_key not in by_month:
            by_month[month_key] = []
        by_month[month_key].append(r)

    total_written = 0
    for month_key, month_records in by_month.items():
        filename = f"evaluations_{month_key}.csv"
        filepath = os.path.join(data_dir, filename)

        # Load existing keys for dedup
        existing_keys = set()
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row.get('date', '')}_{row.get('symbol', '')}_{row.get('plan_id', '')}"
                    existing_keys.add(key)

        # Filter new records
        new_records = []
        for r in month_records:
            key = f"{r['date']}_{r['symbol']}_{r.get('plan_id', '')}"
            if key not in existing_keys:
                new_records.append(r)
                existing_keys.add(key)

        if not new_records:
            print(f"⚠️ {filename}: 所有记录已存在，跳过")
            continue

        # Write
        file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0
        with open(filepath, "a", encoding="utf-8", newline="") as f:
            if not file_exists:
                f.write(BOM)
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            for r in new_records:
                writer.writerow(r)

        total_written += len(new_records)
        print(f"✅ {filename}: 写入 {len(new_records)} 条新记录")

    print(f"\n📊 总计写入 {total_written} 条评估记录")
    print(json.dumps({"action": "write_evaluation", "total_written": total_written, "status": "success"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="写入评估记录")
    parser.add_argument("--records-file", required=True, help="JSON 记录文件路径")
    parser.add_argument("--data-dir", required=True, help="评估数据目录")
    args = parser.parse_args()

    args.data_dir = os.path.expanduser(args.data_dir)

    with open(args.records_file, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        records = [records]

    write_evaluations(records, args.data_dir)


if __name__ == "__main__":
    main()
