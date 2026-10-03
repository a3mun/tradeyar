"""
core/bitpin_fetcher.py
صرافی بیت‌پین — API عمومی v1
============================================================
Endpoints:
  - Markets:    /api/v1/mkt/markets/
  - Candles:    /api/v1/mkt/candles/
  - Tickers:    /api/v1/mkt/tickers/
  - OrderBook:  /api/v1/mth/orderbook/{symbol}/
  - Trades:     /api/v1/mth/matches/{symbol}/
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.bitpin.org"
TIMEOUT = 15
HEADERS = {
    "User-Agent": "TraderBot/Trademun-1.0.0",
    "Accept": "application/json",
}


# ═══════════════════════════════════════════════════════════
# نقشه نماد (BTC-USD → BTC_USDT)
# ═══════════════════════════════════════════════════════════
def map_symbol_to_bitpin(ticker: str) -> str:
    """تبدیل BTC-USD به BTC_USDT"""
    if not ticker:
        return ""
    upper = ticker.upper()
    if upper.endswith("-USD"):
        return upper.replace("-USD", "_USDT")
    if upper.endswith("-USDT"):
        return upper.replace("-USDT", "_USDT")
    if upper.endswith("-IRT"):
        return upper.replace("-IRT", "_IRT")
    if upper.endswith("-RLS"):
        return upper.replace("-RLS", "_IRT")
    return upper.replace("-", "_")


def map_bitpin_to_symbol(bitpin_sym: str) -> str:
    """تبدیل BTC_USDT به BTC-USD"""
    if not bitpin_sym:
        return ""
    upper = bitpin_sym.upper()
    if upper.endswith("_USDT"):
        return upper.replace("_USDT", "-USD")
    if upper.endswith("_IRT"):
        return upper.replace("_IRT", "-IRT")
    return upper.replace("_", "-")


# ═══════════════════════════════════════════════════════════
# نقشه TF (ایران → Bitpin)
# ═══════════════════════════════════════════════════════════
TF_MAP = {
    "۱ دقیقه": "1m",
    "۵ دقیقه": "5m",
    "۱۵ دقیقه": "15m",
    "۳۰ دقیقه": "30m",
    "۱ ساعت": "1h",
    "روزانه": "1d",
}

PERIOD_MAP = {
    "۱ دقیقه": 1,
    "۵ دقیقه": 3,
    "۱۵ دقیقه": 5,
    "۳۰ دقیقه": 7,
    "۱ ساعت": 14,
    "روزانه": 90,
}


def map_tf(tf_name: str) -> str:
    return TF_MAP.get(tf_name, "5m")


# ═══════════════════════════════════════════════════════════
# دریافت OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_bitpin_candles(ticker: str, tf_name: str = "۵ دقیقه") -> pd.DataFrame | None:
    """
    دریافت کندل‌های بیت‌پین.
    symbol=BTC_USDT, res=5m, from, to (Unix seconds)
    """
    symbol = map_symbol_to_bitpin(ticker)
    if not symbol:
        return None

    res = map_tf(tf_name)
    days = PERIOD_MAP.get(tf_name, 3)

    to_ts = int(datetime.now().timestamp())
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    url = f"{BASE_URL}/api/v1/mkt/candles/"
    params = {
        "symbol": symbol,
        "from": from_ts,
        "to": to_ts,
        "res": res,
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Bitpin] {ticker}: {e}")
        return None

    if not data or not isinstance(data, list):
        return None

    try:
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["ts"], unit="s")
        df.set_index("time", inplace=True)

        # ─── تبدیل نوع (open/close عدد، low/high/volume رشته) ───
        for col in ["open", "close", "low", "high", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.dropna(inplace=True)
        df.sort_index(inplace=True)

        if len(df) < 20:
            return None

        return df
    except Exception as e:
        logger.warning(f"[Bitpin] parse {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای
# ═══════════════════════════════════════════════════════════
def fetch_bitpin_ticker(ticker: str) -> dict | None:
    """دریافت قیمت لحظه‌ای از tickers"""
    symbol = map_symbol_to_bitpin(ticker)
    if not symbol:
        return None

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/mkt/tickers/",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Bitpin] ticker {ticker}: {e}")
        return None

    if not isinstance(data, list):
        return None

    for item in data:
        if item.get("symbol") == symbol:
            try:
                return {
                    "price": float(item.get("price", 0)),
                    "change_24h": float(item.get("daily_change_price", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                }
            except Exception:
                return None

    return None


# ═══════════════════════════════════════════════════════════
# Order Book
# ═══════════════════════════════════════════════════════════
def fetch_bitpin_orderbook(ticker: str) -> dict | None:
    """عمق بازار بیت‌پین"""
    symbol = map_symbol_to_bitpin(ticker)
    if not symbol:
        return None

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/mth/orderbook/{symbol}/",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Bitpin] orderbook {ticker}: {e}")
        return None

    try:
        bids = [(float(p), float(q)) for p, q in data.get("bids", [])]
        asks = [(float(p), float(q)) for p, q in data.get("asks", [])]
        return {"bids": bids, "asks": asks}
    except Exception:
        return None
