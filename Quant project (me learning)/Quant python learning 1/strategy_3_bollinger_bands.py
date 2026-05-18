"""
=============================================================
  STRATEGY 3: BOLLINGER BANDS — Multi-Asset Backtest
  Assets: NVDA, SPY, CBA.AX, BHP.AX, 7203.T, 6758.T
  Markets: US, Australia (ASX), Japan (TSE)
=============================================================

WHAT IS BOLLINGER BANDS?
------------------------
Bollinger Bands consist of 3 lines plotted around price:
  - Middle Band  = 20-day Simple Moving Average (SMA)
  - Upper Band   = SMA + (2 × Standard Deviation)
  - Lower Band   = SMA - (2 × Standard Deviation)

TRADING LOGIC (Mean Reversion):
  - BUY  when price touches or falls below the Lower Band
    → price is "statistically cheap" — likely to revert up
  - SELL when price touches or rises above the Upper Band
    → price is "statistically expensive" — likely to revert down

WHY THIS WORKS:
  ~95% of price action stays within the bands (2σ rule).
  When price breaks out, it tends to snap back to the mean.
  Works best in range-bound/choppy markets (like Japanese stocks).

TRAIN/TEST SPLIT:
  - Train: 2018–2021 (fit & optimise parameters)
  - Test:  2022–2024 (out-of-sample validation — the "real" test)

METRICS REPORTED:
  - Total Return      : overall % gain/loss
  - Sharpe Ratio      : return per unit of risk (>1 = good, >2 = great)
  - Max Drawdown      : worst peak-to-trough drop (risk measure)
  - Win Rate          : % of trades that were profitable
  - Number of Trades  : how many round-trips occurred
=============================================================
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings("ignore")

# ── CONFIG ──────────────────────────────────────────────────
ASSETS = {
    "NVDA":    "Nvidia (US)",
    "SPY":     "S&P 500 ETF (US)",
    "CBA.AX":  "Commonwealth Bank (AU)",
    "BHP.AX":  "BHP Group (AU)",
    "7203.T":  "Toyota (JP)",
    "6758.T":  "Sony (JP)",
}

TRAIN_START = "2016-01-01"
TRAIN_END   = "2020-12-31"
TEST_START  = "2021-01-01"
TEST_END    = "2026-12-31"

# Bollinger Bands parameters
BB_WINDOW  = 20    # rolling window for SMA & std dev
BB_STD_DEV = 2.0   # number of standard deviations for bands


# ── HELPER FUNCTIONS ────────────────────────────────────────

def download_data(ticker, start, end):
    """Download OHLCV data from Yahoo Finance."""
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    df = df[["Close"]].copy()
    df.columns = ["Close"]
    df.dropna(inplace=True)
    return df


def compute_bollinger_bands(df, window=20, num_std=2.0):
    """
    Add Bollinger Band columns to dataframe.

    Columns added:
      SMA        : Simple Moving Average (middle band)
      Upper_Band : SMA + (num_std × rolling std)
      Lower_Band : SMA - (num_std × rolling std)
      BB_Width   : (Upper - Lower) / SMA — measures band squeeze
      %B         : Where price sits within bands (0=lower, 1=upper)
    """
    df = df.copy()
    df["SMA"]        = df["Close"].rolling(window).mean()
    rolling_std      = df["Close"].rolling(window).std()
    df["Upper_Band"] = df["SMA"] + (num_std * rolling_std)
    df["Lower_Band"] = df["SMA"] - (num_std * rolling_std)
    df["BB_Width"]   = (df["Upper_Band"] - df["Lower_Band"]) / df["SMA"]
    df["%B"]         = (df["Close"] - df["Lower_Band"]) / (df["Upper_Band"] - df["Lower_Band"])
    return df


def generate_signals(df):
    """
    Generate buy/sell signals:
      +1 (BUY)  when price crosses below the Lower Band
      -1 (SELL) when price crosses above the Upper Band
       0 (HOLD) otherwise

    We hold position until the opposite signal fires.
    This avoids over-trading on every band touch.
    """
    df = df.copy()
    df["Signal"]   = 0
    df["Position"] = 0  # 1 = long, 0 = flat

    position = 0
    for i in range(1, len(df)):
        close = df["Close"].iloc[i]
        lower = df["Lower_Band"].iloc[i]
        upper = df["Upper_Band"].iloc[i]

        if pd.isna(lower) or pd.isna(upper):
            continue

        if position == 0 and close <= lower:
            # Price hit lower band → BUY signal
            df.iloc[i, df.columns.get_loc("Signal")] = 1
            position = 1
        elif position == 1 and close >= upper:
            # Price hit upper band → SELL signal
            df.iloc[i, df.columns.get_loc("Signal")] = -1
            position = 0

        df.iloc[i, df.columns.get_loc("Position")] = position

    return df


def calculate_metrics(df, label=""):
    """
    Calculate performance metrics for a backtest period.

    Strategy returns = daily price change × position held
    Benchmark (Buy & Hold) = daily price change, always invested
    """
    df = df.copy()

    # Daily returns
    df["Daily_Return"]    = df["Close"].pct_change()
    df["Strategy_Return"] = df["Daily_Return"] * df["Position"].shift(1)

    # Cumulative returns
    df["Cum_Strategy"]  = (1 + df["Strategy_Return"]).cumprod()
    df["Cum_BuyHold"]   = (1 + df["Daily_Return"]).cumprod()

    # ── Core metrics ──
    total_return    = df["Cum_Strategy"].iloc[-1] - 1
    bh_return       = df["Cum_BuyHold"].iloc[-1] - 1

    # Annualised Sharpe Ratio (risk-free rate ≈ 0 for simplicity)
    daily_std = df["Strategy_Return"].std()
    if daily_std == 0:
        sharpe = 0.0
    else:
        sharpe = (df["Strategy_Return"].mean() / daily_std) * np.sqrt(252)

    # Max Drawdown
    rolling_max    = df["Cum_Strategy"].cummax()
    drawdown       = (df["Cum_Strategy"] - rolling_max) / rolling_max
    max_drawdown   = drawdown.min()

    # Win rate
    signals        = df[df["Signal"] == -1]   # count completed trades (SELL)
    trade_returns  = []
    buy_price      = None
    for i, row in df.iterrows():
        if row["Signal"] == 1:
            buy_price = row["Close"]
        elif row["Signal"] == -1 and buy_price is not None:
            trade_returns.append((row["Close"] - buy_price) / buy_price)
            buy_price = None

    n_trades  = len(trade_returns)
    win_rate  = (sum(1 for r in trade_returns if r > 0) / n_trades * 100) if n_trades > 0 else 0

    return {
        "Period":         label,
        "Total Return":   f"{total_return:.1%}",
        "B&H Return":     f"{bh_return:.1%}",
        "Sharpe Ratio":   f"{sharpe:.2f}",
        "Max Drawdown":   f"{max_drawdown:.1%}",
        "Win Rate":       f"{win_rate:.0f}%",
        "# Trades":       n_trades,
        "_df":            df,         # keep for plotting
        "_sharpe_raw":    sharpe,
        "_return_raw":    total_return,
        "_maxdd_raw":     max_drawdown,
    }


def run_backtest(ticker, name):
    """Full pipeline for one asset: download → indicators → signals → metrics."""
    print(f"\n{'='*60}")
    print(f"  {name}  ({ticker})")
    print(f"{'='*60}")

    # Download both periods
    train_raw = download_data(ticker, TRAIN_START, TRAIN_END)
    test_raw  = download_data(ticker, TEST_START, TEST_END)

    if train_raw.empty or test_raw.empty:
        print(f"  ⚠️  No data available for {ticker}. Skipping.")
        return None, None

    # Compute Bollinger Bands
    train_bb = compute_bollinger_bands(train_raw, BB_WINDOW, BB_STD_DEV)
    test_bb  = compute_bollinger_bands(test_raw,  BB_WINDOW, BB_STD_DEV)

    # Generate signals
    train_sig = generate_signals(train_bb)
    test_sig  = generate_signals(test_bb)

    # Calculate metrics
    train_metrics = calculate_metrics(train_sig, label="TRAIN 2016–2020")
    test_metrics  = calculate_metrics(test_sig,  label="TEST  2021–2026")

    # Print results
    for m in [train_metrics, test_metrics]:
        print(f"\n  {m['Period']}")
        print(f"    Strategy Return : {m['Total Return']}")
        print(f"    Buy & Hold      : {m['B&H Return']}")
        print(f"    Sharpe Ratio    : {m['Sharpe Ratio']}")
        print(f"    Max Drawdown    : {m['Max Drawdown']}")
        print(f"    Win Rate        : {m['Win Rate']}")
        print(f"    # Trades        : {m['# Trades']}")

    return train_metrics, test_metrics


def plot_asset(ticker, name, train_m, test_m):
    """
    Plot 4-panel chart for one asset:
      [1] Train: Price + Bollinger Bands + signals
      [2] Train: Cumulative returns (Strategy vs Buy & Hold)
      [3] Test:  Price + Bollinger Bands + signals
      [4] Test:  Cumulative returns (Strategy vs Buy & Hold)
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle(f"Bollinger Bands Strategy — {name} ({ticker})",
                 fontsize=14, fontweight="bold", y=1.01)

    for col, (m, period_label) in enumerate(
        [(train_m, "TRAIN 2016–2020"), (test_m, "TEST 2021–2026")]
    ):
        df = m["_df"]

        # ── Panel 1: Price + Bands ──
        ax1 = axes[0][col]
        ax1.fill_between(df.index, df["Upper_Band"], df["Lower_Band"],
                         alpha=0.15, color="blue", label="Band Range")
        ax1.plot(df.index, df["Close"],      color="black", lw=1.2,  label="Price")
        ax1.plot(df.index, df["SMA"],        color="blue",  lw=1.0, ls="--", label="SMA(20)")
        ax1.plot(df.index, df["Upper_Band"], color="red",   lw=0.8, ls="--", label="Upper Band")
        ax1.plot(df.index, df["Lower_Band"], color="green", lw=0.8, ls="--", label="Lower Band")

        # BUY signals (green triangles up)
        buys = df[df["Signal"] == 1]
        ax1.scatter(buys.index, buys["Close"], marker="^", color="green",
                    s=80, zorder=5, label="BUY")

        # SELL signals (red triangles down)
        sells = df[df["Signal"] == -1]
        ax1.scatter(sells.index, sells["Close"], marker="v", color="red",
                    s=80, zorder=5, label="SELL")

        ax1.set_title(f"{period_label} — Price & Bands")
        ax1.set_ylabel("Price")
        ax1.legend(fontsize=7, loc="upper left")
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax1.grid(alpha=0.3)

        # ── Panel 2: Cumulative Returns ──
        ax2 = axes[1][col]
        ax2.plot(df.index, (df["Cum_Strategy"] - 1) * 100,
                 color="blue",  lw=1.5, label=f"BB Strategy ({m['Total Return']})")
        ax2.plot(df.index, (df["Cum_BuyHold"] - 1) * 100,
                 color="gray", lw=1.5, ls="--", label=f"Buy & Hold ({m['B&H Return']})")
        ax2.axhline(0, color="black", lw=0.8, ls=":")
        ax2.set_title(f"{period_label} — Cumulative Return (%)")
        ax2.set_ylabel("Return (%)")
        ax2.legend(fontsize=8)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax2.grid(alpha=0.3)

    plt.tight_layout()
    filename = f"bb_{ticker.replace('.', '_')}.png"
    plt.savefig(filename, dpi=130, bbox_inches="tight")
    print(f"  📊 Chart saved: {filename}")
    plt.show()


def print_summary_table(results):
    """Print final comparison table across all 6 assets."""
    print("\n")
    print("=" * 90)
    print("  BOLLINGER BANDS — SUMMARY TABLE (TEST PERIOD 2021–2026)")
    print("=" * 90)
    print(f"  {'Asset':<20} {'Return':>10} {'B&H':>10} {'Sharpe':>8} {'MaxDD':>10} {'WinRate':>9} {'Trades':>7}")
    print("-" * 90)

    for ticker, name, train_m, test_m in results:
        if test_m is None:
            continue
        print(f"  {name:<20} "
              f"{test_m['Total Return']:>10} "
              f"{test_m['B&H Return']:>10} "
              f"{test_m['Sharpe Ratio']:>8} "
              f"{test_m['Max Drawdown']:>10} "
              f"{test_m['Win Rate']:>9} "
              f"{test_m['# Trades']:>7}")

    print("=" * 90)

    # Interpretation guide
    print("""
  HOW TO READ THIS TABLE:
  ─────────────────────────────────────────────────────────────
  Return    → Strategy's total return over test period
  B&H       → Passive "just hold it" return (the benchmark to beat)
  Sharpe    → Return ÷ Risk. >1 = good, >2 = great, <0 = losing
  MaxDD     → Worst peak-to-trough loss. Smaller (less negative) = better
  WinRate   → % of individual trades that made money
  Trades    → Total round-trips (buy + sell = 1 trade)
  ─────────────────────────────────────────────────────────────
  KEY INSIGHT: Bollinger Bands is a MEAN REVERSION strategy.
  It works best when prices oscillate (range-bound markets).
  In strongly trending markets (e.g. NVDA), it may underperform
  Buy & Hold because the trend never reverts — it just goes up.
  ─────────────────────────────────────────────────────────────
    """)


# ── MAIN ────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  STRATEGY 3: BOLLINGER BANDS BACKTEST")
    print(f"  Parameters: Window={BB_WINDOW}, StdDev={BB_STD_DEV}")
    print(f"  Assets: {', '.join(ASSETS.keys())}")
    print("=" * 60)

    results = []

    for ticker, name in ASSETS.items():
        train_m, test_m = run_backtest(ticker, name)
        results.append((ticker, name, train_m, test_m))

    # Plot each asset
    print("\n\n--- GENERATING CHARTS ---")
    for ticker, name, train_m, test_m in results:
        if train_m and test_m:
            plot_asset(ticker, name, train_m, test_m)

    # Final summary table
    print_summary_table(results)

    print("\n✅ Backtest complete!")
    print("   Charts saved as: bb_TICKER.png in your current directory")


if __name__ == "__main__":
    main()
