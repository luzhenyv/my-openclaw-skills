#!/usr/bin/env python3
"""
generate_weekly_report.py - 生成每周时间分析报告

用法:
  python scripts/generate_weekly_report.py \
    --data-dir ~/openclaw-data/schedules/ \
    --username john_doe \
    --week-start 2026-02-23 \
    --output ~/openclaw-data/reports/weekly_2026-02-23.md
"""

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def load_week_records(data_dir: Path, username: str, week_start: str) -> list:
    """读取指定周的所有记录"""
    start = datetime.strptime(week_start, "%Y-%m-%d")
    end = start + timedelta(days=6)

    records = []
    # 检查可能跨月的情况，读取相关月份文件
    months_to_check = set()
    current = start
    while current <= end:
        months_to_check.add(current.strftime("%Y-%m"))
        current += timedelta(days=1)

    for ym in months_to_check:
        csv_path = data_dir / f"schedule_{ym}.csv"
        if not csv_path.exists():
            continue
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("username", "") != username and username != "all":
                    continue
                try:
                    rec_date = datetime.strptime(row["date"], "%Y-%m-%d")
                    if start <= rec_date <= end:
                        records.append(row)
                except Exception:
                    continue

    return records


def build_time_distribution(records: list) -> dict:
    """按主分类和子分类统计时间"""
    category_totals = defaultdict(int)
    sub_totals = defaultdict(lambda: defaultdict(int))

    for rec in records:
        dur = int(rec.get("duration_min", 0))
        cat = rec.get("category", "其他")
        sub = rec.get("sub_category", "")
        category_totals[cat] += dur
        if sub:
            sub_totals[cat][sub] += dur

    return {
        "category_totals": dict(category_totals),
        "sub_totals": {k: dict(v) for k, v in sub_totals.items()}
    }


def build_frequent_events(records: list, top_n: int = 10) -> list:
    """统计高频事件（按 tags 和 sub_category）"""
    tag_records = defaultdict(list)

    for rec in records:
        tags = [t.strip() for t in rec.get("tags", "").split(",") if t.strip()]
        sub = rec.get("sub_category", "")
        keys = set(tags)
        if sub:
            keys.add(sub)
        for key in keys:
            tag_records[key].append(rec)

    # 按出现次数排序
    sorted_events = sorted(tag_records.items(), key=lambda x: len(x[1]), reverse=True)

    result = []
    for tag, recs in sorted_events[:top_n]:
        latest = max(recs, key=lambda r: r.get("date", "") + r.get("start_time", ""))
        reflections = [r["reflection"] for r in recs if r.get("reflection", "").strip()]
        result.append({
            "tag": tag,
            "count": len(recs),
            "latest_date": latest.get("date", ""),
            "latest_content": latest.get("content", ""),
            "reflections": reflections[-2:] if reflections else []  # 最近2条感想
        })

    return result


def analyze_reflections(records: list) -> dict:
    """简单的情绪关键词分析"""
    positive_words = ["完成", "顺利", "开心", "满意", "进展", "成功", "不错", "好的", "棒", "收获", "希望"]
    negative_words = ["烦", "累", "难", "问题", "失败", "担心", "焦虑", "抱怨", "卡", "困难", "压力"]

    pos_count = 0
    neg_count = 0
    action_items = []

    for rec in records:
        ref = rec.get("reflection", "")
        if not ref.strip():
            continue

        for w in positive_words:
            if w in ref:
                pos_count += 1
                break
        for w in negative_words:
            if w in ref:
                neg_count += 1
                break

        # 提取待办/计划类句子
        action_keywords = ["需要", "计划", "打算", "希望", "准备", "下周", "明天", "后续"]
        for kw in action_keywords:
            if kw in ref:
                # 提取包含关键词的短句
                sentences = ref.replace("，", "。").replace(",", "。").split("。")
                for sent in sentences:
                    if kw in sent and sent.strip() and len(sent.strip()) > 3:
                        item = f"{rec.get('date','')} {sent.strip()}"
                        if item not in action_items:
                            action_items.append(item)
                break

    total = pos_count + neg_count
    if total == 0:
        sentiment = {"positive": 0, "negative": 0, "neutral": 100}
    else:
        neutral = max(0, len(records) - pos_count - neg_count)
        total_all = pos_count + neg_count + neutral
        sentiment = {
            "positive": round(pos_count / total_all * 100),
            "negative": round(neg_count / total_all * 100),
            "neutral": round(neutral / total_all * 100)
        }

    return {
        "sentiment": sentiment,
        "action_items": action_items[:10]
    }


def format_duration(minutes: int) -> str:
    """将分钟数格式化为可读字符串"""
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h}h{m}m"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}m"


def generate_report(records: list, username: str, week_start: str) -> str:
    """生成 Markdown 格式的周报"""
    week_end = (datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
    total_min = sum(int(r.get("duration_min", 0)) for r in records)

    dist = build_time_distribution(records)
    frequent = build_frequent_events(records)
    insights = analyze_reflections(records)

    lines = []
    lines.append(f"# 📅 周报：{week_start} ~ {week_end}")
    lines.append(f"\n**用户**：{username}　**记录条数**：{len(records)}　**总时长**：{format_duration(total_min)}\n")

    # --- 时间分配 ---
    lines.append("---\n\n## 📊 时间分配总览\n")
    sorted_cats = sorted(dist["category_totals"].items(), key=lambda x: x[1], reverse=True)
    for cat, mins in sorted_cats:
        pct = round(mins / total_min * 100) if total_min > 0 else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        lines.append(f"**{cat}**　{bar}　{format_duration(mins)}（{pct}%）")

        # 子分类 top 3
        subs = dist["sub_totals"].get(cat, {})
        if subs:
            top_subs = sorted(subs.items(), key=lambda x: x[1], reverse=True)[:3]
            sub_str = " / ".join([f"{s}·{format_duration(m)}" for s, m in top_subs])
            lines.append(f"　　↳ {sub_str}")
        lines.append("")

    # --- 高频事件 ---
    lines.append("\n---\n\n## 🔁 高频事件 Top 10\n")
    if frequent:
        for i, ev in enumerate(frequent, 1):
            lines.append(f"**{i}. {ev['tag']}**（出现 {ev['count']} 次）")
            lines.append(f"　最近：{ev['latest_date']} {ev['latest_content'][:60]}{'...' if len(ev['latest_content']) > 60 else ''}")
            if ev["reflections"]:
                reflections_str = "；".join(ev["reflections"])[:80]
                lines.append(f"　感想：{reflections_str}")
            lines.append("")
    else:
        lines.append("本周暂无高频事件数据。\n")

    # --- 情绪洞察 ---
    lines.append("\n---\n\n## 💭 状态洞察\n")
    s = insights["sentiment"]
    lines.append(f"**本周情绪**：积极 {s['positive']}% / 中性 {s['neutral']}% / 消极 {s['negative']}%\n")

    if insights["action_items"]:
        lines.append("**本周关注点 & 待办**：\n")
        for item in insights["action_items"]:
            lines.append(f"- {item}")

    lines.append(f"\n\n---\n*报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成周报")
    parser.add_argument("--data-dir", type=str, default="~/openclaw-data/schedules/")
    parser.add_argument("--username", type=str, required=True)
    parser.add_argument("--week-start", type=str, required=True, help="周一日期 YYYY-MM-DD")
    parser.add_argument("--output", type=str, help="输出文件路径（默认打印到 stdout）")
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser()
    records = load_week_records(data_dir, args.username, args.week_start)

    if not records:
        print(f"⚠️  未找到 {args.week_start} 这一周的记录（用户：{args.username}）")
        return

    report = generate_report(records, args.username, args.week_start)

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 周报已保存至：{output_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
