#!/usr/bin/env python3
"""
生成 K 线图（基于 mplfinance）

Usage:
  python3 generate_chart.py --symbol TSLA --period daily --days 60 --output /tmp/tsla_daily.png
  python3 generate_chart.py --symbol TSLA --period weekly --days 120 --output /tmp/tsla_weekly.png
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta


def generate_chart(symbol, period, days, output_path):
    try:
        import yfinance as yf
    except ImportError:
        print("❌ 缺少 yfinance 库，请运行: pip install yfinance")
        sys.exit(1)

    try:
        import mplfinance as mpf
    except ImportError:
        print("❌ 缺少 mplfinance 库，请运行: pip install mplfinance")
        sys.exit(1)

    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend

    # Download data
    end_date = datetime.now()
    # Fetch extra data for weekly aggregation
    extra_days = days * 2 if period == "weekly" else int(days * 1.5)
    start_date = end_date - timedelta(days=extra_days)

    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))

    if df.empty:
        print(f"❌ 没有获取到 {symbol} 的数据")
        sys.exit(1)

    # Resample to weekly if needed
    if period == "weekly":
        df_plot = df.resample("W").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }).dropna()
        # Keep last N weeks
        n_bars = days // 7
        df_plot = df_plot.tail(max(n_bars, 20))
    else:
        df_plot = df.tail(days)

    if df_plot.empty:
        print(f"❌ 数据不足以生成 {period} 图表")
        sys.exit(1)

    # Define moving averages
    if period == "weekly":
        mav = (4, 10, 20)  # ~1m, ~2.5m, ~5m
        title_suffix = "Weekly"
    else:
        mav = (5, 10, 20)
        title_suffix = "Daily"

    # Chart style
    mc = mpf.make_marketcolors(
        up="red", down="green",  # Chinese market convention
        edge="inherit",
        wick="inherit",
        volume="in",
    )
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle="-", gridcolor="#e6e6e6")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    # Generate chart
    mpf.plot(
        df_plot,
        type="candle",
        volume=True,
        mav=mav,
        style=style,
        title=f"\n{symbol} {title_suffix} ({df_plot.index[0].strftime('%Y-%m-%d')} ~ {df_plot.index[-1].strftime('%Y-%m-%d')})",
        ylabel="Price ($)",
        ylabel_lower="Volume",
        figsize=(14, 8),
        savefig=dict(fname=output_path, dpi=150, bbox_inches="tight"),
    )

    print(f"✅ K线图已生成")
    print(f"  股票: {symbol}")
    print(f"  周期: {title_suffix}")
    print(f"  时间范围: {df_plot.index[0].strftime('%Y-%m-%d')} ~ {df_plot.index[-1].strftime('%Y-%m-%d')}")
    print(f"  K线数量: {len(df_plot)}")
    print(f"  均线: MA{mav[0]}, MA{mav[1]}, MA{mav[2]}")
    print(f"  输出文件: {output_path}")
    print(json.dumps({
        "action": "generate_chart",
        "symbol": symbol,
        "period": period,
        "bars": len(df_plot),
        "output": output_path,
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="生成 K 线图")
    parser.add_argument("--symbol", required=True, help="股票代码")
    parser.add_argument("--period", choices=["daily", "weekly"], default="daily", help="周期")
    parser.add_argument("--days", type=int, default=60, help="回溯天数（默认 60）")
    parser.add_argument("--output", required=True, help="PNG 输出路径")
    args = parser.parse_args()

    generate_chart(args.symbol, args.period, args.days, args.output)


if __name__ == "__main__":
    main()
