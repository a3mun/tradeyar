"""
core/tabdeal_fetcher.py
صرافی تبدیل (Tabdeal) — API عمومی
============================================================
نسخه ۱.۰ · فاز ۶.۸

═══ مستندات واقعی (تأیید تجربی ۱۴۰۵/۰۷) ═══

Base URL::

    https://api1.tabdeal.org/r

⚠️ **فرمت نماد حیاتی است:**
    • ``symbol``       → ``BTCIRT``  (بدون جداکننده) ← در URL
    • ``tabdealSymbol`` → ``BTC_IRT`` (با زیرخط)     ← فقط نمایشی

    اگر با ``BTC_IRT`` درخواست بزنی، تبدیل **۴۰۴** می‌دهد.
    این نکته در مستندات رسمی مبهم است و تجربی کشف شد.

═══ endpointهای تأییدشده ═══

    ✅ GET /api/v1/exchangeInfo          — ۱۰۴۶ بازار (IRT و USDT)
    ✅ GET /api/v1/depth?symbol=X&limit=N — عمق بازار
    ✅ GET /api/v1/trades?symbol=X&limit=N— معاملات اخیر

═══ endpointهای **موجود نیست** ═══

    ❌ /api/v1/history    (۴۰۴)
    ❌ /api/v1/klines     (۴۰۴)
    ❌ /api/v1/ohlcv      (۴۰۴)
    ❌ /api/v1/candles    (۴۰۴)
    ❌ /api/v1/udf/history(۴۰۴)
    ❌ /api/v1/ticker/*   (۴۰۴)

    → **تبدیل OHLCV عمومی ندارد.** پس تحلیل تکنیکال مثل
      نوبیتکس/بیت‌پین/والکس برایش ممکن نیست. تحلیل با fallback
      به صرافی دیگر انجام می‌شود (شفاف با ``source_used``).

═══ وضعیت قابلیت‌ها ═══

    ┌──────────────┬────────┐
    │ قابلیت       │ وضعیت  │
    ├──────────────┼────────┤
    │ قیمت لحظه‌ای │ ✅     │ ← از depth (mid) + trades (last)
    │ عمق بازار    │ ✅     │ ← /depth  (فاز ۶.۵ آماده)
    │ معاملات      │ ✅     │ ← /trades (برای CVD دقیق‌تر)
    │ OHLCV        │ ❌     │ ← fallback به صرافی دیگر
    └──────────────┴────────┘

═══ نکته ═══
قیمت از ``depth`` (میانه‌ی بهترین bid/ask) گرفته می‌شود، نه
``trades``. دلیل: آخرین معامله ممکن است دقایق قبل باشد، ولی
عمق بازار **همیشه** زنده است. برای نماد کم‌معامله این تفاوت
مهم است.
"""

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

# ─── کش ماژول برای exchangeInfo (سنگین: ~۱MB) ───
_EXCHANGE_INFO: Optional[list] = None
_MARKET_MAP: dict[str, str] = {}  # {"BTC-USD": "BTCUSDT", "BTC-IRT": "BTCIRT"}


# ═══════════════════════════════════════════════════════════
# نگاشت نماد
# ═══════════════════════════════════════════════════════════
def _load_exchange_info(force: bool = False) -> list:
    """
    دریافت (و کش) لیست بازارها.

    ⚠️ این پاسخ ~۱MB است. یک بار در طول عمر پروسه گرفته
       می‌شود و در ماژول کش می‌ماند.
    """
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

    # ─── ساخت نقشه: ticker استاندارد ما → symbol تبدیل ───
    mapping: dict[str, str] = {}
    for m in data:
        if m.get("status") != "TRADING":
            continue
        base = m.get("baseAsset")
        quote = m.get("quoteAsset")
        symbol = m.get("symbol")  # ← بدون جداکننده: BTCIRT
        if not (base and quote and symbol):
            continue

        # ─── USDT → پسوند -USD (قرارداد داخلی ما) ───
        if quote == "USDT":
            mapping[f"{base}-USD"] = symbol
        elif quote == "IRT":
            mapping[f"{base}-IRT"] = symbol

    _MARKET_MAP = mapping
    logger.info(f"[Tabdeal] {len(mapping)} بازار بارگذاری شد")
    return data


def map_symbol_to_tabdeal(ticker: str) -> Optional[str]:
    """
    نگاشت نماد به فرمت تبدیل.

    Examples:
        >>> map_symbol_to_tabdeal("BTC-USD")
        'BTCUSDT'
        >>> map_symbol_to_tabdeal("BTC-IRT")
        'BTCIRT'
        >>> map_symbol_to_tabdeal("DOES-NOT-EXIST")
        None

    ⚠️ خروجی **بدون** جداکننده است (``BTCIRT`` نه ``BTC_IRT``).
    """
    if not ticker:
        return None

    if not _MARKET_MAP:
        _load_exchange_info()

    upper = ticker.upper().replace("_", "-")

    # ─── نرمال‌سازی: BTCUSDT → BTC-USD ───
    if "-" not in upper:
        for suffix, repl in (("USDT", "-USD"), ("IRT", "-IRT"), ("RLS", "-IRT")):
            if upper.endswith(suffix):
                upper = upper[: -len(suffix)] + repl
                break

    if upper in _MARKET_MAP:
        return _MARKET_MAP[upper]

    # ─── تلاش دوم: USDT ↔ USD ───
    if upper.endswith("-USDT"):
        alt = upper[:-5] + "-USD"
        if alt in _MARKET_MAP:
            return _MARKET_MAP[alt]

    return None


def tabdeal_symbol_to_display(symbol: str) -> str:
    """
    تبدیل symbol به فرمت نمایشی تبدیل (``BTCIRT`` → ``BTC_IRT``).

    ⚠️ فقط برای نمایش — در URL همیشه ``symbol`` بدون جداکننده.
    """
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
    """
    آیا تبدیل این تایم‌فریم را دارد؟

    ⚠️ فعلاً **همیشه False** — چون OHLCV عمومی ندارد.
       (کد آماده است تا اگر endpoint اضافه شد، فقط True برگردانیم.)
    """
    return False


# ═══════════════════════════════════════════════════════════
# OHLCV — ❌ در دسترس نیست
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_candles(
    ticker: str,
    tf_name: str = "۵ دقیقه",
) -> Optional[pd.DataFrame]:
    """
    دریافت کندل — ❌ **در دسترس نیست**.

    ═══ چرا ═══
    API عمومی تبدیل endpoint OHLCV ندارد. ۱۲ مسیر مختلف تست شد:

        /api/v1/history      → 404
        /api/v1/klines       → 404
        /api/v1/ohlcv        → 404
        /api/v1/candles      → 404
        /api/v1/udf/history  → 404
        /api/v1/market/klines→ 404
        /api/v1/chart        → 404
        … و ۵ مسیر دیگر

    ═══ چه می‌شود ═══
    زنجیره‌ی fallback در ``data_service`` خودکار از نوبیتکس/
    بیت‌پین/والکس کندل می‌گیرد و تحلیل انجام می‌شود. منبع واقعی
    در ``source_used`` برچسب می‌خورد.

    Returns:
        همیشه ``None`` (تا زمانی که تبدیل API کندل بدهد).
    """
    logger.debug(
        f"[Tabdeal] {ticker}/{tf_name}: کندل در دسترس نیست "
        f"(API عمومی OHLCV ندارد) — fallback به صرافی دیگر"
    )
    return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای — ✅ از depth
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_depth(
    ticker: str,
    limit: int = 20,
) -> Optional[dict]:
    """
    عمق بازار خام.

    Returns:
        ``{"asks": [[price, qty], ...], "bids": [[price, qty], ...]}``
        یا ``None``.
    """
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


def fetch_tabdeal_ticker(ticker: str) -> Optional[dict]:
    """
    قیمت لحظه‌ای — از **عمق بازار** (نه آخرین معامله).

    چرا میانه‌ی بهترین bid/ask:
        آخرین معامله ممکن است دقایق قبل باشد (خصوصاً نماد
        کم‌معامله)، ولی عمق بازار همیشه زنده است. میانه‌ی
        best_bid و best_ask بهترین تخمین «قیمت منصفانه‌ی فعلی»
        است و اسپرد را هم می‌دهد.

    Returns:
        ``{"price", "change_24h", "best_bid", "best_ask", "spread_pct"}``
        یا ``None``.
    """
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
            # ⚠️ تبدیل endpoint تغییر ۲۴ ساعته ندارد
            "change_24h": 0.0,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_pct": spread_pct,
        }
    except Exception as e:
        logger.warning(f"[Tabdeal] parse ticker {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# معاملات اخیر — ✅ (برای CVD دقیق‌تر در فاز ۶.۵)
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_trades(ticker: str, limit: int = 100) -> Optional[list]:
    """
    معاملات اخیر — برای محاسبه‌ی جریان سفارش (order flow).

    هر آیتم::

        {"price": float, "qty": float, "time": int(ms), "buyer_maker": bool}

    ⚠️ ``buyer_maker=False`` یعنی خریدار aggressor بوده (فشار خرید).
    """
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
            logger.debug(f"[Tabdeal] trades {symbol}: HTTP {r.status_code}")
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
                    # ⚠️ isBuyerMaker=True → فروشنده aggressor
                    "buyer_maker": bool(t.get("isBuyerMaker")),
                }
            )
        except Exception:
            continue
    return out


# ═══════════════════════════════════════════════════════════
# Order Book — ✅ (قرارداد فاز ۶.۵)
# ═══════════════════════════════════════════════════════════
def fetch_tabdeal_orderbook(ticker: str, depth: int = 20) -> Optional[dict]:
    """
    عمق بازار نرمال‌شده — آماده برای فاز ۶.۵.

    Returns::

        {
          "ticker": "BTC-IRT",
          "source": "tabdeal",
          "bids": [{"price": ..., "quantity": ...}, ...],
          "asks": [...],
          "best_bid": ..., "best_ask": ...,
          "spread": ..., "spread_pct": ...,
          "imbalance": ...,   # 0..1
        }

    ⚠️ ``imbalance`` = حجم bids / (حجم bids + حجم asks).
       بالای ۰.۵ → فشار خرید، زیر ۰.۵ → فشار فروش.
    """
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
