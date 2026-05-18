# Goofy Screener — Phase 4: Regime-Aware Strategy Gating

**Built by:** Hiroki (GoofyisDAWG) — UQ Finance student, Brisbane  
**Phase 4 added:** April 2026  
**Builds on:** [Phase 3 multi-market screener](#phase-3-recap)

---

## What Phase 4 adds

Phase 3 picked the best-performing strategy per asset. Phase 4 asks: *should I actually trade that strategy today given current market conditions?*

Three new columns in the Excel output:

| Column | What it means |
|---|---|
| **Current Trend** | Bull / Sideways / Bear (rule-based, 200-day MA slope) |
| **Current Vol** | Low / Normal / High (14-day ATR rolling percentile) |
| **Today's Verdict** | TRADE or STAND DOWN |

---

## Phase 4a — Regime Detector (`regime_detector.py`)

Built a rule-based detector that labels every trading day for any asset:

- **Trend:** 200-day MA slope over a 20-day window. Bull if slope > +0.05%/day, Bear if < −0.05%/day, Sideways otherwise.
- **Volatility:** 14-day ATR ranked within a 252-day rolling window. Low/Normal/High at 33rd/67th percentile.

### What Phase 4a found (and got wrong)

Original theory: gate MA Crossover to Bull regimes, gate RSI/BB to Sideways. Tested on NVDA, CBA.AX, 7203.T.

**NVDA:** Bull gate improved Sharpe 0.94 → 1.02, cut drawdown from −63% to −45%. Theory seemed right.

**CBA.AX:** Bull gate was catastrophic — returns went from +9% to −26%. Sideways gate instead improved every metric. Theory was 180° wrong.

**Core insight from Phase 4a:**
> Optimal gate is per-(asset, strategy) pair, not per-strategy. Theory alone is insufficient. Gates must be learned from data.

---

## Phase 4b — Empirical Gate Search (`Goofy Phase 4b — Empirical Gate Search.ipynb`)

Ran a full grid: **6 assets × 5 strategies × 4 gate options = 120 backtests**

Gate options tested: None (ungated), Bull, Sideways, Bear

### Winning gates (empirical, after overfitting safeguards)

|  | MA | MACD | RSI | BB | MeanReversion |
|---|---|---|---|---|---|
| **NVDA** | None | None | None | None | None |
| **SPY** | None | None | None | None | None |
| **CBA.AX** | Sideways | Sideways | None | None | None |
| **BHP.AX** | Sideways | None | None | None | None |
| **7203.T** | None | Sideways | None | None | None |
| **6758.T** | None | None | None | None | None |

### Three safeguards against overfitting

1. **Sharpe tie threshold (0.05):** if a gate doesn't beat ungated by at least 0.05 Sharpe, use None
2. **Negative Sharpe guard:** if no gate delivers positive Sharpe, use None
3. **Minimum exposure (15%):** if a regime is too rare (<15% of days), that Sharpe is untrustworthy — reject it

The exposure guard alone caught 20+ false positives (e.g. CBA.AX Bear gate Sharpe 0.59 — looks great, but Bear only occurs 2.6% of days on CBA.AX)

### Key findings

**Ungated wins for US assets (NVDA, SPY):** These assets trend strongly. MA and MACD already work well in all conditions — gating only removes valid trades.

**Sideways gate wins for range-bound ASX/JPX assets:** CBA.AX spends ~44% of time Sideways. MA Crossover gets chopped up in slow grinds — but filtering *to* Sideways finds the sharper short moves the strategy actually catches cleanly.

**RSI, BB, MeanReversion → gating doesn't help anyone.** These are already contrarian by design.

**NVDA and 7203.T:** My Phase 4a theory (Bull gate for MA) was wrong. The data says ungated is better for both.

---

## Files

| File | Purpose |
|---|---|
| `goofy_screener_phase4.py` | Main screener — inherits Phase 3 + adds regime columns + verdict |
| `goofy_screener_phase3.py` | Original Phase 3 screener (preserved — historical truth) |
| `regime_detector.py` | Regime detection module (reusable) |
| `asset_specific_gates.json` | Empirical winning gates from Phase 4b |
| `Goofy Phase 4 — Regime Detection.ipynb` | Phase 4a teaching notebook |
| `Goofy Phase 4b — Empirical Gate Search.ipynb` | Full 120-backtest grid search |
| `PHASE_4A_HANDOFF.md` | Detailed findings and parameter notes |

---

## How to run

```bash
# Full screener (all markets)
python3 goofy_screener_phase4.py --market ALL

# Single market
python3 goofy_screener_phase4.py --market US
python3 goofy_screener_phase4.py --market ASX
python3 goofy_screener_phase4.py --market JPX
```

Output: colour-coded Excel in `screener_output/` with tabs: Top Performers, Today's Trade List, US, ASX, JPX, Strategy Distribution, Active Gates

---

## Phase 3 recap

Phase 3 screener: downloads ~120 stocks across US/ASX/JPX, runs 5 strategies (MA Crossover, RSI, Bollinger Bands, MACD, Mean Reversion) with full parameter grid search on 2016–2021 training data, validates best strategy per asset out-of-sample (2021–present), scores assets 0–100, tiers S/A/B/Skip.

---

## Roadmap

- [x] Phase 1–2: Individual strategy backtests (MA, RSI, BB, MACD, Mean Reversion)
- [x] Phase 3: Multi-market screener (US + ASX + JPX, 120 assets, S/A/B tiering)
- [x] Phase 4a: Rule-based regime detector
- [x] Phase 4b: Empirical gate search (120-backtest grid, asset-specific results)
- [x] Phase 5: Position sizing — Kelly Criterion / volatility scaling
- [ ] Phase 6: Portfolio construction with correlation analysis
- [ ] Phase 7: ML features with XGBoost
- [ ] Phase 8: Paper trading framework
