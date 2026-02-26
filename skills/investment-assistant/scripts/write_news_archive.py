#!/usr/bin/env python3
"""
写入重要新闻存档到 CSV

Usage:
  python3 write_news_archive.py --records-file /tmp/news_records.json --data-dir ~/openclaw-data/investment/news_archive/
"""

import argparse
import csv
import json
import os
import sys

FIELDNAMES = [
    "date", "symbol", "headline", "source",
    "summary", "sentiment", "is_significant",
]
BOM = "\ufeff"


def write_news_archive(records, data_dir):
    os.makedirs(data_dir, exist_ok=True)

    by_month = {}
    for r in records:
        month_key = r["date"][:7]
        if month_key not in by_month:
            by_month[month_key] = []
        by_month[month_key].append(r)

    total_written = 0
    for month_key, month_records in by_month.items():
        filename = f"news_archive_{month_key}.csv"
        filepath = os.path.join(data_dir, filename)

        # Load existing keys for dedup
        existing_keys = set()
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row.get('date', '')}_{row.get('symbol', '')}_{row.get('headline', '')[:50]}"
                    existing_keys.add(key)

        new_records = []
        for r in month_records:
            key = f"{r['date']}_{r['symbol']}_{r.get('headline', '')[:50]}"
            if key not in existing_keys:
                new_records.append(r)
                existing_keys.add(key)

        if not new_records:
            continue

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
        print(f"✅ {filename}: 存档 {len(new_records)} 条新闻")

    print(f"\n📰 总计存档 {total_written} 条新闻")
    print(json.dumps({"action": "write_news_archive", "total_written": total_written, "status": "success"}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="写入新闻存档")
    parser.add_argument("--records-file", required=True, help="JSON 记录文件路径")
    parser.add_argument("--data-dir", required=True, help="新闻存档目录")
    args = parser.parse_args()
    args.data_dir = os.path.expanduser(args.data_dir)

    with open(args.records_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list):
        records = [records]

    write_news_archive(records, args.data_dir)


if __name__ == "__main__":
    main()
