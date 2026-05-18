"""
portfolio_builder.py — Phase 6: Correlation-Aware Portfolio Construction

Given a set of assets and their Phase 5 recommended sizes, this module:
  1. Builds a pairwise correlation matrix from test-period daily returns
  2. Groups correlated assets into clusters (connected-components, threshold 0.65)
  3. Scales down positions within clusters so correlated bets don't double up
  4. Computes portfolio-level metrics: annualised vol + diversification ratio

Size adjustment rule:
    adj_size = phase5_size × (1 / √cluster_size)

    Intuition: if two assets move together (ρ > 0.65), holding both is one bet
    expressed twice. Scaling by 1/√2 ≈ 0.71 reduces each without zeroing either.
    A cluster of 4 scales each to 0.5× — equivalent to one full position spread
    across four related names.
"""

import numpy as np
import pandas as pd

CORR_THRESHOLD = 0.65   # pairwise correlation above which two assets share a cluster
MAX_PORTFOLIO  = 1.0    # cap: total adjusted allocation cannot exceed 100%
MIN_OVERLAP    = 100    # minimum overlapping trading days to trust a correlation estimate


# ══════════════════════════════════════════════════════════════════════════════
#  CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════════════════════

def compute_correlation_matrix(returns_dict: dict) -> pd.DataFrame:
    """
    Build a pairwise Pearson correlation matrix.

    Args:
        returns_dict: {ticker: pd.Series of daily returns (float)}
                      Pass test-period returns only (e.g. 2021-present).

    Returns:
        pd.DataFrame (n_assets × n_assets), NaN where < MIN_OVERLAP overlap.
    """
    df = pd.DataFrame(returns_dict).dropna(how="all", axis=1)
    return df.corr(min_periods=MIN_OVERLAP)


# ══════════════════════════════════════════════════════════════════════════════
#  CLUSTER DETECTION (connected components)
# ══════════════════════════════════════════════════════════════════════════════

def find_clusters(corr_matrix: pd.DataFrame,
                  threshold: float = CORR_THRESHOLD) -> dict:
    """
    Group assets into clusters using connected-components on the correlation graph.
    Two assets are connected if their pairwise correlation ≥ threshold.

    Note: this is transitive — if A↔B and B↔C, all three cluster together even
    if A-C correlation is below threshold. This is intentional: B is the bridge.

    Returns:
        {asset: cluster_id (int)}   — cluster IDs start at 1.
        Standalone assets (no neighbours) each get their own unique cluster ID.
    """
    assets = list(corr_matrix.columns)
    n      = len(assets)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]   # path compression
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            a, b = assets[i], assets[j]
            val  = corr_matrix.loc[a, b]
            if pd.notna(val) and val >= threshold:
                union(i, j)

    roots   = {}
    counter = 1
    cluster_map = {}
    for i, asset in enumerate(assets):
        root = find(i)
        if root not in roots:
            roots[root] = counter
            counter += 1
        cluster_map[asset] = roots[root]

    return cluster_map


def cluster_label(asset: str, cluster_map: dict, cluster_sizes: dict) -> str:
    """Returns 'Unique' for solo assets, 'C1' / 'C2' etc for groups."""
    cid = cluster_map.get(asset)
    if cid is None:
        return "—"
    n = cluster_sizes.get(asset, 1)
    return "Unique" if n == 1 else f"C{cid}"


# ══════════════════════════════════════════════════════════════════════════════
#  CORRELATION-ADJUSTED POSITION SIZES
# ══════════════════════════════════════════════════════════════════════════════

def adjust_for_correlation(
    assets: list,
    raw_sizes: dict,
    cluster_map: dict,
) -> tuple:
    """
    Scale Phase 5 recommended sizes by 1/√(cluster_size).

    Args:
        assets      : tickers to size (TRADE-signal, non-Skip)
        raw_sizes   : {ticker: Phase 5 Recommended Size %} (0–100 scale)
        cluster_map : {ticker: cluster_id} from find_clusters()

    Returns (all three are dicts keyed by ticker):
        adj_sizes     : adjusted size % (0–100 scale)
        cluster_sizes : how many active assets share this ticker's cluster
        corr_risk     : "Low" (unique) | "Medium" (2–3) | "High" (4+)

    If total adjusted allocation exceeds MAX_PORTFOLIO (100%), all sizes are
    scaled down proportionally so the portfolio stays fully-but-not-over-invested.
    """
    active_counts: dict = {}
    for asset in assets:
        cid = cluster_map.get(asset)
        if cid is not None:
            active_counts[cid] = active_counts.get(cid, 0) + 1

    adj_sizes     = {}
    cluster_sizes = {}
    corr_risk     = {}

    for asset in assets:
        cid  = cluster_map.get(asset)
        n    = active_counts.get(cid, 1)
        raw  = raw_sizes.get(asset) or 0.0
        adj  = raw * (1.0 / n ** 0.5)

        adj_sizes[asset]     = round(adj, 1)
        cluster_sizes[asset] = n
        corr_risk[asset]     = ("High"   if n >= 4 else
                                "Medium" if n >= 2 else
                                "Low")

    total = sum(adj_sizes.values())
    if total > MAX_PORTFOLIO * 100:
        scale     = (MAX_PORTFOLIO * 100) / total
        adj_sizes = {a: round(v * scale, 1) for a, v in adj_sizes.items()}

    return adj_sizes, cluster_sizes, corr_risk


# ══════════════════════════════════════════════════════════════════════════════
#  PORTFOLIO-LEVEL METRICS
# ══════════════════════════════════════════════════════════════════════════════

def portfolio_metrics(returns_dict: dict, weights: dict) -> dict:
    """
    Compute annualised portfolio volatility and diversification ratio.

    Args:
        returns_dict : {ticker: pd.Series of daily returns}
        weights      : {ticker: weight as fraction 0–1} (will be normalised)

    Returns dict:
        port_vol_ann  — annualised portfolio vol (%)
        div_ratio     — diversification ratio (weighted avg vol / portfolio vol)
                        >1 = genuine diversification; =1 = everything moves together
        effective_n   — div_ratio² ≈ number of truly independent positions
        n_positions   — how many tickers were included
    """
    tickers = [t for t in weights
               if t in returns_dict and returns_dict[t] is not None]
    if not tickers:
        return {"port_vol_ann": None, "div_ratio": None,
                "effective_n": None, "n_positions": 0}

    df = pd.DataFrame({t: returns_dict[t] for t in tickers}).dropna(how="all")
    df = df.dropna(axis=1, how="all")
    tickers = [t for t in tickers if t in df.columns]
    if not tickers:
        return {"port_vol_ann": None, "div_ratio": None,
                "effective_n": None, "n_positions": 0}

    w = np.array([weights.get(t, 0.0) for t in tickers], dtype=float)
    if w.sum() <= 0:
        return {"port_vol_ann": None, "div_ratio": None,
                "effective_n": None, "n_positions": 0}
    w /= w.sum()   # normalise

    cov          = df[tickers].cov() * 252        # annualise
    port_var     = float(w @ cov.values @ w)
    port_vol     = float(port_var ** 0.5)
    indiv_vols   = np.sqrt(np.diag(cov.values))
    wavg_vol     = float(w @ indiv_vols)
    div_ratio    = wavg_vol / port_vol if port_vol > 0 else 1.0

    return {
        "port_vol_ann": round(port_vol * 100, 1),
        "div_ratio":    round(div_ratio, 2),
        "effective_n":  round(div_ratio ** 2, 1),
        "n_positions":  len(tickers),
    }
