"""
regime_detector.py
------------------
Phase 4 of Goofy's Quant Learning — Regime Detection + Signal Gating.

Detects TWO independent regimes for any daily OHLC price series:
  1. Trend regime   : Bull / Sideways / Bear   (based on 200-day MA slope)
  2. Vol regime     : Low  / Normal   / High   (based on rolling ATR percentile)

Every trading day gets one label in each dimension. Downstream strategy code
uses these labels to "gate" signals — i.e. only take MA/MACD trades when
the trend regime supports them, only take BB/mean-reversion trades when
the trend regime supports them, and so on.

═══════════════════════════════════════════════════════════════════════════
PHASE 4a → 4b UPGRADE (this file)
─────────────────────────────────
Phase 4a exposed the fact that universal theory-based gates (MA→Bull,
BB→Sideways, etc.) are WRONG for some (asset, strategy) pairs. CBA.AX
example: Bull gate on MA crossover DESTROYS returns (+9% → -26%), but a
Sideways gate WINS every metric. Same gate, opposite direction vs NVDA.

This upgrade adds:
  • DEFAULT_STRATEGY_GATES  — the original theory (kept as fallback)
  • ASSET_SPECIFIC_GATES    — empirical overrides per (asset, strategy)
  • get_allowed_regimes()   — resolves asset-specific first, default second
  • apply_gate_mask()       — zero-out signals outside allowed regimes
  • detect_trend_regime(min_regime_days=...) — optional hysteresis
  • regime_summary()        — auto-detects N assets (1..6+), shows them ALL
  • save/load helpers for the JSON that Phase 4b will produce

Author: Goofy / Hiroki
Date:   2026-04-17 (4a), 2026-04-22 (4b upgrade)
"""

import json
import os
import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════
# 1. TREND REGIME — based on slope of the 200-day moving average
# ═══════════════════════════════════════════════════════════════════════════
def detect_trend_regime(
    close: pd.Series,
    ma_window: int = 200,
    slope_window: int = 20,
    bull_threshold: float = 0.0005,    # +0.05% per day  (≈ +12.5% annualised)
    bear_threshold: float = -0.0005,   # -0.05% per day
    min_regime_days: int = 0,          # hysteresis: ignore regime flips shorter than N days
) -> pd.Series:
    """
    Classify each day as 'Bull', 'Sideways', or 'Bear' using the 200-day
    moving-average slope.

    Intuition
    ---------
    The 200-day MA is a ~10-month smoothed view of price. Its SLOPE tells
    you the direction of that smoothed view. Rising → buyers dominate
    (Bull). Flat → indecision (Sideways). Falling → sellers dominate (Bear).

    Hysteresis (new in 4b)
    ----------------------
    If ``min_regime_days > 0`` we require a new regime to persist at least
    that many days before accepting the switch — this kills single-day
    "flicker" around the thresholds that can otherwise whipsaw a gated
    strategy. Set to 0 to disable (matches Phase 4a behaviour).

    Returns
    -------
    pd.Series of strings ('Bull' | 'Sideways' | 'Bear' | NaN before warmup).
    """
    ma = close.rolling(ma_window).mean()

    # Slope = fractional change of the MA over slope_window days, scaled to %/day.
    slope = ma.pct_change(slope_window) / slope_window

    regime = pd.Series(index=close.index, dtype=object)
    regime[slope > bull_threshold] = "Bull"
    regime[slope < bear_threshold] = "Bear"
    regime[(slope >= bear_threshold) & (slope <= bull_threshold)] = "Sideways"

    if min_regime_days > 0:
        regime = _apply_hysteresis(regime, min_regime_days)
    return regime


def _apply_hysteresis(regime: pd.Series, min_days: int) -> pd.Series:
    """
    Smooth short regime flips: don't accept a switch unless it lasts >= min_days.
    Walks the series forward, holding the previous label until the new label has
    lasted ``min_days`` consecutive days.
    """
    out = regime.copy()
    labels = regime.dropna().tolist()
    if not labels:
        return out
    idxs = regime.dropna().index

    current = labels[0]
    pending = current
    pending_count = 0
    smoothed = []
    for lbl in labels:
        if lbl == current:
            pending = current
            pending_count = 0
        else:
            if lbl == pending:
                pending_count += 1
            else:
                pending = lbl
                pending_count = 1
            if pending_count >= min_days:
                current = pending
                pending_count = 0
        smoothed.append(current)

    out.loc[idxs] = smoothed
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 2. VOLATILITY REGIME — rolling ATR percentile
# ═══════════════════════════════════════════════════════════════════════════
def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                window: int = 14) -> pd.Series:
    """
    Average True Range — Wilder's classic volatility measure.

    True Range = max of
        (high - low),               # today's range
        |high - prev_close|,        # gap up overnight
        |low  - prev_close|.        # gap down overnight

    Then take a simple rolling mean over `window` days (default 14).
    Output is in PRICE UNITS (not %).
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def detect_volatility_regime(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    atr_window: int = 14,
    percentile_window: int = 252,   # ~1 trading year
    low_cut: float = 0.33,
    high_cut: float = 0.67,
) -> pd.Series:
    """
    Classify each day as 'Low', 'Normal', or 'High' vol based on where today's
    ATR sits within the previous year's ATR distribution FOR THIS ASSET.

    Why per-asset percentile?
        Raw ATR isn't comparable across assets — NVDA's "calm" might be
        CBA.AX's "wild." Percentile-ranking in the asset's own history
        yields a label that's meaningful regardless of asset.

    Returns
    -------
    pd.Series of strings ('Low' | 'Normal' | 'High' | NaN before warmup).
    """
    atr = compute_atr(high, low, close, window=atr_window)

    def _pct_rank(window_vals):
        # Position of the LAST value in the sorted window, as fraction [0,1].
        return (window_vals < window_vals[-1]).sum() / (len(window_vals) - 1)

    atr_pct = atr.rolling(percentile_window).apply(_pct_rank, raw=True)

    regime = pd.Series(index=close.index, dtype=object)
    regime[atr_pct < low_cut] = "Low"
    regime[(atr_pct >= low_cut) & (atr_pct <= high_cut)] = "Normal"
    regime[atr_pct > high_cut] = "High"
    return regime


# ═══════════════════════════════════════════════════════════════════════════
# 3. CONVENIENCE — label a full OHLC DataFrame
# ═══════════════════════════════════════════════════════════════════════════
def label_regimes(df: pd.DataFrame, min_regime_days: int = 0) -> pd.DataFrame:
    """
    Given an OHLC DataFrame with columns ['Open','High','Low','Close'],
    return the same DataFrame with three new columns:
        Trend  : Bull | Sideways | Bear
        Vol    : Low  | Normal   | High
        Regime : e.g. 'Bull-Low', 'Sideways-High', etc.

    ``min_regime_days`` applies trend-regime hysteresis (new in 4b).
    """
    out = df.copy()
    out["Trend"] = detect_trend_regime(out["Close"], min_regime_days=min_regime_days)
    out["Vol"] = detect_volatility_regime(out["High"], out["Low"], out["Close"])
    out["Regime"] = out["Trend"].astype(str) + "-" + out["Vol"].astype(str)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 4. STRATEGY GATES — default (theory) + asset-specific (empirical)
# ═══════════════════════════════════════════════════════════════════════════

# ---------------------------------------------------------------------------
# DEFAULT gates — the theory-based starting point. Used as fallback whenever
# an asset doesn't have its own entry in ASSET_SPECIFIC_GATES below.
# ---------------------------------------------------------------------------
DEFAULT_STRATEGY_GATES = {
    "MA":            {"Bull"},         # trend-following: needs trend
    "MACD":          {"Bull"},         # trend-following: needs trend
    "RSI":           {"Sideways"},     # mean-reversion: needs chop
    "BB":            {"Sideways"},     # mean-reversion: needs chop
    "MeanReversion": {"Sideways"},     # mean-reversion: needs chop
}

# ---------------------------------------------------------------------------
# ASSET-SPECIFIC overrides — populated empirically by Phase 4b.
# Format: ASSET_SPECIFIC_GATES[asset][strategy] = set of allowed regimes.
#
# Any (asset, strategy) NOT listed here falls through to DEFAULT_STRATEGY_GATES.
# Seed values below are from the Phase 4a empirical runs (2026-04-21):
# ---------------------------------------------------------------------------
ASSET_SPECIFIC_GATES = {
    # Validated in Phase 4a — kept here so the logic is live even before
    # the full 4b grid search completes.
    "NVDA":   {"MA": {"Bull"}},          # Bull gate wins every metric
    "7203.T": {"MA": {"Bull"}},          # Bull gate halves drawdown at same Sharpe
    "CBA.AX": {"MA": {"Sideways"}},      # Bull gate catastrophic; Sideways wins
}


def get_allowed_regimes(asset: str | None, strategy: str) -> set:
    """
    Resolve the set of allowed trend regimes for (asset, strategy).

    Lookup order:
        1. ASSET_SPECIFIC_GATES[asset][strategy]  (empirical override)
        2. DEFAULT_STRATEGY_GATES[strategy]       (theory fallback)
        3. empty set (strategy unknown)
    """
    if asset is not None:
        asset_overrides = ASSET_SPECIFIC_GATES.get(asset, {})
        if strategy in asset_overrides:
            return asset_overrides[strategy]
    return DEFAULT_STRATEGY_GATES.get(strategy, set())


def is_strategy_allowed(strategy: str, trend_regime, asset: str | None = None) -> bool:
    """
    Return True if ``strategy`` should trade on a day labelled ``trend_regime``.

    Back-compat: the original Phase 4a signature (strategy, trend_regime) still
    works — pass ``asset=...`` to get asset-specific gating.
    """
    if pd.isna(trend_regime):
        return False  # warmup: block everything by default
    return trend_regime in get_allowed_regimes(asset, strategy)


def apply_gate_mask(signal: pd.Series, trend_regime: pd.Series,
                    allowed_regimes: set | None) -> pd.Series:
    """
    Zero-out signals outside of ``allowed_regimes``. If ``allowed_regimes`` is
    None or empty, the signal is returned unchanged (no gating).

    Parameters
    ----------
    signal : pd.Series
        0/1 (or -1/0/1) position series, indexed by date.
    trend_regime : pd.Series
        Aligned 'Bull'/'Sideways'/'Bear'/NaN labels.
    allowed_regimes : set or None
        Regimes in which the signal is permitted to be non-zero.
    """
    if not allowed_regimes:
        return signal
    mask = trend_regime.isin(list(allowed_regimes))
    return signal.where(mask, 0)


# ═══════════════════════════════════════════════════════════════════════════
# 5. AUTO-DETECT N ASSETS & SUMMARISE — "show ALL stocks up to 6" helper
# ═══════════════════════════════════════════════════════════════════════════
def regime_summary(asset_data: dict, max_assets: int = 6,
                   min_regime_days: int = 0) -> pd.DataFrame:
    """
    Given a dict of {ticker: OHLC DataFrame}, label regimes and return a tidy
    summary table with ONE ROW PER ASSET showing its trend-regime composition.

    This is the helper the user asked for: "detect how many stocks there are
    up to 6 and show the outcomes of them." It auto-adapts to whatever you
    give it — 1 asset, 3 assets, 6 assets — and shows every one.

    Parameters
    ----------
    asset_data : dict[str, pd.DataFrame]
        Each value must have columns Open/High/Low/Close.
    max_assets : int
        Hard cap — won't process more than this many (default 6). Protects
        you from accidentally feeding in 500 tickers.
    min_regime_days : int
        Hysteresis passed through to ``detect_trend_regime``.

    Returns
    -------
    pd.DataFrame with columns:
        Asset | Rows | Bull % | Sideways % | Bear % | Current Regime |
        Current Since
    """
    tickers = list(asset_data.keys())
    n = min(len(tickers), max_assets)
    rows = []
    for ticker in tickers[:n]:
        df = asset_data[ticker]
        labelled = label_regimes(df, min_regime_days=min_regime_days)
        trend = labelled["Trend"].dropna()
        if trend.empty:
            rows.append({
                "Asset": ticker, "Rows": len(df),
                "Bull %": np.nan, "Sideways %": np.nan, "Bear %": np.nan,
                "Current Regime": "—", "Current Since": "—",
            })
            continue
        pct = trend.value_counts(normalize=True) * 100
        # Find the date at which the CURRENT regime started (last flip).
        current = trend.iloc[-1]
        flip_mask = trend != trend.shift(1)
        current_since = trend.index[flip_mask][trend[flip_mask] == current][-1]
        rows.append({
            "Asset": ticker,
            "Rows": len(df),
            "Bull %": round(pct.get("Bull", 0), 1),
            "Sideways %": round(pct.get("Sideways", 0), 1),
            "Bear %": round(pct.get("Bear", 0), 1),
            "Current Regime": current,
            "Current Since": current_since.strftime("%Y-%m-%d"),
        })

    if len(tickers) > max_assets:
        print(f"[regime_summary] Warning: {len(tickers)} assets passed, "
              f"only first {max_assets} processed (max_assets cap).")

    return pd.DataFrame(rows).set_index("Asset")


# ═══════════════════════════════════════════════════════════════════════════
# 6. PERSISTENCE HELPERS — load/save ASSET_SPECIFIC_GATES from JSON
# ═══════════════════════════════════════════════════════════════════════════
# Phase 4b produces a JSON file of the form
#     {"NVDA": {"MA": ["Bull"], "RSI": ["Sideways"], ...}, ...}
# These helpers let us round-trip it without manually editing this .py file.

GATES_JSON_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "asset_specific_gates.json",
)


def save_asset_gates(path: str = GATES_JSON_DEFAULT,
                     gates: dict | None = None) -> str:
    """Serialise ASSET_SPECIFIC_GATES (or ``gates`` override) to JSON."""
    g = gates if gates is not None else ASSET_SPECIFIC_GATES
    serialisable = {
        asset: {strat: sorted(list(regs)) for strat, regs in strats.items()}
        for asset, strats in g.items()
    }
    with open(path, "w") as f:
        json.dump(serialisable, f, indent=2)
    return path


def load_asset_gates(path: str = GATES_JSON_DEFAULT,
                     install: bool = True) -> dict:
    """
    Read a gates JSON file. If ``install=True`` also mutates the live
    ASSET_SPECIFIC_GATES dict so subsequent calls use the loaded values.
    """
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        raw = json.load(f)
    loaded = {
        asset: {strat: set(regs) for strat, regs in strats.items()}
        for asset, strats in raw.items()
    }
    if install:
        ASSET_SPECIFIC_GATES.clear()
        ASSET_SPECIFIC_GATES.update(loaded)
    return loaded


# ═══════════════════════════════════════════════════════════════════════════
# 7. SMOKE TEST
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import yfinance as yf

    tickers = ["NVDA", "SPY", "CBA.AX", "BHP.AX", "7203.T", "6758.T"]
    data = {}
    for t in tickers:
        df = yf.download(t, start="2016-01-01", end="2026-04-01",
                         progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        data[t] = df

    print("\n=== Regime summary (ALL assets, auto-detected) ===")
    print(regime_summary(data))

    print("\n=== Gate resolution demo ===")
    for asset in ["NVDA", "CBA.AX", "SPY"]:
        for strat in ["MA", "RSI", "BB"]:
            regs = get_allowed_regimes(asset, strat)
            print(f"  {asset:<8} {strat:<4} → {sorted(regs) if regs else '— (no gate)'}")
