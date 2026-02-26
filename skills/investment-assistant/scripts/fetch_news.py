#!/usr/bin/env python3
"""
拉取新闻数据（基于 yfinance）
迁移自 TradingAgents yfinance_news.py

Usage:
  python3 fetch_news.py --mode company --symbol TSLA --days 7 --output /tmp/tsla_news.json
  python3 fetch_news.py --mode global --days 7 --limit 5 --output /tmp/global_news.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta


def fetch_company_news(symbol, days, output_path):
    try:
        import yfinance as yf
    except ImportError:
        print("❌ 缺少 yfinance 库，请运行: pip install yfinance")
        sys.exit(1)

    ticker = yf.Ticker(symbol)

    try:
        news_items = ticker.get_news(count=20)
    except Exception:
        # Fallback: older yfinance versions use .news property
        try:
            news_items = ticker.news
        except Exception as e:
            print(f"⚠️ 获取 {symbol} 新闻失败: {e}")
            news_items = []

    if not news_items:
        print(f"⚠️ 没有获取到 {symbol} 的新闻")
        output = {"symbol": symbol, "mode": "company", "count": 0, "news": []}
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(json.dumps(output, ensure_ascii=False))
        return

    # Filter by date range
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_ts = int(cutoff.timestamp())

    filtered = []
    for item in news_items:
        # Handle different yfinance news formats
        if isinstance(item, dict):
            pub_ts = item.get("providerPublishTime", item.get("publish_time", 0))
            if isinstance(pub_ts, str):
                try:
                    pub_ts = int(datetime.fromisoformat(pub_ts).timestamp())
                except ValueError:
                    pub_ts = 0

            if pub_ts < cutoff_ts:
                continue

            pub_date = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M") if pub_ts else "unknown"

            news_entry = {
                "title": item.get("title", item.get("headline", "")),
                "publisher": item.get("publisher", item.get("source", "")),
                "link": item.get("link", item.get("url", "")),
                "published_date": pub_date,
                "summary": item.get("summary", item.get("text", "")),
            }
            filtered.append(news_entry)

    output = {
        "symbol": symbol,
        "mode": "company",
        "lookback_days": days,
        "count": len(filtered),
        "news": filtered,
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 已获取 {symbol} 新闻: {len(filtered)} 条")
    for i, n in enumerate(filtered[:5], 1):
        title = n["title"][:60] + "..." if len(n["title"]) > 60 else n["title"]
        print(f"  {i}. [{n['published_date']}] {title}")
    if len(filtered) > 5:
        print(f"  ... 共 {len(filtered)} 条")
    print(f"  输出文件: {output_path}")
    print(json.dumps({"action": "fetch_news", "symbol": symbol, "mode": "company", "count": len(filtered), "output": output_path}, ensure_ascii=False))


def fetch_global_news(days, limit, output_path):
    try:
        import yfinance as yf
    except ImportError:
        print("❌ 缺少 yfinance 库，请运行: pip install yfinance")
        sys.exit(1)

    queries = [
        "stock market economy",
        "Federal Reserve interest rates",
        "inflation economic outlook",
        "global markets trading",
    ]

    all_news = []
    seen_titles = set()

    for query in queries:
        try:
            search = yf.Search(query, news_count=limit)
            news_list = search.news if hasattr(search, "news") else []
            for item in news_list:
                if isinstance(item, dict):
                    title = item.get("title", item.get("headline", ""))
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    pub_ts = item.get("providerPublishTime", item.get("publish_time", 0))
                    if isinstance(pub_ts, str):
                        try:
                            pub_ts = int(datetime.fromisoformat(pub_ts).timestamp())
                        except ValueError:
                            pub_ts = 0
                    pub_date = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M") if pub_ts else "unknown"

                    all_news.append({
                        "title": title,
                        "publisher": item.get("publisher", item.get("source", "")),
                        "link": item.get("link", item.get("url", "")),
                        "published_date": pub_date,
                        "summary": item.get("summary", item.get("text", "")),
                        "query": query,
                    })
        except Exception as e:
            print(f"⚠️ 搜索 '{query}' 失败: {e}")
            continue

    output = {
        "mode": "global",
        "lookback_days": days,
        "count": len(all_news),
        "news": all_news,
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 已获取全球宏观新闻: {len(all_news)} 条")
    for i, n in enumerate(all_news[:5], 1):
        title = n["title"][:60] + "..." if len(n["title"]) > 60 else n["title"]
        print(f"  {i}. [{n['published_date']}] {title}")
    if len(all_news) > 5:
        print(f"  ... 共 {len(all_news)} 条")
    print(f"  输出文件: {output_path}")
    print(json.dumps({"action": "fetch_news", "mode": "global", "count": len(all_news), "output": output_path}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="拉取新闻数据")
    parser.add_argument("--mode", choices=["company", "global"], required=True, help="新闻模式")
    parser.add_argument("--symbol", help="股票代码（company 模式必填）")
    parser.add_argument("--days", type=int, default=7, help="回溯天数（默认 7）")
    parser.add_argument("--limit", type=int, default=5, help="每个搜索词返回数量（global 模式）")
    parser.add_argument("--output", required=True, help="JSON 输出路径")
    args = parser.parse_args()

    if args.mode == "company":
        if not args.symbol:
            print("❌ company 模式需要 --symbol 参数")
            sys.exit(1)
        fetch_company_news(args.symbol, args.days, args.output)
    else:
        fetch_global_news(args.days, args.limit, args.output)


if __name__ == "__main__":
    main()
