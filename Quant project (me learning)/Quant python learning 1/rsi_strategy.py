import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import datetime as dt

# ── Configuration ──────────────────────────────────────────────────────────────
endDate   = dt.datetime.now()
startDate = endDate - dt.timedelta(days=365 * 10)

stocks = ["AAPL", "SPY", "TSLA", "WM", "BTC-USD", "ETH-USD"]

# RSI parameter combos to test: (period, overbought_threshold, oversold_threshold)
rsi_periods  = [7, 9, 14, 21]
ob_os_pairs  = [(70, 30), (65, 35), (75, 25), (80, 20)]
rsi_params   = [(p, ob, os) for p in rsi_periods for ob, os in ob_os_pairs]

# 252 trading days/year for stocks; crypto trades 365 but 252 is fine for comparison
PERIODS_PER_YEAR = 252


# ── Helper: compute RSI ────────────────────────────────────────────────────────
# RSI measures momentum: how fast and how strongly price is moving.
# Formula: 100 - (100 / (1 + RS)) where RS = avg_gain / avg_loss over `period` days.
# < oversold  → market is likely beaten down → potential buy opportunity
# > overbought → market has run up hard      → potential sell/exit signal
def compute_rsi(price_series, period):
    delta    = price_series.diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs       = avg_gain / avg_loss
    rsi      = 100 - (100 / (1 + rs))
    return rsi


# ── Helper: run a single RSI backtest ─────────────────────────────────────────
def run_backtest(price_series, period, overbought, oversold):
    df = pd.DataFrame({'price': price_series})
    df['RSI'] = compute_rsi(df['price'], period)

    # Generate raw signals:
    #   1 = buy  when RSI falls below oversold  threshold
    #   0 = exit when RSI rises above overbought threshold
    #   NaN in between → forward-fill to hold position
    df['raw_signal'] = np.nan
    df.loc[df['RSI'] < oversold,   'raw_signal'] = 1   # oversold  → go long
    df.loc[df['RSI'] > overbought, 'raw_signal'] = 0   # overbought → exit

    df['signal']   = df['raw_signal'].ffill().fillna(0)
    df['position'] = df['signal'].shift(1)              # act the day after signal

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

    total_mkt   = df['cum_market'].dropna().iloc[-1]   - 1
    total_strat = df['cum_strategy'].dropna().iloc[-1] - 1

    ann_mkt     = np.exp(market_lr.mean()   * PERIODS_PER_YEAR) - 1
    ann_strat   = np.exp(strategy_lr.mean() * PERIODS_PER_YEAR) - 1

    vol_mkt     = market_lr.std()   * np.sqrt(PERIODS_PER_YEAR)
    vol_strat   = strategy_lr.std() * np.sqrt(PERIODS_PER_YEAR)

    sharpe_mkt   = ann_mkt   / vol_mkt   if vol_mkt   != 0 else np.nan
    sharpe_strat = ann_strat / vol_strat if vol_strat != 0 else np.nan

    mdd_mkt   = max_drawdown(df['cum_market'].dropna())
    mdd_strat = max_drawdown(df['cum_strategy'].dropna())

    # win rate: % of days the strategy had a positive return
    winning_days = (strategy_lr > 0).sum()
    total_days   = (strategy_lr != 0).sum()
    win_rate     = winning_days / total_days if total_days > 0 else np.nan

    return {
        'B&H Total Return %':    round(total_mkt   * 100, 2),
        'Strat Total Return %':  round(total_strat * 100, 2),
        'Strat Annual Return %': round(ann_strat   * 100, 2),
        'B&H Sharpe':            round(sharpe_mkt,   2),
        'Strat Sharpe':          round(sharpe_strat, 2),
        'B&H Max DD %':          round(mdd_mkt   * 100, 2),
        'Strat Max DD %':        round(mdd_strat * 100, 2),
        'Win Rate %':            round(win_rate   * 100, 2),
    }


# ── Step 1: Download price data (once per ticker) ─────────────────────────────
print("Downloading price data...\n")
price_data = {}
for stock in stocks:
    raw = yf.download(stock, start=startDate, end=endDate, auto_adjust=True, progress=False)
    price_data[stock] = raw['Close'].squeeze()
    print(f"  {stock}: {len(raw)} rows")


# ── Step 2: Run all RSI param × stock combinations ────────────────────────────
all_results = []

for period, overbought, oversold in rsi_params:
    for stock in stocks:
        df      = run_backtest(price_data[stock], period, overbought, oversold)
        metrics = get_metrics(df)
        metrics['Ticker']    = stock
        metrics['RSI Params'] = f"RSI{period}({oversold}/{overbought})"  # e.g. RSI14(30/70)
        all_results.append(metrics)


# ── Step 3: Build the comparison table ────────────────────────────────────────
results_df = (
    pd.DataFrame(all_results)
    .set_index(['Ticker', 'RSI Params'])
    .sort_index()
)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 140)

print("\n" + "=" * 100)
print("  RSI STRATEGY — FULL COMPARISON TABLE")
print("=" * 100)
print(results_df.to_string())


# ── Step 4: Best RSI params per stock (by Strategy Sharpe) ────────────────────
reset    = results_df.reset_index()
best_idx = reset.groupby('Ticker')['Strat Sharpe'].idxmax()
best     = reset.loc[best_idx, ['Ticker', 'RSI Params', 'Strat Sharpe',
                                  'Strat Total Return %', 'Strat Max DD %', 'Win Rate %']]
best     = best.set_index('Ticker')

print("\n" + "=" * 100)
print("  BEST RSI PARAMS PER TICKER  (ranked by Strategy Sharpe Ratio)")
print("=" * 100)
print(best.to_string())


# ── Step 5: Equity curves — best RSI params per stock ─────────────────────────
best_params = best['RSI Params'].to_dict()   # e.g. {'AAPL': 'RSI14(30/70)', ...}

n_stocks = len(stocks)
cols = 3
rows = (n_stocks + cols - 1) // cols

fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 5))
axes = axes.flatten()

for i, stock in enumerate(stocks):
    ax         = axes[i]
    param_str  = best_params[stock]           # e.g. 'RSI14(30/70)'
    # parse back: RSI{period}({oversold}/{overbought})
    import re
    m          = re.match(r'RSI(\d+)\((\d+)/(\d+)\)', param_str)
    period     = int(m.group(1))
    oversold   = int(m.group(2))
    overbought = int(m.group(3))

    df = run_backtest(price_data[stock], period, overbought, oversold)
    df[['cum_market', 'cum_strategy']].plot(ax=ax)

    ax.set_title(f"{stock}  |  Best params: {param_str}", fontsize=12)
    ax.set_xlabel('')
    ax.legend(['Buy & Hold', f"{param_str} Strategy"])
    ax.grid(True, alpha=0.3)

# hide any unused subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

plt.suptitle("Equity Curves — Best RSI Params per Ticker", fontsize=15, y=1.01)
plt.tight_layout()
plt.savefig('rsi_best_equity_curves.png', dpi=150, bbox_inches='tight')
plt.show()
print("\nChart saved as 'rsi_best_equity_curves.png'")


# ── Step 6: Strategy Sharpe heatmap (RSI params vs Ticker) ────────────────────
sharpe_pivot = reset.pivot(index='RSI Params', columns='Ticker', values='Strat Sharpe')

fig2, ax2 = plt.subplots(figsize=(14, 8))
im = ax2.imshow(sharpe_pivot.values, cmap='RdYlGn', aspect='auto')
plt.colorbar(im, ax=ax2, label='Strategy Sharpe Ratio')

ax2.set_xticks(range(len(sharpe_pivot.columns)))
ax2.set_xticklabels(sharpe_pivot.columns, rotation=45, ha='right')
ax2.set_yticks(range(len(sharpe_pivot.index)))
ax2.set_yticklabels(sharpe_pivot.index)
ax2.set_title("Strategy Sharpe Ratio Heatmap — RSI Params vs Ticker", fontsize=13)

# annotate cells
for row_i in range(len(sharpe_pivot.index)):
    for col_j in range(len(sharpe_pivot.columns)):
        val = sharpe_pivot.values[row_i, col_j]
        if not np.isnan(val):
            ax2.text(col_j, row_i, f"{val:.2f}", ha='center', va='center',
                     fontsize=9, color='black')

plt.tight_layout()
plt.savefig('rsi_sharpe_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print("Heatmap saved as 'rsi_sharpe_heatmap.png'")
