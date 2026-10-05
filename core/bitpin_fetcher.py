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
from datetime import datetime, timezone

import pandas as pd
import requests

from core.contracts import TIMEFRAME_SPECS, get_tf_spec
from core.tz import ensure_utc_index
from core.utils import parse_number

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
# نقشه TF (نام فارسی → بیت‌پین)
# ═══════════════════════════════════════════════════════════
# بیت‌پین همه‌ی تایم‌فریم‌های ما را دارد؛ جدول از contracts می‌آید
# تا یک منبع حقیقت باشد.
TF_MAP: dict[str, str] = {
    s.name_fa: s.bitpin_res for s in TIMEFRAME_SPECS.values()
}


def map_tf(tf_name: str) -> str | None:
    """
    نام فارسی → resolution بیت‌پین.

    Returns:
        resolution، یا ``None`` اگر ناشناخته باشد (به‌جای پیش‌فرض
        بی‌صدا به "5m").
    """
    return TF_MAP.get(tf_name)


def supports_tf(tf_name: str) -> bool:
    """آیا بیت‌پین از این تایم‌فریم پشتیبانی می‌کند؟"""
    return tf_name in TF_MAP


# ═══════════════════════════════════════════════════════════
# دریافت OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_bitpin_candles(ticker: str, tf_name: str = "۵ دقیقه") -> pd.DataFrame | None:
    """
    دریافت کندل‌های بیت‌پین.
    symbol=BTC_USDT, res=5m, from, to (Unix seconds)

    ⚠️ tf_name باید نام فارسی باشد («۵ دقیقه»، «۱ ساعت»، ...).
       پیش از این، اگر tf_name انگلیسی ("5m") پاس می‌شد،
       ``TF_MAP.get`` شکست می‌خورد و **بی‌صدا** به ۵ دقیقه
       برمی‌گشت — یعنی «روزانه» روی کندل ۵ دقیقه تحلیل می‌شد.
    """
    symbol = map_symbol_to_bitpin(ticker)
    if not symbol:
        return None

    if not tf_name:
        logger.error("[Bitpin] tf_name خالی — تایم‌فریم مشخص نیست")
        return None

    res = map_tf(tf_name)
    if res is None:
        logger.warning(
            f"[Bitpin] تایم‌فریم ناشناخته {tf_name!r} "
            f"(پشتیبانی‌شده: {list(TF_MAP)}) — None برمی‌گردد"
        )
        return None

    spec = get_tf_spec(tf_name)
    days = spec.period_days

    to_ts = int(datetime.now(timezone.utc).timestamp())
    from_ts = to_ts - days * 86400

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

        # ═══ ایندکس زمانی ═══
        # epoch بیت‌پین UTC است (تأیید تجربی: ts=1791030600 → 12:30Z)
        # پس صریحاً utc=True می‌دهیم. بدون آن، pandas آن را به وقت
        # محلی سرور تفسیر می‌کند و مقایسه با timestampهای UTC
        # در backtest_service ۳:۳۰ ساعت شیفت می‌خورد.
        df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True)
        df.set_index("time", inplace=True)

        # ─── تبدیل نوع (open/close عدد، low/high/volume رشته) ───
        for col in ["open", "close", "low", "high", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.dropna(inplace=True)
        df = df[~df.index.duplicated(keep="last")]
        df.sort_index(inplace=True)

        # ─── تضمین نهایی UTC-aware ───
        df = ensure_utc_index(df)
        if df is None or df.empty:
            return None

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
            # ⚠️ بیت‌پین قیمت‌ها را **رشته** می‌دهد (مثلاً '4151.31').
            #    برای مقاومت در برابر تغییر فرمت (کاما، ارقام فارسی)
            #    از parse_number استفاده می‌کنیم، نه float() خام.
            price = parse_number(item.get("price"))
            if price is None or price <= 0:
                return None
            return {
                "price": price,
                "change_24h": parse_number(item.get("daily_change_price")) or 0.0,
                "high": parse_number(item.get("high")) or 0.0,
                "low": parse_number(item.get("low")) or 0.0,
            }

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
