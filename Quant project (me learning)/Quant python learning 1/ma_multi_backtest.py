import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt

# ── Configuration ──────────────────────────────────────────────────────────────
endDate   = dt.datetime.now()
startDate = endDate - dt.timedelta(days=365 * 10)

stocks = ["AAPL", "SPY", "TSLA", "WM", "BTC-USD", "ETH-USD"]

# MA pairs to test: (fast window, slow window)
ma_pairs = [(10, 30), (20, 50), (25, 60), (30, 70)]

# 252 trading days/year for stocks; crypto trades 365 but 252 is fine for comparison
PERIODS_PER_YEAR = 252


# ── Helper: run a single MA crossover backtest ─────────────────────────────────
def run_backtest(price_series, fast, slow):
    df = pd.DataFrame({'price': price_series})
    df[f'MA{fast}'] = df['price'].rolling(window=fast).mean()
    df[f'MA{slow}'] = df['price'].rolling(window=slow).mean()

    # 1 when fast MA is above slow MA, else 0
    df['signal']   = (df[f'MA{fast}'] > df[f'MA{slow}']).astype(int)
    df['position'] = df['signal'].shift(1)          # act the day after signal

    df['log_returns']          = np.log(df['price'] / df['price'].shift(1))
    df['strategy_log_returns'] = df['position'] * df['log_returns']

    df['cum_market']   = np.exp(df['log_returns'].cumsum())
    df['cum_strategy'] = np.exp(df['strategy_log_returns'].cumsum())
    return df


# ── Helper: max drawdown ───────────────────────────────────────────────────────
def max_drawdown(cum_series):
    running_max = cum_series.cummax()
    drawdown    = (cum_series - running_max) / running_max
    return drawdown.min()


# ── Helper: compute all metrics for one backtest run ──────────────────────────
def get_metrics(df):
    market_lr   = df['log_returns'].dropna()
    strategy_lr = df['strategy_log_returns'].dropna()

    total_mkt  = df['cum_market'].dropna().iloc[-1]   - 1
    total_strat = df['cum_strategy'].dropna().iloc[-1] - 1

    ann_mkt    = np.exp(market_lr.mean()   * PERIODS_PER_YEAR) - 1
    ann_strat  = np.exp(strategy_lr.mean() * PERIODS_PER_YEAR) - 1

    vol_mkt    = market_lr.std()   * np.sqrt(PERIODS_PER_YEAR)
    vol_strat  = strategy_lr.std() * np.sqrt(PERIODS_PER_YEAR)

    sharpe_mkt   = ann_mkt   / vol_mkt   if vol_mkt   != 0 else np.nan
    sharpe_strat = ann_strat / vol_strat if vol_strat != 0 else np.nan

    mdd_mkt   = max_drawdown(df['cum_market'].dropna())
    mdd_strat = max_drawdown(df['cum_strategy'].dropna())

    # win rate: % of days the strategy had a positive return
    winning_days = (strategy_lr > 0).sum()
    total_days   = (strategy_lr != 0).sum()
    win_rate     = winning_days / total_days if total_days > 0 else np.nan

    return {
        'B&H Total Return %':      round(total_mkt   * 100, 2),
        'Strat Total Return %':    round(total_strat * 100, 2),
        'Strat Annual Return %':   round(ann_strat   * 100, 2),
        'B&H Sharpe':              round(sharpe_mkt,  2),
        'Strat Sharpe':            round(sharpe_strat, 2),
        'B&H Max DD %':            round(mdd_mkt   * 100, 2),
        'Strat Max DD %':          round(mdd_strat * 100, 2),
        'Win Rate %':              round(win_rate   * 100, 2),
    }


# ── Step 1: Download price data (once per ticker) ─────────────────────────────
print("Downloading price data...\n")
price_data = {}
for stock in stocks:
    raw = yf.download(stock, start=startDate, end=endDate, auto_adjust=True, progress=False)
    price_data[stock] = raw['Close'].squeeze()
    print(f"  {stock}: {len(raw)} rows")


# ── Step 2: Run all MA pair × stock combinations ──────────────────────────────
all_results = []

for fast, slow in ma_pairs:
    for stock in stocks:
        df = run_backtest(price_data[stock], fast, slow)
        metrics = get_metrics(df)
        metrics['Ticker']  = stock
        metrics['MA Pair'] = f"MA{fast}/{slow}"
        all_results.append(metrics)


# ── Step 3: Build the comparison table ────────────────────────────────────────
results_df = (
    pd.DataFrame(all_results)
    .set_index(['Ticker', 'MA Pair'])
    .sort_index()
)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 140)

print("\n" + "=" * 100)
print("  MA CROSSOVER STRATEGY — FULL COMPARISON TABLE")
print("=" * 100)
print(results_df.to_string())


# ── Step 4: Best MA pair per stock (by Strategy Sharpe) ───────────────────────
reset = results_df.reset_index()
best_idx = reset.groupby('Ticker')['Strat Sharpe'].idxmax()
best = reset.loc[best_idx, ['Ticker', 'MA Pair', 'Strat Sharpe',
                              'Strat Total Return %', 'Strat Max DD %', 'Win Rate %']]
best = best.set_index('Ticker')

print("\n" + "=" * 100)
print("  BEST MA PAIR PER TICKER  (ranked by Strategy Sharpe Ratio)")
print("=" * 100)
print(best.to_string())


# ── Step 5: Equity curves — best MA pair per stock ────────────────────────────
best_pairs = best['MA Pair'].to_dict()   # e.g. {'AAPL': 'MA10/30', ...}

n_stocks = len(stocks)
cols = 3
rows = (n_stocks + cols - 1) // cols

fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 5))
axes = axes.flatten()

for i, stock in enumerate(stocks):
    ax = axes[i]
    fast_str, slow_str = best_pairs[stock].replace('MA', '').split('/')
    fast, slow = int(fast_str), int(slow_str)

    df = run_backtest(price_data[stock], fast, slow)
    df[['cum_market', 'cum_strategy']].plot(ax=ax)

    ax.set_title(f"{stock}  |  Best pair: {best_pairs[stock]}", fontsize=12)
    ax.set_xlabel('')
    ax.legend(['Buy & Hold', f"MA{fast}/{slow} Strategy"])
    ax.grid(True, alpha=0.3)

# hide any unused subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

plt.suptitle("Equity Curves — Best MA Pair per Ticker", fontsize=15, y=1.01)
plt.tight_layout()
plt.savefig('ma_best_equity_curves.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nChart saved as 'ma_best_equity_curves.png'")


# ── Step 6: Strategy Sharpe heatmap (MA pair vs Ticker) ───────────────────────
sharpe_pivot = reset.pivot(index='MA Pair', columns='Ticker', values='Strat Sharpe')

fig2, ax2 = plt.subplots(figsize=(12, 5))
im = ax2.imshow(sharpe_pivot.values, cmap='RdYlGn', aspect='auto')
plt.colorbar(im, ax=ax2, label='Strategy Sharpe Ratio')

ax2.set_xticks(range(len(sharpe_pivot.columns)))
ax2.set_xticklabels(sharpe_pivot.columns, rotation=45, ha='right')
ax2.set_yticks(range(len(sharpe_pivot.index)))
ax2.set_yticklabels(sharpe_pivot.index)
ax2.set_title("Strategy Sharpe Ratio Heatmap — MA Pair vs Ticker", fontsize=13)

# annotate cells
for row_i in range(len(sharpe_pivot.index)):
    for col_j in range(len(sharpe_pivot.columns)):
        val = sharpe_pivot.values[row_i, col_j]
        if not np.isnan(val):
            ax2.text(col_j, row_i, f"{val:.2f}", ha='center', va='center',
                     fontsize=10, color='black')

plt.tight_layout()
plt.savefig('ma_sharpe_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print("Heatmap saved as 'ma_sharpe_heatmap.png'")
