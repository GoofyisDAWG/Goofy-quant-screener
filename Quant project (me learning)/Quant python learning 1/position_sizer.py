"""
position_sizer.py
-----------------
Phase 5 of Goofy's Quant Learning — Position Sizing.

Answers the Phase 4 follow-up question: you know WHICH asset to trade and
WHETHER to trade today — but HOW MUCH should you put in?

Two complementary methods:

  1. Kelly Criterion  (confidence-based)
     Uses your strategy's historical win rate and avg win/loss to compute
     the theoretically optimal fraction of capital to deploy.  We always
     use HALF-Kelly in practice — full Kelly is too aggressive and leads
     to extreme drawdowns even when the math is right.

  2. Volatility Scaling  (risk-based)
     Scales each position so every asset targets the same annualised
     volatility (default 15%).  A calm stock → bigger size; a wild stock →
     smaller size.  This equalises the *risk contribution* across your
     trade list, which is a prerequisite for Phase 6 portfolio construction.

Final recommended size = Half-Kelly × Vol Scalar, capped at 100%
(no leverage for now — Phase 6 will revisit this).

═══════════════════════════════════════════════════════════════════════════
WHAT EACH FUNCTION RETURNS

  compute_trade_stats()   → dict: n_trades, win_rate, avg_win, avg_loss
  half_kelly()            → float: fraction of capital [0, 1]
  vol_scalar()            → float: multiplier to hit target vol
  recommend_size()        → dict: Kelly %, Vol Scalar, Recommended Size %

Author: Goofy / Hiroki
Date:   2026-05-05 (Phase 5)
"""

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════
# 1. TRADE STATISTICS — extract per-trade win/loss data
# ═══════════════════════════════════════════════════════════════════════════

def compute_trade_stats(price: pd.Series, position: pd.Series,
                        min_trades: int = 5) -> dict | None:
    """
    Walk through a price + position series and extract individual trade returns.

    A "trade" starts when position goes 0→1 and ends when it goes 1→0.
    The return is (exit_price / entry_price) - 1.

    Parameters
    ----------
    price    : pd.Series   Close prices, indexed by date.
    position : pd.Series   0/1 signals (already shift(1)-delayed as in the screener).
    min_trades : int       Minimum completed trades needed — returns None if fewer.

    Returns
    -------
    dict with keys:
        n_trades  : int    — number of completed round-trips
        win_rate  : float  — fraction of trades that were profitable
        avg_win   : float  — mean return of winning trades (as decimal, e.g. 0.08)
        avg_loss  : float  — mean abs return of losing trades (positive, e.g. 0.04)
    or None if not enough data.
    """
    pos = position.reindex(price.index).fillna(0)
    df  = pd.DataFrame({'price': price, 'pos': pos}).dropna()

    trades = []
    in_trade   = False
    entry_price = None

    for _, row in df.iterrows():
        is_in = row['pos'] >= 0.5
        if not in_trade and is_in:
            in_trade    = True
            entry_price = row['price']
        elif in_trade and not is_in:
            in_trade = False
            if entry_price and entry_price > 0:
                trades.append((row['price'] - entry_price) / entry_price)

    if len(trades) < min_trades:
        return None

    wins   = [t for t in trades if t > 0]
    losses = [abs(t) for t in trades if t <= 0]

    if not wins or not losses:
        return None

    return {
        'n_trades': len(trades),
        'win_rate': round(len(wins) / len(trades), 4),
        'avg_win':  round(float(np.mean(wins)), 4),
        'avg_loss': round(float(np.mean(losses)), 4),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. KELLY CRITERION
# ═══════════════════════════════════════════════════════════════════════════

def half_kelly(win_rate: float, avg_win: float, avg_loss: float,
               fraction: float = 0.5) -> float:
    """
    Compute the Kelly-optimal fraction of capital and return HALF of it.

    Formula
    -------
    Full Kelly:  f* = p - q/b
    where:
        p = win probability
        q = 1 - p  (loss probability)
        b = avg_win / avg_loss  (win-to-loss ratio)

    Intuition
    ---------
    Kelly tells you the fraction that, if bet repeatedly, maximises the
    long-run geometric growth rate of your capital.  Full Kelly is
    mathematically optimal but brutally volatile — a single bad streak
    can wipe out a huge slice of equity.  Half-Kelly sacrifices ~25% of
    long-run growth but cuts drawdowns by ~half.  Most practitioners use
    half-Kelly or less.

    Returns 0 if the edge is negative (strategy loses money on average).
    Capped at 1.0 (no leverage from Kelly alone).

    Parameters
    ----------
    win_rate : float   e.g. 0.55 for 55% win rate
    avg_win  : float   e.g. 0.08 for average 8% gain per winning trade
    avg_loss : float   e.g. 0.04 for average 4% loss per losing trade (positive)
    fraction : float   Kelly multiplier — 0.5 = half-Kelly (default)

    Returns
    -------
    float in [0, 1] — fraction of capital to deploy.
    """
    if avg_loss <= 0 or avg_win <= 0 or not (0 < win_rate < 1):
        return 0.0

    b = avg_win / avg_loss           # win/loss ratio
    p = win_rate
    q = 1.0 - p
    f_full = p - q / b              # full Kelly

    return round(max(0.0, min(1.0, f_full * fraction)), 4)


# ═══════════════════════════════════════════════════════════════════════════
# 3. VOLATILITY SCALING
# ═══════════════════════════════════════════════════════════════════════════

def vol_scalar(returns: pd.Series, target_vol: float = 0.15,
               lookback: int = 21, max_scale: float = 2.0) -> float:
    """
    Return a multiplier that scales a position to target a given annualised vol.

    Intuition
    ---------
    Without vol scaling, a calm stock (5% annual vol) and a wild stock (40%
    annual vol) sitting side-by-side in a portfolio have wildly different
    risk contributions.  The wild stock dominates every drawdown even if
    you hold the same nominal position.

    Vol scaling fixes this: position_size = target_vol / current_vol.
    The result is every position contributes approximately the same
    annualised risk, making your portfolio much more balanced.

    Parameters
    ----------
    returns    : pd.Series  Daily log or simple returns (use recent test period).
    target_vol : float      Annualised volatility target (default 15%).
    lookback   : int        Days of recent data used for realized vol (default 21 ≈ 1 month).
    max_scale  : float      Cap on the multiplier — prevents tiny-vol assets from
                            getting absurdly large positions (default 2.0 = 200%).

    Returns
    -------
    float — the multiplier.  1.0 = position unchanged.
             > 1 = scale up (asset is calm).
             < 1 = scale down (asset is wild).
    """
    recent = returns.dropna().tail(lookback)
    if len(recent) < 5:
        return 1.0
    realized = float(recent.std()) * (252 ** 0.5)
    if realized <= 0:
        return 1.0
    return round(min(max_scale, target_vol / realized), 4)


# ═══════════════════════════════════════════════════════════════════════════
# 4. COMBINED RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════════

def recommend_size(trade_stats: dict | None,
                   recent_returns: pd.Series,
                   target_vol: float = 0.15,
                   kelly_fraction: float = 0.5,
                   max_size: float = 1.0) -> dict:
    """
    Combine Half-Kelly and volatility scaling into a single position-size
    recommendation.

    Final size = half_kelly(...) × vol_scalar(...)  capped at max_size.

    If trade_stats is None (not enough trades), all outputs are None —
    the screener will show '—' for this asset.

    Parameters
    ----------
    trade_stats    : dict or None  — output of compute_trade_stats()
    recent_returns : pd.Series     — recent daily returns for vol scaling
    target_vol     : float         — annualised vol target (default 15%)
    kelly_fraction : float         — Kelly multiplier (default 0.5 = half)
    max_size       : float         — hard cap on recommended size (default 1.0)

    Returns
    -------
    dict with keys:
        Kelly %           : float or None  — half-Kelly fraction as a percentage
        Vol Scalar        : float or None  — vol scaling multiplier
        Recommended Size %: float or None  — final recommendation as percentage
    """
    if trade_stats is None:
        return {
            'Kelly %':            None,
            'Vol Scalar':         None,
            'Recommended Size %': None,
        }

    kf = half_kelly(
        trade_stats['win_rate'],
        trade_stats['avg_win'],
        trade_stats['avg_loss'],
        fraction=kelly_fraction,
    )
    vs   = vol_scalar(recent_returns, target_vol=target_vol)
    size = round(min(kf * vs, max_size), 4)

    return {
        'Kelly %':            round(kf * 100, 1),
        'Vol Scalar':         vs,
        'Recommended Size %': round(size * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. SMOKE TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import yfinance as yf

    print("=== position_sizer.py — smoke test ===\n")

    # Synthetic example — teaching the math first
    print("── Half-Kelly formula examples ──")
    cases = [
        (0.55, 0.10, 0.05, "55% WR, 2:1 win/loss"),
        (0.60, 0.08, 0.06, "60% WR, 1.33:1 win/loss"),
        (0.45, 0.15, 0.05, "45% WR, 3:1 win/loss"),
        (0.40, 0.05, 0.08, "40% WR, 0.625:1 (negative edge)"),
    ]
    for wr, aw, al, label in cases:
        k = half_kelly(wr, aw, al)
        print(f"  {label:35} → half-Kelly = {k*100:.1f}%")

    print()

    # Real data test
    ticker = "SPY"
    print(f"── Real test on {ticker} ──")
    df = yf.download(ticker, start="2021-01-01", end="2026-01-01",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    close = df["Close"].squeeze()

    # Simple MA crossover signal (20/50)
    pos = (close.rolling(20).mean() > close.rolling(50).mean()).astype(int).shift(1)

    stats = compute_trade_stats(close, pos)
    print(f"  Trade stats: {stats}")

    ret = close.pct_change()
    rec = recommend_size(stats, ret)
    print(f"  Recommendation: {rec}")
