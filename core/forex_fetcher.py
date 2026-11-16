"""
core/forex_fetcher.py
OHLCV فارکس/کالا/شاخص از Biquote — نسخه ۲.۰
============================================================
🔴 تغییرات نسخه ۲.۰:
  • ۱۱ نماد (طلا، نقره، نفت، شاخص‌ها، یورو، بیت‌کوین)
  • حذف کندل فعلی (volume=0) برای جلوگیری از باگ analyzer
  • User-Agent از TraderBot (طبق مستندات)
"""

import logging
from typing import Optional

import pandas as pd
from core.utils import parse_number

from core.tz import ensure_utc_index

try:
    from biquote import Biquote
except ImportError:
    Biquote = None

logger = logging.getLogger(__name__)

# 🔴 نقشه‌ی TF (نام فارسی → interval Biquote)
_TF_TO_BIQUOTE = {
    "۱ دقیقه": "1m",
    "۵ دقیقه": "5m",
    "۱۵ دقیقه": "15m",
    "۳۰ دقیقه": "30m",
    "۱ ساعت": "1h",
    "روزانه": "1d",
}

# 🔴 نمادهای فارکس (Biquote → ticker استاندارد)
# کلید = ticker استاندارد، مقدار = symbol Biquote
_FOREX_SYMBOLS = {
    "XAU-USD": "XAUUSD",
    "XAG-USD": "XAGUSD",
    "USOIL-USD": "USOIL",
    "UKOIL-USD": "UKOIL",
    "DXY-USD": "DXY",
    "US500-USD": "US500",
    "US30-USD": "US30",
    "USTEC-USD": "USTEC",
    "EUR-USD": "EURUSD",
    "DE30-USD": "DE30",
    "BTC-USD": "BTCUSD",
}


def _to_biquote(ticker: str) -> Optional[str]:
    """XAU-USD → XAUUSD"""
    return _FOREX_SYMBOLS.get(ticker.upper())


def get_forex_symbols() -> dict:
    """نگاشت ticker → symbol Biquote"""
    return dict(_FOREX_SYMBOLS)


def fetch_forex_candles(
    ticker: str,
    tf_name: str = "۱ ساعت",
    limit: int = 500,
) -> Optional[pd.DataFrame]:
    """
    دریافت OHLCV از Biquote.

    ⚠️ کندل فعلی (ناقص) حذف می‌شه (volume=0) تا analyzer خراب نشه.
    """
    if Biquote is None:
        logger.debug("[Forex] biquote نصب نیست")
        return None

    symbol = _to_biquote(ticker)
    if not symbol:
        logger.debug(f"[Forex] {ticker}: نماد در Biquote نیست")
        return None

    interval = _TF_TO_BIQUOTE.get(tf_name)
    if not interval:
        logger.debug(f"[Forex] {tf_name}: TF در Biquote نیست")
        return None

    try:
        bq = Biquote()
        bars = bq.ohlc(symbol, interval=interval, limit=limit)
    except Exception as e:
        logger.warning(f"[Forex] ohlc {ticker}/{tf_name}: {e!r}")
        return None

    if not bars:
        return None

    try:
        df = pd.DataFrame(bars)
        # Biquote: openTime, open, high, low, close, volume
        df["time"] = pd.to_datetime(df["openTime"], utc=True)
        df.set_index("time", inplace=True)
        df = df[["open", "high", "low", "close", "volume"]].copy()

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].apply(
                lambda x: parse_number(x) if x is not None else None
            )

        # 🔴 فاز ۱۶.۵ — اگه volume صفره (فارکس/CFD)، از tickVolume یا range استفاده کن
        if df["volume"].sum() == 0:
            if "tickVolume" in df.columns:
                df["volume"] = pd.to_numeric(df["tickVolume"], errors="coerce").fillna(
                    0
                )
            if df["volume"].sum() == 0:
                # fallback: از range کندل به عنوان حجم ساختگی
                df["volume"] = (df["high"] - df["low"]) / df["close"] * 1000

        df.dropna(inplace=True)
        df = df[~df.index.duplicated(keep="last")]
        df.sort_index(inplace=True)

        # 🔴 حذف کندل فعلی (volume=0) — جلوگیری از باگ analyzer
        if len(df) > 30 and df["volume"].iloc[-1] == 0:
            df = df.iloc[:-1]

        df = ensure_utc_index(df)
        if df is None or df.empty or len(df) < 20:
            return None

        return df
    except Exception as e:
        logger.warning(f"[Forex] parse ohlc {ticker}: {e!r}")
        return None


def fetch_forex_ticker(ticker: str) -> Optional[dict]:
    """قیمت لحظه‌ای (REST) — fallback اگه WebSocket قطع شد."""
    if Biquote is None:
        return None

    symbol = _to_biquote(ticker)
    if not symbol:
        return None

    try:
        bq = Biquote()
        tick = bq.tick(symbol)
    except Exception as e:
        logger.debug(f"[Forex] tick {ticker}: {e!r}")
        return None

    if not tick:
        return None

    try:
        price = float(tick.get("mid") or 0)
        if price <= 0:
            return None

        return {
            "ticker": ticker,
            "price": price,
            "change_pct": float(tick.get("dayDiffPercent") or 0),
            "source": "forex",
        }
    except (TypeError, ValueError):
        return None


__all__ = [
    "fetch_forex_candles",
    "fetch_forex_ticker",
    "get_forex_symbols",
]
