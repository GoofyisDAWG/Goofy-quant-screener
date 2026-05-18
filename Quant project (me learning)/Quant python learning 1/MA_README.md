# Moving Average Crossover Backtest Study

**A beginner quant research project — by Hiroki Kunu**

---

## What This Project Is

A systematic backtest of Moving Average (MA) crossover trading strategies across two separate studies, built entirely in Python. This is Part 1 of an ongoing strategy library being built toward an automated asset screener.

The goal was not just to find a profitable strategy, but to understand *how to properly test whether a strategy is real or just lucky.*

---

## Two Studies

### Study 1 — Original 6 Assets (Crypto + US Stocks)
**Files:** `ma_multi_backtest.py`, `out_of_sample_test.py`

| Asset | Market | Type |
|-------|--------|------|
| AAPL | US | Large-cap tech |
| SPY | US | S&P 500 index ETF |
| TSLA | US | High-volatility growth |
| WM | US | Defensive / utility-like |
| BTC-USD | Crypto | Bitcoin |
| ETH-USD | Crypto | Ethereum |

### Study 2 — US + Australian ASX Stocks
**File:** `Goofy MA for 6 assets.ipynb`

| Asset | Market | Type |
|-------|--------|------|
| NVDA | US | High-growth tech / AI |
| AAPL | US | Large-cap tech |
| SPY | US | S&P 500 index ETF |
| CBA.AX | ASX | Australian banking |
| BHP.AX | ASX | Australian mining |
| CSL.AX | ASX | Australian biotech |

---

## How MA Crossover Works

Two moving averages are calculated — a fast MA (short window) and a slow MA (long window). When the fast MA crosses above the slow MA, the trend is turning up — buy. When it crosses below — exit. It's a trend-following strategy that rides momentum rather than fighting it.

---

## Validation Method

1. **Parameter robustness** — multiple MA pairs tested per asset to check results are consistent, not dependent on one lucky setting
2. **Out-of-sample validation** — trained on 2016–2020 data only, tested on unseen 2021–2026 data

---

## Key Findings

**Study 1 — Crypto + US Stocks**

ETH was the standout. The MA strategy didn't just reduce risk — it massively outperformed Buy & Hold in total return (5,424% vs 564%). The strategy successfully dodged the 80%+ crypto crashes while staying in during the big bull runs.

BTC showed strong risk-adjusted performance (Sharpe > 1.0) across multiple MA pairs — a sign of robustness, not just one lucky parameter.

For stable stocks like AAPL and SPY, Buy & Hold was actually better. The MA strategy kept stepping out of the market during short corrections and missing the rebounds.

The out-of-sample test was the reality check. Sharpe ratios dropped 80–95% for crypto when tested on 2021–2026. The post-2021 period was choppy and mean-reverting — exactly the worst environment for MA crossover strategies.

TSLA was the surprise — the only asset to beat Buy & Hold out-of-sample despite being the most suspicious going in.

**Study 2 — US + ASX Stocks**

MA works on smooth trending assets. SPY with MA5/20 held a Sharpe of 0.96 out-of-sample — the most stable result across both studies.

NVDA confirmed the core weakness of MA — too slow to catch parabolic momentum. The strategy returned 262% vs Buy & Hold's 1,258% out-of-sample.

CBA.AX (Commonwealth Bank) was the ASX standout — Sharpe actually improved from 0.19 in-sample to 0.48 out-of-sample, showing the strategy genuinely adapted to CBA's steady post-COVID trend.

BHP.AX was the clearest failure — Sharpe collapsed from 0.92 to -0.11 out-of-sample. Commodity-driven, choppy stocks are poorly suited to trend-following.

---

## The Core Lesson

A strategy that looks perfect on historical data often breaks down on new data. That gap — between in-sample and out-of-sample — is where real quant research lives. The goal isn't to find a strategy that worked in the past. It's to find one robust enough to survive conditions it hasn't seen yet.

Trend-following works best on assets that move in sustained, clean directions. It fails on parabolic momentum stocks, commodity-driven names, and anything choppy or mean-reverting.

---

## Part of a Larger Project

- ✅ Strategy 1 — Moving Average Crossover (this repo)
- ✅ Strategy 2 — RSI
- ⬜ Strategy 3 — Bollinger Bands
- ⬜ Strategy 4 — MACD
- ⬜ Strategy 5 — Mean Reversion
- ⬜ Phase 2 — Automated Screener

---

## How to Run

```bash
pip install yfinance numpy pandas matplotlib
```

**Study 1:** Run `ma_multi_backtest.py` then `out_of_sample_test.py`

**Study 2:** Open `Goofy MA for 6 assets.ipynb` in Jupyter and run cells top to bottom

---

## Author

**Hiroki Kunu**
UQ Brisbane | Quantitative Research
[LinkedIn](https://www.linkedin.com/in/hiroki-kunu-ba4218401) | [GitHub](https://github.com/GoofyisDAWG)
