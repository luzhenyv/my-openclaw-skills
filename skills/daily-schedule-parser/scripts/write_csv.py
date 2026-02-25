#!/usr/bin/env python3
"""
write_csv.py - 将解析好的日程记录写入本地 CSV 文件

用法:
  python scripts/write_csv.py --records '<json_array>' --data-dir ~/openclaw-data/schedules/
  python scripts/write_csv.py --records-file /tmp/records.json --data-dir ~/openclaw-data/schedules/ --overwrite
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

FIELDS = [
    "date", "username", "start_time", "end_time", "duration_min",
    "category", "sub_category", "content", "reflection", "tags"
]


def get_csv_path(data_dir: Path, date_str: str) -> Path:
    """根据日期返回对应月份的 CSV 文件路径"""
    year_month = date_str[:7]  # "2026-02"
    return data_dir / f"schedule_{year_month}.csv"


def calculate_duration(start: str, end: str) -> int:
    """计算两个 HH:MM 时间之间的分钟数"""
    try:
        fmt = "%H:%M"
        s = datetime.strptime(start, fmt)
        e = datetime.strptime(end, fmt)
        diff = int((e - s).total_seconds()) // 60
        # 处理跨午夜情况
        if diff < 0:
            diff += 24 * 60
        return diff
    except Exception:
        return 0


def load_existing_keys(csv_path: Path) -> set:
    """读取已有记录的唯一键集合（date+username+start_time）"""
    keys = set()
    if not csv_path.exists():
        return keys
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row.get('date','')}-{row.get('username','')}-{row.get('start_time','')}"
            keys.add(key)
    return keys


def write_records(records: list, data_dir: Path, overwrite: bool = False) -> dict:
    """
    写入记录到 CSV
    返回: {"written": N, "skipped": N, "files": [...]}
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    # 按月份分组
    by_month: dict[str, list] = {}
    for rec in records:
        # 自动计算 duration_min（如果未提供）
        if not rec.get("duration_min") and rec.get("start_time") and rec.get("end_time"):
            rec["duration_min"] = calculate_duration(rec["start_time"], rec["end_time"])

        date_str = rec.get("date", "")
        year_month = date_str[:7] if date_str else "unknown"
        by_month.setdefault(year_month, []).append(rec)

    written = 0
    skipped = 0
    files_written = []

    for year_month, month_records in by_month.items():
        csv_path = data_dir / f"schedule_{year_month}.csv"
        file_exists = csv_path.exists()

        if overwrite and file_exists:
            # Read all existing records, filter out ones being overwritten, then rewrite
            existing_records = []
            overwrite_keys = {
                f"{r.get('date','')}-{r.get('username','')}-{r.get('start_time','')}"
                for r in month_records
            }
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row.get('date','')}-{row.get('username','')}-{row.get('start_time','')}"
                    if key not in overwrite_keys:
                        existing_records.append(row)

            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
                writer.writeheader()
                for row in existing_records:
                    writer.writerow(row)
                for rec in month_records:
                    row = {field: rec.get(field, "") for field in FIELDS}
                    writer.writerow(row)
                    written += 1
        else:
            # Append mode: skip duplicates
            existing_keys = load_existing_keys(csv_path)

            with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")

                # New file: write header
                if not file_exists:
                    writer.writeheader()

                for rec in month_records:
                    key = f"{rec.get('date','')}-{rec.get('username','')}-{rec.get('start_time','')}"
                    if key in existing_keys:
                        skipped += 1
                        continue
                    row = {field: rec.get(field, "") for field in FIELDS}
                    writer.writerow(row)
                    written += 1

        if csv_path not in files_written:
            files_written.append(str(csv_path))

    return {"written": written, "skipped": skipped, "files": files_written}


def main():
    parser = argparse.ArgumentParser(description="写入日程记录到 CSV")
    parser.add_argument("--records", type=str, help="JSON 格式的记录数组字符串")
    parser.add_argument("--records-file", type=str, help="包含 JSON 记录数组的文件路径")
    parser.add_argument("--data-dir", type=str, default="~/openclaw-data/schedules/",
                        help="CSV 存储目录")
    parser.add_argument("--overwrite", action="store_true",
                        help="若记录已存在则覆盖（默认跳过）")
    args = parser.parse_args()

    # 读取记录
    if args.records:
        records = json.loads(args.records)
    elif args.records_file:
        with open(args.records_file, encoding="utf-8") as f:
            records = json.load(f)
    else:
        print("错误：请提供 --records 或 --records-file 参数", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(args.data_dir).expanduser()
    result = write_records(records, data_dir, overwrite=args.overwrite)

    print(f"✅ 写入完成")
    print(f"   写入: {result['written']} 条")
    print(f"   跳过（已存在）: {result['skipped']} 条")
    for f in result["files"]:
        print(f"   文件: {f}")

    # 输出 JSON 供调用方解析
    print(json.dumps(result))


if __name__ == "__main__":
    main()
