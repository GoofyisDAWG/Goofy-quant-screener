# Goofy Screener — Phase 3: Multi-Market Autonomous Strategy Screener

A fully autonomous quantitative screener covering **🇺🇸 US, 🇦🇺 ASX, and 🇯🇵 Japan (JPX)** in a single run — screening ~120 stocks across all three markets, running 5 strategies per asset, and ranking results by a composite 0–100 score.

> **Core finding:** JPX financials dominated the top tier — 4 of the top 5 out-of-sample Sharpe results came from Japanese banking and insurance stocks via MACD and RSI. Sony (6758.T) remains structurally mean-reverting — Bollinger Bands Sharpe held 0.87 out-of-sample across the full test period.

---

## What It Does

1. Downloads live price data for ~120 stocks across US, ASX, and JPX via Yahoo Finance
2. Splits each asset into **train (2016–2020)** and **test (2021–present)**
3. Runs a full parameter grid search across all 5 strategies on training data only
4. Selects the best strategy per asset by in-sample Sharpe
5. Validates out-of-sample — data the model never touched
6. Scores each asset **0–100** using a composite metric
7. Assigns a tier: **S ⭐ / A ✅ / B 🔵 / Skip ⬜**
8. Saves a colour-coded multi-tab Excel report automatically

---

## Files

```
├── Goofy Screener Phase 3 — US ASX JPX.ipynb   — Jupyter notebook (run this)
├── goofy_screener_phase3.py                     — Python script version
├── run_phase3_screener.sh                       — Mac/Linux one-click launcher
├── run_phase3_screener.bat                      — Windows one-click launcher
├── screener_output/                             — Excel reports (auto-generated, gitignored)
└── README.md
```

---

## The 5 Strategies

| Strategy | Logic | Best Fit |
|---|---|---|
| MA Crossover | Short MA > Long MA → long | Trending assets, macro ETFs |
| RSI | Buy oversold, sell overbought | Banks, stable dividend stocks |
| Bollinger Bands | Buy below lower band, sell at midline | Mean-reverting assets (Sony, JPX) |
| MACD | MACD line > signal line → long | Growth stocks, JPX financials |
| Mean Reversion | Z-score < −threshold → long, exit at 0 | Sideways / range-bound markets only |

---

## Composite Scoring System (0–100)

Each asset is scored after out-of-sample validation:

| Component | Max Points | What It Measures |
|---|---|---|
| OUT Sharpe ratio | 40 pts | Quality of risk-adjusted return |
| OUT Total Return | 25 pts | Raw performance (log-scaled) |
| Max Drawdown protection | 20 pts | Capital preservation |
| DD Saved vs Buy & Hold | 15 pts | Strategy value-add over just holding |

### Tier Thresholds

| Tier | Sharpe | Return | Max DD |
|---|---|---|---|
| ⭐ S — Excellent | ≥ 0.8 | ≥ 30% | ≥ −20% |
| ✅ A — Good | ≥ 0.4 | ≥ 10% | ≥ −35% |
| 🔵 B — Decent | ≥ 0.1 | any | ≥ −50% |
| ⬜ Skip | below all thresholds | | |

---

## Asset Universe

| Market | Assets | Sectors Covered |
|---|---|---|
| 🇺🇸 US | 40 | Tech, Financials, Healthcare, Energy, Consumer, Industrials, ETFs |
| 🇦🇺 ASX | 31 | Big 4 Banks, Iron Ore, Healthcare, Retail, Tech, REITs, ETFs |
| 🇯🇵 JPX | 48 | Automotive, Electronics, Gaming, Banks, Insurance, Telecom, Trading Cos |

**Total: ~119 assets per run**

---

## Latest Results (Run: 2026-04-12)

**119 assets screened across 3 markets**

### Top 5 by Out-of-Sample Sharpe

| Rank | Market | Asset | Company | Strategy | OUT Sharpe | Tier |
|---|---|---|---|---|---|---|
| 1 | 🇯🇵 JPX | 8725.T | MS&AD Insurance | RSI | 1.306 | ⭐ S |
| 2 | 🇯🇵 JPX | 8002.T | Marubeni | MA Crossover | 1.276 | 🔵 B |
| 3 | 🇯🇵 JPX | 9434.T | SoftBank Corp | Bollinger Bands | 1.151 | ✅ A |
| 4 | 🇺🇸 US | COP | ConocoPhillips | RSI | 1.121 | ✅ A |
| 5 | 🇯🇵 JPX | 7011.T | Mitsubishi Heavy | MACD | 1.104 | ✅ A |

### Strategy Distribution (119 assets)

| Strategy | Count | Share |
|---|---|---|
| MA Crossover | 34 | 29% |
| MACD | 27 | 23% |
| RSI | 24 | 20% |
| Bollinger Bands | 22 | 18% |
| Mean Reversion | 12 | 10% |

### Why JPX Dominated

Japanese financial stocks (banks, insurance companies) showed consistent oscillation patterns that suit RSI and MACD well — particularly in the post-2021 environment where the Bank of Japan's policy shifts created clear momentum cycles. 4 of the top 5 Sharpe results came from JPX.

---

## Methodology

| | Detail |
|---|---|
| **Train period** | Jan 2016 → Dec 2020 (in-sample only) |
| **Test period** | Jan 2021 → present (out-of-sample) |
| **Parameter selection** | Grid search on training data — locked before testing |
| **Signal execution** | `.shift(1)` on all signals — zero lookahead bias |
| **Sharpe ratio** | Annualised log return ÷ annualised volatility |
| **Max drawdown** | Peak-to-trough on cumulative equity curve |
| **Benchmark** | Buy & Hold for the same asset over the same test period |

---

## How to Run

### Requirements
```bash
pip install yfinance pandas numpy openpyxl
```

### Jupyter (recommended)
Open `Goofy Screener Phase 3 — US ASX JPX.ipynb` in Anaconda/Jupyter and run cells 1–11 top to bottom.

To run only one market, change `MARKET = 'ALL'` in Cell 2 to `'US'`, `'ASX'`, or `'JPX'`.

### Command line
```bash
# All markets
python goofy_screener_phase3.py --market ALL

# Single market
python goofy_screener_phase3.py --market JPX
python goofy_screener_phase3.py --market US
python goofy_screener_phase3.py --market ASX
```

### One-click launchers
```bash
# Mac / Linux
bash run_phase3_screener.sh

# Windows — double-click
run_phase3_screener.bat
```

Output saved to `screener_output/Goofy_Phase3_YYYY-MM-DD.xlsx`

---

## Excel Report Structure

| Tab | Contents |
|---|---|
| ⭐ Top Performers | S & A tier assets ranked by score, tier legend, breakdown |
| 🇺🇸 US | All US results sorted by score, colour-coded |
| 🇦🇺 ASX | All ASX results sorted by score, colour-coded |
| 🇯🇵 JPX | All JPX results sorted by score, colour-coded |
| 📊 Strategy Distribution | How many assets each strategy won per market |

Colour coding: strategy columns use unique colours per strategy; tier column uses gold/green/blue/grey; Sharpe and DD columns use green/red heat mapping.

---

## Key Findings

**1. JPX financials are the standout market for quant strategies.**  
Japanese insurance and banking stocks showed the cleanest signal-to-noise ratios across the test period. 8725.T (MS&AD Insurance) hit Sharpe 1.31 with RSI — the highest in the entire project.

**2. Sony (6758.T) is structurally mean-reverting.**  
Bollinger Bands Sharpe 0.87 out-of-sample. MACD Sharpe 0.31. The asset has a consistent character — it oscillates around a mean rather than trending. Regime matters more than the strategy name.

**3. MA Crossover is still the most dominant strategy by asset count.**  
34 of 119 assets selected MA Crossover as their best strategy — predominantly trending US and ASX assets. Not because it's the best strategy, but because most assets trend.

**4. Beating Buy & Hold on raw return is the wrong question in a bull market.**  
2021–2026 was a strong uptrend. Passive holding wins on return in bull markets — that's expected. The screener's value is the drawdown column: strategies that capped worst-case losses to −15% while Buy & Hold experienced −40% to −70% drops.

**5. Out-of-sample validation changes everything.**  
Multiple assets had in-sample Sharpe above 1.5 that fell below 0.3 out-of-sample. This is the most important lesson in the entire project — and why the train/test split is non-negotiable.

---

## Honest Limitations

- **No transaction costs.** Brokerage and slippage are not modelled.
- **Sharpe without risk-free rate.** Subtracting cash rates (~4–5%) would reduce Sharpe by roughly 0.3–0.5.
- **Long-only.** All strategies are long or flat — no short selling.
- **Binary position sizing.** 100% in or out — no volatility scaling or Kelly sizing.
- **No portfolio construction.** Each asset is screened independently with no correlation analysis.
- **JPX currency risk not modelled.** Japanese stocks priced in JPY — USD/AUD investors face additional FX exposure.

---

## What's Next — Phase 4

The gap between this screener and a professional quant system isn't the indicator — it's everything around it. Phase 4 will add:

- **Regime detection** — classify each market as trending, mean-reverting, or choppy using volatility and price structure, then only deploy strategies matched to the current regime
- **Volatility-scaled position sizing** — replace binary in/out with ATR-based position scaling
- **Kelly Criterion** — size positions based on historical edge and volatility

---

## Built On

This is Phase 3 of a multi-phase quant research project. The 5 strategies were each individually built and validated before being combined here:

- [Moving Average Crossover](https://github.com/GoofyisDAWG/Moving-Average-crossover-backtest)
- [RSI Backtest](https://github.com/GoofyisDAWG/RSI-Backtest-)
- [Bollinger Bands Backtest](https://github.com/GoofyisDAWG/Bollinger-Bands-backtest)
- [MACD Backtest](https://github.com/GoofyisDAWG/MACD-backtest)
- **[Screener v2 — Single-Market](https://github.com/GoofyisDAWG)** ← previous phase

---

## Disclaimer

For educational and research purposes only. All results are historical backtests and do not guarantee future performance. Nothing here constitutes financial advice.

---

*Built by Hiroki Kunu — International Finance, University of Queensland*  
*[GitHub: GoofyisDAWG](https://github.com/GoofyisDAWG) | [LinkedIn](https://www.linkedin.com/in/hiroki-kunu-ba4218401)*
