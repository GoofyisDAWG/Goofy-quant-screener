# Mean Reversion Backtest — Z-Score Strategy

Z-score based mean reversion strategy backtested across 6 global assets. The strategy buys when price drops significantly below its rolling mean and exits when price reverts. Grid searches 20 parameter combinations across rolling windows and Z-score thresholds, with full walk-forward train/test validation.

This is **Strategy 5 of 5** in a series building toward an automated multi-strategy asset screener. Previous strategies: [Moving Average](https://github.com/your-username/MA-backtest) · [RSI](https://github.com/your-username/RSI-Backtest-) · [Bollinger Bands](https://github.com/your-username/Bollinger-Bands-backtest) · [MACD](https://github.com/your-username/MACD-backtest)

---

## Strategy Logic

- Compute a rolling Z-score: `Z = (Price − Rolling Mean) / Rolling Std Dev`
- **Enter long** when Z-score drops below `-threshold` (price is unusually cheap vs recent history)
- **Exit** when Z-score reverts back above `0` (price has returned to its mean)
- Long-only. No shorting.

**Parameters grid-searched:**
| Parameter | Values tested |
|---|---|
| Rolling window | 10, 20, 30, 40, 60 days |
| Z-score threshold | 1.0, 1.5, 2.0, 2.5 |

---

## Assets & Period

| Asset | Market |
|---|---|
| NVDA | US — NASDAQ |
| SPY | US — S&P 500 ETF |
| CBA.AX | Australia — ASX |
| BHP.AX | Australia — ASX |
| 7203.T | Japan — Toyota |
| 6758.T | Japan — Sony |

- **Training period:** 2016–2020 (in-sample optimisation)
- **Test period:** 2021–2026 (out-of-sample validation)

---

## Results

| Ticker | Best Params | IN Sharpe | OUT Sharpe | OUT Strat Return % | OUT B&H Return % | OUT Max DD % |
|---|---|---|---|---|---|---|
| NVDA | w=10, z=1.0 | 0.60 | 0.57 | 152.22% | 1292.47% | -30.95% |
| SPY | w=30, z=2.0 | 0.31 | **0.55** | 36.69% | 96.90% | -16.19% |
| CBA.AX | w=20, z=1.0 | 0.31 | **0.64** | 41.70% | 166.03% | -14.64% |
| BHP.AX | w=20, z=1.0 | 1.10 | 0.66 | 70.58% | 109.22% | -26.79% |
| 7203.T | w=60, z=1.5 | 0.88 | 0.19 | 18.88% | 145.92% | -35.30% |
| 6758.T | w=10, z=1.5 | 1.34 | 0.27 | 30.92% | 67.37% | -20.44% |

---

## Key Findings

**No asset beat Buy & Hold in absolute return.** 2021–2026 was a broad bull market across US, Australian, and Japanese equities — mean reversion is structurally a sideways/range-bound market strategy and is expected to underperform in sustained uptrends.

**SPY and CBA.AX improved their Sharpe ratio out-of-sample** (+77% and +106% respectively). This is a rare result and suggests the strategy is doing something genuinely useful for those assets — sitting out volatile periods, which significantly reduced drawdowns (SPY max DD dropped from -28% to -16%, CBA from -33% to -14%). The trade-off is giving up raw return for lower risk.

**The Japanese stocks (Toyota, Sony) collapsed out-of-sample** despite Sony having the highest in-sample Sharpe (1.34) of any asset across all five strategies. Both entered strong uptrends post-2021 — the strategy kept exiting positions early interpreting trend moves as mean-reversion opportunities. This is the clearest example in the study of a strategy that fits an asset in one regime and completely breaks in another.

**NVDA behaved as expected** — pure momentum stock, mean reversion captured some gains (152%) but missed the AI-driven uptrend almost entirely (B&H: 1292%). MACD remains the best strategy fit for NVDA across all backtests.

**BHP.AX showed moderate performance** with the strategy returning 70% vs B&H 109%, holding a Sharpe of 0.66 — consistent with BHP's commodity-driven, macro-dependent character which doesn't fit cleanly into any single strategy.

---

## Notebook Structure

| Cell | Content |
|---|---|
| 0–3 | pip installs |
| 4 | Full grid search across all 20 param combos + Sharpe heatmap |
| 5 | All param combinations overlaid per stock (robustness check) |
| 6 | Walk-forward train/test split — best params applied to unseen data |

---

## What's Next — Phase 2

With all 5 strategies built and characterised, the next step is an **automated screener**: input any list of assets, run all strategies, and output a comparison table showing which strategy fits each asset best based on Sharpe, return, and max drawdown.

---

## Dependencies

```
yfinance
numpy
pandas
matplotlib
```
