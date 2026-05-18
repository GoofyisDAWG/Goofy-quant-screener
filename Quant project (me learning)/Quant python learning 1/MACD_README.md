# MACD Backtest Study

**A beginner quant research project — by Hiroki Kunu**

---

## What This Project Is

A systematic backtest of MACD (Moving Average Convergence Divergence) momentum strategies across 6 assets spanning 3 markets, built entirely in Python. This is Part 4 of an ongoing strategy library being built toward an automated asset screener.

The goal was not just to find a profitable strategy, but to understand *how a hybrid momentum-trend strategy behaves differently from the pure mean-reversion strategies tested in Parts 2 and 3 — and whether the right strategy finally fits the right stock.*

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

---

## How MACD Works

MACD uses three components, all derived from Exponential Moving Averages (EMAs). Unlike Simple Moving Averages, EMAs give more weight to recent prices — making MACD faster to react and more sensitive to current momentum.

- **MACD Line** = EMA(fast period) − EMA(slow period)
- **Signal Line** = EMA of the MACD Line over a signal period
- **Histogram** = MACD Line − Signal Line (shows momentum acceleration)

**Trading logic (momentum / trend-following):**
- MACD Line crosses **above** Signal Line → short-term momentum accelerating → **buy signal**
- MACD Line crosses **below** Signal Line → momentum fading or reversing → **exit signal**

MACD is a **hybrid strategy** — it is trend-following in structure but captures momentum in the rate of change, not just direction. The classic parameters (12, 26, 9) were invented by Gerald Appel in the 1970s and remain widely used today.

---

## What Was Tested

- **3 fast EMA periods:** 8, 12, 16 days
- **3 slow EMA periods:** 21, 26, 30 days
- **3 signal periods:** 7, 9, 12 days
- **27 total parameter combinations** per asset (162 backtests total)
- **Full window:** 2016–2026

---

## Validation Method

1. **Parameter robustness** — all 27 combinations tested per asset. A broad green band across the heatmap means the strategy concept genuinely fits the stock. Scattered results across params indicate noise or overfitting
2. **Out-of-sample validation** — best parameters selected using 2016–2020 training data only, then applied blind to unseen 2021–2026 data. Sharpe improvement out-of-sample is the strongest possible signal of a genuine edge

---

## Key Findings

**NVDA — best MACD result, and a turning point in this study**
MACD is the first strategy across all four studies where Sharpe actually *improved* on unseen data: 0.94 in-sample → 1.03 out-of-sample (+9.6%). A momentum strategy meeting a momentum stock — the fit is structurally correct. NVDA still did not beat Buy & Hold on raw return due to the sheer magnitude of the AI-driven uptrend, but the risk-adjusted case is the strongest yet seen for any strategy on NVDA. This confirms the hypothesis from earlier studies: NVDA needs trend-following, not mean-reversion.

**CBA.AX — most surprising result of the study**
Sharpe nearly tripled out-of-sample: 0.26 in-sample → 0.73 out-of-sample (+180.8%). This is rare — most strategies decay on unseen data, not improve. CBA's post-2021 period featured clearer trending behaviour than the choppy 2016–2020 training period, and MACD picked this up cleanly. Did not beat Buy & Hold on raw return, but the risk-adjusted improvement is genuine and robust. A credible risk-management candidate for conservative investors.

**6758.T (Sony) — the most important finding by contrast**
Sony completely failed under MACD: Sharpe of 0.14 in-sample, 0.31 out-of-sample. This is the exact opposite of the Bollinger Bands study (Part 3), where Sony was the standout result. The explanation is structural: Sony's price behaviour is mean-reverting, not trending. MACD is a momentum strategy that looks for breakouts Sony never produces. Same stock, opposite outcomes, depending entirely on strategy type. This confirms the core thesis of the screener project — strategy-asset fit matters more than the strategy itself.

**7203.T (Toyota) — inconclusive**
Moderate Sharpe decay in-sample to out-of-sample (-12.5%), low absolute levels throughout. The all-params spaghetti chart showed strategies clumped together below Buy & Hold for seven years before randomly separating on a 2023–2024 rally. The few parameter combos that looked good in-sample were likely catching that one specific move rather than a consistent edge. Neither MACD nor BB produced a clean result for Toyota — it may require a different approach entirely.

**SPY — largest Sharpe collapse in the study**
In-sample Sharpe of 1.33 dropped to 0.41 out-of-sample (-69.2%). MACD performed well on the steady pre-COVID trend of 2016–2020 but struggled with the choppier, regime-switching environment of 2021–2026. SPY has now consistently resisted all four strategies — it is already efficient, diversified, and smooth. The strategies add friction without adding edge.

**BHP.AX — consistent underperformer across all strategies**
Moderate Sharpe decay (-21.7%), never beat Buy & Hold on raw return. BHP is commodity-driven with macro-dependent price swings that neither mean-reversion nor momentum frameworks handle cleanly. Now confirmed as a poor candidate across BB and MACD.

---

## Understanding the Results: Return vs Risk-Adjusted Return

A key insight from this study is the distinction between two separate questions:

**"Beats B&H: True/False"** answers whether the strategy made more money in raw return than just holding. This is purely about total return %.

**Sharpe Ratio** answers whether the strategy produced good risk-adjusted returns — return per unit of risk taken.

These are independent. A strategy can fail the first test and pass the second simultaneously. CBA and NVDA are the clearest examples: both show Sharpe improvement out-of-sample despite not beating Buy & Hold on raw return. For risk-conscious investors, the Sharpe story is often the more meaningful one.

---

## The Core Insight

MACD confirmed the pattern established across all four studies: **no single strategy works on all assets, and the same asset can produce opposite results depending on strategy type.** Sony's failure under MACD directly mirrors its success under Bollinger Bands — the stock hasn't changed, only the strategy assumption has.

This is not a weakness of MACD. It is evidence that the automated screener (Phase 2) is the right next step — a system that identifies what kind of price behaviour each asset exhibits and routes it to the appropriate strategy automatically.

---

## Part of a Larger Project

- ✅ Strategy 1 — Moving Average Crossover
- ✅ Strategy 2 — RSI
- ✅ Strategy 3 — Bollinger Bands
- ✅ Strategy 4 — MACD (this repo)
- ⬜ Strategy 5 — Mean Reversion
- ⬜ Phase 2 — Automated Screener

---

## How to Run

```bash
pip install yfinance numpy pandas matplotlib
```

Open `Goofy MACD for 6 assets.ipynb` in Jupyter Notebook or Anaconda and run cells top to bottom.

- **Cell 4** — Full backtest: all 6 assets × 27 parameter combinations, comparison table, equity curves, Sharpe heatmap
- **Cell 5** — All 27 MACD parameter combos overlaid per stock
- **Cell 6** — In-sample vs out-of-sample validation (2016–2020 train, 2021–2026 test)

---

## Author

**Hiroki Kunu**
UQ Brisbane | Quantitative Research
[LinkedIn](https://www.linkedin.com/in/hiroki-kunu-ba4218401) | [GitHub](https://github.com/GoofyisDAWG)
