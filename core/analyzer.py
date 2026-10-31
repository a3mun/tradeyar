"""
core/analyzer.py
موتور تحلیل تکنیکال — نسخه ۱۲.۱ (فاز ۱۲.۶ — ai_export خام)
============================================================
🔴 تغییرات نسخه ۱۲.۱:
  ۱. MIN_CONF_TO_SHOW = 25 (نمایش «ضعیف» از ۲۵٪)
  ۲. TF_CONFIDENCE_OFFSET — آستانه دینامیک per TF
  ۳. TF_RR_PROFILES — R:R خام per TF (۱.۸۳ تا ۲.۳۳)
  ۴. TF_MIN_SL_PCT — حداقل فاصله SL per TF (بالاتر)
  ۵. _determine_signal — منطق «جهت + قدرت» جدا
  ۶. _is_boring_market — خنثی فقط وقتی بازار خوابه
  ۷. رفع باگ cmf (UnboundLocalError)
  ۸. ai_export واقعاً خام (OHLCV کامل + بدون جهت‌گیری)
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pandas_ta_classic as ta

logger = logging.getLogger(__name__)

# 🔴 نسخه analyzer
ANALYZER_VERSION = "12.1.0"

from .contracts import (
    Signal as SigEnum,
    TF_ATR_MULT,
    compute_net_rr,
    get_adaptive_thresholds,
    get_fee_rate,
    get_tf_atr_mult,
    get_tf_spec,
)
from .pre_breakout import detect_pre_breakout
from .utils import safe_num

# ═══════════════════════════════════════════════════════════
# ثابت‌های جدید (فاز ۱۲.۱)
# ═══════════════════════════════════════════════════════════
MIN_CONF_TO_SHOW = 25

TF_CONFIDENCE_OFFSET = {
    "۱ دقیقه": -10,
    "۵ دقیقه": -5,
    "۱۵ دقیقه": 0,
    "۳۰ دقیقه": 0,
    "۱ ساعت": +5,
    "روزانه": +10,
}

# 🔴 پروفایل R:R per TF
TF_RR_PROFILES = {
    "۱ دقیقه": {"sl_mult": 1.2, "tp_mult": 1.5},
    "۵ دقیقه": {"sl_mult": 1.3, "tp_mult": 1.8},
    "۱۵ دقیقه": {"sl_mult": 1.4, "tp_mult": 2.5},
    "۳۰ دقیقه": {"sl_mult": 1.5, "tp_mult": 3.3},
    "۱ ساعت": {"sl_mult": 1.6, "tp_mult": 3.8},
    "روزانه": {"sl_mult": 1.8, "tp_mult": 4.2},
}


def _get_tf_rr_profile(tf_name: str, profile_key: str) -> tuple[float, float]:
    tf_specs = TF_RR_PROFILES.get(tf_name)
    if tf_specs:
        return (tf_specs["sl_mult"], tf_specs["tp_mult"])
    return (1.3, 2.5)


CONFIDENCE_LEVELS = {
    "golden": (85, 100, "طلایی 💎", "golden"),
    "strong": (70, 84, "قوی", "strong"),
    "normal": (50, 69, "معمولی", "normal"),
    "weak": (25, 49, "ضعیف", "weak"),
    "neutral": (0, 24, "خنثی", "neutral"),
}

BORING_MARKET_ADX = 15
BORING_MARKET_VOL_RATIO = 0.7
BORING_MARKET_SCORE = 0.10
BORING_MARKET_NEUTRAL_VOTES = 4

RR_LOW_PENALTY = 0.7
RR_VERY_LOW_PENALTY = 0.5


# ═══════════════════════════════════════════════════════════
# پروفایل‌های ریسک
# ═══════════════════════════════════════════════════════════
RISK_PROFILES = {
    "aggressive_spot": {
        "name": "جسور (اسپات)",
        "sl_mult": 1.3,
        "tp_mult": 2.5,
        "min_confidence": 40,
        "min_votes_required": 2,
        "min_rr_net": 1.0,
        "min_adx": 0,
        "require_higher_tf": False,
        "color": "#DB6D28",
        "advice": "خرید در اسپات با حد ضرر. ۲-۳٪ سرمایه.",
        "leverage": None,
        "allow_short": False,
    },
    "aggressive_futures": {
        "name": "جسور (فیوچرز)",
        "sl_mult": 1.3,
        "tp_mult": 2.5,
        "min_confidence": 40,
        "min_votes_required": 2,
        "min_rr_net": 1.0,
        "min_adx": 0,
        "require_higher_tf": False,
        "color": "#DB6D28",
        "advice": "فیوچرز با اهرم ۲-۳x. حتماً حد ضرر.",
        "leverage": 3,
        "allow_short": True,
    },
    "conservative_spot": {
        "name": "محتاط (اسپات)",
        "sl_mult": 1.6,
        "tp_mult": 3.0,
        "min_confidence": 55,
        "min_votes_required": 3,
        "min_rr_net": 1.3,
        "min_adx": 18,
        "require_higher_tf": False,
        "color": "#3FB950",
        "advice": "خرید مطمئن در اسپات. ۱-۲٪ سرمایه.",
        "leverage": None,
        "allow_short": False,
    },
    "conservative_futures": {
        "name": "محتاط (فیوچرز)",
        "sl_mult": 1.6,
        "tp_mult": 3.0,
        "min_confidence": 55,
        "min_votes_required": 3,
        "min_rr_net": 1.3,
        "min_adx": 18,
        "require_higher_tf": False,
        "color": "#3FB950",
        "advice": "فیوچرز با اهرم ۱-۲x. با دقت وارد شو.",
        "leverage": 2,
        "allow_short": True,
    },
}

CONFIDENCE_TIERS = {
    "golden": (85, 100, "طلایی"),
    "strong": (70, 84, "قوی"),
    "normal": (50, 69, "معمولی"),
    "weak": (25, 49, "ضعیف"),
    "neutral": (0, 24, "خنثی"),
}


def _regime_weights(regime: str) -> dict:
    if regime == "trend":
        return {
            "momentum": 1.2,
            "trend": 1.8,
            "volatility": 0.9,
            "volume": 1.1,
            "structure": 1.0,
        }
    elif regime == "transitional":
        return {
            "momentum": 1.3,
            "trend": 1.3,
            "volatility": 1.0,
            "volume": 1.3,
            "structure": 1.2,
        }
    else:
        return {
            "momentum": 1.4,
            "trend": 0.9,
            "volatility": 1.1,
            "volume": 1.4,
            "structure": 1.3,
        }


def _confidence_tier(conf: int) -> str:
    for key in ["golden", "strong", "normal", "weak", "neutral"]:
        lo, hi, _ = CONFIDENCE_TIERS[key]
        if lo <= conf <= hi:
            return key
    return "neutral"


def _is_iranian_ticker(ticker: str) -> bool:
    if not ticker:
        return False
    upper = ticker.upper()
    return "IRT" in upper or "RLS" in upper or upper == "USDT-IRT"


def classify_regime(
    adx,
    channel_width_pct=None,
    bb_width_pct=None,
    volume_ratio=None,
    ema_slope=None,
    di_diff=None,
) -> str:
    if adx is None or adx <= 0:
        return "range"
    if adx >= 30:
        base = "trend"
    elif adx >= 22:
        base = "transitional"
    else:
        base = "range"
    if ema_slope is not None:
        if base == "trend" and abs(ema_slope) < 0.05:
            base = "transitional"
        elif base == "range" and abs(ema_slope) > 0.1:
            base = "transitional"
    if di_diff is not None and base == "trend" and abs(di_diff) < 5:
        base = "transitional"
    if (
        bb_width_pct is not None
        and bb_width_pct > 0
        and bb_width_pct < 0.5
        and base == "trend"
    ):
        base = "transitional"
    if (
        volume_ratio is not None
        and volume_ratio > 2.0
        and base == "range"
        and adx >= 18
    ):
        base = "transitional"
    return base


def _group_strength(score: float) -> tuple:
    a = abs(score)
    if a >= 0.6:
        return ("strong", "قوی")
    elif a >= 0.3:
        return ("normal", "متوسط")
    elif a >= 0.1:
        return ("weak", "ضعیف")
    else:
        return ("flat", "بی‌جهت")


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy(deep=True)
    n = len(df)

    try:
        if n >= 14:
            df["rsi"] = ta.rsi(df["close"], length=14)
            df["willr"] = ta.willr(df["high"], df["low"], df["close"], length=14)
            adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
            if adx_df is not None and len(adx_df.columns) >= 3:
                df["adx"] = adx_df.iloc[:, 0]
                df["dmp"] = adx_df.iloc[:, 1]
                df["dmn"] = adx_df.iloc[:, 2]
            else:
                df["adx"] = df["dmp"] = df["dmn"] = 20.0
        else:
            df["rsi"] = df["willr"] = 50.0
            df["adx"] = df["dmp"] = df["dmn"] = 20.0

        if n >= 20:
            df["cci"] = ta.cci(df["high"], df["low"], df["close"], length=20)
            stoch_df = ta.stoch(
                df["high"], df["low"], df["close"], k=5, d=3, smooth_k=3
            )
            if stoch_df is not None and len(stoch_df.columns) >= 2:
                df["stoch_k"] = stoch_df.iloc[:, 0]
                df["stoch_d"] = stoch_df.iloc[:, 1]
            else:
                df["stoch_k"] = df["stoch_d"] = 50.0
        else:
            df["cci"] = 0.0
            df["stoch_k"] = df["stoch_d"] = 50.0

        if n >= 10:
            df["roc"] = ta.roc(df["close"], length=10)
        else:
            df["roc"] = 0.0

        if n >= 200:
            df["ema200"] = ta.ema(df["close"], length=200)
        else:
            df["ema200"] = np.nan
        if n >= 50:
            df["ema50"] = ta.ema(df["close"], length=50)
        else:
            df["ema50"] = ta.ema(df["close"], length=min(n, 20))
        if n >= 20:
            df["ema20"] = ta.ema(df["close"], length=20)
        else:
            df["ema20"] = df["close"]

        if n >= 26:
            macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
            if macd_df is not None and len(macd_df.columns) >= 3:
                df["macd_hist"] = macd_df.iloc[:, 2]
            else:
                df["macd_hist"] = 0.0
        else:
            df["macd_hist"] = 0.0

        if n >= 14:
            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)
        else:
            df["atr"] = (df["high"] - df["low"]).rolling(5).mean().fillna(0)

        if n >= 20:
            bb_df = ta.bbands(df["close"], length=20, std=2)
            if bb_df is not None and len(bb_df.columns) >= 3:
                df["bb_lower"] = bb_df.iloc[:, 0]
                df["bb_mid"] = bb_df.iloc[:, 1]
                df["bb_upper"] = bb_df.iloc[:, 2]
            else:
                df["bb_lower"] = df["bb_mid"] = df["bb_upper"] = df["close"]
            df["bb_width_pct"] = (
                (df["bb_upper"] - df["bb_lower"])
                / df["bb_mid"].replace(0, np.nan)
                * 100
            )
        else:
            df["bb_lower"] = df["bb_mid"] = df["bb_upper"] = df["close"]
            df["bb_width_pct"] = 0.0

        if "volume" in df.columns and df["volume"].sum() > 0 and n >= 20:
            df["obv"] = ta.obv(df["close"], df["volume"])
            df["vol_ma"] = df["volume"].rolling(20).mean()
            try:
                df["cmf"] = ta.cmf(
                    df["high"], df["low"], df["close"], df["volume"], length=20
                )
            except:
                df["cmf"] = 0.0
            try:
                df["mfi"] = ta.mfi(
                    df["high"], df["low"], df["close"], df["volume"], length=14
                )
            except:
                df["mfi"] = 50.0
            df["buy_vol"] = 0.0
            df["sell_vol"] = 0.0
            valid_range = (df["high"] - df["low"]) > 0
            df.loc[valid_range, "buy_vol"] = (
                (df.loc[valid_range, "close"] - df.loc[valid_range, "low"])
                / (df.loc[valid_range, "high"] - df.loc[valid_range, "low"])
                * df.loc[valid_range, "volume"]
            )
            df.loc[valid_range, "sell_vol"] = (
                df.loc[valid_range, "volume"] - df.loc[valid_range, "buy_vol"]
            )
            df["delta"] = df["buy_vol"] - df["sell_vol"]
            df["cvd"] = df["delta"].cumsum()
            df["cvd_zscore"] = (df["cvd"] - df["cvd"].rolling(20).mean()) / df[
                "cvd"
            ].rolling(20).std().replace(0, np.nan)
            try:
                tp = (df["high"] + df["low"] + df["close"]) / 3
                df["vwap"] = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
            except:
                pass
        else:
            df["obv"] = 0
            df["vol_ma"] = 0
            df["cmf"] = 0.0
            df["mfi"] = 50.0
            df["delta"] = 0.0
            df["cvd"] = 0.0
            df["cvd_zscore"] = 0.0

        if n >= 10:
            try:
                st = ta.supertrend(
                    df["high"], df["low"], df["close"], length=10, multiplier=3.0
                )
                df["supertrend_dir"] = (
                    st.iloc[:, 1] if st is not None and st.shape[1] > 1 else 1
                )
            except Exception:
                df["supertrend_dir"] = 1
        else:
            df["supertrend_dir"] = 1

        if n >= 52:
            try:
                df["tenkan"] = (
                    df["high"].rolling(9).max() + df["low"].rolling(9).min()
                ) / 2
                df["kijun"] = (
                    df["high"].rolling(26).max() + df["low"].rolling(26).min()
                ) / 2
                df["senkou_a"] = ((df["tenkan"] + df["kijun"]) / 2).shift(26)
                df["senkou_b"] = (
                    (df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2
                ).shift(26)
            except Exception:
                pass

    except Exception as e:
        logger.warning(f"[Analyzer] compute_indicators: {e}")
    return df


def compute_pivot_points(df: pd.DataFrame) -> dict:
    if df is None or df.empty or len(df) < 2:
        return {}
    prev = df.iloc[-2]
    high = safe_num(prev.get("high"))
    low = safe_num(prev.get("low"))
    close = safe_num(prev.get("close"))
    if abs(high - low) < 1e-8:
        recent = df.iloc[-7:-2] if len(df) >= 7 else df.iloc[:-2]
        if not recent.empty:
            high = safe_num(recent["high"].max())
            low = safe_num(recent["low"].min())
            close = safe_num(recent["close"].iloc[-1])
    if high <= 0 or low <= 0 or close <= 0 or high <= low:
        return {}
    pivot = (high + low + close) / 3
    return {
        "pivot": pivot,
        "r1": 2 * pivot - low,
        "s1": 2 * pivot - high,
        "r2": pivot + (high - low),
        "s2": pivot - (high - low),
        "r3": high + 2 * (pivot - low),
        "s3": low - 2 * (high - pivot),
    }


def find_swing_points(df: pd.DataFrame, lookback: int = 50, window: int = 3) -> dict:
    result = {
        "swing_highs": [],
        "swing_lows": [],
        "nearest_resistance": 0.0,
        "nearest_support": 0.0,
        "strongest_resistance": 0.0,
        "strongest_support": 0.0,
    }
    if df is None or df.empty or len(df) < lookback:
        return result
    data = df.tail(lookback).reset_index(drop=True)
    highs = data["high"].values
    lows = data["low"].values
    n = len(data)
    current_price = safe_num(data["close"].iloc[-1])
    swing_highs = []
    swing_lows = []
    for i in range(window, n):
        h = highs[i]
        l = lows[i]
        if all(h >= highs[i - j] for j in range(1, window + 1)):
            swing_highs.append((i, float(h)))
        if all(l <= lows[i - j] for j in range(1, window + 1)):
            swing_lows.append((i, float(l)))
    result["swing_highs"] = swing_highs
    result["swing_lows"] = swing_lows
    res_above = [p for _, p in swing_highs if p > current_price]
    if res_above:
        result["nearest_resistance"] = min(res_above)
        result["strongest_resistance"] = max(res_above)
    elif swing_highs:
        result["nearest_resistance"] = max(p for _, p in swing_highs)
        result["strongest_resistance"] = result["nearest_resistance"]
    sup_below = [p for _, p in swing_lows if p < current_price]
    if sup_below:
        result["nearest_support"] = max(sup_below)
        result["strongest_support"] = min(sup_below)
    elif swing_lows:
        result["nearest_support"] = min(p for _, p in swing_lows)
        result["strongest_support"] = result["nearest_support"]
    return result


def compute_fibonacci(df: pd.DataFrame, lookback: int = 50) -> dict:
    if df is None or df.empty or len(df) < lookback:
        return {}
    data = df.tail(lookback)
    high = safe_num(data["high"].max())
    low = safe_num(data["low"].min())
    if high <= low:
        return {}
    diff = high - low
    return {
        "high": high,
        "low": low,
        "levels": {
            "0.0": high,
            "0.236": high - diff * 0.236,
            "0.382": high - diff * 0.382,
            "0.500": high - diff * 0.500,
            "0.618": high - diff * 0.618,
            "0.786": high - diff * 0.786,
            "1.0": low,
        },
    }


def _analyze_momentum(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons, signals = [], []
    last = df.iloc[-1]
    adx = safe_num(last.get("adx"), 20)
    is_trending = adx >= 25
    rsi = safe_num(last.get("rsi"), 50)
    if is_trending:
        if rsi >= 70:
            signals.append((+1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} مومنتوم قوی صعودی")
        elif rsi >= 60:
            signals.append((+0.6, 1.0))
            reasons.append(f"RSI={rsi:.0f} مومنتوم صعودی")
        elif rsi <= 30:
            signals.append((-1.0, 1.2))
            reasons.append(f"RSI={rsi:.0f} مومنتوم قوی نزولی")
        elif rsi <= 40:
            signals.append((-0.6, 1.0))
            reasons.append(f"RSI={rsi:.0f} مومنتوم نزولی")
        else:
            signals.append((0.0, 0.5))
    else:
        if rsi < 35:
            signals.append((+0.8, 1.0))
            reasons.append(f"RSI={rsi:.0f} نزدیک اشباع فروش")
        elif rsi > 65:
            signals.append((-0.8, 1.0))
            reasons.append(f"RSI={rsi:.0f} نزدیک اشباع خرید")
        elif rsi < 42:
            signals.append((+0.3, 0.6))
            reasons.append(f"RSI={rsi:.0f} متمایل به فروش")
        elif rsi > 58:
            signals.append((-0.3, 0.6))
            reasons.append(f"RSI={rsi:.0f} متمایل به خرید")
        else:
            signals.append((0.0, 0.5))
    stoch_k = safe_num(last.get("stoch_k"), 50)
    stoch_d = safe_num(last.get("stoch_d"), 50)
    if is_trending:
        if stoch_k > stoch_d and stoch_k > 50:
            signals.append((+0.7, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} کراس صعودی")
        elif stoch_k < stoch_d and stoch_k < 50:
            signals.append((-0.7, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} کراس نزولی")
        elif stoch_k > 80:
            signals.append((+0.5, 0.8))
        elif stoch_k < 20:
            signals.append((-0.5, 0.8))
        else:
            signals.append((0.0, 0.5))
    else:
        if stoch_k < 20 and stoch_d < 20:
            signals.append((+1.0, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} اشباع فروش")
        elif stoch_k > 80 and stoch_d > 80:
            signals.append((-1.0, 1.0))
            reasons.append(f"Stochastic={stoch_k:.0f} اشباع خرید")
        elif stoch_k > stoch_d and stoch_k < 50:
            signals.append((+0.3, 0.7))
        elif stoch_k < stoch_d and stoch_k > 50:
            signals.append((-0.3, 0.7))
        else:
            signals.append((0.0, 0.5))
    willr = safe_num(last.get("willr"), -50)
    if is_trending:
        if willr > -20:
            signals.append((+0.7, 0.9))
            reasons.append(f"Williams %R={willr:.0f} قدرت خریدار")
        elif willr < -80:
            signals.append((-0.7, 0.9))
            reasons.append(f"Williams %R={willr:.0f} قدرت فروشنده")
        else:
            signals.append((0.0, 0.5))
    else:
        if willr < -80:
            signals.append((+1.0, 0.9))
            reasons.append(f"Williams %R={willr:.0f} اشباع فروش")
        elif willr > -20:
            signals.append((-1.0, 0.9))
            reasons.append(f"Williams %R={willr:.0f} اشباع خرید")
        else:
            signals.append((0.0, 0.5))
    cci = safe_num(last.get("cci"), 0)
    if is_trending:
        if cci > 100:
            signals.append((+0.7, 0.9))
            reasons.append(f"CCI={cci:.0f} مومنتوم صعودی")
        elif cci < -100:
            signals.append((-0.7, 0.9))
            reasons.append(f"CCI={cci:.0f} مومنتوم نزولی")
        else:
            signals.append((0.0, 0.5))
    else:
        if cci < -100:
            signals.append((+0.8, 0.8))
            reasons.append(f"CCI={cci:.0f} اشباع فروش")
        elif cci > 100:
            signals.append((-0.8, 0.8))
            reasons.append(f"CCI={cci:.0f} اشباع خرید")
        else:
            signals.append((0.0, 0.5))
    roc = safe_num(last.get("roc"), 0)
    if roc > 2:
        signals.append((+0.6, 0.7))
        reasons.append(f"ROC={roc:.1f}% مومنتوم صعودی")
    elif roc < -2:
        signals.append((-0.6, 0.7))
        reasons.append(f"ROC={roc:.1f}% مومنتوم نزولی")
    elif roc > 0.5:
        signals.append((+0.3, 0.5))
    elif roc < -0.5:
        signals.append((-0.3, 0.5))
    else:
        signals.append((0.0, 0.5))
    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0
    mom_thr = _thresholds[0] if _thresholds else 0.25
    vote = +1 if score > mom_thr else (-1 if score < -mom_thr else 0)
    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "rsi": rsi,
            "stoch_k": stoch_k,
            "stoch_d": stoch_d,
            "willr": willr,
            "cci": cci,
            "roc": roc,
            "is_trending": is_trending,
            "adx_at_calc": adx,
        },
        "weight": 1.0,
    }


def _analyze_trend(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons, signals = [], []
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = safe_num(last["close"])
    ema200 = safe_num(last.get("ema200"))
    ema50 = safe_num(last.get("ema50"))
    ema20 = safe_num(last.get("ema20"))

    if not np.isnan(ema200) and ema200 > 0:
        prev_ema200 = safe_num(df["ema200"].iloc[-2]) if len(df) > 1 else ema200
        if price > ema200 and ema200 > prev_ema200:
            signals.append((+1.0, 1.2))
            reasons.append("قیمت بالای EMA200 با شیب صعودی")
        elif price < ema200 and ema200 < prev_ema200:
            signals.append((-1.0, 1.2))
            reasons.append("قیمت زیر EMA200 با شیب نزولی")
        else:
            signals.append((0.0, 0.5))
    elif ema50 > 0:
        prev_ema50 = safe_num(df["ema50"].iloc[-2]) if len(df) > 1 else ema50
        if price > ema50 and ema50 > prev_ema50:
            signals.append((+0.8, 1.2))
            reasons.append("قیمت بالای EMA50 (جایگزین)")
        elif price < ema50 and ema50 < prev_ema50:
            signals.append((-0.8, 1.2))
            reasons.append("قیمت زیر EMA50 (جایگزین)")
        else:
            signals.append((0.0, 0.5))

    if ema20 > 0 and ema50 > 0 and not np.isnan(ema200) and ema200 > 0:
        if ema20 > ema50 > ema200:
            signals.append((+0.8, 1.0))
            reasons.append("ترتیب صعودی EMA20>50>200")
        elif ema20 < ema50 < ema200:
            signals.append((-0.8, 1.0))
            reasons.append("ترتیب نزولی EMA20<50<200")

    macd_h = safe_num(last.get("macd_hist"))
    prev_macd_h = safe_num(prev.get("macd_hist"))
    if prev_macd_h <= 0 < macd_h:
        signals.append((+1.0, 1.3))
        reasons.append("MACD کراس صعودی")
    elif prev_macd_h >= 0 > macd_h:
        signals.append((-1.0, 1.3))
        reasons.append("MACD کراس نزولی")
    elif macd_h > 0:
        signals.append((+0.5, 0.9))
        reasons.append("MACD مثبت")
    elif macd_h < 0:
        signals.append((-0.5, 0.9))
        reasons.append("MACD منفی")
    else:
        signals.append((0.0, 0.5))

    adx = safe_num(last.get("adx"), 20)
    dmp = safe_num(last.get("dmp"), 20)
    dmn = safe_num(last.get("dmn"), 20)
    if adx > 40:
        reasons.append(f"ADX={adx:.0f} روند قوی")
    elif adx > 25:
        reasons.append(f"ADX={adx:.0f} روند نرمال")
    elif adx > 20:
        reasons.append(f"ADX={adx:.0f} روند ضعیف")
    else:
        reasons.append(f"ADX={adx:.0f} بدون روند")
    if dmp > dmn and adx > 20:
        signals.append((+0.9, 1.1))
        reasons.append(f"DI+={dmp:.0f} > DI-={dmn:.0f} صعودی")
    elif dmn > dmp and adx > 20:
        signals.append((-0.9, 1.1))
        reasons.append(f"DI-={dmn:.0f} > DI+={dmp:.0f} نزولی")

    st_dir = safe_num(last.get("supertrend_dir"), 1)
    if st_dir > 0:
        signals.append((+0.9, 1.1))
        reasons.append("Supertrend صعودی")
    elif st_dir < 0:
        signals.append((-0.9, 1.1))
        reasons.append("Supertrend نزولی")

    try:
        t_val = safe_num(last.get("tenkan"))
        k_val = safe_num(last.get("kijun"))
        sa_val = safe_num(last.get("senkou_a"))
        sb_val = safe_num(last.get("senkou_b"))
        if t_val > 0 and k_val > 0:
            if t_val > k_val and price > k_val:
                signals.append((+0.8, 0.9))
                reasons.append("Ichimoku: Tenkan > Kijun صعودی")
            elif t_val < k_val and price < k_val:
                signals.append((-0.8, 0.9))
                reasons.append("Ichimoku: Tenkan < Kijun نزولی")
        if sa_val > 0 and sb_val > 0:
            cloud_top = max(sa_val, sb_val)
            cloud_bottom = min(sa_val, sb_val)
            if price > cloud_top:
                signals.append((+0.6, 0.8))
                reasons.append("Ichimoku: قیمت بالای ابر صعودی")
            elif price < cloud_bottom:
                signals.append((-0.6, 0.8))
                reasons.append("Ichimoku: قیمت زیر ابر نزولی")
    except Exception:
        pass

    try:
        swings = find_swing_points(df, lookback=50, window=3)
        swing_highs = swings.get("swing_highs", [])
        swing_lows = swings.get("swing_lows", [])
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            recent_highs = [p for _, p in swing_highs[-2:]]
            recent_lows = [p for _, p in swing_lows[-2:]]
            hh = recent_highs[-1] > recent_highs[-2]
            hl = recent_lows[-1] > recent_lows[-2]
            lh = recent_highs[-1] < recent_highs[-2]
            ll = recent_lows[-1] < recent_lows[-2]
            if hh and hl:
                signals.append((+1.0, 1.2))
                reasons.append("ساختار HH/HL صعودی")
            elif lh and ll:
                signals.append((-1.0, 1.2))
                reasons.append("ساختار LH/LL نزولی")
    except Exception:
        pass

    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0
    t_thr = _thresholds[1] if _thresholds else 0.30
    vote = +1 if score > t_thr else (-1 if score < -t_thr else 0)
    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "ema200": ema200,
            "ema50": ema50,
            "ema20": ema20,
            "macd_hist": macd_h,
            "adx": adx,
            "dmp": dmp,
            "dmn": dmn,
            "supertrend_dir": st_dir,
        },
        "weight": 1.0,
    }


def _analyze_volatility(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons = []
    last = df.iloc[-1]
    price = safe_num(last["close"])
    bb_upper = safe_num(last.get("bb_upper"))
    bb_lower = safe_num(last.get("bb_lower"))
    bb_mid = safe_num(last.get("bb_mid"))
    if bb_upper > 0 and bb_lower > 0:
        if price <= bb_lower * 1.005:
            reasons.append("نزدیک باند پایین Bollinger")
        elif price >= bb_upper * 0.995:
            reasons.append("نزدیک باند بالا Bollinger")
    atr = safe_num(last.get("atr"))
    if atr > 0 and price > 0:
        atr_pct = (atr / price) * 100
        reasons.append(f"ATR={atr_pct:.2f}% نوسان")
    kc_upper = safe_num(last.get("kc_upper"))
    kc_lower = safe_num(last.get("kc_lower"))
    if kc_upper > 0 and kc_lower > 0:
        if price <= kc_lower * 1.005:
            reasons.append("نزدیک کانال پایین Keltner")
        elif price >= kc_upper * 0.995:
            reasons.append("نزدیک کانال بالای Keltner")
    dc_upper = safe_num(last.get("dc_upper"))
    dc_lower = safe_num(last.get("dc_lower"))
    if dc_upper > 0 and dc_lower > 0:
        if price >= dc_upper * 0.998:
            reasons.append("نزدیک سقف Donchian")
        elif price <= dc_lower * 1.002:
            reasons.append("نزدیک کف Donchian")
    stddev = safe_num(last.get("stddev"))
    if stddev > 0 and price > 0:
        cv = (stddev / price) * 100
        if cv > 3:
            reasons.append(f"نوسان بالا (StdDev={cv:.2f}%)")
        elif cv < 1:
            reasons.append(f"نوسان کم (StdDev={cv:.2f}%)")
    return {
        "vote": 0,
        "score": 0.0,
        "reasons": reasons,
        "details": {
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "atr": atr,
            "kc_upper": kc_upper,
            "kc_lower": kc_lower,
            "dc_upper": dc_upper,
            "dc_lower": dc_lower,
            "stddev": stddev,
        },
        "weight": 1.0,
    }


def _analyze_volume(
    df: pd.DataFrame,
    market_type: str = "spot",
    _thresholds: tuple = None,
    orderbook: dict = None,
    regime: str = "range",
) -> dict:
    reasons, signals = [], []
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = safe_num(last["close"])
    ob_details = {}
    if orderbook and orderbook.get("imbalance") is not None:
        from .orderbook import imbalance_vote

        imb = float(orderbook["imbalance"])
        ob_vote, ob_score = imbalance_vote(imb)
        pressure = orderbook.get("pressure_fa", "")
        ob_details = {
            "imbalance": imb,
            "spread_pct": orderbook.get("spread_pct"),
            "pressure_fa": pressure,
            "best_bid": orderbook.get("best_bid"),
            "best_ask": orderbook.get("best_ask"),
            "wall": orderbook.get("wall"),
        }
        if ob_vote != 0:
            signals.append((ob_score * 0.8, 0.4))
            reasons.append(f"عمق بازار: {pressure} (imbalance={imb:.2f})")
        wall = orderbook.get("wall")
        if wall:
            side_fa = "خرید" if wall["side"] == "bid" else "فروش"
            reasons.append(
                f"🧱 دیوار سفارش {side_fa} در {wall['price']:,.2f} ({wall['ratio']:.1f}x)"
            )
        sp = orderbook.get("spread_pct") or 0
        if sp > 0.5:
            reasons.append(f"⚠️ اسپرد {sp:.2f}٪ — نقدینگی ضعیف")
    has_volume = "volume" in df.columns and df["volume"].sum() > 0
    if not has_volume:
        total_w = sum(w for _, w in signals)
        score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0
        o_thr = _thresholds[2] if _thresholds else 0.25
        vote = +1 if score > o_thr else (-1 if score < -o_thr else 0)
        return {
            "vote": vote,
            "score": round(score, 3),
            "reasons": reasons or ["حجم در دسترس نیست"],
            "details": {**ob_details, "has_volume": False},
            "weight": 1.0,
        }
    obv_last = safe_num(last.get("obv"))
    obv_prev = safe_num(prev.get("obv"))
    if obv_last > obv_prev:
        signals.append((+0.5, 0.9))
        reasons.append("OBV صعودی")
    elif obv_last < obv_prev:
        signals.append((-0.5, 0.9))
        reasons.append("OBV نزولی")
    vol = safe_num(last.get("volume"))
    vol_ma = safe_num(last.get("vol_ma"))
    vol_ratio = vol / vol_ma if vol_ma > 0 else 1.0
    if vol_ma > 0:
        if vol_ratio > 1.5:
            reasons.append(f"حجم بالا ({vol_ratio:.1f}x)")
            close_last = safe_num(last["close"])
            close_prev = safe_num(prev["close"])
            if close_last > close_prev:
                signals.append((+0.6, 0.8))
            else:
                signals.append((-0.6, 0.8))
        elif vol_ratio < 0.5:
            reasons.append(f"حجم کم ({vol_ratio:.1f}x)")
    cmf = safe_num(last.get("cmf"), 0)
    if "cvd" in df.columns:
        cvd_last = safe_num(last.get("cvd"))
        cvd_prev = safe_num(prev.get("cvd"))
        delta_last = safe_num(last.get("delta"))
        if cvd_last > cvd_prev:
            signals.append((+0.5, 0.9))
            reasons.append("CVD صعودی")
        elif cvd_last < cvd_prev:
            signals.append((-0.5, 0.9))
            reasons.append("CVD نزولی")
        if delta_last > 0:
            signals.append((+0.4, 0.8))
        elif delta_last < 0:
            signals.append((-0.4, 0.8))
        cvd_z = safe_num(last.get("cvd_zscore"), 0)
        if regime == "trend":
            if cvd_z > 2.5:
                signals.append((-0.5, 0.7))
                reasons.append(f"CVD Z-Score={cvd_z:.1f} اشباع خرید")
            elif cvd_z < -2.5:
                signals.append((+0.5, 0.7))
                reasons.append(f"CVD Z-Score={cvd_z:.1f} اشباع فروش")
        else:
            if cvd_z > 3.0:
                signals.append((-0.3, 0.5))
            elif cvd_z < -3.0:
                signals.append((+0.3, 0.5))
    if cmf > 0.1:
        signals.append((+0.7, 1.0))
        reasons.append(f"CMF={cmf:.2f} ورودی")
    elif cmf < -0.1:
        signals.append((-0.7, 1.0))
        reasons.append(f"CMF={cmf:.2f} خروجی")
    mfi = safe_num(last.get("mfi"), 50)
    if mfi < 20:
        signals.append((+0.8, 1.0))
        reasons.append(f"MFI={mfi:.0f} اشباع فروش")
    elif mfi > 80:
        signals.append((-0.8, 1.0))
        reasons.append(f"MFI={mfi:.0f} اشباع خرید")
    if "vwap" in df.columns:
        vwap = safe_num(last.get("vwap"))
        if vwap > 0:
            if price > vwap * 1.02:
                signals.append((-0.4, 0.7))
                reasons.append("قیمت بالای VWAP")
            elif price < vwap * 0.98:
                signals.append((+0.4, 0.7))
                reasons.append("قیمت زیر VWAP")
    if "volume" in df.columns and vol_ma > 0:
        candle_range = safe_num(last["high"]) - safe_num(last["low"])
        if candle_range > 0:
            upper_wick = safe_num(last["high"]) - max(
                safe_num(last["close"]), safe_num(last["open"])
            )
            lower_wick = min(
                safe_num(last["close"]), safe_num(last["open"])
            ) - safe_num(last["low"])
            vol_spike = vol > vol_ma * 1.5
            if vol_spike and lower_wick / candle_range > 0.66:
                signals.append((+0.9, 1.3))
                reasons.append("Absorption صعودی")
            elif vol_spike and upper_wick / candle_range > 0.66:
                signals.append((-0.9, 1.3))
                reasons.append("Absorption نزولی")
    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0
    o_thr = _thresholds[2] if _thresholds else 0.25
    vote = +1 if score > o_thr else (-1 if score < -o_thr else 0)
    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "obv": obv_last,
            "vol_ratio": vol_ratio,
            "cmf": cmf,
            "mfi": mfi,
            "cvd": safe_num(last.get("cvd")),
            "delta": safe_num(last.get("delta")),
            **ob_details,
        },
        "weight": 1.0,
    }


def _analyze_structure(df: pd.DataFrame, _thresholds: tuple = None) -> dict:
    reasons, signals = [], []
    last = df.iloc[-1]
    price = safe_num(last["close"])
    pivots = compute_pivot_points(df)
    swings = find_swing_points(df, lookback=50, window=3)
    fib = compute_fibonacci(df, lookback=50)
    if pivots:
        r1 = pivots.get("r1", 0)
        s1 = pivots.get("s1", 0)
        if r1 > 0 and price >= r1 * 0.995:
            signals.append((-0.6, 1.0))
            reasons.append("نزدیک R1")
        elif s1 > 0 and price <= s1 * 1.005:
            signals.append((+0.6, 1.0))
            reasons.append("نزدیک S1")
    nearest_r = swings.get("nearest_resistance", 0)
    nearest_s = swings.get("nearest_support", 0)
    if nearest_r > 0 and price > 0:
        dist_r = (nearest_r - price) / price * 100
        if dist_r < 0.5:
            signals.append((-0.8, 1.2))
            reasons.append("نزدیک مقاومت Swing")
    if nearest_s > 0 and price > 0:
        dist_s = (price - nearest_s) / price * 100
        if dist_s < 0.5:
            signals.append((+0.8, 1.2))
            reasons.append("نزدیک حمایت Swing")
    if fib and fib.get("levels"):
        levels = fib["levels"]
        for ratio in ["0.618", "0.500", "0.382"]:
            fib_price = levels.get(ratio, 0)
            if fib_price > 0 and abs(price - fib_price) / price < 0.005:
                signals.append((+0.4, 0.8))
                reasons.append(f"نزدیک Fibonacci {ratio}")
                break
    total_w = sum(w for _, w in signals)
    score = sum(s * w for s, w in signals) / total_w if total_w > 0 else 0.0
    o_thr = _thresholds[2] if _thresholds else 0.30
    vote = +1 if score > o_thr else (-1 if score < -o_thr else 0)
    return {
        "vote": vote,
        "score": round(score, 3),
        "reasons": reasons,
        "details": {
            "pivots": pivots,
            "swings": swings,
            "fibonacci": fib,
            "nearest_resistance": nearest_r,
            "nearest_support": nearest_s,
        },
        "weight": 1.0,
    }


def _detect_divergence(momentum: dict, volume: dict) -> dict:
    m_vote, v_vote = momentum.get("vote", 0), volume.get("vote", 0)
    m_score, v_score = momentum.get("score", 0.0), volume.get("score", 0.0)
    result = {"has_divergence": False, "type": None, "penalty": 0, "reason": ""}
    if m_vote > 0 and v_vote < 0 and abs(v_score) > 0.3:
        result.update(
            {
                "has_divergence": True,
                "type": "bull_trap",
                "penalty": 5,
                "reason": f"⚠️ واگرایی: مومنتوم صعودی ({m_score:+.2f}) ولی حجم خروجی ({v_score:+.2f})",
            }
        )
    elif m_vote < 0 and v_vote > 0 and abs(v_score) > 0.3:
        result.update(
            {
                "has_divergence": True,
                "type": "bear_trap",
                "penalty": 5,
                "reason": f"⚠️ واگرایی: مومنتوم نزولی ({m_score:+.2f}) ولی حجم ورودی ({v_score:+.2f})",
            }
        )
    return result


def _detect_traps(groups: dict, price: float, atr: float) -> dict:
    traps = {
        "bull_trap": {"active": False, "reason": "", "severity": 0},
        "bear_trap": {"active": False, "reason": "", "severity": 0},
        "fake_breakout": {"active": False, "reason": "", "severity": 0},
        "exhaustion": {"active": False, "reason": "", "severity": 0},
    }
    if not groups:
        return traps
    m, t, v, s, vol = (
        groups.get("momentum", {}),
        groups.get("trend", {}),
        groups.get("volume", {}),
        groups.get("structure", {}),
        groups.get("volatility", {}),
    )
    m_score, v_score, s_score, vol_score = (
        m.get("score", 0.0),
        v.get("score", 0.0),
        s.get("score", 0.0),
        vol.get("score", 0.0),
    )
    t_details, v_details = t.get("details", {}), v.get("details", {})
    adx, vol_ratio = t_details.get("adx", 20), v_details.get("vol_ratio", 1.0)
    if m_score > 0.45 and v_score < -0.35 and s_score < -0.25:
        traps["bull_trap"].update(
            {
                "active": True,
                "reason": f"⚡ مومنتوم صعودی ({m_score:+.2f}) ولی حجم خروجی ({v_score:+.2f})",
                "severity": 8,
            }
        )
    if m_score < -0.45 and v_score > 0.35 and s_score > 0.25:
        traps["bear_trap"].update(
            {
                "active": True,
                "reason": f"⚡ مومنتوم نزولی ({m_score:+.2f}) ولی حجم ورودی ({v_score:+.2f})",
                "severity": 8,
            }
        )
    if adx > 30 and vol_ratio < 0.6:
        if s_score < -0.30:
            traps["fake_breakout"].update(
                {
                    "active": True,
                    "reason": f"📉 ADX={adx:.0f} حجم کم {vol_ratio:.1f}x + نزدیک مقاومت",
                    "severity": 7,
                }
            )
        elif s_score > 0.30:
            traps["fake_breakout"].update(
                {
                    "active": True,
                    "reason": f"📈 ADX={adx:.0f} حجم کم {vol_ratio:.1f}x + نزدیک حمایت",
                    "severity": 7,
                }
            )
    if adx > 45 and abs(m_score) < 0.25 and abs(vol_score) > 0.3:
        traps["exhaustion"].update(
            {
                "active": True,
                "reason": f"😮‍💨 ADX={adx:.0f} مومنتوم ضعیف ({m_score:+.2f}) — خستگی",
                "severity": 6,
            }
        )
    return traps


def _traps_summary(traps: dict) -> dict:
    active = [k for k, v in traps.items() if v.get("active")]
    max_severity = max((v.get("severity", 0) for v in traps.values()), default=0)
    return {
        "active_count": len(active),
        "active_names": active,
        "max_severity": max_severity,
        "has_high_risk": max_severity >= 7,
        "has_warning": max_severity >= 5,
    }


def build_scenarios(
    price,
    atr,
    groups,
    support,
    resistance,
    regime,
    direction="neutral",
    traps=None,
    ticker="",
) -> list[dict]:
    scenarios = []
    if not groups:
        return scenarios
    is_iranian = _is_iranian_ticker(ticker)
    is_tsetmc = bool(ticker) and not ticker[0].isascii()
    unit = "ریال" if is_tsetmc else ("تومان" if is_iranian else "$")
    m, t, v = (
        groups.get("momentum", {}),
        groups.get("trend", {}),
        groups.get("volume", {}),
    )
    m_score, v_score = m.get("score", 0.0), v.get("score", 0.0)
    m_details, t_details = m.get("details", {}), t.get("details", {})
    rsi, adx = m_details.get("rsi", 50), t_details.get("adx", 20)

    def _fmt(val):
        return f"{val:,.0f} {unit}" if is_iranian else f"${val:,.2f}"

    if regime == "trend" and adx > 35 and price > 0 and atr > 0:
        if direction == "neutral" and m_score < 0.3 and v_score < 0.3:
            sl = price - atr * 1.2
            scenarios.append(
                {
                    "condition": f"اگه حجم بالاتر بره و RSI از {rsi:.0f} بالاتر بره",
                    "action": f"ورود LONG — SL={_fmt(sl)}",
                    "probability": 0.55,
                    "color": "green",
                    "type": "entry",
                    "icon": "🟢",
                }
            )
        elif direction == "long":
            sl, tp = price - atr * 1.2, price + atr * 3.0
            scenarios.append(
                {
                    "condition": "اگه حجم تأیید کنه و RSI بالای ۵۰ بره",
                    "action": f"LONG با SL={_fmt(sl)} · TP={_fmt(tp)}",
                    "probability": 0.65,
                    "color": "green",
                    "type": "entry",
                    "icon": "🟢",
                }
            )
    if resistance > 0 and price > 0:
        dist_r = (resistance - price) / price * 100
        if dist_r < 1.5:
            scenarios.append(
                {
                    "condition": f"اگه قیمت از R ({_fmt(resistance)}) رد نشه",
                    "action": "مراقب باش",
                    "probability": 0.55,
                    "color": "red",
                    "type": "reversal",
                    "icon": "🔴",
                }
            )
        elif dist_r < 3.0:
            scenarios.append(
                {
                    "condition": f"اگه قیمت با حجم بالا از {_fmt(resistance)} رد بشه",
                    "action": "ورود LONG بعد از تأیید حجم",
                    "probability": 0.50,
                    "color": "green",
                    "type": "breakout",
                    "icon": "🚀",
                }
            )
    if support > 0 and price > 0:
        dist_s = (price - support) / price * 100
        if dist_s < 1.5:
            scenarios.append(
                {
                    "condition": f"اگه قیمت به حمایت ({_fmt(support)}) برسه",
                    "action": "فرصت خرید — SL زیر حمایت",
                    "probability": 0.60,
                    "color": "green",
                    "type": "entry",
                    "icon": "💚",
                }
            )
    if traps and traps.get("fake_breakout", {}).get("active"):
        scenarios.append(
            {
                "condition": "اگه قیمت سریع برگرده داخل محدوده",
                "action": "شکست جعلیه — منتظر تأیید بمون",
                "probability": 0.70,
                "color": "yellow",
                "type": "warning",
                "icon": "⚠️",
            }
        )
    if traps and traps.get("bull_trap", {}).get("active"):
        scenarios.append(
            {
                "condition": "اگه قیمت ناگهان برگرده پایین",
                "action": "تله صعودیه — وارد LONG نشو",
                "probability": 0.65,
                "color": "red",
                "type": "warning",
                "icon": "🚨",
            }
        )
    if traps and traps.get("bear_trap", {}).get("active"):
        scenarios.append(
            {
                "condition": "اگه قیمت ناگهان برگرده بالا",
                "action": "تله نزولیه — وارد SHORT نشو",
                "probability": 0.65,
                "color": "red",
                "type": "warning",
                "icon": "🚨",
            }
        )
    if len(scenarios) < 2:
        scenarios.append(
            {
                "condition": "اگه شرایط فعلی ادامه داشته باشه",
                "action": "صبر کن — سیگنال واضحی نداره",
                "probability": 0.70,
                "color": "yellow",
                "type": "wait",
                "icon": "⏸",
            }
        )
    scenarios.sort(key=lambda x: -x["probability"])
    return scenarios[:3]


def _apply_trend_override(
    direction: str, aggregate: dict, groups: dict, regime: str
) -> tuple[str, int, str]:
    trend = groups.get("trend", {}) or {}
    trend_details = trend.get("details", {})
    trend_score = trend.get("score", 0.0)
    adx = trend_details.get("adx", 0)
    dmp = trend_details.get("dmp", 0)
    dmn = trend_details.get("dmn", 0)
    STRONG_TREND = 0.65
    MEDIUM_TREND = 0.45
    trend_bull = trend_score >= STRONG_TREND and adx > 20 and dmp > dmn
    trend_bear = trend_score <= -STRONG_TREND and adx > 20 and dmn > dmp
    if trend_bull and direction == "short":
        return (
            "neutral",
            0,
            f"🚫 SHORT بلاک شد — روند قوی صعودی (ADX={adx:.0f}, DI+ > DI-)",
        )
    if trend_bear and direction == "long":
        return (
            "neutral",
            0,
            f"🚫 LONG بلاک شد — روند قوی نزولی (ADX={adx:.0f}, DI- > DI+)",
        )
    if trend_score >= MEDIUM_TREND and direction == "short":
        return direction, 25, "⚠️ روند صعودی متوسط ولی SHORT"
    if trend_score <= -MEDIUM_TREND and direction == "long":
        return direction, 25, "⚠️ روند نزولی متوسط ولی LONG"
    return direction, 0, ""


def _aggregate_votes(
    groups: dict,
    regime: str,
    profile: str,
    adx: float,
    market_type: str = "spot",
    tf_hint: str = "۵ دقیقه",
) -> dict:
    weights = _regime_weights(regime)
    weighted_sum, total_weight = 0.0, 0.0
    votes_long, votes_short, votes_neutral = 0, 0, 0
    groups_summary = {}
    for group_name, result in groups.items():
        if result is None:
            continue
        w = weights.get(group_name, 1.0)
        vote = result.get("vote", 0)
        score = result.get("score", 0.0)
        weighted_sum += score * w
        total_weight += w
        if vote > 0:
            votes_long += 1
        elif vote < 0:
            votes_short += 1
        else:
            votes_neutral += 1
        strength_key, strength_fa = _group_strength(score)
        groups_summary[group_name] = {
            "vote": vote,
            "score": score,
            "weight": w,
            "strength": strength_key,
            "strength_fa": strength_fa,
            "reasons": result.get("reasons", []),
        }
    final_score = weighted_sum / total_weight if total_weight > 0 else 0.0
    if regime == "trend":
        final_score *= 1.2
    elif regime == "range":
        final_score *= 0.85
    profile_key = f"{profile}_{market_type}"
    profile_cfg = RISK_PROFILES.get(
        profile_key,
        RISK_PROFILES.get(f"{profile}_spot", RISK_PROFILES["aggressive_spot"]),
    )

    # 🔴 جهت بر اساس weighted_sum (وزن‌ها واقعاً اثر می‌گذارند)
    WEIGHTED_DIR_THRESHOLD = 0.15
    if final_score > WEIGHTED_DIR_THRESHOLD:
        weighted_direction = "long"
    elif final_score < -WEIGHTED_DIR_THRESHOLD:
        weighted_direction = "short"
    else:
        weighted_direction = "neutral"

    if tf_hint in ("۱ دقیقه", "۵ دقیقه"):
        _tf_threshold = 1
    elif tf_hint in ("۱۵ دقیقه", "۳۰ دقیقه"):
        _tf_threshold = 2
    else:
        _tf_threshold = 2
    min_votes = profile_cfg.get("min_votes_required", _tf_threshold)
    required_votes = max(min_votes, _tf_threshold)
    min_adx = profile_cfg.get("min_adx", 0)
    adx_ok = adx >= min_adx
    if profile == "aggressive":
        if weighted_direction == "long" and votes_long >= required_votes:
            direction = "long"
            consensus = (
                "weak"
                if votes_long <= required_votes
                else ("normal" if votes_long <= required_votes + 1 else "strong")
            )
        elif weighted_direction == "short" and votes_short >= required_votes:
            direction = "short"
            consensus = (
                "weak"
                if votes_short <= required_votes
                else ("normal" if votes_short <= required_votes + 1 else "strong")
            )
        else:
            direction, consensus = "neutral", "neutral"
    else:
        if not adx_ok:
            direction, consensus = "neutral", "neutral"
        elif weighted_direction == "long" and votes_long >= required_votes:
            direction = "long"
            consensus = "normal" if votes_long == required_votes else "strong"
        elif weighted_direction == "short" and votes_short >= required_votes:
            direction = "short"
            consensus = "normal" if votes_short == required_votes else "strong"
        else:
            direction, consensus = "neutral", "neutral"
    if market_type == "spot" and direction == "short":
        direction, consensus = "neutral", "neutral"
    direction, penalty, override_reason = _apply_trend_override(
        direction, {"final_score": final_score}, groups, regime
    )

    return {
        "final_score": round(final_score, 3),
        "votes_long": votes_long,
        "votes_short": votes_short,
        "votes_neutral": votes_neutral,
        "consensus": consensus,
        "direction": direction,
        "required_votes": required_votes,
        "adx_ok": adx_ok,
        "groups_summary": groups_summary,
        "override_reason": override_reason,
        "override_penalty_pct": penalty,
    }


def _compute_confidence(
    aggregate: dict, adx: float, divergence: dict, groups: dict = None
) -> int:
    consensus = aggregate.get("consensus", "neutral")
    direction = aggregate.get("direction", "neutral")
    votes_long, votes_short = aggregate.get("votes_long", 0), aggregate.get(
        "votes_short", 0
    )
    final_score = aggregate.get("final_score", 0.0)
    if direction == "neutral" or consensus == "neutral":
        return 0
    base_map = {"strong": 45, "normal": 32, "weak": 18}
    base = base_map.get(consensus, 0)
    quality = 0
    quality += min(15, abs(final_score) * 20)
    if adx > 40:
        quality += 8
    elif adx > 30:
        quality += 5
    elif adx > 25:
        quality += 2
    elif adx < 18:
        quality -= 5
    if groups:
        t_score = groups.get("trend", {}).get("score", 0.0)
        m_score = groups.get("momentum", {}).get("score", 0.0)
        v_score = groups.get("volume", {}).get("score", 0.0)
        if direction == "long":
            if t_score > 0.3 and m_score > 0.3 and v_score > 0.2:
                quality += 12
            elif t_score > 0.3 and m_score > 0.2:
                quality += 8
            elif t_score > 0.3 or m_score > 0.3:
                quality += 4
        elif direction == "short":
            if t_score < -0.3 and m_score < -0.3 and v_score < -0.2:
                quality += 12
            elif t_score < -0.3 and m_score < -0.2:
                quality += 8
            elif t_score < -0.3 or m_score < -0.3:
                quality += 4
    quality = max(0, min(35, quality))
    majority = votes_long if direction == "long" else votes_short
    agreement = 0
    if majority >= 4:
        agreement = 15
    elif majority == 3:
        agreement = 10
    elif majority == 2:
        agreement = 5
    confidence = base + quality + agreement
    if divergence.get("has_divergence"):
        confidence -= divergence.get("penalty", 0)
    override_penalty = aggregate.get("override_penalty_pct", 0)
    if override_penalty > 0:
        confidence = int(confidence * (1 - override_penalty / 100))
    return max(0, min(100, int(confidence)))


def _explain_neutral(
    aggregate,
    regime,
    divergence,
    market_type="spot",
    tfs_data=None,
    current_tf=None,
    traps=None,
) -> dict:
    votes_long, votes_short, votes_neutral = (
        aggregate.get("votes_long", 0),
        aggregate.get("votes_short", 0),
        aggregate.get("votes_neutral", 0),
    )
    override_reason = aggregate.get("override_reason", "")
    short_msg = (
        "🚫 روند قوی — سیگنال مخالف بلاک شد"
        if override_reason
        else (
            f"⚪ بدون سیگنال — {votes_neutral} گروه خنثی"
            if votes_neutral >= 3
            else (
                "⚪ تعادل گروه‌ها"
                if votes_long == votes_short and votes_long > 0
                else "⚪ بدون سیگنال معتبر"
            )
        )
    )
    reasons = []
    if override_reason:
        reasons.append(override_reason)
    if regime == "range":
        reasons.append("بازار در رژیم «رنج» هست")
    elif regime == "transitional":
        reasons.append("بازار در حالت «گذار» هست")
    elif regime == "trend":
        reasons.append("بازار روند داره ولی گروه‌ها هم‌جهت نیستن")
    if votes_neutral >= 3:
        reasons.append(f"{votes_neutral} از ۵ گروه خنثی موندن")
    if votes_long == votes_short and votes_long > 0:
        reasons.append(
            f"{votes_long} گروه صعودی مقابل {votes_short} گروه نزولی — تعادل"
        )
    if divergence.get("has_divergence"):
        reasons.append("واگرایی مومنتوم/حجم دیده می‌شه")
    if market_type == "spot" and votes_short > votes_long:
        reasons.append("در اسپات فقط خرید مجاز است")
    if not reasons:
        reasons.append("شرایط بازار نامشخصه")
    hint = None
    if tfs_data and current_tf:
        higher_tfs = [
            f"{htf} ({r.get('signal')} · {r.get('confidence')}%)"
            for htf in ["۱ ساعت", "روزانه"]
            if htf != current_tf
            and (r := tfs_data.get(htf))
            and SigEnum.is_directional(r.get("signal", ""))
        ]
        if higher_tfs:
            hint = "💡 TF بالاتر سیگنال داره: " + " | ".join(higher_tfs)
    if traps:
        active_traps = [
            traps[t].get("reason", "") for t in traps if traps[t].get("active")
        ]
        if active_traps:
            hint = (
                (hint + "\n🚨 هشدار: " + " | ".join(active_traps))
                if hint
                else ("🚨 هشدار: " + " | ".join(active_traps))
            )
    return {
        "short": short_msg,
        "long": " • ".join(reasons),
        "hint": hint,
        "traps": traps or {},
    }


def _is_boring_market(
    aggregate: dict, adx: float, vol_ratio: float, final_score: float
) -> bool:
    votes_neutral = aggregate.get("votes_neutral", 0)
    return (
        votes_neutral >= BORING_MARKET_NEUTRAL_VOTES
        and adx < BORING_MARKET_ADX
        and vol_ratio < BORING_MARKET_VOL_RATIO
        and abs(final_score) < BORING_MARKET_SCORE
    )


def _determine_signal(
    direction: str,
    confidence: int,
    tier: str,
    min_conf: int,
    tf_name: str,
    is_boring: bool,
    allow_short: bool,
    market_type: str,
) -> tuple[str, str, str]:

    # 🔴 ۱. از ۰ تا ۱۵: خنثی
    if confidence < 15:
        return ("خنثی", f"بدون سیگنال ({confidence}٪)", "⚪ صبر کن")

    # 🔴 ۲. از ۱۵ تا ۳۰: دور
    if confidence < 30:
        return ("دور", f"دور از نقطه ورود ({confidence}٪)", "⚪ صبر کن")

    # 🔴 ۳. از ۳۰ تا ۴۰: در حال تشکیل
    if confidence < 40:
        return ("در حال تشکیل", f"در حال شکل‌گیری ({confidence}٪)", "⚪ صبر کن")

    # 🔴 از اینجا به بعد سیگنال‌های واقعی هستند (۴۰٪ به بالا):
    is_golden = confidence >= 85
    is_strong = 70 <= confidence < 85
    is_normal = 55 <= confidence < 70
    is_weak = 40 <= confidence < 55

    if direction == "neutral" or is_boring:
        return ("خنثی", f"بدون جهت مشخص ({confidence}٪)", "⚪ صبر کن")

    if market_type == "spot" and direction == "short":
        return "خنثی", f"🔴 در اسپات نمی‌تونی بفروشی ({confidence}٪)", "⚪ صبر کن"

    if direction == "long":
        if is_golden:
            return "LONG", "💎 سیگنال طلایی خرید", "🟢 LONG بزن"
        elif is_strong:
            return "LONG", "🟢 سیگنال خرید قوی", "🟢 بخر"
        elif is_normal:
            return "LONG", "🟡 سیگنال خرید معمولی", "🟢 بخر"
        else:
            return "LONG ضعیف", f"🟠 خرید ضعیف ({confidence}٪)", "🟡 بخر با احتیاط"
    else:
        if is_golden:
            return "SHORT", "💎 سیگنال طلایی فروش", "🔴 SHORT بزن"
        elif is_strong:
            return "SHORT", "🔴 سیگنال فروش قوی", "🔴 SHORT بزن"
        elif is_normal:
            return "SHORT", "🔴 سیگنال فروش معمولی", "🔴 SHORT بزن"
        else:
            return "SHORT ضعیف", f"🟠 فروش ضعیف ({confidence}٪)", "🟠 SHORT ضعیف"


def _get_session_multiplier() -> tuple[float, str]:
    """
    ضریب تعدیل بر اساس سشن‌های جهانی و روز هفته.
    Returns: (multiplier, label_fa)
    """
    now_utc = datetime.now(ZoneInfo("UTC"))
    hour = now_utc.hour
    weekday = now_utc.weekday()  # 0=Monday, 5=Saturday, 6=Sunday

    # همپوشانی لندن-نیویورک (پیک نقدینگی): ۱۲:۰۰–۱۶:۰۰ UTC
    if 12 <= hour < 16:
        base_mult = 1.10
        label = "🔥 همپوشانی لندن-نیویورک"
    # همپوشانی توکیو-لندن: ۰۷:۰۰–۰۹:۰۰ UTC
    elif 7 <= hour < 9:
        base_mult = 1.0
        label = "⚖️ همپوشانی توکیو-لندن"
    # فقط بازار آسیا (غرب خواب): ۰۰:۰۰–۰۶:۰۰ UTC
    elif 0 <= hour < 6:
        base_mult = 0.75  # 🔴 نرم‌تر شد (قبلاً 0.65 بود)
        label = "🌙 فقط بازار آسیا"
    # بقیه ساعات
    else:
        base_mult = 1.0
        label = "⚖️ بازار عادی"

    # 🔴 آخر هفته: کاهش ملایم‌تر (۵٪ به جای ۱۰٪)
    if weekday >= 5:
        base_mult *= 0.95
        label += " (📅 آخر هفته)"

    return base_mult, label


def analyze_symbol(
    df: pd.DataFrame,
    risk_profile: str = "aggressive",
    tf_name: str = "۵ دقیقه",
    tfs_data: dict = None,
    market_type: str = "spot",
    ticker: str = "",
    source: str = "nobitex",
    orderbook: dict = None,
) -> dict | None:
    if df is None or df.empty:
        return None
    try:
        df = compute_indicators(df)
        if df is None or df.empty:
            return None
        last = df.iloc[-1]
        price = safe_num(last["close"])
        atr = safe_num(last.get("atr"))
        adx = safe_num(last.get("adx"), 20)
        bb_width_pct = safe_num(last.get("bb_width_pct"), None)
        vol, vol_ma = safe_num(last.get("volume")), safe_num(last.get("vol_ma"))
        vol_ratio = vol / vol_ma if vol_ma > 0 else 1.0
        ema200_val = safe_num(last.get("ema200"))
        prev_ema200 = (
            safe_num(df["ema200"].iloc[-2])
            if "ema200" in df.columns and len(df) > 1
            else ema200_val
        )
        ema_slope = (
            ((ema200_val - prev_ema200) / prev_ema200)
            if (not np.isnan(ema200_val) and prev_ema200 > 0)
            else 0
        )
        dmp_val, dmn_val = safe_num(last.get("dmp")), safe_num(last.get("dmn"))
        di_diff = dmp_val - dmn_val
        regime = classify_regime(
            adx,
            bb_width_pct=bb_width_pct,
            volume_ratio=vol_ratio,
            ema_slope=ema_slope,
            di_diff=di_diff,
        )
        thresholds = get_adaptive_thresholds(regime, adx)
        groups = {
            "momentum": _analyze_momentum(df, _thresholds=thresholds),
            "trend": _analyze_trend(df, _thresholds=thresholds),
            "volatility": _analyze_volatility(df, _thresholds=thresholds),
            "volume": _analyze_volume(
                df,
                market_type,
                _thresholds=thresholds,
                orderbook=orderbook,
                regime=regime,
            ),
            "structure": _analyze_structure(df, _thresholds=thresholds),
        }
        structure_details = groups["structure"].get("details", {})
        df_with_levels = df.copy()
        df_with_levels["nearest_resistance"] = structure_details.get(
            "nearest_resistance", 0
        )
        df_with_levels["nearest_support"] = structure_details.get("nearest_support", 0)
        try:
            pre_breakout = detect_pre_breakout(df_with_levels)
        except Exception:
            pre_breakout = {
                "is_pre_breakout": False,
                "score": 0,
                "direction_bias": "neutral",
                "reasons": [],
                "details": {},
            }
        aggregate = _aggregate_votes(
            groups, regime, risk_profile, adx, market_type, tf_name
        )
        divergence = _detect_divergence(groups["momentum"], groups["volume"])
        traps = _detect_traps(groups, price, atr)
        traps_summary = _traps_summary(traps)
        trap_penalty = (
            15
            if traps_summary["has_high_risk"]
            else (5 if traps_summary["has_warning"] else 0)
        )
        confidence = _compute_confidence(aggregate, adx, divergence, groups)
        if trap_penalty > 0:
            confidence = max(0, confidence - trap_penalty)
        tier = _confidence_tier(confidence)
        multi_tf_ok, multi_tf_info = True, "بدون بررسی"
        # 🔴 فیلتر ساعت و روز هفته
        session_mult, session_label = _get_session_multiplier()
        confidence = max(0, min(100, int(confidence * session_mult)))
        tier = _confidence_tier(confidence)

        # 🔴 فیلتر ATR (فشردگی نوسان) — نرم‌تر شده
        atr_val = safe_num(last.get("atr"))
        atr_ma = (
            safe_num(df["atr"].rolling(20).mean().iloc[-1])
            if len(df) >= 20
            else atr_val
        )
        if atr_ma > 0 and atr_val > 0:
            atr_ratio = atr_val / atr_ma
            if atr_ratio < 0.60:  # 🔴 از 0.70 به 0.60 کاهش یافت
                # بازار کاملاً مرده — سیگنال خنثی
                confidence = 0
                tier = "neutral"

        if tfs_data and aggregate["direction"] != "neutral":
            higher_signals = []
            for tf_check in ["۱ ساعت", "روزانه"]:
                if tf_check in tfs_data and tf_check != tf_name:
                    r = tfs_data[tf_check]
                    if r:
                        sig = r.get("signal", "")
                        higher_signals.append(
                            +1
                            if SigEnum.is_long(sig)
                            else (-1 if SigEnum.is_short(sig) else 0)
                        )
            if higher_signals:
                confirms = sum(
                    1
                    for s in higher_signals
                    if (s > 0 if aggregate["direction"] == "long" else s < 0)
                )
                if confirms >= 2:
                    multi_tf_info = (
                        f"✅ تأیید {confirms}/{len(higher_signals)} TF بالاتر"
                    )
                elif confirms == 1:
                    multi_tf_info, multi_tf_ok = (
                        f"⚠️ تأیید ۱/{len(higher_signals)} TF بالاتر",
                        False,
                    )
                else:
                    multi_tf_info, multi_tf_ok = "❌ عدم تأیید TF های بالاتر", False
        if tfs_data and aggregate["direction"] != "neutral":
            higher_confirms, higher_total = 0, 0
            for tf_check in ["۱ ساعت", "روزانه"]:
                if (
                    tf_check in tfs_data
                    and tf_check != tf_name
                    and (r := tfs_data[tf_check])
                ):
                    higher_total += 1
                    sig = r.get("signal", "")
                    if (aggregate["direction"] == "long" and SigEnum.is_long(sig)) or (
                        aggregate["direction"] == "short" and SigEnum.is_short(sig)
                    ):
                        higher_confirms += 1
            if higher_total > 0:
                if higher_confirms == higher_total:
                    confidence = min(100, int(confidence * 1.15))
                elif higher_confirms >= higher_total / 2:
                    confidence = min(100, int(confidence * 1.08))
                elif higher_confirms == 0:
                    confidence = int(confidence * 0.75)
                tier = _confidence_tier(confidence)
        if not multi_tf_ok and aggregate["direction"] != "neutral":
            confidence = int(confidence * 0.9)
            tier = _confidence_tier(confidence)
        if (
            aggregate["direction"] != "neutral"
            and orderbook
            and orderbook.get("imbalance") is not None
        ):
            ob_boost = 0
            imb = orderbook.get("imbalance", 0.5)
            dir_agg = aggregate["direction"]
            if dir_agg == "long" and imb > 0.6:
                ob_boost += 10
            elif dir_agg == "short" and imb < 0.4:
                ob_boost += 10
            elif dir_agg == "long" and imb < 0.4:
                ob_boost -= 15
            elif dir_agg == "short" and imb > 0.6:
                ob_boost -= 15
            try:
                if vol_ma > 0 and vol > vol_ma * 1.5:
                    ob_boost += 5
            except:
                pass
            if ob_boost != 0:
                confidence = max(0, min(100, confidence + ob_boost))
                tier = _confidence_tier(confidence)
        direction = aggregate["direction"]
        profile_key = f"{risk_profile}_{market_type}"
        profile = RISK_PROFILES.get(
            profile_key,
            RISK_PROFILES.get(f"{risk_profile}_spot", RISK_PROFILES["aggressive_spot"]),
        )
        min_conf = profile["min_confidence"]
        consensus = aggregate.get("consensus", "neutral")
        allow_short = profile.get("allow_short", True)
        neutral_explain_dict = {}
        if direction == "neutral" or confidence < min_conf:
            neutral_explain_dict = _explain_neutral(
                aggregate,
                regime,
                divergence,
                market_type,
                tfs_data=tfs_data,
                current_tf=tf_name,
                traps=traps,
            )
        final_score_raw = aggregate.get("final_score", 0.0)
        is_boring = _is_boring_market(aggregate, adx, vol_ratio, final_score_raw)
        signal, explanation, action_fa = _determine_signal(
            direction=direction,
            confidence=confidence,
            tier=tier,
            min_conf=min_conf,
            tf_name=tf_name,
            is_boring=is_boring,
            allow_short=allow_short,
            market_type=market_type,
        )
        sl_tp, rr, fee_warning, _soft_rr_net = None, None, None, None
        is_directional = SigEnum.is_directional(signal)
        if market_type == "spot" and SigEnum.is_short(signal):
            is_directional = False
        if atr > 0 and is_directional:
            tf_mult = get_tf_atr_mult(tf_name)
            tf_sl_mult, tf_tp_mult = _get_tf_rr_profile(tf_name, profile_key)

            # 🔴 SL بر اساس TF (نه پروفایل) — نوسان واقعی بازار
            effective_sl_mult = tf_sl_mult

            # 🔴 TP: محتاطانه نزدیک‌تر (WR بالاتر)، جسورانه استاندارد (RR بالاتر)
            if risk_profile == "conservative":
                effective_tp_mult = tf_tp_mult * 0.85
            else:
                effective_tp_mult = tf_tp_mult

            if SigEnum.is_long(signal):
                sl, tp = (
                    price - atr * effective_sl_mult,
                    price + atr * effective_tp_mult,
                )
                sl_tp = {
                    "sl": sl,
                    "tp": tp,
                    "type": "LONG",
                    "tf_mult": tf_mult,
                    "effective_sl_mult": effective_sl_mult,
                    "effective_tp_mult": effective_tp_mult,
                }
            elif SigEnum.is_short(signal) and market_type == "futures":
                sl, tp = (
                    price + atr * effective_sl_mult,
                    price - atr * effective_tp_mult,
                )
                sl_tp = {
                    "sl": sl,
                    "tp": tp,
                    "type": "SHORT",
                    "tf_mult": tf_mult,
                    "effective_sl_mult": effective_sl_mult,
                    "effective_tp_mult": effective_tp_mult,
                }
            if sl_tp:
                base_fee = get_fee_rate(
                    source or "nobitex", market_type=market_type, ticker=ticker
                )
                if orderbook and orderbook.get("spread_pct") is not None:
                    from .orderbook import execution_cost_pct

                    cost = execution_cost_pct(orderbook["spread_pct"], base_fee)
                    fee_rate, execution_cost = cost["total_pct"] / 100, cost
                else:
                    fee_rate, execution_cost = base_fee, None
                MIN_COST_RATIO = 8.0
                min_total_pct = (
                    execution_cost["total_pct"] * MIN_COST_RATIO
                    if execution_cost
                    else 0
                )
                actual_total_pct = (
                    (abs(price - sl_tp["sl"]) + abs(sl_tp["tp"] - price)) / price * 100
                )
                scaled = False
                if min_total_pct > 0 and actual_total_pct < min_total_pct:
                    scale = min(min_total_pct / actual_total_pct, 10.0)
                    if SigEnum.is_long(signal):
                        sl_tp["sl"], sl_tp["tp"] = (
                            price - abs(price - sl_tp["sl"]) * scale,
                            price + abs(sl_tp["tp"] - price) * scale,
                        )
                    else:
                        sl_tp["sl"], sl_tp["tp"] = (
                            price + abs(sl_tp["sl"] - price) * scale,
                            price - abs(price - sl_tp["tp"]) * scale,
                        )
                    sl_tp.update(
                        {
                            "sl_tp_scaled": True,
                            "scale_factor": round(scale, 2),
                            "original_sl": sl,
                            "original_tp": tp,
                            "scale_reason": "ATR کوچکتر از هزینه معامله بود",
                        }
                    )
                    scaled = True
                TF_MIN_SL_PCT = {
                    "۱ دقیقه": 0.8,
                    "۵ دقیقه": 1.0,
                    "۱۵ دقیقه": 1.5,
                    "۳۰ دقیقه": 1.8,
                    "۱ ساعت": 2.2,
                    "روزانه": 3.0,
                }
                tf_min_sl_pct = TF_MIN_SL_PCT.get(tf_name, 1.0)
                sl_dist_pct = abs(price - sl_tp["sl"]) / price * 100
                if sl_dist_pct < tf_min_sl_pct:
                    scale_tf = tf_min_sl_pct / sl_dist_pct
                    if SigEnum.is_long(signal):
                        sl_tp["sl"], sl_tp["tp"] = (
                            price - abs(price - sl_tp["sl"]) * scale_tf,
                            price + abs(sl_tp["tp"] - price) * scale_tf,
                        )
                    else:
                        sl_tp["sl"], sl_tp["tp"] = (
                            price + abs(sl_tp["sl"] - price) * scale_tf,
                            price - abs(price - sl_tp["tp"]) * scale_tf,
                        )
                    sl_tp["sl_tp_scaled"], sl_tp["scale_factor"] = True, round(
                        sl_tp.get("scale_factor", 1.0) * scale_tf, 2
                    )
                    if "original_sl" not in sl_tp:
                        sl_tp.update({"original_sl": sl, "original_tp": tp})
                    sl_tp["scale_reason"] = (
                        f"حداقل فاصله SL برای «{tf_name}» برآورده نشده بود"
                    )
                    scaled = True
                nearest_support = groups["structure"]["details"].get(
                    "nearest_support", 0
                )
                nearest_resistance = groups["structure"]["details"].get(
                    "nearest_resistance", 0
                )
                if SigEnum.is_long(signal) and nearest_support > 0:
                    structural_sl = nearest_support * 0.998
                    if structural_sl < sl_tp["sl"] and structural_sl < price:
                        sl_tp["sl"] = structural_sl
                elif SigEnum.is_short(signal) and nearest_resistance > 0:
                    structural_sl = nearest_resistance * 1.002
                    if structural_sl > sl_tp["sl"] and structural_sl > price:
                        sl_tp["sl"] = structural_sl
                fee_stats = compute_net_rr(price, sl_tp["sl"], sl_tp["tp"], fee_rate)
                rr = fee_stats.get("rr_gross")
                sl_tp.update(fee_stats)
                sl_tp.update({"fee_rate": fee_rate, "fee_rate_base": base_fee})
                if execution_cost:
                    sl_tp["execution_cost"] = execution_cost
                if not fee_stats.get("is_worthwhile", True):
                    extra = " (شامل کارمزد+اسپرد+اسلیپیج)" if execution_cost else ""
                    fee_warning = f"⚠️ R:R خالص {fee_stats['rr_net']:.2f} (خام {fee_stats['rr_gross']:.2f}) — هزینه {fee_stats['fee_pct']:.2f}٪{extra} ({fee_stats['rr_decay_pct']:.0f}٪ از R:R را می‌خورد)"
                elif scaled:
                    fee_warning = f"ℹ️ حد ضرر/هدف بزرگ‌تر شد تا با هزینه {fee_stats['fee_pct']:.2f}٪ معامله معنادار بماند"
                _soft_rr_net = fee_stats.get("rr_net")
        all_reasons = [fee_warning] if fee_warning else []
        for g_res in groups.values():
            if g_res:
                all_reasons.extend(g_res.get("reasons", []))
        if divergence.get("has_divergence"):
            all_reasons.insert(0, divergence["reason"])
        if aggregate.get("override_reason"):
            all_reasons.insert(0, aggregate["override_reason"])
        if _soft_rr_net is not None and is_directional:
            min_rr = profile.get("min_rr_net", 1.2)
            if _soft_rr_net < min_rr * 0.5:
                confidence = int(confidence * RR_VERY_LOW_PENALTY)
                tier = _confidence_tier(confidence)
                all_reasons.insert(
                    0, f"⚠️ R:R خالص {_soft_rr_net:.2f} خیلی پایین — اطمینان کاهش یافت"
                )
            elif _soft_rr_net < min_rr:
                confidence = int(confidence * RR_LOW_PENALTY)
                tier = _confidence_tier(confidence)
                all_reasons.insert(
                    0, f"⚠️ R:R خالص {_soft_rr_net:.2f} — هزینه بالا، اطمینان کاهش یافت"
                )
            signal, explanation, action_fa = _determine_signal(
                direction=direction,
                confidence=confidence,
                tier=tier,
                min_conf=min_conf,
                tf_name=tf_name,
                is_boring=is_boring,
                allow_short=allow_short,
                market_type=market_type,
            )
        support = groups["structure"]["details"].get("nearest_support", 0)
        resistance = groups["structure"]["details"].get("nearest_resistance", 0)
        is_golden = confidence >= 85 and SigEnum.is_directional(signal)
        return {
            "price": price,
            "rsi": safe_num(last.get("rsi"), 50),
            "willr": safe_num(last.get("willr"), -50),
            "stoch_k": safe_num(last.get("stoch_k"), 50),
            "stoch_d": safe_num(last.get("stoch_d"), 50),
            "adx": adx,
            "macd_hist": safe_num(last.get("macd_hist")),
            "atr": atr,
            "ema200": safe_num(last.get("ema200")),
            "bb_upper": safe_num(last.get("bb_upper")),
            "bb_lower": safe_num(last.get("bb_lower")),
            "vwap": safe_num(last.get("vwap")) if "vwap" in df.columns else None,
            "support": support,
            "resistance": resistance,
            "pivots": groups["structure"]["details"].get("pivots", {}),
            "swings": groups["structure"]["details"].get("swings", {}),
            "fibonacci": groups["structure"]["details"].get("fibonacci", {}),
            "score": round(aggregate["final_score"], 3),
            "raw_score": aggregate["final_score"],
            "signal": signal,
            "explanation": explanation,
            "neutral_explain": neutral_explain_dict,
            "action_fa": action_fa,
            "confidence": confidence,
            "confidence_tier": tier,
            "is_golden": is_golden,
            "reasons": all_reasons,
            "groups": aggregate["groups_summary"],
            "votes_long": aggregate["votes_long"],
            "votes_short": aggregate["votes_short"],
            "votes_neutral": aggregate["votes_neutral"],
            "consensus": consensus,
            "direction": direction,
            "multi_tf_info": multi_tf_info,
            "multi_tf_ok": multi_tf_ok,
            "regime": regime,
            "session_label": session_label,
            "risk_profile": risk_profile,
            "market_type": market_type,
            "leverage": profile.get("leverage"),
            "allow_short": allow_short,
            "divergence": divergence,
            "sl_tp": sl_tp,
            "rr": rr,
            "is_ranging": regime == "range",
            "close_series": df["close"].tail(30).tolist(),
            "traps": traps,
            "traps_summary": traps_summary,
            "orderbook": orderbook,
            "trap_penalty": trap_penalty,
            "thresholds_used": thresholds,
            "ticker": ticker,
            "is_iranian": _is_iranian_ticker(ticker),
            "scenarios": build_scenarios(
                price,
                atr,
                aggregate["groups_summary"],
                support,
                resistance,
                regime,
                direction,
                traps,
                ticker,
            ),
            "trend_score": groups["trend"].get("score", 0.0),
            "trend_vote": groups["trend"].get("vote", 0),
            "override_reason": aggregate.get("override_reason", ""),
            "pre_breakout": pre_breakout,
            "pre_breakout_score": pre_breakout.get("score", 0),
            "is_pre_breakout": pre_breakout.get("is_pre_breakout", False),
            "trend_predicted_at_entry": (
                "bull"
                if groups["trend"].get("score", 0) >= 0.30
                else "bear" if groups["trend"].get("score", 0) <= -0.30 else "flat"
            ),
            "is_boring_market": is_boring,
            "analyzer_version": ANALYZER_VERSION,
        }
    except Exception as e:
        logger.exception(f"[Analyzer] خطا در تحلیل: {e}")
        return None


def compute_fear_greed(df: pd.DataFrame) -> float:
    try:
        if df is None or df.empty or len(df) < 20:
            return 50.0
        df = compute_indicators(df)
        if df is None or df.empty:
            return 50.0
        rsi = safe_num(df["rsi"].iloc[-1], 50)
        price = safe_num(df["close"].iloc[-1])
        atr = safe_num(df["atr"].iloc[-1]) if "atr" in df.columns else 0
        macd_h = safe_num(df["macd_hist"].iloc[-1]) if "macd_hist" in df.columns else 0
        ema50_series = ta.ema(df["close"], length=50)
        ema50 = (
            safe_num(ema50_series.iloc[-1], price)
            if ema50_series is not None and len(ema50_series) > 0
            else price
        )
        rsi_score = max(0, min(100, rsi))
        stretch = (
            max(0, min(100, ((price - ema50) / atr) * 10 + 50)) if atr > 0 else 50.0
        )
        macd_score = max(0, min(100, 50 + (macd_h * 10)))
        return max(
            0.0,
            min(100.0, float(rsi_score * 0.45 + stretch * 0.30 + macd_score * 0.25)),
        )
    except Exception:
        return 50.0


GROUP_LABELS = {
    "momentum": ("⚡", "مومنتوم", "RSI, Stochastic, Williams, CCI, ROC"),
    "trend": ("📈", "روند", "EMA200, MACD, ADX, Supertrend, Ichimoku"),
    "volatility": ("📊", "نوسان", "Bollinger, ATR, Keltner, Donchian, StdDev"),
    "volume": ("💧", "حجم", "OBV, CVD, Delta, CMF, MFI, Absorption"),
    "structure": ("🏗", "ساختار", "Pivot, Swing, Fibonacci, S/R"),
}


def build_checklist_weighted(tfs: dict, main_tf: str = "۵ دقیقه") -> tuple:
    r_main = tfs.get(main_tf) or tfs.get("۵ دقیقه")
    if not r_main:
        return [], 0, "داده کافی نیست", "red"
    items, regime = [], r_main.get("regime", "range")
    weights = _regime_weights(regime)
    groups = r_main.get("groups", {})
    total_w, earned_w = 0, 0
    multi_tf_ok, multi_tf_info = r_main.get("multi_tf_ok", True), r_main.get(
        "multi_tf_info", ""
    )
    if multi_tf_info:
        items.append(
            {
                "group": "multi_tf",
                "label": "🎯 تأیید چند تایم‌فریمی",
                "icon": "🎯",
                "detail": multi_tf_info,
                "score": 1.0 if multi_tf_ok else 0.0,
                "weight": 20,
                "color": "green" if multi_tf_ok else "red",
            }
        )
        total_w += 20
        earned_w += 20 if multi_tf_ok else 0
    divergence = r_main.get("divergence", {})
    if divergence.get("has_divergence"):
        items.append(
            {
                "group": "divergence",
                "label": "⚠️ واگرایی مومنتوم/حجم",
                "icon": "⚠️",
                "detail": divergence.get("reason", ""),
                "score": -1.0,
                "weight": 15,
                "color": "red",
            }
        )
        total_w += 15
    traps = r_main.get("traps", {})
    if traps:
        trap_names = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        for trap_key, trap_info in traps.items():
            if trap_info.get("active"):
                items.append(
                    {
                        "group": "trap_" + trap_key,
                        "label": f"🚨 {trap_names.get(trap_key, trap_key)}",
                        "icon": "🚨",
                        "detail": trap_info.get("reason", ""),
                        "score": -1.0,
                        "weight": trap_info.get("severity", 5),
                        "color": "red",
                    }
                )
                total_w += trap_info.get("severity", 5)
    for g_key, (icon, g_name, g_desc) in GROUP_LABELS.items():
        if g_key not in groups:
            continue
        g_res, g_score, g_vote, g_strength_fa = (
            groups[g_key],
            groups[g_key].get("score", 0.0),
            groups[g_key].get("vote", 0),
            groups[g_key].get("strength_fa", ""),
        )
        g_weight_pct = int(weights.get(g_key, 1.0) * 100 / 6 * 1.5)
        g_color = "green" if g_vote > 0 else ("red" if g_vote < 0 else "yellow")
        detail_with_strength = (
            f"قدرت: {g_strength_fa} · {g_desc}"
            if g_strength_fa and g_strength_fa != "بی‌جهت"
            else g_desc
        )
        items.append(
            {
                "group": g_key,
                "label": f"{icon} {g_name}",
                "icon": icon,
                "detail": detail_with_strength,
                "reasons": g_res.get("reasons", [])[:3],
                "score": g_score,
                "weight": g_weight_pct,
                "color": g_color,
                "vote": g_vote,
            }
        )
        total_w += g_weight_pct
        earned_w += g_weight_pct * 0.5 if g_vote == 0 else g_weight_pct
    sl_tp, rr = r_main.get("sl_tp"), safe_num(r_main.get("rr"))
    if sl_tp:
        items.append(
            {
                "group": "sl_tp",
                "label": "🛑 حد ضرر و هدف",
                "icon": "🛑",
                "detail": f"R:R = {rr:.1f}" if rr else "تعریف‌شده",
                "score": 1.0 if rr and rr >= 1.5 else 0.5,
                "weight": 15,
                "color": "green" if rr and rr >= 1.5 else "yellow",
            }
        )
        total_w += 15
        earned_w += 15 if (rr and rr >= 1.5) else 7
    else:
        items.append(
            {
                "group": "sl_tp",
                "label": "🛑 حد ضرر و هدف",
                "icon": "🛑",
                "detail": "تعریف نشده",
                "score": 0.0,
                "weight": 15,
                "color": "red",
            }
        )
        total_w += 15
    percentage = int(earned_w / total_w * 100) if total_w > 0 else 0
    signal, confidence = r_main.get("signal", "خنثی"), r_main.get("confidence", 0)
    regime_fa = {
        "trend": "جهت‌دار",
        "transitional": "در حال‌تغییر",
        "range": "بی‌جهت",
    }.get(regime, "")
    if SigEnum.is_long(signal):
        golden_mark = " 💎" if confidence >= 85 else ""
        final, final_color = (
            f"🟢 سیگنال خرید {'قوی' if confidence >= 70 else ''}{golden_mark} — {confidence}% ({regime_fa})",
            "green",
        )
    elif SigEnum.is_short(signal):
        golden_mark = " 💎" if confidence >= 85 else ""
        final, final_color = (
            f"🔴 سیگنال فروش {'قوی' if confidence >= 70 else ''}{golden_mark} — {confidence}% ({regime_fa})",
            "red",
        )
    else:
        ne = r_main.get("neutral_explain", {})
        final, final_color = (
            ne.get("short") if ne and ne.get("short") else f"⚪ خنثی — {regime_fa}"
        ), "yellow"
    return items, percentage, final, final_color


def _build_fundamental_context(
    df, r_main, ticker, is_iranian, unit, fee_pct=None
) -> list[str]:
    out = []
    try:
        if df is None or df.empty or len(df) < 60:
            return out
        last, price, atr = (
            df.iloc[-1],
            safe_num(df.iloc[-1].get("close")),
            safe_num(df.iloc[-1].get("atr")),
        )
        if price <= 0:
            return out
        fmt = (
            (lambda v: f"{v:,.2f}$")
            if not is_iranian
            else (lambda v: f"{v:,.0f} {unit}")
        )
        if atr > 0:
            atr_pct = atr / price * 100
            if atr_pct < 0.3:
                vol_fa = "بسیار کم — حرکت کند، خطر رکود"
            elif atr_pct < 1.0:
                vol_fa = "کم — مناسب پوزیشن‌های محتاط"
            elif atr_pct < 3.0:
                vol_fa = "متوسط — متعادل"
            elif atr_pct < 6.0:
                vol_fa = "بالا — سود و ضرر سریع"
            else:
                vol_fa = "بسیار بالا — ریسک شدید، اهرم خطرناک"
            out.append(f"📊 **نوسان:** {atr_pct:.2f}٪ — {vol_fa}")
            if fee_pct and fee_pct > 0:
                ratio = atr_pct / fee_pct
                if ratio < 1:
                    out.append(
                        f"🔴 **نوسان از هزینه کمتر است** ({atr_pct:.2f}٪ ÷ {fee_pct:.2f}٪ = {ratio:.1f}×) — معامله در این TF صرفه ندارد"
                    )
                elif ratio < 3:
                    out.append(
                        f"🟡 **نوسان کم است** (نسبت {ratio:.1f}× هزینه) — حرکت بزرگ‌تری لازم است"
                    )
                else:
                    out.append(
                        f"🟢 **نوسان کافی است** (نسبت {ratio:.1f}× هزینه) — معامله می‌تواند هزینه‌ها را پوشش دهد"
                    )
        lookback = min(90, len(df))
        window = df.tail(lookback)
        hi, lo = safe_num(window["high"].max()), safe_num(window["low"].min())
        if hi > lo > 0:
            pos = (price - lo) / (hi - lo) * 100
            if pos >= 90:
                zone = "نزدیک سقف بازه — احتمال مقاومت یا شکست"
            elif pos >= 70:
                zone = "نیمه‌ی بالای بازه — روند صعودی"
            elif pos >= 40:
                zone = "میانه‌ی بازه — بی‌طرف"
            elif pos >= 15:
                zone = "نیمه‌ی پایین بازه — ضعیف"
            else:
                zone = "نزدیک کف بازه — احتمال حمایت یا شکست"
            out.append(f"📍 **موقعیت در {lookback} کندل:** {pos:.0f}٪ — {zone}")
            out.append(
                f"   سقف {fmt(hi)} · کف {fmt(lo)} · فاصله از سقف {(hi - price) / price * 100:.1f}٪"
            )
        adx, ema200, ema50 = (
            safe_num(last.get("adx"), 0),
            safe_num(last.get("ema200")),
            safe_num(last.get("ema50")),
        )
        bits = []
        if adx > 0:
            bits.append(
                f"ADX={adx:.0f} ({'روند قوی' if adx >= 40 else 'روند نرمال' if adx >= 25 else 'بدون روند'})"
            )
        if not np.isnan(ema200) and ema200 > 0 and ema50 > 0:
            if price > ema200 and ema50 > ema200:
                bits.append("صعودی (قیمت > EMA50 > EMA200)")
            elif price < ema200 and ema50 < ema200:
                bits.append("نزولی (قیمت < EMA50 < EMA200)")
            else:
                bits.append("مختلط (EMAها هم‌جهت نیستند)")
        if bits:
            out.append("📈 **ساختار روند:** " + " · ".join(bits))
        vol, vol_ma = safe_num(last.get("volume")), safe_num(last.get("vol_ma"))
        if vol_ma > 0:
            vr = vol / vol_ma
            if vr >= 1.5:
                v_txt = f"بالا ({vr:.1f}× میانگین)"
            elif vr <= 0.5:
                v_txt = f"کم ({vr:.1f}× میانگین)"
            else:
                v_txt = f"نرمال ({vr:.1f}× میانگین)"
            if len(df) > 2:
                prev_close, up = safe_num(df["close"].iloc[-2]), price > safe_num(
                    df["close"].iloc[-2]
                )
                if vr >= 1.5:
                    v_txt += " · هم‌جهت با قیمت ✅" if up else " · هم‌جهت با نزول ✅"
                elif vr <= 0.5:
                    v_txt += " · حجم تأییدکننده نیست ⚠️"
            out.append(f"💧 **حجم:** {v_txt}")
        r_lvl, s_lvl = safe_num(r_main.get("resistance")), safe_num(
            r_main.get("support")
        )
        if r_lvl > 0 and s_lvl > 0:
            out.append(
                f"🎯 **فضای حرکت:** تا مقاومت {(r_lvl - price) / price * 100:+.2f}٪ · تا حمایت {(s_lvl - price) / price * 100:+.2f}٪"
            )
        out.append(
            "ℹ️ *داده‌ی بنیادی در فاز بعد اضافه می‌شود — این بخش از قیمت و ساختار بازار استخراج شده.*"
        )
    except Exception as e:
        logger.warning(f"[Analyzer] زمینه‌ی بنیادی: {e!r}")
        return []
    return out


def build_analysis_paragraph(
    ticker, name, tfs, gsr=None, risk_profile="aggressive", tf_name="۵ دقیقه"
) -> str:
    lines = []
    r_main = tfs.get(tf_name) or tfs.get("۵ دقیقه")
    if not r_main:
        return "داده کافی نیست."
    regime = r_main.get("regime", "range")
    regime_fa = {
        "trend": "جهت‌دار",
        "transitional": "در حال‌تغییر",
        "range": "رنج",
    }.get(regime, "رنج")
    is_iranian = _is_iranian_ticker(ticker)
    is_tsetmc = bool(ticker) and not ticker[0].isascii()
    unit = "ریال" if is_tsetmc else ("تومان" if is_iranian else "$")
    market_type = r_main.get("market_type", "spot")
    market_fa = "اسپات" if market_type == "spot" else "فیوچرز"
    profile_fa = {"aggressive": "جسورانه", "conservative": "محتاطانه"}.get(
        risk_profile, "جسورانه"
    )
    signal, confidence, price = (
        r_main.get("signal", "خنثی"),
        r_main.get("confidence", 0),
        safe_num(r_main.get("price")),
    )
    adx, votes_long, votes_short, votes_neutral = (
        safe_num(r_main.get("adx"), 20),
        r_main.get("votes_long", 0),
        r_main.get("votes_short", 0),
        r_main.get("votes_neutral", 0),
    )
    groups, divergence = r_main.get("groups", {}), r_main.get("divergence", {})
    multi_tf_info, neutral_explain, traps = (
        r_main.get("multi_tf_info", ""),
        r_main.get("neutral_explain", {}),
        r_main.get("traps", {}),
    )
    override_reason, sl_tp, scenarios = (
        r_main.get("override_reason", ""),
        r_main.get("sl_tp"),
        r_main.get("scenarios", []),
    )

    def H(text: str) -> str:
        return f"▎**{text}**"

    lines.extend([f"_{tf_name} · {profile_fa} · {market_fa}_", ""])
    if SigEnum.is_long(signal):
        if confidence >= 85:
            main_line = f"💎 **سیگنال طلایی خرید** · اطمینان {confidence}٪"
        elif confidence >= 70:
            main_line = f"✅ **خرید قوی** · اطمینان {confidence}٪"
        elif confidence >= 50:
            main_line = f"🟢 **خرید** · اطمینان {confidence}٪"
        else:
            main_line = f"🟡 **خرید ضعیف** · اطمینان {confidence}٪"
    elif SigEnum.is_short(signal):
        if confidence >= 85:
            main_line = f"💎 **سیگنال طلایی فروش** · اطمینان {confidence}٪"
        elif confidence >= 70:
            main_line = f"🔴 **فروش قوی** · اطمینان {confidence}٪"
        elif confidence >= 50:
            main_line = f"🔴 **فروش** · اطمینان {confidence}٪"
        else:
            main_line = f"🟠 **فروش ضعیف** · اطمینان {confidence}٪"
    else:
        main_line = (
            "🚫 **بلاک شده** — روند مخالف قویه"
            if override_reason
            else f"⚪ **صبر کن** — سیگنال واضحی نیست ({confidence}٪)"
        )
    lines.extend([main_line, ""])
    if sl_tp:
        sl, tp = safe_num(sl_tp.get("sl")), safe_num(sl_tp.get("tp"))
        rr_net, fee_pct = sl_tp.get("rr_net"), sl_tp.get("fee_pct")
        if is_iranian:
            lines.append(f"ورود {price:,.0f} {unit} · SL {sl:,.0f} · TP {tp:,.0f}")
        else:
            lines.append(f"ورود {price:,.2f}$ · SL {sl:,.2f}$ · TP {tp:,.2f}$")
        if rr_net is not None:
            rr_verdict = (
                "عالی"
                if rr_net >= 2.0
                else (
                    "خوب"
                    if rr_net >= 1.5
                    else ("قابل قبول" if rr_net >= 1.0 else "ضعیف")
                )
            )
            fee_line = f" · هزینه {fee_pct:.2f}٪" if fee_pct is not None else ""
            lines.append(f"R:R خالص {rr_net:.2f} ({rr_verdict}){fee_line}")
        lines.append("")
    active_traps = {k: v for k, v in traps.items() if v.get("active")}
    if active_traps:
        trap_names = {
            "bull_trap": "تله صعودی",
            "bear_trap": "تله نزولی",
            "fake_breakout": "شکست جعلی",
            "exhaustion": "خستگی روند",
        }
        lines.extend(
            [
                f"🚨 **هشدار:** {' · '.join(trap_names.get(k, k) for k in active_traps.keys())}",
                "",
            ]
        )
    lines.extend([H("۱. بازار چطوره؟"), ""])
    if adx >= 40:
        adx_fa, adx_note = "روند قویه", "بالای ۴۰ یعنی روند محکم و قابل اعتماد"
    elif adx >= 25:
        adx_fa, adx_note = "روند فعاله", "بین ۲۵ تا ۴۰ یعنی روند داره شکل می‌گیره"
    elif adx >= 18:
        adx_fa, adx_note = "روند ضعیفه", "بین ۱۸ تا ۲۵ یعنی روند شکننده‌ست"
    else:
        adx_fa, adx_note = "بدون رونده", "زیر ۱۸ یعنی بازار بی‌جهته"
    if SigEnum.is_long(signal) or SigEnum.is_short(signal):
        direction_fa = "صعودی" if SigEnum.is_long(signal) else "نزولی"
        lines.extend(
            [f"جهت غالب {direction_fa}ه و {adx_fa} (ADX={adx:.0f}).", f"{adx_note}."]
        )
    else:
        if neutral_explain and neutral_explain.get("long"):
            lines.append(neutral_explain["long"])
        else:
            lines.extend(
                [
                    f"بازار در رژیم «{regime_fa}» هست و {adx_fa} (ADX={adx:.0f}).",
                    f"{adx_note}.",
                ]
            )
    if override_reason:
        lines.extend(["", f"⚠️ {override_reason}"])
    lines.append("")
    if SigEnum.is_long(signal) or SigEnum.is_short(signal):
        lines.extend([H("۲. چرا این سیگنال؟"), ""])
        GROUP_META = {
            "momentum": "مومنتوم",
            "trend": "روند",
            "volatility": "نوسان",
            "volume": "حجم",
            "structure": "ساختار",
        }
        if groups:
            for g_key, g_data in sorted(
                groups.items(), key=lambda x: abs(x[1].get("score", 0)), reverse=True
            )[:3]:
                g_name, g_vote, g_strength_fa, g_reasons = (
                    GROUP_META.get(g_key, g_key),
                    g_data.get("vote", 0),
                    g_data.get("strength_fa", ""),
                    g_data.get("reasons", []),
                )
                direction_mark = "▲" if g_vote > 0 else ("▼" if g_vote < 0 else "●")
                strength_txt = (
                    f" · {g_strength_fa}"
                    if g_strength_fa and g_strength_fa != "بی‌جهت"
                    else ""
                )
                lines.append(f"**{g_name}{strength_txt}** {direction_mark}")
                for reason in g_reasons[:2]:
                    lines.append(f"  {reason.strip()}")
                lines.append("")
    lines.extend([H("۳. نظر گروه‌ها"), ""])
    if votes_long > votes_short:
        summary = (
            f"{votes_long} گروه صعودی · {votes_neutral} خنثی · {votes_short} نزولی"
        )
    elif votes_short > votes_long:
        summary = (
            f"{votes_short} گروه نزولی · {votes_neutral} خنثی · {votes_long} صعودی"
        )
    elif votes_long == votes_short and votes_long > 0:
        summary = f"تعادل: {votes_long} صعودی مقابل {votes_short} نزولی"
    else:
        summary = f"{votes_neutral} گروه خنثی — بازار خوابه"
    lines.extend([summary, ""])
    if groups:
        GROUP_META = {
            "momentum": "مومنتوم",
            "trend": "روند",
            "volatility": "نوسان",
            "volume": "حجم",
            "structure": "ساختار",
        }
        ORDER = ["momentum", "trend", "volume", "volatility", "structure"]
        lines.extend(["| گروه | نظر | قدرت |", "|------|-----|------|"])
        for g_key in ORDER:
            if g_key not in groups:
                continue
            g_data, g_name, g_vote, g_strength_fa = (
                groups[g_key],
                GROUP_META.get(g_key, g_key),
                groups[g_key].get("vote", 0),
                groups[g_key].get("strength_fa", ""),
            )
            verdict = (
                "▲ صعودی" if g_vote > 0 else ("▼ نزولی" if g_vote < 0 else "● خنثی")
            )
            strength_txt = (
                g_strength_fa if g_strength_fa and g_strength_fa != "بی‌جهت" else "—"
            )
            lines.append(f"| {g_name} | {verdict} | {strength_txt} |")
        lines.append("")
    if divergence.get("has_divergence"):
        lines.extend([f"⚠️ واگرایی: {divergence.get('reason', '')}", ""])
    if multi_tf_info and multi_tf_info != "بدون بررسی":
        lines.extend([f"🎯 {multi_tf_info}", ""])
    ob = r_main.get("orderbook")
    if ob and ob.get("imbalance") is not None:
        lines.extend([H("۴. عمق بازار"), ""])
        imb, spread_pct = ob["imbalance"], ob.get("spread_pct", 0)
        if imb > 0.65:
            imb_fa = f"فشار خریدارها قویه — {imb*100:.0f}٪ خرید در برابر {(1-imb)*100:.0f}٪ فروش"
        elif imb < 0.35:
            imb_fa = f"فشار فروشنده‌ها قویه — {(1-imb)*100:.0f}٪ فروش در برابر {imb*100:.0f}٪ خرید"
        else:
            imb_fa = f"تعادل خریدار/فروشنده — {imb*100:.0f}٪ خرید در برابر {(1-imb)*100:.0f}٪ فروش"
        lines.append(f"• {imb_fa}")
        if spread_pct > 0.5:
            spread_fa = f"اسپرد بالا ({spread_pct:.2f}٪) — نقدینگی ضعیف، مراقب باش"
        elif spread_pct > 0.1:
            spread_fa = f"اسپرد متوسط ({spread_pct:.2f}٪) — قابل قبول"
        else:
            spread_fa = f"اسپرد کم ({spread_pct:.3f}٪) — بازار نقدشونده"
        lines.append(f"• {spread_fa}")
        wall = ob.get("wall")
        if wall:
            lines.append(
                f"• دیوار سفارش {'خرید' if wall['side'] == 'bid' else 'فروش'} در {wall['price']:,.2f} ({wall['ratio']:.1f}× حجم معمولی)"
            )
        lines.append("")
    r, s = safe_num(r_main.get("resistance")), safe_num(r_main.get("support"))
    if (r > 0 or s > 0) and price > 0:
        lines.extend([H("۵. سطوح کلیدی"), ""])
        if r > 0:
            dist_r = (r - price) / price * 100
            proximity = (
                "خیلی نزدیک، مراقب برگشت"
                if dist_r < 1.0
                else ("متوسط" if dist_r < 3.0 else "دور")
            )
            if is_tsetmc:
                lines.append(
                    f"🔴 **مقاومت:** {r:,.0f} ریال ({dist_r:+.2f}٪ — {proximity})"
                )
            elif is_iranian:
                lines.append(
                    f"🔴 **مقاومت:** {r:,.0f} تومان ({dist_r:+.2f}٪ — {proximity})"
                )
            else:
                lines.append(f"🔴 **مقاومت:** {r:,.2f}$ ({dist_r:+.2f}٪ — {proximity})")
        if s > 0:
            dist_s = (s - price) / price * 100
            proximity_s = (
                "خیلی نزدیک"
                if abs(dist_s) < 1.0
                else ("متوسط" if abs(dist_s) < 3.0 else "دور")
            )
            if is_tsetmc:
                lines.append(
                    f"🟢 **حمایت:** {s:,.0f} ریال ({dist_s:+.2f}٪ — {proximity_s})"
                )
            elif is_iranian:
                lines.append(
                    f"🟢 **حمایت:** {s:,.0f} تومان ({dist_s:+.2f}٪ — {proximity_s})"
                )
            else:
                lines.append(
                    f"🟢 **حمایت:** {s:,.2f}$ ({dist_s:+.2f}٪ — {proximity_s})"
                )
        lines.append("")
    if scenarios:
        lines.extend([H("۶. سناریوهای پیش‌رو"), ""])
        for sc in scenarios[:3]:
            lines.extend(
                [
                    f"{sc.get('icon', '•')} {sc.get('condition', '')} (احتمال {int(sc.get('probability', 0.5) * 100)}٪)",
                    f"   ↪️ {sc.get('action', '')}",
                    "",
                ]
            )
    lines.extend([H("جمع‌بندی"), ""])
    if SigEnum.is_long(signal) and confidence >= 85 and not active_traps:
        lines.append(
            "💎 **سیگنال طلایی!** — این فرصت نایابه. می‌تونی با اطمینان بالا وارد شی."
        )
    elif SigEnum.is_long(signal) and confidence >= 70 and not active_traps:
        lines.append("✅ **می‌تونی وارد شی** — اطمینان بالا، تله‌ای نیست.")
        if r > 0 and (r - price) / price * 100 < 1.5:
            lines.append(f"⚠️ ولی مقاومت {r:,.0f} نزدیکه — TP رو کمی پایین‌تر بذار.")
    elif SigEnum.is_long(signal) and active_traps:
        lines.append("🚨 **صبر کن** — تله فعاله. حتی با سیگنال LONG، الان نخر.")
    elif SigEnum.is_long(signal) and confidence >= 50:
        lines.append("⚠️ **با احتیاط وارد شو** — فقط با ۰.۵-۱٪ سرمایه.")
    elif SigEnum.is_long(signal):
        lines.append("🟡 **صبر کن** — سیگنال ضعیفه، احتمال خطا بالاست.")
    elif SigEnum.is_short(signal) and confidence >= 85 and not active_traps:
        lines.append("💎 **سیگنال طلایی فروش!** — این فرصت نایابه.")
    elif SigEnum.is_short(signal) and confidence >= 70:
        lines.append("🔴 **SHORT منطقیه** — ولی SL تنگ بذار، نوسان بالاست.")
    elif SigEnum.is_short(signal) and confidence >= 50:
        lines.append("🔴 **SHORT با احتیاط** — سریع خارج شو.")
    elif SigEnum.is_short(signal):
        lines.append("🟠 **صبر کن** — ریسک SHORT ضعیف بالاست.")
    else:
        if override_reason:
            lines.append("⏸ **وارد نشو** — رفتن خلاف روند قوی، پول سوزوندنه.")
        else:
            lines.append(
                "⏸ **بهترین معامله، معامله‌ای هست که انجام نشه.** صبر کن تا سیگنال واضح بیاد."
            )
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 🔴 ai_export — واقعاً خام (فاز ۱۲.۶)
# ═══════════════════════════════════════════════════════════
def _now_shamsi_str() -> str:
    try:
        now = datetime.now(ZoneInfo("Asia/Tehran"))
        try:
            import jdatetime

            j = jdatetime.datetime.fromgregorian(datetime=now)
            date_str = f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
        except ImportError:
            date_str = now.strftime("%Y/%m/%d")
        return f"{date_str} {now.strftime('%H:%M:%S')}"
    except Exception:
        return "—"


def _build_ai_export(
    ticker: str,
    name: str,
    tf_name: str,
    analysis: dict,
    tfs_data: dict | None = None,
    df=None,
) -> str:
    if not analysis:
        return ""
    lines: list[str] = []
    L = lines.append
    L(f"# دیتای خام: {name} ({ticker}) — {tf_name}")
    L("")
    L("## شناسنامه")
    L(f"- نماد: {ticker}")
    L(f"- نام: {name}")
    L(f"- تایم‌فریم: {tf_name}")
    L(f"- منبع درخواست: {analysis.get('source', '—')}")
    L(f"- منبع واقعی: {analysis.get('source_used', '—')}")
    L(
        f"- نوع بازار: {'فیوچرز' if analysis.get('market_type') == 'futures' else 'اسپات'}"
    )
    L(f"- پروفایل ریسک: {analysis.get('risk_profile', '—')}")
    L(f"- زمان تحلیل: {_now_shamsi_str()}")
    L("")
    if df is not None and not df.empty:
        try:
            tail = df.tail(30)
            has_vol = "volume" in tail.columns
            L("## OHLCV (۳۰ کندل آخر)")
            if has_vol:
                L("timestamp,open,high,low,close,volume")
            else:
                L("timestamp,open,high,low,close")
            for ts, row in tail.iterrows():
                ts_str = str(ts) if hasattr(ts, "strftime") else str(ts)
                o = row.get("open", 0)
                h = row.get("high", 0)
                l = row.get("low", 0)
                c = row.get("close", 0)
                if has_vol:
                    v = row.get("volume", 0)
                    L(f"{ts_str},{o},{h},{l},{c},{v}")
                else:
                    L(f"{ts_str},{o},{h},{l},{c}")
            L("")
        except Exception as e:
            logger.warning(f"[Analyzer] ai_export OHLCV: {e!r}")
    L("## اندیکاتورهای تکنیکال (خام)")
    for key, label in [
        ("rsi", "rsi_14"),
        ("stoch_k", "stoch_k_5_3_3"),
        ("stoch_d", "stoch_d_5_3_3"),
        ("willr", "williams_r_14"),
        ("cci", "cci_20"),
        ("roc", "roc_10"),
    ]:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")
    L("### روند")
    for key, label in [
        ("ema200", "ema_200"),
        ("ema50", "ema_50"),
        ("ema20", "ema_20"),
        ("macd_hist", "macd_hist_12_26_9"),
        ("adx", "adx_14"),
        ("dmp", "di_plus_14"),
        ("dmn", "di_minus_14"),
    ]:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")
    L("### نوسان")
    for key, label in [
        ("atr", "atr_14"),
        ("bb_upper", "bb_upper_20_2"),
        ("bb_lower", "bb_lower_20_2"),
    ]:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")
    L("### حجم")
    for key, label in [
        ("vol_ratio", "volume_ratio_vs_ma20"),
        ("cvd", "cvd_cumulative"),
        ("delta", "delta_buy_minus_sell"),
    ]:
        v = analysis.get(key)
        if v is not None:
            L(f"- {label}: {v}")
    L("")
    L("## سطوح کلیدی (محاسبه ریاضی)")
    price = analysis.get("price")
    if price:
        L(f"- قیمت فعلی: {price}")
    pivots = analysis.get("pivots") or {}
    if pivots:
        L("- Pivot Points (روزانه):")
        for k, v in pivots.items():
            L(f"  - {k}: {v}")
    support = analysis.get("support")
    resistance = analysis.get("resistance")
    if support:
        L(f"- حمایت نزدیک (Swing): {support}")
    if resistance:
        L(f"- مقاومت نزدیک (Swing): {resistance}")
    fib = analysis.get("fibonacci") or {}
    if fib and fib.get("levels"):
        L("- Fibonacci retracement:")
        for ratio, level in fib["levels"].items():
            L(f"  - {ratio}: {level}")
    L("")
    ob = analysis.get("orderbook")
    if ob and ob.get("imbalance") is not None:
        L("## عمق بازار (اسنپ‌شات)")
        L(f"- best_bid: {ob.get('best_bid')}")
        L(f"- best_ask: {ob.get('best_ask')}")
        L(f"- mid: {ob.get('mid')}")
        L(f"- spread: {ob.get('spread')}")
        L(f"- spread_pct: {ob.get('spread_pct')}%")
        L(f"- imbalance (bid/(bid+ask)): {ob.get('imbalance')}")
        L(f"- bid_volume: {ob.get('bid_volume')}")
        L(f"- ask_volume: {ob.get('ask_volume')}")
        L(f"- depth_value: {ob.get('depth_value')}")
        L("")
    close_series = analysis.get("close_series") or []
    if close_series:
        L("## سری close (۳۰ کندل آخر — برای نمودار)")
        L(",".join(str(round(c, 4)) for c in close_series))
        L("")
    L("---")
    L("")
    L("⚠️ **این دیتای خام است — بدون تحلیل یا جهت‌گیری.**")
    L("سیستم تحلیل ما هم ممکنه اشتباه کرده باشه.")
    L("تو به عنوان یک تحلیل‌گر مستقل، از این اعداد استفاده کن و خودت تحلیل کن.")
    L("")
    L("⏰ زمان تولید: " + _now_shamsi_str())
    L(f"🏷️ نسخه analyzer: {ANALYZER_VERSION}")
    return "\n".join(lines)


__all__ = [
    "RISK_PROFILES",
    "CONFIDENCE_TIERS",
    "CONFIDENCE_LEVELS",
    "MIN_CONF_TO_SHOW",
    "TF_CONFIDENCE_OFFSET",
    "TF_RR_PROFILES",
    "ANALYZER_VERSION",
    "classify_regime",
    "compute_indicators",
    "compute_pivot_points",
    "find_swing_points",
    "compute_fibonacci",
    "analyze_symbol",
    "compute_fear_greed",
    "build_checklist_weighted",
    "build_analysis_paragraph",
    "GROUP_LABELS",
    "_detect_traps",
    "_traps_summary",
    "build_scenarios",
]
