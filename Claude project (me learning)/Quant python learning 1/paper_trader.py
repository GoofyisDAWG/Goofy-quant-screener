"""
paper_trader.py — Phase 8: Paper Trading Framework

Maintains a persistent JSON log of paper trades triggered by Phase 7 TRADE signals.

Each screener run does three things in order:
  1. mark_to_market()   — update unrealised P&L; close positions held ≥ 20 trading days
  2. log_new_signals()  — add new TRADE signals that aren't already being tracked
  3. get_performance()  — return summary stats on closed trades

Storage: paper_trades/trades_log.json  (auto-created on first run)

Exit rule: fixed 20-day hold (matches Phase 7 LOOKFORWARD).
           No transaction costs, no slippage — this is paper trading.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

HOLD_DAYS   = 20
TRADES_DIR  = Path(__file__).parent / "paper_trades"
TRADES_FILE = TRADES_DIR / "trades_log.json"


# ══════════════════════════════════════════════════════════════════════════════
#  PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════

def _load_log() -> dict:
    if not TRADES_FILE.exists():
        return {
            "metadata": {"created": str(datetime.today().date()), "total_logged": 0},
            "open":     [],
            "closed":   [],
        }
    with open(TRADES_FILE) as f:
        return json.load(f)


def _save_log(log: dict):
    TRADES_DIR.mkdir(exist_ok=True)
    with open(TRADES_FILE, "w") as f:
        json.dump(log, f, indent=2, default=str)


# ══════════════════════════════════════════════════════════════════════════════
#  CORE OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

def log_new_signals(signals_df: pd.DataFrame,
                    price_data: dict,
                    run_date: str = None) -> list:
    """
    Record new TRADE signals not already in the open log.

    signals_df must have at minimum: Asset, Market, Best Strategy, Tier,
                                     Score, ML Score, Val AUC, P7 Verdict
    price_data: {asset: pd.Series of close prices}

    Returns list of newly added trade records.
    """
    if run_date is None:
        run_date = str(datetime.today().date())

    log = _load_log()
    open_assets = {t["asset"] for t in log["open"]}

    if "P7 Verdict" in signals_df.columns:
        trade_rows = signals_df[
            (signals_df["P7 Verdict"] == "TRADE") &
            (signals_df.get("Tier", pd.Series(index=signals_df.index)).isin(["S", "A", "B"]))
        ]
    else:
        trade_rows = signals_df[signals_df.get("Today's Verdict", pd.Series()) == "TRADE"]

    new_entries = []
    for _, row in trade_rows.iterrows():
        asset = row["Asset"]
        if asset in open_assets:
            continue

        price_series = price_data.get(asset)
        if price_series is None or price_series.empty:
            continue

        entry_price = float(price_series.iloc[-1])
        ml_score = row.get("ML Score")
        val_auc  = row.get("Val AUC")
        adj_size = row.get("Adj Size %") or row.get("Recommended Size %") or 0

        entry = {
            "asset":             asset,
            "market":            str(row.get("Market", "")),
            "entry_date":        run_date,
            "entry_price":       round(entry_price, 4),
            "hold_days_target":  HOLD_DAYS,
            "size_pct":          round(float(adj_size), 2),
            "ml_score":          round(float(ml_score), 1) if ml_score is not None else None,
            "val_auc":           round(float(val_auc), 3)  if val_auc  is not None else None,
            "strategy":          str(row.get("Best Strategy", "")),
            "tier":              str(row.get("Tier", "")),
            "score":             int(row.get("Score", 0)),
            "p7_verdict":        "TRADE",
        }
        log["open"].append(entry)
        new_entries.append(entry)

    log["metadata"]["total_logged"] = (
        log["metadata"].get("total_logged", 0) + len(new_entries)
    )
    _save_log(log)
    return new_entries


def mark_to_market(price_data: dict, run_date: str = None) -> tuple:
    """
    Update all open positions with latest prices.
    Close any that have been held for ≥ HOLD_DAYS trading days.

    Returns (still_open: list, newly_closed: list)
    """
    if run_date is None:
        run_date = str(datetime.today().date())

    log = _load_log()
    run_dt = pd.Timestamp(run_date)
    still_open, newly_closed = [], []

    for trade in log["open"]:
        entry_dt  = pd.Timestamp(trade["entry_date"])
        days_held = max(0, len(pd.bdate_range(entry_dt, run_dt)) - 1)

        price_series  = price_data.get(trade["asset"])
        current_price = (float(price_series.iloc[-1])
                         if price_series is not None and not price_series.empty
                         else None)

        pnl_pct = None
        if current_price is not None:
            pnl_pct = round((current_price / trade["entry_price"] - 1) * 100, 3)

        if days_held >= HOLD_DAYS:
            closed_trade = {
                **{k: v for k, v in trade.items()
                   if k not in ("current_price", "unrealised_pnl_pct", "days_held")},
                "exit_date":   run_date,
                "exit_price":  round(current_price, 4) if current_price else None,
                "days_held":   days_held,
                "pnl_pct":     pnl_pct,
                "win":         bool(pnl_pct > 0) if pnl_pct is not None else None,
            }
            log["closed"].append(closed_trade)
            newly_closed.append(closed_trade)
        else:
            updated = {
                **trade,
                "current_price":      round(current_price, 4) if current_price else None,
                "unrealised_pnl_pct": pnl_pct,
                "days_held":          days_held,
            }
            still_open.append(updated)

    log["open"] = still_open
    _save_log(log)
    return still_open, newly_closed


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

def get_performance() -> dict:
    """Compute summary stats on all closed trades."""
    log   = _load_log()
    open_ = log["open"]

    if not log["closed"]:
        return {
            "n_closed": 0,
            "n_open":   len(open_),
            "message":  f"No closed trades yet — positions close after {HOLD_DAYS} trading days.",
        }

    df = pd.DataFrame(log["closed"]).dropna(subset=["pnl_pct"])
    if df.empty:
        return {"n_closed": 0, "n_open": len(open_), "message": "No P&L data available yet."}

    n         = len(df)
    win_rate  = float((df["pnl_pct"] > 0).mean())
    avg_ret   = float(df["pnl_pct"].mean())
    med_ret   = float(df["pnl_pct"].median())
    std_ret   = float(df["pnl_pct"].std()) if n > 1 else 0.0

    periods_per_year = 252 / HOLD_DAYS
    sharpe = float((avg_ret / std_ret) * np.sqrt(periods_per_year)) if std_ret > 0 else None

    best_idx  = df["pnl_pct"].idxmax()
    worst_idx = df["pnl_pct"].idxmin()

    by_tier = {}
    if "tier" in df.columns:
        for tier, grp in df.groupby("tier"):
            by_tier[str(tier)] = {
                "n":           len(grp),
                "win_rate":    round(float((grp["pnl_pct"] > 0).mean()), 3),
                "avg_pnl_pct": round(float(grp["pnl_pct"].mean()), 2),
            }

    by_market = {}
    if "market" in df.columns:
        for mkt, grp in df.groupby("market"):
            by_market[str(mkt)] = {
                "n":           len(grp),
                "win_rate":    round(float((grp["pnl_pct"] > 0).mean()), 3),
                "avg_pnl_pct": round(float(grp["pnl_pct"].mean()), 2),
            }

    return {
        "n_closed":          n,
        "n_open":            len(open_),
        "win_rate":          round(win_rate, 3),
        "avg_pnl_pct":       round(avg_ret, 2),
        "median_pnl_pct":    round(med_ret, 2),
        "std_pnl_pct":       round(std_ret, 2),
        "annualised_sharpe": round(sharpe, 2) if sharpe is not None else None,
        "best_trade":  {"asset": df.loc[best_idx,  "asset"], "pnl_pct": df.loc[best_idx,  "pnl_pct"], "entry_date": df.loc[best_idx,  "entry_date"]},
        "worst_trade": {"asset": df.loc[worst_idx, "asset"], "pnl_pct": df.loc[worst_idx, "pnl_pct"], "entry_date": df.loc[worst_idx, "entry_date"]},
        "by_tier":           by_tier,
        "by_market":         by_market,
        "all_returns":       df["pnl_pct"].tolist(),
    }


def get_open_positions() -> pd.DataFrame:
    """Return open positions as a DataFrame."""
    log = _load_log()
    return pd.DataFrame(log["open"]) if log["open"] else pd.DataFrame()


def get_closed_trades() -> pd.DataFrame:
    """Return closed trades as a DataFrame."""
    log = _load_log()
    return pd.DataFrame(log["closed"]) if log["closed"] else pd.DataFrame()
