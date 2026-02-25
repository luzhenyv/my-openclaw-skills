#!/usr/bin/env python3
"""
generate_daily_summary.py - 生成每日英语学习汇总

用法:
  python scripts/generate_daily_summary.py \
    --data-dir ~/openclaw-data/english/ \
    --username john_doe \
    --date 2026-03-01 \
    --include-review \
    --output ~/openclaw-data/english/summaries/daily_2026-03-01.md
"""

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def load_day_records(data_dir: Path, username: str, date_str: str) -> list:
    """读取指定日期的所有记录"""
    year_month = date_str[:7]
    csv_path = data_dir / f"expressions_{year_month}.csv"

    records = []
    if not csv_path.exists():
        return records

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("username", "") != username and username != "all":
                continue
            if row.get("date", "") == date_str:
                records.append(row)

    return records


def load_review_candidates(data_dir: Path, username: str, date_str: str, lookback_days: int = 30) -> list:
    """从过去 N 天的记录中找出复习候选（高频优先）"""
    end_date = datetime.strptime(date_str, "%Y-%m-%d")
    start_date = end_date - timedelta(days=lookback_days)

    # 收集所有相关月份
    months_to_check = set()
    current = start_date
    while current < end_date:
        months_to_check.add(current.strftime("%Y-%m"))
        current += timedelta(days=1)

    # 读取所有记录
    expression_counts = defaultdict(list)
    for ym in months_to_check:
        csv_path = data_dir / f"expressions_{ym}.csv"
        if not csv_path.exists():
            continue
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("username", "") != username and username != "all":
                    continue
                try:
                    rec_date = datetime.strptime(row["date"], "%Y-%m-%d")
                    if start_date <= rec_date < end_date:
                        expr = row.get("expression", "")
                        if expr:
                            expression_counts[expr].append(row)
                except Exception:
                    continue

    # 按出现次数排序
    candidates = []
    for expr, recs in sorted(expression_counts.items(), key=lambda x: len(x[1]), reverse=True):
        latest = max(recs, key=lambda r: r.get("date", ""))
        candidates.append({
            "expression": expr,
            "phonetic": latest.get("phonetic", ""),
            "query": latest.get("query", ""),
            "pos": latest.get("pos", ""),
            "count": len(recs),
            "example_sentence": latest.get("example_sentence", ""),
        })

    return candidates


def generate_summary(records: list, review_candidates: list, username: str, date_str: str, include_review: bool) -> str:
    """生成 Markdown 格式的每日汇总"""
    lines = []
    lines.append(f"# 📚 每日英语汇总 | {date_str}")

    if records:
        lines.append(f"\n**用户**：{username}　**今日新学**：{len(records)} 个表达\n")
        lines.append("| # | 你的问题 | 推荐表达 | 音标 | 词性 | 例句 |")
        lines.append("|---|---------|---------|------|------|------|")
        for i, rec in enumerate(records, 1):
            query = rec.get("query", "")
            expr = rec.get("expression", "")
            phonetic = rec.get("phonetic", "")
            pos = rec.get("pos", "")
            example = rec.get("example_sentence", "")
            # 截断过长内容
            if len(example) > 60:
                example = example[:57] + "..."
            if len(query) > 30:
                query = query[:27] + "..."
            lines.append(f"| {i} | {query} | {expr} | {phonetic} | {pos} | {example} |")
    else:
        lines.append(f"\n**用户**：{username}\n")
        lines.append("今天还没有新的学习记录哦！来问我一个英语表达吧 💪\n")

    # 复习回顾
    if include_review and review_candidates:
        lines.append("\n---\n")
        lines.append("## 🔁 复习回顾（来自过去 30 天）\n")

        # 高频词（出现 >= 2 次）优先
        high_freq = [c for c in review_candidates if c["count"] >= 2]
        low_freq = [c for c in review_candidates if c["count"] < 2]

        # 排除今天已学的
        today_expressions = {r.get("expression", "") for r in records}
        high_freq = [c for c in high_freq if c["expression"] not in today_expressions]
        low_freq = [c for c in low_freq if c["expression"] not in today_expressions]

        review_items = []
        # 取高频词（最多 2 个）
        review_items.extend(high_freq[:2])
        # 不足 3 个则从低频中随机补充
        remaining = 3 - len(review_items)
        if remaining > 0 and low_freq:
            review_items.extend(random.sample(low_freq, min(remaining, len(low_freq))))

        if review_items:
            lines.append("| # | 表达 | 音标 | 含义 | 出现次数 |")
            lines.append("|---|------|------|------|---------|")
            for i, item in enumerate(review_items, 1):
                lines.append(
                    f"| {i} | {item['expression']} | {item['phonetic']} | {item['query']} | {item['count']} 次 |"
                )
        else:
            lines.append("暂无复习内容。\n")

    lines.append(f"\n---\n*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成每日英语学习汇总")
    parser.add_argument("--data-dir", type=str, default="~/openclaw-data/english/")
    parser.add_argument("--username", type=str, required=True)
    parser.add_argument("--date", type=str, required=True, help="日期 YYYY-MM-DD")
    parser.add_argument("--include-review", action="store_true",
                        help="包含复习回顾（从过去 30 天抽取）")
    parser.add_argument("--output", type=str, help="输出文件路径（默认打印到 stdout）")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser()
    records = load_day_records(data_dir, args.username, args.date)

    review_candidates = []
    if args.include_review:
        review_candidates = load_review_candidates(data_dir, args.username, args.date)

    summary = generate_summary(records, review_candidates, args.username, args.date, args.include_review)

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"✅ 每日汇总已保存至：{output_path}")
    else:
        print(summary)


if __name__ == "__main__":
    main()
