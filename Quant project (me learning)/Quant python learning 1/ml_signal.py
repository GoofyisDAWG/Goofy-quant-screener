"""
ml_signal.py — Phase 7: XGBoost ML Signal Layer

Trains a gradient-boosted classifier to predict whether the next 20 trading
days will be directionally favourable for a given asset. The output is a
probability score (0–1) that acts as an additional gate on top of Phase 4's
regime verdict and Phase 5's Kelly sizing.

Design principles:
  1. No lookahead — all features use only past data at each point in time.
  2. Time-aware split — training always ends at TRAIN_END (2021-01-01).
     Validation is strictly the test period (2021–present).
  3. Conservative model — shallow trees, high min_child_weight, L1/L2
     regularisation. Financial time series is noisy; overfitting is the
     primary failure mode.
  4. Fall back gracefully — if a model can't be trained (too few samples,
     no variance in target), return None so Phase 6 verdict is preserved.

Features (11 total, all normalised or bounded):
  Momentum:   ret_1m, ret_3m, ret_6m
  RSI:        rsi_14
  MACD:       macd_hist (normalised by price)
  BB:         bb_pos (0=lower band, 1=upper band), bb_width
  Trend:      ma200_slope, price_vs_ma200
  Volatility: vol_21 (ann.), vol_ratio (short/long)
  Regime:     drawdown, atr_pct
"""

import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

try:
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    print("  [Phase 7] xgboost or scikit-learn not found. "
          "Run: pip install xgboost scikit-learn")

LOOKFORWARD      = 20     # days ahead to predict (1 trading month)
MIN_TRAIN        = 200    # minimum training samples required
ML_PASS_THRESH   = 0.55   # probability above this → ML Gate = PASS


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def engineer_features(price: pd.Series,
                      ohlc: pd.DataFrame = None) -> pd.DataFrame:
    """
    Compute 11–12 technical features from a price series.
    All values use only data available at that point in time (no lookahead).
    Returns a DataFrame aligned to price.index, with rows dropped where
    any feature is NaN.
    """
    df = pd.DataFrame(index=price.index)
    daily = price.pct_change()

    # ── Momentum ──────────────────────────────────────────────────────────────
    df["ret_1m"] = price.pct_change(21)
    df["ret_3m"] = price.pct_change(63)
    df["ret_6m"] = price.pct_change(126)

    # ── RSI (14-day) ──────────────────────────────────────────────────────────
    delta = price.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi_14"] = (100 - (100 / (1 + rs))) / 100   # scale 0–1

    # ── MACD histogram (normalised by price) ──────────────────────────────────
    ema12 = price.ewm(span=12, adjust=False).mean()
    ema26 = price.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    sig   = macd.ewm(span=9, adjust=False).mean()
    df["macd_hist"] = (macd - sig) / price   # dimensionless

    # ── Bollinger Band position and width ─────────────────────────────────────
    sma20  = price.rolling(20).mean()
    std20  = price.rolling(20).std()
    upper  = sma20 + 2 * std20
    lower  = sma20 - 2 * std20
    bw     = (upper - lower).replace(0, np.nan)
    df["bb_pos"]   = (price - lower) / bw      # 0 = at lower band, 1 = at upper
    df["bb_width"] = bw / sma20                # relative band width

    # ── Trend (200-day MA) ────────────────────────────────────────────────────
    ma200 = price.rolling(200).mean()
    df["ma200_slope"]    = ma200.pct_change(20)       # 20-day slope of MA
    df["price_vs_ma200"] = (price / ma200) - 1        # % above/below MA

    # ── Volatility ────────────────────────────────────────────────────────────
    df["vol_21"]    = daily.rolling(21).std() * np.sqrt(252)
    df["vol_ratio"] = df["vol_21"] / (daily.rolling(63).std() * np.sqrt(252))

    # ── Drawdown from 252-day rolling high ────────────────────────────────────
    df["drawdown"] = (price / price.rolling(252).max()) - 1

    # ── ATR percentile (if OHLC available) ───────────────────────────────────
    if ohlc is not None and {"High", "Low", "Close"}.issubset(ohlc.columns):
        try:
            h, l, c = ohlc["High"], ohlc["Low"], ohlc["Close"]
            tr  = pd.concat([h - l,
                              (h - c.shift()).abs(),
                              (l - c.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            df["atr_pct"] = atr.rolling(252).rank(pct=True)
        except Exception:
            pass

    return df.dropna()


# ══════════════════════════════════════════════════════════════════════════════
#  TARGET VARIABLE
# ══════════════════════════════════════════════════════════════════════════════

def build_target(price: pd.Series,
                 lookforward: int = LOOKFORWARD) -> pd.Series:
    """
    Binary target: 1 if price is higher LOOKFORWARD days from now, else 0.
    Shift by -lookforward to align with current features (no lookahead).
    """
    fwd = price.pct_change(lookforward).shift(-lookforward)
    return (fwd > 0).astype(int)


# ══════════════════════════════════════════════════════════════════════════════
#  MODEL TRAINING
# ══════════════════════════════════════════════════════════════════════════════

def build_ml_model(price: pd.Series,
                   ohlc: pd.DataFrame = None,
                   train_end: str = "2021-01-01") -> tuple:
    """
    Train XGBoost on [start, train_end) and validate on [train_end, now].

    Returns:
        model         — trained XGBClassifier (or None if insufficient data)
        feature_names — list of feature column names used
        train_auc     — AUC on training set
        val_auc       — AUC on validation (test) set
    """
    if not XGB_AVAILABLE:
        return None, [], None, None

    features = engineer_features(price, ohlc)
    target   = build_target(price, LOOKFORWARD)

    common    = features.index.intersection(target.index)
    X         = features.loc[common]
    y         = target.loc[common]

    train_mask = X.index < pd.Timestamp(train_end)
    val_mask   = X.index >= pd.Timestamp(train_end)

    X_train, y_train = X[train_mask], y[train_mask]
    X_val,   y_val   = X[val_mask],   y[val_mask]

    if len(X_train) < MIN_TRAIN or y_train.nunique() < 2:
        return None, list(X.columns), None, None

    model = xgb.XGBClassifier(
        n_estimators     = 300,
        max_depth        = 3,        # shallow — resist memorisation
        learning_rate    = 0.03,
        subsample        = 0.8,
        colsample_bytree = 0.7,
        min_child_weight = 20,       # require 20+ samples per leaf
        gamma            = 1.0,      # minimum gain per split
        reg_alpha        = 0.5,      # L1 regularisation
        reg_lambda       = 2.0,      # L2 regularisation
        eval_metric      = "logloss",
        verbosity        = 0,
        random_state     = 42,
    )

    eval_set = [(X_val, y_val)] if len(X_val) >= 20 and y_val.nunique() > 1 else []
    model.fit(X_train, y_train,
              eval_set=eval_set,
              verbose=False)

    try:
        train_auc = roc_auc_score(y_train, model.predict_proba(X_train)[:, 1])
    except Exception:
        train_auc = None

    val_auc = None
    if len(X_val) >= 20 and y_val.nunique() > 1:
        try:
            val_auc = roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])
        except Exception:
            pass

    return model, list(X.columns), train_auc, val_auc


# ══════════════════════════════════════════════════════════════════════════════
#  SCORING + GATE
# ══════════════════════════════════════════════════════════════════════════════

def get_current_score(model, feature_names: list,
                      price: pd.Series,
                      ohlc: pd.DataFrame = None) -> float | None:
    """
    Score today's conditions using the trained model.
    Returns a probability (0–1) or None if scoring fails.
    """
    if model is None or not feature_names:
        return None
    try:
        features = engineer_features(price, ohlc)
        available = [f for f in feature_names if f in features.columns]
        if not available or features.empty:
            return None
        latest = features[available].dropna().iloc[[-1]]
        if latest.empty:
            return None
        prob = model.predict_proba(latest)[0, 1]
        return round(float(prob), 3)
    except Exception:
        return None


def ml_gate(score: float | None,
            threshold: float = ML_PASS_THRESH) -> str:
    """
    Convert ML probability score to a gate label.
    None score (no model) defaults to PASS so Phase 6 verdict is preserved.
    """
    if score is None:
        return "PASS"
    return "PASS" if score >= threshold else "HOLD"


def combined_verdict(phase6_verdict: str, gate: str) -> str:
    """
    Merge Phase 6 regime verdict with ML gate.
    STAND DOWN is always preserved — ML can only reduce trades, not create them.
    """
    if phase6_verdict == "STAND DOWN":
        return "STAND DOWN"
    if phase6_verdict == "TRADE" and gate == "PASS":
        return "TRADE"
    if phase6_verdict == "TRADE" and gate == "HOLD":
        return "ML HOLD"
    return phase6_verdict
