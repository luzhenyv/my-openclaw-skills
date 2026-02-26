#!/usr/bin/env python3
"""
拉取股价 OHLCV 数据（基于 yfinance）

Usage:
  python3 fetch_stock_data.py --symbol TSLA --start-date 2026-01-01 --end-date 2026-02-26 --output /tmp/tsla_ohlcv.csv
  python3 fetch_stock_data.py --symbol TSLA --days 60 --output /tmp/tsla_ohlcv.csv
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta


def fetch_stock_data(symbol, start_date, end_date, output_path):
    try:
        import yfinance as yf
    except ImportError:
        print("❌ 缺少 yfinance 库，请运行: pip install yfinance")
        sys.exit(1)

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date, end=end_date)

    if df.empty:
        print(f"❌ 没有获取到 {symbol} 从 {start_date} 到 {end_date} 的数据")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # Save to CSV
    df.to_csv(output_path)

    # Print summary
    latest = df.iloc[-1]
    print(f"✅ 已获取 {symbol} 数据")
    print(f"  日期范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
    print(f"  数据条数: {len(df)}")
    print(f"  最新收盘: ${latest['Close']:.2f}")
    print(f"  最新成交量: {int(latest['Volume']):,}")
    print(f"  输出文件: {output_path}")

    result = {
        "symbol": symbol,
        "start_date": df.index[0].strftime('%Y-%m-%d'),
        "end_date": df.index[-1].strftime('%Y-%m-%d'),
        "count": len(df),
        "latest_close": round(latest['Close'], 2),
        "latest_volume": int(latest['Volume']),
        "output": output_path,
    }
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="拉取股价 OHLCV 数据")
    parser.add_argument("--symbol", required=True, help="股票代码，如 TSLA")
    parser.add_argument("--start-date", help="开始日期 YYYY-MM-DD")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="回溯天数（与 start-date/end-date 二选一）")
    parser.add_argument("--output", required=True, help="CSV 输出路径")
    args = parser.parse_args()

    if args.days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    else:
        print("❌ 请指定 --days 或 --start-date + --end-date")
        sys.exit(1)

    fetch_stock_data(args.symbol, start_date, end_date, args.output)


if __name__ == "__main__":
    main()
