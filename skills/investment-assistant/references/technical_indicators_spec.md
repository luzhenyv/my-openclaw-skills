```markdown
# 技术指标规范

## 支持的技术指标

以下指标由 `scripts/fetch_indicators.py` 计算，数据来源为 yfinance + stockstats。

### 均线系统

| 指标 | Key | 计算方式 | 用途 |
|------|-----|---------|------|
| 50 日简单均线 | `close_50_sma` | 50 日收盘价算术平均 | 中期趋势判断 |
| 200 日简单均线 | `close_200_sma` | 200 日收盘价算术平均 | 长期趋势判断（牛熊分界） |
| 10 日指数均线 | `close_10_ema` | 10 日 EMA 加权 | 短期动量 |

**解读要点**：
- 价格 > MA50 > MA200：多头排列，趋势向上
- 价格 < MA50 < MA200：空头排列，趋势向下
- MA50 上穿 MA200（金叉）：长期看多信号
- MA50 下穿 MA200（死叉）：长期看空信号

### MACD 系统

| 指标 | Key | 计算方式 | 用途 |
|------|-----|---------|------|
| MACD 线 | `macd` | EMA12 - EMA26 | 趋势动量方向 |
| 信号线 | `macds` | MACD 的 9日 EMA | 交叉触发 |
| 柱状图 | `macdh` | MACD - Signal | 动量强弱 |

**解读要点**：
- MACD 上穿 Signal（金叉）：买入信号
- MACD 下穿 Signal（死叉）：卖出信号
- 柱状图由负转正/由正转负：动量转换
- 零轴上方：多头市场；零轴下方：空头市场

### 动量指标

| 指标 | Key | 计算方式 | 用途 |
|------|-----|---------|------|
| RSI | `rsi` | 14 日相对强弱指标 | 超买超卖判断 |
| MFI | `mfi` | 资金流量指标（成交量加权 RSI） | 量价配合判断 |

**解读要点**：
- RSI > 70：超买区域，注意回调风险
- RSI < 30：超卖区域，可能存在反弹机会
- RSI 背离：价格创新高但 RSI 未创新高 → 顶背离（看空）
- MFI > 80：资金流入过热；MFI < 20：资金流出过度

### 布林带

| 指标 | Key | 计算方式 | 用途 |
|------|-----|---------|------|
| 中轨 | `boll` | 20 日 SMA | 均值回归中心 |
| 上轨 | `boll_ub` | 中轨 + 2σ | 压力/超买区域 |
| 下轨 | `boll_lb` | 中轨 - 2σ | 支撑/超卖区域 |

**解读要点**：
- 价格触及上轨：可能超买，短期回调概率增大
- 价格触及下轨：可能超卖，短期反弹概率增大
- 布林带收窄（squeeze）：变盘在即，方向待定
- 布林带扩张：趋势加速

### 波动性 & 成交量

| 指标 | Key | 计算方式 | 用途 |
|------|-----|---------|------|
| ATR | `atr` | 14 日平均真实波幅 | 波动性衡量 |
| VWMA | `vwma` | 成交量加权均价 | 量价确认 |

**解读要点**：
- ATR 升高：波动加剧，可能出现大行情
- ATR 降低：波动缩小，可能处于盘整
- 价格 > VWMA：多方控制；价格 < VWMA：空方控制

## 指标组合建议

对不同分析场景，推荐以下组合（最多选 8 个）：

### 趋势确认
`close_50_sma`, `close_200_sma`, `macd`, `macds`, `rsi`, `boll`, `boll_ub`, `boll_lb`

### 短期交易
`close_10_ema`, `macd`, `macdh`, `rsi`, `boll_ub`, `boll_lb`, `atr`, `vwma`

### 超买超卖判断
`rsi`, `mfi`, `boll`, `boll_ub`, `boll_lb`, `macd`, `macds`, `close_50_sma`

## 脚本调用

```bash
# 计算所有指标
python3 <SKILL_DIR>/scripts/fetch_indicators.py \
  --symbol TSLA --all --date 2026-02-26 --lookback 60 \
  --output /tmp/tsla_indicators.json

# 计算指定指标
python3 <SKILL_DIR>/scripts/fetch_indicators.py \
  --symbol TSLA \
  --indicators "macd,rsi,boll,close_50_sma,close_200_sma" \
  --date 2026-02-26 --lookback 60 \
  --output /tmp/tsla_indicators.json
```

## 输出格式

```json
{
  "symbol": "TSLA",
  "target_date": "2026-02-26",
  "lookback_days": 60,
  "latest_close": 408.50,
  "indicators": {
    "rsi": {
      "description": "14-period Relative Strength Index — overbought (>70) / oversold (<30)",
      "latest_value": 42.35,
      "values": [
        {"date": "2026-02-26", "value": 42.35},
        {"date": "2026-02-25", "value": 45.12}
      ]
    }
  }
}
```
```
