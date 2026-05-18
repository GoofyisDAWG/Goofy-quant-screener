# Bollinger Bands Backtest Study

**A beginner quant research project — by Hiroki Kunu**

---

## What This Project Is

A systematic backtest of Bollinger Bands mean-reversion strategies across 6 assets spanning 3 markets, built entirely in Python. This is Part 3 of an ongoing strategy library being built toward an automated asset screener.

The goal was not just to find a profitable strategy, but to understand *which market characters Bollinger Bands actually suits — and which it fundamentally cannot work on.*

---

## Assets Tested

| Asset | Market | Type |
|-------|--------|------|
| NVDA | US | High-growth tech / AI |
| SPY | US | S&P 500 index ETF |
| CBA.AX | ASX | Australian banking |
| BHP.AX | ASX | Australian mining / commodities |
| 7203.T | TSE | Toyota — Japanese auto |
| 6758.T | TSE | Sony — Japanese electronics |

This was the first study to include Japanese stocks (Tokyo Stock Exchange), adding a third market alongside US and ASX.

---

## How Bollinger Bands Works

Three lines are plotted around price:

- **Middle Band** = Simple Moving Average over a rolling window
- **Upper Band** = SMA + (N × rolling standard deviation)
- **Lower Band** = SMA - (N × rolling standard deviation)

The bands expand during high volatility and contract during low volatility — they anchor the statistical top and bottom of price movement at any point in time. Roughly 95% of all price action stays within 2 standard deviations of the mean.

**Trading logic (mean reversion):**
- Price touches or falls below the Lower Band → statistically cheap → **buy signal**
- Price touches or rises above the Upper Band → statistically expensive → **exit signal**

The bet is that extreme moves will snap back to the mean. This works in range-bound, choppy markets. It fails when price breaks out and keeps going — i.e., genuine trends.

---

## What Was Tested

- **4 window sizes:** 10, 15, 20, 30 days
- **4 standard deviation widths:** 1.5σ, 2.0σ, 2.5σ, 3.0σ
- **16 total parameter combinations** per asset (96 backtests total)
- **Full window:** 2016–2026

---

## Validation Method

1. **Parameter robustness** — all 16 combinations tested per asset. Broad green regions in the heatmap indicate the strategy concept genuinely fits the stock, not just one lucky parameter setting
2. **Out-of-sample validation** — best parameters selected using 2016–2020 training data only, then applied blind to unseen 2021–2026 data

---

## Key Findings

**6758.T (Sony) — the standout result of the study**
The only asset to beat Buy & Hold out-of-sample (Beats B&H: True). Sharpe dropped from 1.34 in-sample to 0.87 out-of-sample — a 35% decay, which is actually contained compared to other assets. The heatmap showed broad robustness across multiple parameter combinations, confirming the mean-reversion behaviour in Sony is structural rather than a lucky setting. Sony's range-bound price character makes it a natural fit for this strategy type.

**7203.T (Toyota) — strong risk-adjusted performance**
Did not beat Buy & Hold in raw return out-of-sample, but delivered a smoother equity curve with meaningfully lower drawdown. Sharpe held at 0.62 on unseen data. For investors prioritising capital preservation over maximum return, Toyota is a valid target for this strategy.

**Japan as a market — confirmed hypothesis**
Both Japanese stocks outperformed expectations. Japan's lower volatility and range-bound market character makes it structurally well-suited to mean-reversion strategies. This was the most surprising and interesting finding of the study.

**SPY — tracks the market, doesn't beat it**
The BB strategy on SPY produced an equity curve that almost perfectly shadows Buy & Hold. SPY is already diversified across 500 stocks, so it has naturally low volatility and rarely makes extreme moves outside the bands. The risk reduction wasn't large enough to justify the opportunity cost of missing the upside. Buy & Hold is better for SPY.

**CBA.AX — generates return but at higher relative risk**
Can produce return, but the Sharpe ratio reveals the risk taken to get there isn't well compensated. Some investors might accept this tradeoff; most wouldn't when comparing to alternatives.

**BHP.AX — largest in-sample to out-of-sample deterioration**
Sharpe collapsed from 1.00 to 0.33 out-of-sample (-67%). Something in BHP's price behaviour changed significantly between the training and test periods. Commodity-driven stocks with external macro drivers are poorly suited to a pure mean-reversion framework.

**NVDA — worst outcome in the study**
Not only failed to beat Buy & Hold — it actively increased risk while missing the entire AI-driven uptrend. Every time the strategy sold at the upper band, NVDA continued higher. BB is fundamentally the wrong strategy type for parabolic momentum stocks. NVDA belongs in a trend-following framework, not a mean-reversion one.

---

## The Core Insight

Bollinger Bands is not a universal strategy — it is a mean-reversion tool that only works when that assumption holds. Range-bound stocks with consistent oscillation around a mean (like Japanese equities) are natural fits. Trending stocks (NVDA) and commodity-driven names (BHP) will actively punish this strategy by continuing to move in the direction the strategy just bet against.

This is not a failure of Bollinger Bands. It is a confirmation that **strategy-asset fit matters more than the strategy itself** — the exact motivation for building the automated screener in Phase 2.

---

## Part of a Larger Project

- ✅ Strategy 1 — Moving Average Crossover
- ✅ Strategy 2 — RSI
- ✅ Strategy 3 — Bollinger Bands (this repo)
- ⬜ Strategy 4 — MACD
- ⬜ Strategy 5 — Mean Reversion
- ⬜ Phase 2 — Automated Screener

---

## How to Run

```bash
pip install yfinance numpy pandas matplotlib
```

Open `Goofy BB for 6 assets.ipynb` in Jupyter Notebook or Anaconda and run cells top to bottom.

- **Cell 4** — Full backtest: all 6 assets × 16 parameter combinations, comparison table, equity curves, Sharpe heatmap
- **Cell 5** — All 16 BB parameter combos overlaid per stock
- **Cell 6** — In-sample vs out-of-sample validation (2016–2020 train, 2021–2026 test)

---

## Author

**Hiroki Kunu**
UQ Brisbane | Quantitative Research
[LinkedIn](https://www.linkedin.com/in/hiroki-kunu-ba4218401) | [GitHub](https://github.com/GoofyisDAWG)
