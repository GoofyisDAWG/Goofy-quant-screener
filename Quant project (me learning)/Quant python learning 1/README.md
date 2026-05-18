# Goofy Screener — Multi-Market Quant Strategy System

A quantitative trading research project built from scratch in Python.  
Five strategies individually backtested, then combined into a 9-phase systematic pipeline that screens **117 assets across US, ASX, and JPX markets** — complete with regime detection, Kelly-based sizing, correlation-aware portfolio construction, an XGBoost ML signal layer, paper trading, and walk-forward validation.

> **Core finding:** Strategy-asset fit matters more than the strategy itself. The same strategy that produces a Sharpe of 0.87 on one stock produces -0.21 on another. The screener exists to find which combination actually works — and proves it on data the model never saw.

---

## Build Phases

| Phase | What it adds | Key file |
|-------|-------------|----------|
| 1–2 | Individual strategy backtests (MA, RSI, BB, MACD, Mean Rev) | `Goofy MA/RSI/BB/MACD/Mean Reversion for 6 assets.ipynb` |
| 3 | Multi-market screener — 117 assets, 3 markets, Excel output | `goofy_screener_phase3.py` |
| 4a | Regime detection — VIX + SMA regime gate | `regime_detector.py` |
| 4b | Empirical gate search — finds which regime thresholds actually improve results | `Goofy Phase 4b — Empirical Gate Search.ipynb` |
| 5 | Position sizing — Half-Kelly + 15% vol target | `position_sizer.py` |
| 6 | Portfolio construction — correlation clusters (ρ ≥ 0.65), 1/√N size adjustment | `portfolio_builder.py` |
| 7 | ML signal layer — XGBoost 20-day directional classifier, 55% pass threshold | `ml_signal.py` |
| 8 | Paper trading — persistent JSON trade log, mark-to-market, -5% stop-loss | `paper_trader.py` |
| 9 | Walk-forward validation — rolling 5yr train / 1yr test across 10 assets | `Goofy Phase 9 — Walk-Forward Validation.ipynb` |

**Current status:** 16 paper trades open as of May 2026, closing mid-June 2026.

---

## Project Structure

```
── Strategy notebooks ──────────────────────────────────────────────────────
├── Goofy MA for 6 assets.ipynb             Strategy 1: MA Crossover
├── Goofy8 RSI for 6 assets.ipynb           Strategy 2: RSI
├── Goofy BB for 6 assets.ipynb             Strategy 3: Bollinger Bands
├── Goofy MACD for 6 assets.ipynb           Strategy 4: MACD
├── Goofy Mean Reversion for 6 assets.ipynb Strategy 5: Mean Reversion

── Phase notebooks ─────────────────────────────────────────────────────────
├── Goofy Screener Phase 3 — US ASX JPX.ipynb
├── Goofy Phase 4 — Regime Detection.ipynb
├── Goofy Phase 4b — Empirical Gate Search.ipynb
├── Goofy Phase 5 — Position Sizing.ipynb
├── Goofy Phase 6 — Portfolio Construction.ipynb
├── Goofy Phase 7 — ML Signal.ipynb
├── Goofy Phase 8 — Paper Trading.ipynb
├── Goofy Phase 9 — Walk-Forward Validation.ipynb  ← Phase 9 (new)

── Core modules ────────────────────────────────────────────────────────────
├── goofy_screener_phase8.py   Main weekly run script (run this)
├── ml_signal.py               XGBoost feature engineering + model
├── portfolio_builder.py       Correlation matrix + cluster sizing
├── position_sizer.py          Kelly Criterion + volatility scaling
├── regime_detector.py         Regime gate (VIX + SMA)
├── paper_trader.py            Persistent paper trade log + stop-loss

── Live data ───────────────────────────────────────────────────────────────
├── paper_trades/
│   └── trades_log.json        Live paper trade log (16 open positions)
```

---

## Methodology

All strategies share the same validation framework:

| | Detail |
|---|---|
| **Train period** | Jan 2016 → Dec 2020 (in-sample) |
| **Test period** | Jan 2021 → present (out-of-sample) |
| **Parameter selection** | Grid search on training data only — locked before testing |
| **Signal execution** | `.shift(1)` on all signals — zero lookahead bias |
| **Sharpe ratio** | Annualised return ÷ annualised volatility |
| **Max drawdown** | Peak-to-trough on cumulative equity curve |
| **Benchmark** | Buy & Hold (passive holding of the same asset) |

Parameters are chosen on historical data only, then frozen and applied to future data the model never saw.

---

## The 5 Strategies

### 1 — Moving Average Crossover
Goes long when the fast MA crosses above the slow MA; exits on the reverse. Pure trend-following.  
**Best fit:** SPY, broad indices, macro ETFs  
**Worst fit:** Mean-reverting stocks (generates whipsaws)

### 2 — RSI (Relative Strength Index)
Buys on oversold dips, sells on overbought spikes. Captures momentum extremes.  
**Best fit:** CBA.AX, NAB.AX, stable dividend stocks  
**Worst fit:** NVDA-style trending assets (kept triggering premature sells during the AI bull run)

### 3 — Bollinger Bands
Buys when price breaks below the lower band (2σ); sells at the upper band. Volatility-adjusted mean reversion.  
**Best fit:** Sony (6758.T) — the only strategy-asset pair to beat Buy & Hold out-of-sample in the entire project  
**Worst fit:** NVDA (negative Sharpe OOS — parabolic trends never mean-revert to a 20-day average)

### 4 — MACD
Goes long when MACD crosses above its signal line. Hybrid momentum + trend.  
**Best fit:** NVDA, trending US growth stocks, Japanese financials  
**Standout:** NVDA is the only asset where OOS Sharpe *exceeded* in-sample (0.94 → 1.03)

### 5 — Mean Reversion (Z-Score)
Goes long when price drops N standard deviations below its rolling mean; exits at mean.  
**Best fit:** Sideways / range-bound markets  
**Key limitation:** Structurally underperforms in bull markets — 2021–2026 was the wrong regime for this strategy

---

## Phase 9 Walk-Forward Findings

Walk-forward validation tests whether the XGBoost edge is consistent across time, not just lucky in the 2021–2026 OOS window. 100 rolling windows (5yr train / 1yr test) across 10 representative assets.

| Metric | ML PASS signals | Baseline (no gate) | ML lift |
|---|---|---|---|
| Avg val AUC | 0.533 | 0.500 (random) | +0.033 |
| Win rate | 62.3% | 61.1% | **+1.2%** |
| Avg 20-day return | +1.81% | +1.63% | **+0.18%** |
| Windows where WR > 50% | **80%** | — | — |

**Verdict: Weak but consistent edge.** The ML gate adds a small but real improvement in 80% of time windows. The model breaks in sharp bear regimes (2022 rate shock) — the -5% stop-loss in Phase 8 directly addresses this.

**Strongest assets (ML adds most value):** XOM (AUC 0.576), MSFT (0.561), JPM (0.551), 7203.T (0.554)  
**Weakest (ML adds least):** CBA.AX (AUC 0.493), WBC.AX (0.495) — ASX bank stocks follow macro drivers more than technical patterns

---

## Key Findings

**1. Strategy-asset fit is everything.**  
Sony beat Buy & Hold with Bollinger Bands (Sharpe 0.87) but failed with MACD (Sharpe 0.31). Same asset, wrong strategy.

**2. Out-of-sample validation is non-negotiable.**  
Sony's Mean Reversion in-sample Sharpe was 1.34 — the highest single result in the whole project. Out-of-sample it fell to 0.41. Without the train/test split that looks like the best strategy in the study. It isn't.

**3. Regime determines performance.**  
Mean Reversion underperformed across the board because 2021–2026 was trending. The Phase 4 regime gate reduces damage in wrong-regime periods.

**4. Japanese markets showed the strongest signals.**  
JPX financials (8725.T, 8411.T, 8750.T, 8306.T) dominated the top Sharpe rankings. Japanese bank stocks have cleaner oscillation patterns that suit RSI and MACD well.

**5. Walk-forward shows the ML edge is real but fragile.**  
AUC averaged 0.533 across 100 windows — consistently above random. But the lift over baseline is only +1.2% win rate. Most of the 62% win rate is beta (bull market). The true alpha is small and regime-sensitive.

---

## Asset Universe

| Market | Count | Examples |
|--------|-------|---------|
| 🇺🇸 US | ~40 | NVDA, TSLA, AAPL, JPM, XOM, GLD, SPY |
| 🇦🇺 ASX | ~37 | CBA.AX, BHP.AX, CSL.AX, WTC.AX, STW.AX |
| 🇯🇵 JPX | ~40 | 7203.T, 6758.T, 8306.T, 9984.T, 8725.T |

---

## How to Run

### Requirements
```bash
pip install yfinance pandas numpy openpyxl xgboost scikit-learn
```

### Run the full Phase 8 screener (weekly)
```bash
python3 goofy_screener_phase8.py --market ALL
```

Outputs a colour-coded multi-tab Excel report to `screener_output/`.  
Updates the paper trade log at `paper_trades/trades_log.json`.

### Run walk-forward validation (Phase 9)
Open `Goofy Phase 9 — Walk-Forward Validation.ipynb` and run all cells.  
Takes ~5–10 minutes. Saves charts to `screener_output/`.

### Individual strategy notebooks
Open any `.ipynb` file in Jupyter. Each notebook is self-contained.

---

## Honest Limitations

- **No transaction costs.** Brokerage and slippage would reduce returns, especially for high-frequency strategies.
- **Sharpe without risk-free rate.** Subtracting cash rates (~4–5%) would reduce headline Sharpe by roughly 0.3–0.5.
- **Multiple comparisons.** Selecting the best of 5 strategies introduces selection bias even with a proper train/test split.
- **Long-only.** All strategies are long or flat. No short selling.
- **ML edge is small (+1.2% win rate lift).** Most of the 62% win rate is market beta. The model adds real but modest value.
- **Regime sensitivity.** The system underperforms in sharp bear markets (2022). The -5% stop-loss partially mitigates this.

---

## Disclaimer

This project is for educational and research purposes only. All backtested results are historical simulations and do not guarantee future performance. Nothing in this repository constitutes financial advice.

---

![Phase 4 Excel Output](phase4_sample_output.png)

*Each weekly run produces a colour-coded multi-tab Excel report ranking ~120 stocks across US/ASX/JPX with regime context, ML signals, and paper trade P&L.*

*Built by Hiroki Kunu — International Finance, University of Queensland*  
*GitHub: [GoofyisDAWG](https://github.com/GoofyisDAWG) | LinkedIn: [Hiroki Kunu](https://www.linkedin.com/in/hiroki-kunu-ba4218401)*
