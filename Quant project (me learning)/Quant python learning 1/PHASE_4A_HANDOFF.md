# Phase 4a Handoff — Regime Detection + Signal Gating

**Session date:** 2026-04-21
**Status:** Phase 4a partially complete — detector built and validated, but a critical empirical finding changed the plan. Phase 4a is NOT a clean "done" — it exposed a problem that requires a follow-on empirical study before Phase 3 screener can be updated.

---

## What Phase 4a was about

Every trading strategy has a market regime it loves and one it hates. Mean reversion dies in bull runs; MA crossover gets chopped up in sideways markets (proven in Phases 1-3). Phase 4a was supposed to fix this by:
1. Detecting the current regime for each asset every day
2. Gating existing strategies — only run them in regimes where they have an edge

---

## What was built

**Two files, both in `Quant python learning 1/`:**

1. **`regime_detector.py`** — reusable module with:
   - `detect_trend_regime(close)` → labels each day Bull / Sideways / Bear based on 200-day MA slope (thresholds ±0.05% per day over a 20-day slope window)
   - `detect_volatility_regime(high, low, close)` → labels each day Low / Normal / High based on 14-day ATR's rolling percentile over a 252-day window (33/67 cuts)
   - `label_regimes(df)` → convenience wrapper returning DataFrame with Trend, Vol, Regime columns
   - `STRATEGY_GATES` dict + `is_strategy_allowed()` → **currently broken, see findings below**

2. **`Goofy Phase 4 — Regime Detection.ipynb`** — teaching notebook with:
   - Cell 1: setup, downloads 6 assets from yfinance (NVDA, SPY, CBA.AX, BHP.AX, 7203.T, 6758.T, 2016-2026)
   - Cell 2: applies `label_regimes` to all 6 assets
   - Cell 3: per-asset regime composition breakdown + stacked bar chart
   - Cell 4: 2×3 grid of price charts with regime shading (green=Bull, yellow=Sideways, red=Bear)
   - Cell 5: `backtest_ma()` function + NVDA ungated-vs-gated-vs-B&H comparison
   - Cell 6: equity curves plot for NVDA
   - Cell 7: markdown space for observations
   - Added cells 18-20: extra backtests on CBA.AX and 7203.T with different gate settings

---

## Key findings from actual runs

### Regime breakdown (validated against eyeball intuition, looks correct):

| Asset | Bull | Sideways | Bear |
|---|---|---|---|
| NVDA | 80% | 3% | 17% |
| SPY | 65% | 30% | 5% |
| CBA.AX | 49% | 44% | 7% |
| BHP.AX | 59% | 37% | 4% |
| 7203.T | 49% | 41% | 9% |
| 6758.T | 68% | 25% | 6% |

NVDA's 80% Bull matches its character as a decade-defining momentum stock. CBA.AX at near 50/50 Bull-Sideways confirms why mean reversion worked so well on it in Phase 1-3. Detector is calibrated correctly.

### MA(20,50) gated-vs-ungated backtests — THE CORE FINDING:

| Asset | Gate | Return | Sharpe | MaxDD | Exposure |
|---|---|---|---|---|---|
| NVDA | Ungated | 1334% | 0.94 | -63.6% | 65.7% |
| NVDA | **Bull** | **1452%** | **1.02** | **-44.8%** | 56.7% |
| NVDA | Buy & Hold | 9455% | 1.23 | -66.3% | 100% |
| CBA.AX | Ungated | 9.2% | 0.14 | -34.4% | 62.0% |
| CBA.AX | Bull | **-26.0%** | **-0.19** | -37.7% | 37.0% |
| CBA.AX | **Sideways** | **13.4%** | **0.20** | **-11.9%** | 22.2% |
| 7203.T | Ungated | 95.9% | 0.47 | -41.0% | 62.1% |
| 7203.T | **Bull** | 72.4% | **0.46** | **-22.0%** | 34.4% |
| 7203.T | Sideways | 7.2% | 0.12 | -36.6% | 22.6% |

### The critical empirical finding

**The universal `STRATEGY_GATES = {"MA": {"Bull"}}` rule I originally wrote is WRONG.**

- NVDA: Bull gate wins every metric. My theory was right here.
- 7203.T: Bull gate gives nearly identical Sharpe (0.47 → 0.46) with drawdown nearly halved (-41% → -22%). My theory was right here too.
- **CBA.AX: Bull gate is CATASTROPHIC (+9% → -26%), but Sideways gate WINS on every metric, especially drawdown (-34% → -12%).** My theory was 180° wrong for this asset.

**CBA.AX and 7203.T have nearly identical regime distributions (both ~49% Bull / ~40% Sideways / ~7% Bear), yet they respond to the same gate in OPPOSITE directions.** You cannot predict optimal gate from regime distribution alone.

### The insight (most valuable takeaway of Phase 4a):

> **Optimal gate is per-(asset, strategy) pair, not per-strategy.**
> Theory-based universal gating is insufficient.
> Gates must be built empirically by measuring backtest performance per (asset, strategy, regime) triple.

Why CBA.AX is different (hypothesis, not tested): dividend-heavy Australian bank, "Bull" periods may be slow grinds with whipsaws, "Sideways" regime contains the sharper short-duration breakouts that MA(20,50) catches cleanly. Pure speculation until tested on more assets.

---

## What is NOT done

1. **No empirical gate search across the full universe.** Only NVDA, CBA.AX, and 7203.T tested, only on MA(20,50). Have not tested RSI, BB, MACD, Mean Reversion × regime × asset. That's a 6 assets × 5 strategies × 3 regimes = 90-cell grid that needs running.

2. **`STRATEGY_GATES` dict in `regime_detector.py` is still the old theory-based version.** Needs to be rewritten as a nested dict keyed by asset: `STRATEGY_GATES = {"NVDA": {"MA": "Bull", ...}, "CBA.AX": {"MA": "Sideways", ...}, ...}` — with values populated from empirical results, not theory.

3. **Phase 3 screener (`goofy_screener_phase3.py`) not yet updated.** Original plan was to add a "Current Regime" column to the Excel output. DEFERRED until empirical gate search complete, because a regime column without correct gating is just noise.

4. **Vol regime is computed but not used in gating logic yet.** Only trend regime is being used. Vol regime might matter more than trend for some strategies (e.g. volatility scaling in Phase 5).

5. **Phase 4b (Hidden Markov Models)** — still on the roadmap as a later upgrade path. Not attempted yet. Rule-based detection should be well understood and working before introducing statistical machinery.

---

## Recommended next steps for the next session

**Priority 1: Build the empirical gate search (should be a single notebook session):**

Create a new notebook `Goofy Phase 4b — Empirical Gate Search.ipynb` that:
- Loops over all 6 assets × all 5 strategies (MA, MACD, RSI, BB, Mean Reversion) × all 4 gate options (None, Bull, Sideways, Bear)
- Computes Return, Sharpe, MaxDD, Exposure for each of the ~120 combinations
- Outputs a big results table + a heatmap showing which gate is optimal per (asset, strategy)
- Saves the winning gate per pair to a JSON or dict

**Priority 2:** Rewrite `STRATEGY_GATES` in `regime_detector.py` as asset-specific nested dict using the empirical results from Priority 1.

**Priority 3:** Now update `goofy_screener_phase3.py` to add "Current Regime" column AND apply the correct asset-specific gate when selecting the best strategy per asset.

**Later (Phase 5 onwards — do NOT do yet):**
- Position sizing (Kelly / vol scaling)
- Portfolio construction with correlation analysis
- ML feature engineering with XGBoost
- Paper trading framework

---

## Technical / environment notes

- **Running locally now** in Anaconda Desktop (not Anaconda Cloud). Fresh install today. Jupyter launched via Anaconda Navigator → Launch Jupyter. Python env: `base` (conda env:base, Python 3.13).
- **Local project folder:** `/Users/hiro/quant-research/Claude project (me learning)/Quant python learning 1/`
- yfinance, pandas, numpy, matplotlib all working locally
- A previous attempt to run on Anaconda Cloud Notebooks failed because `regime_detector.py` couldn't be uploaded alongside the notebook. Local is the right setup.

---

## Parameter choices (current defaults — starter values, will need tuning later)

Inside `regime_detector.py`:
- `ma_window = 200` — industry standard, safe
- `slope_window = 20` — 1 trading month, reasonable
- `bull_threshold = 0.0005` / `bear_threshold = -0.0005` — ±0.05% per day, ARBITRARY and may need tuning per asset
- `atr_window = 14` — Wilder's default, safe
- `percentile_window = 252` — 1 trading year, reasonable
- `low_cut = 0.33` / `high_cut = 0.67` — equal thirds, ARBITRARY

Known weaknesses: hard thresholds cause regime "flicker" (no hysteresis), thresholds are identical across assets (should probably be per-asset), binary labels lose confidence information (HMM would fix this in Phase 4b).

---

## One-line summary for next session's context

*"We built a rule-based regime detector, validated it on 6 assets, and discovered that my original theory-based `STRATEGY_GATES` dict (MA→Bull, RSI→Sideways, etc.) is wrong — optimal gates are asset-specific and must be learned empirically. Next step: run a full grid search over (asset × strategy × regime) and build asset-specific gates from the data."*
