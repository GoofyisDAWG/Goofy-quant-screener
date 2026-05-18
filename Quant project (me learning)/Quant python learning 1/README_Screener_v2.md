# Goofy Screener v2 — Automated Single-Market Strategy Screener

A quantitative trading screener that automatically runs **5 backtested strategies** across any stock universe, selects the best strategy per asset using in-sample optimisation, and validates performance on out-of-sample data the model never saw.

> **Core idea:** Given any list of assets, automatically find which quant strategy fits each one best — and prove it on data the model was never trained on.

---

## What It Does

1. Downloads live price data via Yahoo Finance
2. Splits into **train (2016–2020)** and **test (2021–present)**
3. Grid searches all strategies and parameter combinations on training data only
4. Selects the best strategy per asset by in-sample Sharpe ratio
5. Locks parameters and applies to out-of-sample test data
6. Compares strategy vs Buy & Hold on return, Sharpe, and max drawdown
7. Exports a colour-coded Excel report

---

## Files

```
├── Goofy Screener v2.ipynb     — Interactive Jupyter notebook (run this)
├── goofy_screener_daily.py     — Standalone Python script version
├── screener_output/            — Excel reports (auto-generated, gitignored)
└── README.md
```

---

## The 5 Strategies

| Strategy | Logic | Best Fit |
|---|---|---|
| MA Crossover | Short MA > Long MA → long | Smooth trending assets, broad ETFs |
| RSI | Buy oversold, sell overbought | Stable dividend stocks, banks |
| Bollinger Bands | Buy below lower band, sell at midline | Range-bound, mean-reverting assets |
| MACD | MACD line > signal line → long | Growth stocks, hybrid momentum |
| Mean Reversion | Z-score < −threshold → long, exit at 0 | Sideways markets only |

---

## Methodology

| | Detail |
|---|---|
| **Train period** | Jan 2016 → Dec 2020 (in-sample) |
| **Test period** | Jan 2021 → present (out-of-sample) |
| **Parameter selection** | Grid search on training data only — parameters locked before testing |
| **Signal execution** | `.shift(1)` on all signals — zero lookahead bias |
| **Sharpe ratio** | Annualised log return ÷ annualised volatility |
| **Max drawdown** | Peak-to-trough on cumulative equity curve |
| **Benchmark** | Buy & Hold (passive holding of the same asset) |

---

## Asset Universes

Change the `UNIVERSE` variable in the notebook to switch markets:

| Universe | Assets | Examples |
|---|---|---|
| `"ASX"` | 23 stocks | CBA.AX, BHP.AX, CSL.AX, XRO.AX, IOZ.AX |
| `"US"` | 22 stocks | NVDA, SPY, AAPL, JPM, GLD, QQQ |
| `"CUSTOM"` | Your own list | Edit the `CUSTOM_UNIVERSE` list |

---

## Output — Excel Report

Each run saves `screener_output/Goofy_Screener_YYYY-MM-DD.xlsx` with:

| Column | What it means |
|---|---|
| Best Strategy | Strategy with highest in-sample Sharpe |
| Train Sharpe | Sharpe on 2016–2020 data (used for selection) |
| OUT Sharpe | Sharpe on 2021–present data (real performance) |
| OUT Strat Ret % | Total return of strategy in test period |
| OUT B&H Ret % | Total return of buy & hold in test period |
| OUT Strat Max DD % | Strategy's worst peak-to-trough drop |
| OUT B&H Max DD % | Buy & hold's worst peak-to-trough drop |
| DD Saved % | How much drawdown the strategy avoided vs holding |
| Beats B&H | Whether strategy beat buy & hold on raw return |

---

## Key Findings

**Strategy-asset fit matters more than the strategy itself.**
The same MACD strategy produces a Sharpe of 1.03 on NVDA and 0.31 on Sony. The same Bollinger Bands strategy produces 0.87 on Sony and −0.12 on NVDA. The screener exists to find the right match.

**Out-of-sample is everything.**
Sony's Mean Reversion in-sample Sharpe was 1.34 — the highest result in the entire project. Out-of-sample it dropped to 0.41. Without the train/test split that looks like the best strategy. It isn't.

**Why most strategies don't beat Buy & Hold on return — and why that's honest.**
2021–2026 was a strong bull market. Passive holding wins on raw return in sustained uptrends. The real value of these strategies is drawdown protection — capping worst-case losses to −10%/−20% while Buy & Hold drops −30%/−70% over the same period.

---

## How to Run

### Requirements
```bash
pip install yfinance pandas numpy openpyxl matplotlib
```

### Jupyter (recommended)
Open `Goofy Screener v2.ipynb` in Anaconda/Jupyter and run cells top to bottom.

### Command line
```bash
# Run ASX universe (default)
python goofy_screener_daily.py

# Change UNIVERSE in the script to "US" or "CUSTOM" before running
```

---

## Honest Limitations

- **No transaction costs.** Brokerage and slippage would reduce returns, especially for frequent traders.
- **Sharpe without risk-free rate.** Subtracting cash rates (~4–5%) would reduce Sharpe by roughly 0.3–0.5.
- **Long-only.** All strategies are long or flat. No short selling.
- **No position sizing.** Each trade is 100% in or 100% out — no volatility scaling.
- **No portfolio construction.** Assets are screened individually with no correlation analysis.

---

## Part of a Larger Project

This screener is built on top of **5 individually backtested strategies** — each one built and validated before being combined here:

- [Moving Average Crossover Backtest](https://github.com/GoofyisDAWG/Moving-Average-crossover-backtest)
- [RSI Backtest](https://github.com/GoofyisDAWG/RSI-Backtest-)
- [Bollinger Bands Backtest](https://github.com/GoofyisDAWG/Bollinger-Bands-backtest)
- [MACD Backtest](https://github.com/GoofyisDAWG/MACD-backtest)

**Next step → [Phase 3: Multi-Market Screener (US + ASX + JPX)](https://github.com/GoofyisDAWG)** — adds Japan, composite scoring, and tier ranking.

---

## Disclaimer

For educational and research purposes only. All results are historical backtests and do not guarantee future performance. Nothing here constitutes financial advice.

---

*Built by Hiroki Kunu — International Finance, University of Queensland*  
*[GitHub: GoofyisDAWG](https://github.com/GoofyisDAWG) | [LinkedIn](https://www.linkedin.com/in/hiroki-kunu-ba4218401)*
