#!/usr/bin/env python3
"""
计算技术指标（基于 yfinance + stockstats）
迁移自 TradingAgents stockstats_utils.py + y_finance.py

Usage:
  python3 fetch_indicators.py --symbol TSLA --indicators "macd,rsi,boll,close_50_sma" --date 2026-02-26 --lookback 60 --output /tmp/tsla_indicators.json
  python3 fetch_indicators.py --symbol TSLA --all --date 2026-02-26 --output /tmp/tsla_indicators.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

ALL_INDICATORS = [
    "close_50_sma", "close_200_sma", "close_10_ema",
    "macd", "macds", "macdh",
    "rsi",
    "boll", "boll_ub", "boll_lb",
    "atr", "vwma", "mfi",
]

INDICATOR_DESCRIPTIONS = {
    "close_50_sma": "50-period Simple Moving Average — medium-term trend direction",
    "close_200_sma": "200-period Simple Moving Average — long-term trend direction",
    "close_10_ema": "10-period Exponential Moving Average — short-term momentum",
    "macd": "MACD Line (12-26 EMA difference) — trend momentum",
    "macds": "MACD Signal Line (9-period EMA of MACD) — momentum crossover trigger",
    "macdh": "MACD Histogram (MACD minus Signal) — momentum strength",
    "rsi": "14-period Relative Strength Index — overbought (>70) / oversold (<30)",
    "boll": "Bollinger Bands Middle (20 SMA) — price mean reversion center",
    "boll_ub": "Bollinger Upper Band (middle + 2σ) — resistance / overbought zone",
    "boll_lb": "Bollinger Lower Band (middle - 2σ) — support / oversold zone",
    "atr": "Average True Range (14-period) — volatility measure",
    "vwma": "Volume Weighted Moving Average — volume-confirmed price level",
    "mfi": "Money Flow Index — volume-weighted RSI, overbought (>80) / oversold (<20)",
}


def _download_data(symbol, years=15):
    """Download historical data and cache locally."""
    try:
        import yfinance as yf
    except ImportError:
        print("❌ 缺少 yfinance 库，请运行: pip install yfinance")
        sys.exit(1)

    end = datetime.now()
    start = end - timedelta(days=years * 365)
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))
    if df.empty:
        print(f"❌ 无法获取 {symbol} 的历史数据")
        sys.exit(1)
    return df


def _compute_indicators(df, indicators):
    """Compute indicators using stockstats."""
    try:
        from stockstats import wrap
    except ImportError:
        print("❌ 缺少 stockstats 库，请运行: pip install stockstats")
        sys.exit(1)

    # stockstats expects lowercase column names
    df_copy = df.copy()
    df_copy.columns = [c.lower() for c in df_copy.columns]

    ss = wrap(df_copy)
    results = {}

    for indicator in indicators:
        try:
            series = ss[indicator]
            results[indicator] = series.dropna()
        except Exception as e:
            print(f"⚠️ 计算 {indicator} 失败: {e}")
            results[indicator] = None

    return results


def fetch_indicators(symbol, indicators, target_date, lookback, output_path):
    df = _download_data(symbol)

    # Filter to dates before/on target_date
    target = datetime.strptime(target_date, "%Y-%m-%d")
    # df.index is tz-aware, make target_date tz-aware too
    if df.index.tz is not None:
        import pytz
        target = target.replace(tzinfo=df.index.tz)

    df_filtered = df[df.index <= target]
    if df_filtered.empty:
        print(f"❌ {target_date} 之前没有 {symbol} 的数据")
        sys.exit(1)

    computed = _compute_indicators(df_filtered, indicators)

    output = {
        "symbol": symbol,
        "target_date": target_date,
        "lookback_days": lookback,
        "latest_close": round(float(df_filtered.iloc[-1]["Close"]), 2),
        "indicators": {},
    }

    for ind_name, series in computed.items():
        if series is None or series.empty:
            output["indicators"][ind_name] = {
                "description": INDICATOR_DESCRIPTIONS.get(ind_name, ""),
                "error": "计算失败或无数据",
                "values": [],
            }
            continue

        # Get last N values
        recent = series.tail(lookback)
        values = []
        for idx, val in recent.items():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            values.append({"date": date_str, "value": round(float(val), 4)})

        latest_val = round(float(series.iloc[-1]), 4)
        output["indicators"][ind_name] = {
            "description": INDICATOR_DESCRIPTIONS.get(ind_name, ""),
            "latest_value": latest_val,
            "values": values,
        }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 已计算 {symbol} 的技术指标")
    print(f"  日期: {target_date}")
    print(f"  最新收盘: ${output['latest_close']:.2f}")
    for ind_name, ind_data in output["indicators"].items():
        if "latest_value" in ind_data:
            print(f"  {ind_name}: {ind_data['latest_value']}")
    print(f"  输出文件: {output_path}")
    print(json.dumps({"action": "fetch_indicators", "symbol": symbol, "count": len(indicators), "output": output_path}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="计算技术指标")
    parser.add_argument("--symbol", required=True, help="股票代码")
    parser.add_argument("--indicators", help="逗号分隔的指标列表")
    parser.add_argument("--all", action="store_true", help="计算所有指标")
    parser.add_argument("--date", required=True, help="目标日期 YYYY-MM-DD")
    parser.add_argument("--lookback", type=int, default=60, help="回溯天数（默认 60）")
    parser.add_argument("--output", required=True, help="JSON 输出路径")
    args = parser.parse_args()

    if args.all:
        indicators = ALL_INDICATORS
    elif args.indicators:
        indicators = [i.strip() for i in args.indicators.split(",")]
        invalid = [i for i in indicators if i not in ALL_INDICATORS]
        if invalid:
            print(f"⚠️ 未知指标将尝试计算: {invalid}")
    else:
        print("❌ 请指定 --indicators 或 --all")
        sys.exit(1)

    fetch_indicators(args.symbol, indicators, args.date, args.lookback, args.output)


if __name__ == "__main__":
    main()
