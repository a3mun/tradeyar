"""
core/tabdeal_fetcher.py
صرافی تبدیل (Tabdeal) — API عمومی
============================================================
نسخه ۲.۰ · فاز ۱۶.۴

🔴 تغییرات نسخه ۲.۰:
  • WebSocket برای نمادهای پرمعامله (سریع و زنده)
  • fallback به REST برای بقیه نمادها
  • limit افزایش یافت (100) برای حجم بهتر

═══ مستندات واقعی (تأیید تجربی ۱۴۰۵/۰۷) ═══

Base URL::

    https://api1.tabdeal.org/r

⚠️ **فرمت نماد حیاتی است:**
    • ``symbol``       → ``BTCIRT``  (بدون جداکننده) ← در URL
    • ``tabdealSymbol`` → ``BTC_IRT`` (با زیرخط)     ← فقط نمایشی

═══ endpointهای موجود ═══

    ✅ GET /api/v1/exchangeInfo          — لیست بازارها
    ✅ GET /api/v1/depth?symbol=X&limit=N — عمق بازار
    ✅ GET /api/v1/trades?symbol=X&limit=N— معاملات اخیر
    ✅ wss://api1.tabdeal.org/stream/    — WebSocket قیمت لحظه‌ای

═══ endpointهای **موجود نیست** ═══

    ❌ /api/v1/history, /klines, /ohlcv, /candles, ...

    → تبدیل OHLCV عمومی ندارد. تحلیل با fallback به صرافی دیگر.
"""

import json
import logging
from typing import Optional

import pandas as pd
import requests

from core.utils import parse_number

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# ثابت‌ها
# ═══════════════════════════════════════════════════════════
BASE_URL = "https://api1.tabdeal.org/r"
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ─── کش ماژول برای exchangeInfo ───
_EXCHANGE_INFO: Optional[list] = None
_MARKET_MAP: dict[str, str] = {}


# ═══════════════════════════════════════════════════════════
# نگاشت نماد
# ═══════════════════════════════════════════════════════════
def _load_exchange_info(force: bool = False) -> list:
    """دریافت و کش لیست بازارهای تبدیل"""
    global _EXCHANGE_INFO, _MARKET_MAP

    if _EXCHANGE_INFO is not None and not force:
        return _EXCHANGE_INFO

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/exchangeInfo",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[Tabdeal] exchangeInfo: {e}")
        return []

    if not isinstance(data, list):
        return []

    _EXCHANGE_INFO = data

    mapping: dict[str, str] = {}
    for m in data:
        if m.get("status") != "TRADING":
            continue
        base = m.get("baseAsset")
        quote = m.get("quoteAsset")
        symbol = m.get("symbol")
        if not (base and quote and symbol):
            continue

        if quote == "USDT":
            mapping[f"{base}-USD"] = symbol
        elif quote == "IRT":
            mapping[f"{base}-IRT"] = symbol

    _MARKET_MAP = mapping
    logger.info(f"[Tabdeal] {len(mapping)} بازار بارگذاری شد")
    return data


def map_symbol_to_tabdeal(ticker: str) -> Optional[str]:
    """نگاشت نماد به فرمت تبدیل"""
    if not ticker:
        return None

    if not _MARKET_MAP:
        _load_exchange_info()

    upper = ticker.upper().replace("_", "-")

    if "-" not in upper:
        for suffix, repl in (("USDT", "-USD"), ("IRT", "-IRT"), ("RLS", "-IRT")):
            if upper.endswith(suffix):
                upper = upper[: -len(suffix)] + repl
                break

    if upper in _MARKET_MAP:
        return _MARKET_MAP[upper]

    if upper.endswith("-USDT"):
        alt = upper[:-5] + "-USD"
        if alt in _MARKET_MAP:
            return _MARKET_MAP[alt]

    return None


def tabdeal_symbol_to_display(symbol: str) -> str:
    """تبدیل symbol به فرمت نمایشی تبدیل"""
    if not symbol:
        return ""
    data = _load_exchange_info()
    for m in data:
        if m.get("symbol") == symbol:
            return m.get("tabdealSymbol") or symbol
    return symbol


def is_in_tabdeal(ticker: str) -> bool:
    """آیا این نماد روی تبدیل لیست شده؟"""
    return map_symbol_to_tabdeal(ticker) is not None


def supports_tf(tf_name: str) -> bool:
    """تبدیل OHLCV ندارد"""
    return False


# ═══════════════════════════════════════════════════════════
# OHLCV — ❌ در دسترس نیست
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_candles(
    ticker: str,
    tf_name: str = "۵ دقیقه",
) -> Optional[pd.DataFrame]:
    """دریافت کندل — ❌ در دسترس نیست (fallback به صرافی دیگر)"""
    logger.debug(
        f"[Tabdeal] {ticker}/{tf_name}: کندل در دسترس نیست "
        f"(API عمومی OHLCV ندارد) — fallback به صرافی دیگر"
    )
    return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای — ✅ اول WebSocket، بعد REST
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_ticker(ticker: str) -> Optional[dict]:
    """
    قیمت لحظه‌ای — اول از WebSocket (سریع و زنده)، بعد fallback به REST.
    """
    # 🔴 فاز ۱۶.۴ — اول WebSocket
    try:
        from core.tabdeal_ws import get_tabdeal_price

        ws_data = get_tabdeal_price(ticker)
        if ws_data and ws_data.get("price"):
            return {
                "price": ws_data["price"],
                "change_24h": 0.0,  # WebSocket تغییر ۲۴س نداره
                "best_bid": ws_data["best_bid"],
                "best_ask": ws_data["best_ask"],
                "spread_pct": ws_data.get("spread_pct", 0.0),
                "volume": ws_data.get("total_volume", 0.0),
            }
    except Exception as e:
        logger.debug(f"[Tabdeal] WS fallback: {e}")

    # ─── fallback به REST ───
    depth = fetch_tabdeal_depth(ticker, limit=1)
    if not depth:
        return None

    try:
        bids = depth.get("bids") or []
        asks = depth.get("asks") or []
        if not bids or not asks:
            return None

        best_bid = parse_number(bids[0][0])
        best_ask = parse_number(asks[0][0])

        if not best_bid or not best_ask or best_bid <= 0 or best_ask <= 0:
            return None

        mid = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid * 100 if mid else 0.0

        return {
            "price": mid,
            "change_24h": 0.0,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_pct": spread_pct,
        }
    except Exception as e:
        logger.warning(f"[Tabdeal] parse ticker {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# عمق بازار (REST)
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_depth(
    ticker: str,
    limit: int = 100,  # 🔴 از 20 به 100
) -> Optional[dict]:
    """عمق بازار خام"""
    symbol = map_symbol_to_tabdeal(ticker)
    if not symbol:
        return None

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/depth",
            headers=HEADERS,
            params={"symbol": symbol, "limit": limit},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            logger.debug(f"[Tabdeal] depth {symbol}: HTTP {r.status_code}")
            return None
        data = r.json()
    except Exception as e:
        logger.warning(f"[Tabdeal] depth {ticker}: {e}")
        return None

    if not isinstance(data, dict):
        return None
    return data


# ═══════════════════════════════════════════════════════════
# معاملات اخیر
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_trades(ticker: str, limit: int = 100) -> Optional[list]:
    """معاملات اخیر — برای order flow"""
    symbol = map_symbol_to_tabdeal(ticker)
    if not symbol:
        return None

    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/trades",
            headers=HEADERS,
            params={"symbol": symbol, "limit": limit},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception as e:
        logger.warning(f"[Tabdeal] trades {ticker}: {e}")
        return None

    if not isinstance(data, list):
        return None

    out = []
    for t in data:
        try:
            out.append(
                {
                    "price": parse_number(t.get("price")) or 0.0,
                    "qty": parse_number(t.get("qty")) or 0.0,
                    "time": int(t.get("time") or 0),
                    "buyer_maker": bool(t.get("isBuyerMaker")),
                }
            )
        except Exception:
            continue
    return out


# ═══════════════════════════════════════════════════════════
# Order Book — نرمال‌شده
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_orderbook(ticker: str, depth: int = 20) -> Optional[dict]:
    """عمق بازار نرمال‌شده"""
    raw = fetch_tabdeal_depth(ticker, limit=depth)
    if not raw:
        return None

    try:
        bids = [
            {"price": parse_number(p), "quantity": parse_number(q)}
            for p, q in (raw.get("bids") or [])
            if parse_number(p) and parse_number(q)
        ]
        asks = [
            {"price": parse_number(p), "quantity": parse_number(q)}
            for p, q in (raw.get("asks") or [])
            if parse_number(p) and parse_number(q)
        ]

        if not bids or not asks:
            return None

        best_bid = bids[0]["price"]
        best_ask = asks[0]["price"]
        mid = (best_bid + best_ask) / 2

        bid_vol = sum(b["quantity"] for b in bids)
        ask_vol = sum(a["quantity"] for a in asks)
        total_vol = bid_vol + ask_vol

        return {
            "ticker": ticker,
            "source": "tabdeal",
            "bids": bids,
            "asks": asks,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": best_ask - best_bid,
            "spread_pct": ((best_ask - best_bid) / mid * 100) if mid else 0.0,
            "imbalance": (bid_vol / total_vol) if total_vol else 0.5,
        }
    except Exception as e:
        logger.warning(f"[Tabdeal] orderbook {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "fetch_tabdeal_candles",
    "fetch_tabdeal_depth",
    "fetch_tabdeal_orderbook",
    "fetch_tabdeal_ticker",
    "fetch_tabdeal_trades",
    "is_in_tabdeal",
    "map_symbol_to_tabdeal",
    "supports_tf",
    "tabdeal_symbol_to_display",
]
