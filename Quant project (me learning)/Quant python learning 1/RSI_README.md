# RSI Backtest Study

**A beginner quant research project — by Hiroki Kunu**

---

## What This Project Is

A systematic backtest of RSI (Relative Strength Index) mean-reversion strategies across 6 assets over 10 years, built entirely in Python. This is Part 2 of an ongoing strategy library being built toward an automated asset screener.

The goal was not just to find a profitable strategy, but to understand *when and why* RSI works — and when it doesn't.

---

## Assets Tested

| Asset | Market | Type |
|-------|--------|------|
| NVDA | US | High-growth tech / AI |
| AAPL | US | Large-cap tech |
| SPY | US | S&P 500 index ETF |
| CBA.AX | ASX | Australian banking |
| BHP.AX | ASX | Australian mining / commodities |
| CSL.AX | ASX | Australian biotech / healthcare |

---

## How RSI Works

RSI measures momentum by comparing average up-days to average down-days over a rolling window (7, 9, 14, or 21 days). It outputs a value from 0–100.

- **RSI < oversold threshold** (20, 25, 30, or 35) → price has been beaten down → **buy signal**
- **RSI > overbought threshold** (65, 70, 75, or 80) → price has run up hard → **exit signal**

This is a **mean-reversion strategy** — the opposite of trend-following. It bets that extreme price moves will snap back to normal.

---

## What Was Tested

- **4 RSI periods:** 7, 9, 14, 21 days
- **4 overbought/oversold threshold pairs:** (70/30), (65/35), (75/25), (80/20)
- **16 total parameter combinations** per asset (96 backtests total)
- **10-year window:** 2016–2026

---

## Validation Method

To check whether results are real or just lucky:

1. **Parameter robustness** — tested all 16 combinations to see if results are consistent across parameters, not dependent on one lucky setting
2. **Out-of-sample validation** — trained on 2016–2020 data only, then tested on unseen 2021–2026 data. If the strategy holds up on data it has never seen, the result is more likely to be genuine

---

## Key Findings

**CBA.AX (Commonwealth Bank) — strongest result**
RSI Sharpe ratio went from 0.53 in-sample to 0.51 out-of-sample — only a 3.8% decay. Remarkable stability across time periods. The strategy consistently detected CBA's short-term bounce behavior and maintained performance on unseen data.

**NVDA — confirmed RSI weakness on momentum stocks**
RSI Sharpe collapsed from 1.17 in-sample to 0.33 out-of-sample (-71.8%). RSI kept signalling overbought during the AI boom when NVDA was genuinely trending. The strategy was not wrong — the asset simply broke the mean-reversion assumption.

**CSL.AX — broken asset problem**
RSI technically "beat" a declining buy-and-hold in some periods, but both were losing propositions. A mean-reversion strategy cannot save a stock in structural decline — the mean itself is falling.

**BHP.AX — parameter robustness concern**
One RSI parameter combination significantly outperformed all others. When results depend heavily on one specific parameter set, they are more likely to be luck than signal.

**SPY — MA beats RSI**
Compared directly against the MA backtest (Part 1), moving average crossover outperforms RSI on SPY. A smooth trending index suits trend-following better than mean-reversion.

---

## The Core Insight

RSI and Moving Average crossover are complementary, not competing. RSI works best on choppy, range-bound assets. MA works best on smooth trending assets. Neither strategy works well on everything — which is exactly the motivation for building an automated screener that can match the right strategy to the right asset.

---

## Part of a Larger Project

This is Strategy 2 of 5 in a strategy library being built toward an automated screener:

- ✅ Strategy 1 — Moving Average Crossover
- ✅ Strategy 2 — RSI (this repo)
- ⬜ Strategy 3 — Bollinger Bands
- ⬜ Strategy 4 — MACD
- ⬜ Strategy 5 — Mean Reversion
- ⬜ Phase 2 — Automated Screener

---

## How to Run

```bash
pip install yfinance numpy pandas matplotlib
```

Open `Goofy8 RSI for 6 assets.ipynb` in Jupyter Notebook or Anaconda and run cells top to bottom.

- **Cell 4** — Full backtest: all 6 assets × 16 parameter combinations
- **Cell 5** — All RSI parameters overlaid per stock
- **Cell 6** — In-sample vs out-of-sample validation (2016–2020 train, 2021–2026 test)

---

## Author

**Hiroki Kunu**
UQ Brisbane | Quantitative Research
[LinkedIn](https://www.linkedin.com/in/hiroki-kunu-ba4218401) | [GitHub](https://github.com/GoofyisDAWG)
