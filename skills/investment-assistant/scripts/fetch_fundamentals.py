#!/usr/bin/env python3
"""
拉取财报基本面数据（基于 yfinance），带季度缓存
迁移自 TradingAgents alpha_vantage_fundamentals.py + y_finance.py

Usage:
  python3 fetch_fundamentals.py --symbol TSLA --output /tmp/tsla_fundamentals.json --data-dir ~/openclaw-data/investment/
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime


def _current_quarter():
    now = datetime.now()
    q = (now.month - 1) // 3 + 1
    return f"{now.year}Q{q}"


def _cache_path(data_dir, symbol, quarter):
    return os.path.join(data_dir, "fundamentals", f"{symbol}_{quarter}.md")


def _check_cache(data_dir, symbol):
    quarter = _current_quarter()
    path = _cache_path(data_dir, symbol, quarter)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read(), quarter
    return None, quarter


def _safe(val, fmt=".2f"):
    """Safely format a value that might be None or NaN."""
    if val is None:
        return "N/A"
    try:
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return "N/A"
        return f"{val:{fmt}}"
    except (ValueError, TypeError):
        return str(val)


def _format_large_number(val):
    if val is None:
        return "N/A"
    try:
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return "N/A"
        abs_val = abs(val)
        if abs_val >= 1e12:
            return f"${val/1e12:.2f}T"
        elif abs_val >= 1e9:
            return f"${val/1e9:.2f}B"
        elif abs_val >= 1e6:
            return f"${val/1e6:.2f}M"
        else:
            return f"${val:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def fetch_fundamentals(symbol, output_path, data_dir):
    # Check cache first
    cached, quarter = _check_cache(data_dir, symbol)
    if cached:
        print(f"✅ 使用缓存的 {symbol} {quarter} 财报分析")
        print(f"  缓存文件: {_cache_path(data_dir, symbol, quarter)}")
        result = {
            "symbol": symbol,
            "quarter": quarter,
            "source": "cache",
            "cache_path": _cache_path(data_dir, symbol, quarter),
            "content": cached,
        }
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps({"action": "fetch_fundamentals", "symbol": symbol, "source": "cache", "quarter": quarter}, ensure_ascii=False))
        return

    # Fetch fresh data
    try:
        import yfinance as yf
    except ImportError:
        print("❌ 缺少 yfinance 库，请运行: pip install yfinance")
        sys.exit(1)

    ticker = yf.Ticker(symbol)
    info = ticker.info

    # Company overview
    overview = {
        "Name": info.get("longName", info.get("shortName", symbol)),
        "Sector": info.get("sector", "N/A"),
        "Industry": info.get("industry", "N/A"),
        "Market Cap": _format_large_number(info.get("marketCap")),
        "PE Ratio (TTM)": _safe(info.get("trailingPE")),
        "Forward PE": _safe(info.get("forwardPE")),
        "PEG Ratio": _safe(info.get("pegRatio")),
        "Price to Book": _safe(info.get("priceToBook")),
        "EPS (TTM)": _safe(info.get("trailingEps")),
        "Forward EPS": _safe(info.get("forwardEps")),
        "Dividend Yield": _safe(info.get("dividendYield", 0) * 100 if info.get("dividendYield") else None) + "%" if info.get("dividendYield") else "N/A",
        "Beta": _safe(info.get("beta")),
        "52 Week High": f"${_safe(info.get('fiftyTwoWeekHigh'))}",
        "52 Week Low": f"${_safe(info.get('fiftyTwoWeekLow'))}",
        "50 Day Average": f"${_safe(info.get('fiftyDayAverage'))}",
        "200 Day Average": f"${_safe(info.get('twoHundredDayAverage'))}",
        "Revenue (TTM)": _format_large_number(info.get("totalRevenue")),
        "Gross Profit": _format_large_number(info.get("grossProfits")),
        "EBITDA": _format_large_number(info.get("ebitda")),
        "Net Income": _format_large_number(info.get("netIncomeToCommon")),
        "Profit Margin": _safe((info.get("profitMargins", 0) or 0) * 100) + "%",
        "Operating Margin": _safe((info.get("operatingMargins", 0) or 0) * 100) + "%",
        "Return on Equity": _safe((info.get("returnOnEquity", 0) or 0) * 100) + "%",
        "Return on Assets": _safe((info.get("returnOnAssets", 0) or 0) * 100) + "%",
        "Debt to Equity": _safe(info.get("debtToEquity")),
        "Current Ratio": _safe(info.get("currentRatio")),
        "Book Value": f"${_safe(info.get('bookValue'))}",
        "Free Cash Flow": _format_large_number(info.get("freeCashflow")),
    }

    # Financial statements
    def _df_to_dict(df):
        if df is None or df.empty:
            return {}
        result = {}
        for col in df.columns:
            col_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
            result[col_str] = {}
            for idx in df.index:
                val = df.loc[idx, col]
                try:
                    if val is not None and not (isinstance(val, float) and math.isnan(val)):
                        result[col_str][str(idx)] = float(val) if isinstance(val, (int, float)) else str(val)
                except (ValueError, TypeError):
                    result[col_str][str(idx)] = str(val)
        return result

    balance_sheet = _df_to_dict(ticker.quarterly_balance_sheet)
    cashflow = _df_to_dict(ticker.quarterly_cashflow)
    income_stmt = _df_to_dict(ticker.quarterly_income_stmt)

    # Build output
    output = {
        "symbol": symbol,
        "quarter": quarter,
        "source": "yfinance",
        "fetched_at": datetime.now().isoformat(),
        "overview": overview,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "income_statement": income_stmt,
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Generate cache memo (Markdown)
    memo_lines = [
        f"# {symbol} {quarter} 财报分析",
        "",
        f"> 数据来源: yfinance | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 公司概况",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
    ]
    for k, v in overview.items():
        memo_lines.append(f"| {k} | {v} |")

    memo_lines.extend([
        "",
        "## 最近季度资产负债表",
        "",
    ])
    if balance_sheet:
        first_q = list(balance_sheet.keys())[0]
        memo_lines.append(f"### {first_q}")
        memo_lines.append("")
        memo_lines.append("| 项目 | 值 |")
        memo_lines.append("|------|-----|")
        for k, v in list(balance_sheet[first_q].items())[:15]:
            memo_lines.append(f"| {k} | {_format_large_number(v) if isinstance(v, (int, float)) else v} |")

    memo_lines.extend([
        "",
        "## 最近季度现金流",
        "",
    ])
    if cashflow:
        first_q = list(cashflow.keys())[0]
        memo_lines.append(f"### {first_q}")
        memo_lines.append("")
        memo_lines.append("| 项目 | 值 |")
        memo_lines.append("|------|-----|")
        for k, v in list(cashflow[first_q].items())[:15]:
            memo_lines.append(f"| {k} | {_format_large_number(v) if isinstance(v, (int, float)) else v} |")

    memo_lines.extend([
        "",
        "## 最近季度利润表",
        "",
    ])
    if income_stmt:
        first_q = list(income_stmt.keys())[0]
        memo_lines.append(f"### {first_q}")
        memo_lines.append("")
        memo_lines.append("| 项目 | 值 |")
        memo_lines.append("|------|-----|")
        for k, v in list(income_stmt[first_q].items())[:15]:
            memo_lines.append(f"| {k} | {_format_large_number(v) if isinstance(v, (int, float)) else v} |")

    memo_text = "\n".join(memo_lines)

    # Save cache
    cache_dir = os.path.join(data_dir, "fundamentals")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = _cache_path(data_dir, symbol, quarter)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(memo_text)

    print(f"✅ 已获取 {symbol} 基本面数据")
    print(f"  季度: {quarter}")
    print(f"  市值: {overview['Market Cap']}")
    print(f"  PE (TTM): {overview['PE Ratio (TTM)']}")
    print(f"  营收: {overview['Revenue (TTM)']}")
    print(f"  数据文件: {output_path}")
    print(f"  缓存文件: {cache_file}")
    print(json.dumps({"action": "fetch_fundamentals", "symbol": symbol, "source": "yfinance", "quarter": quarter, "output": output_path}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="拉取财报基本面数据")
    parser.add_argument("--symbol", required=True, help="股票代码")
    parser.add_argument("--output", required=True, help="JSON 输出路径")
    parser.add_argument("--data-dir", required=True, help="数据目录（用于缓存）")
    parser.add_argument("--force-refresh", action="store_true", help="强制刷新，忽略缓存")
    args = parser.parse_args()

    args.data_dir = os.path.expanduser(args.data_dir)
    fetch_fundamentals(args.symbol, args.output, args.data_dir)


if __name__ == "__main__":
    main()
