"""
core/wallex_fetcher.py
صرافی والکس — API عمومی v1
============================================================
Endpoints:
  - Markets:    /v1/markets
  - UDF History: /v1/udf/history
  - Depth:      /v1/depth
  - Trades:     /v1/trades
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.wallex.ir"
TIMEOUT = 15
HEADERS = {
    "User-Agent": "TraderBot/Trademun-1.0.0",
    "Accept": "application/json",
}


# ═══════════════════════════════════════════════════════════
# نقشه نماد (BTC-USD → BTCUSDT)
# ═══════════════════════════════════════════════════════════
def map_symbol_to_wallex(ticker: str) -> str:
    """تبدیل BTC-USD به BTCUSDT"""
    if not ticker:
        return ""
    upper = ticker.upper()
    if upper.endswith("-USD"):
        return upper.replace("-USD", "USDT")
    if upper.endswith("-USDT"):
        return upper.replace("-USDT", "USDT")
    if upper.endswith("-IRT"):
        return upper.replace("-IRT", "TMN")
    if upper.endswith("-RLS"):
        return upper.replace("-RLS", "TMN")
    return upper.replace("-", "")


def map_wallex_to_symbol(wallex_sym: str) -> str:
    """تبدیل BTCUSDT به BTC-USD"""
    if not wallex_sym:
        return ""
    upper = wallex_sym.upper()
    if upper.endswith("USDT"):
        return upper[:-4] + "-USD"
    if upper.endswith("TMN"):
        return upper[:-3] + "-IRT"
    return upper


# ═══════════════════════════════════════════════════════════
# نقشه TF (ایران → Wallex)
# ═══════════════════════════════════════════════════════════
TF_MAP = {
    "۱ دقیقه": "1",
    "۵ دقیقه": "15",  # Wallex ۵ دقیقه نداره → نزدیک‌ترین ۱۵
    "۱۵ دقیقه": "15",
    "۳۰ دقیقه": "60",  # Wallex ۳۰ نداره → ۱ ساعت
    "۱ ساعت": "60",
    "روزانه": "1D",
}

PERIOD_MAP = {
    "۱ دقیقه": 1,
    "۵ دقیقه": 5,
    "۱۵ دقیقه": 5,
    "۳۰ دقیقه": 14,
    "۱ ساعت": 14,
    "روزانه": 90,
}


def map_tf(tf_name: str) -> str:
    return TF_MAP.get(tf_name, "15")


# ═══════════════════════════════════════════════════════════
# دریافت OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_wallex_candles(ticker: str, tf_name: str = "۵ دقیقه") -> pd.DataFrame | None:
    """
    دریافت کندل‌های والکس (UDF format).
    Response: {s, t: [...], o: [...], h: [...], l: [...], c: [...], v: [...]}
    """
    symbol = map_symbol_to_wallex(ticker)
    if not symbol:
        return None

    res = map_tf(tf_name)
    days = PERIOD_MAP.get(tf_name, 3)

    to_ts = int(datetime.now().timestamp())
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    url = f"{BASE_URL}/v1/udf/history"
    params = {
        "symbol": symbol,
        "resolution": res,
        "from": from_ts,
        "to": to_ts,
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Wallex] {ticker}: {e}")
        return None

    if not data or data.get("s") != "ok":
        return None

    try:
        df = pd.DataFrame(
            {
                "time": pd.to_datetime(data["t"], unit="s"),
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            }
        )
        df.set_index("time", inplace=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(inplace=True)
        df.sort_index(inplace=True)

        if len(df) < 20:
            return None

        return df
    except Exception as e:
        logger.warning(f"[Wallex] parse {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای
# ═══════════════════════════════════════════════════════════
def fetch_wallex_ticker(ticker: str) -> dict | None:
    """دریافت قیمت لحظه‌ای از markets"""
    symbol = map_symbol_to_wallex(ticker)
    if not symbol:
        return None

    try:
        r = requests.get(
            f"{BASE_URL}/v1/markets",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Wallex] ticker {ticker}: {e}")
        return None

    symbols = data.get("result", {}).get("symbols", {})
    item = symbols.get(symbol)
    if not item:
        return None

    try:
        stats = item.get("stats", {})
        return {
            "price": float(stats.get("lastPrice", 0)),
            "change_24h": float(stats.get("24h_ch", 0)),
            "high": float(stats.get("24h_highPrice", 0)),
            "low": float(stats.get("24h_lowPrice", 0)),
        }
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════
# Order Book
# ═══════════════════════════════════════════════════════════
def fetch_wallex_orderbook(ticker: str) -> dict | None:
    """عمق بازار والکس"""
    symbol = map_symbol_to_wallex(ticker)
    if not symbol:
        return None

    try:
        r = requests.get(
            f"{BASE_URL}/v1/depth",
            params={"symbol": symbol},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Wallex] orderbook {ticker}: {e}")
        return None

    try:
        result = data.get("result", {})
        bids = [
            (float(x["price"]), float(x["quantity"])) for x in result.get("bid", [])
        ]
        asks = [
            (float(x["price"]), float(x["quantity"])) for x in result.get("ask", [])
        ]
        return {"bids": bids, "asks": asks}
    except Exception:
        return None
