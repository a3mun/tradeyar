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
from datetime import datetime, timezone

import pandas as pd
import requests

from core.contracts import get_tf_spec
from core.tz import ensure_utc_index
from core.utils import parse_number

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
# نقشه TF (نام فارسی → والکس)
# ═══════════════════════════════════════════════════════════
# ⚠️ کشف‌شده از خود API با بررسی **بازه‌ی واقعی کندل‌ها**
#    (۲۰۲۶-۱۰-۰۳) — نه فقط کد HTTP:
#
#   res=1  → 200 ولی no_data          → ندارد
#   res=5  → 200 ولی کندل ۱ دقیقه‌ای  → ❌ دروغین
#   res=15 → 200 ولی کندل ۱ دقیقه‌ای  → ❌ دروغین
#   res=30 → error                    → ندارد
#   res=60 → کندل ۱ ساعته ✅
#   res=1D → کندل روزانه ✅
#
# 🔴 نکته‌ی حیاتی:
#   والکس برای res=5 و res=15 کد 200 می‌دهد ولی **کندل ۱ دقیقه**
#   برمی‌گرداند! اگر فقط کد HTTP را چک کنیم، ATR و SL/TP روی
#   کندل ۱ دقیقه محاسبه می‌شود ولی برچسب «۱۵ دقیقه» می‌خورد.
#   پس این‌ها در نقشه **نیستند** و لایه‌ی `data_service` هم
#   بازه را دوباره اعتبارسنجی می‌کند (دفاع دو لایه).
#
# نتیجه: والکس مستقیم فقط «۱ ساعت» و «روزانه» را واقعاً دارد.
# برای بقیه‌ی TFها به نوبیتکس می‌رویم (fallback شفاف) که
# داده‌ی **درست** می‌دهد.
WALLEX_RESOLUTIONS: dict[str, str] = {
    "۱ دقیقه": "1",  # ─── مستند، ولی فعلاً no_data ───
    "۵ دقیقه": "5",  # ─── 200 می‌دهد ولی کندل اشتباه ───
    "۱۵ دقیقه": "15",  # ─── 200 می‌دهد ولی کندل اشتباه ───
    "۳۰ دقیقه": "30",  # ─── error ───
    "۱ ساعت": "60",  # ✅
    "روزانه": "1D",  # ✅
}

# ─── resolution هایی که والکس **واقعاً با بازه‌ی درست** می‌دهد ───
# ⚠️ «15» عمداً حذف شده: کد 200 می‌دهد ولی محتوایش ۱ دقیقه است.
_WALLEX_WORKING_RES = frozenset({"60", "1D"})

# ─── نقشه‌ی صریح: نام فارسی → resolution (فقط معتبرها) ───
TF_MAP: dict[str, str] = {
    tf: res for tf, res in WALLEX_RESOLUTIONS.items() if res in _WALLEX_WORKING_RES
}
# نتیجه: {"۱ ساعت": "60", "روزانه": "1D"}


def map_tf(tf_name: str) -> str | None:
    """
    نام فارسی → resolution والکس.

    Returns:
        resolution والکس، یا ``None`` اگر والکس مستقیم نداشته باشد.

    ⚠️ ``None`` یعنی «والکس این TF را ندارد» — نه اینکه
       «resolution پیش‌فرض بده». برای TF غایب هیچ درخواستی
       فرستاده نمی‌شود.
    """
    return TF_MAP.get(tf_name)


def supports_tf(tf_name: str) -> bool:
    """آیا والکس مستقیماً از این تایم‌فریم پشتیبانی می‌کند؟"""
    return tf_name in TF_MAP


# ═══════════════════════════════════════════════════════════
# دریافت OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_wallex_candles(ticker: str, tf_name: str = "۵ دقیقه") -> pd.DataFrame | None:
    """
    دریافت کندل‌های والکس (UDF format).
    Response: {s, t: [...], o: [...], h: [...], l: [...], c: [...], v: [...]}

    ⚠️ tf_name باید نام فارسی باشد («۵ دقیقه»، «۱ ساعت»، ...).
       اگر والکس آن TF را نداشته باشد، ``None`` برمی‌گردد —
       بدون درخواست، تا زنجیره‌ی fallback سریع به نوبیتکس برود.
    """
    symbol = map_symbol_to_wallex(ticker)
    if not symbol:
        return None

    if not tf_name:
        logger.error("[Wallex] tf_name خالی — تایم‌فریم مشخص نیست")
        return None

    res = map_tf(tf_name)
    if res is None:
        # ─── والکس این TF را ندارد؛ درخواست بی‌فایده نزن ───
        logger.debug(
            f"[Wallex] «{tf_name}» ندارد (موجود: {list(TF_MAP)}) — None"
        )
        return None

    spec = get_tf_spec(tf_name)
    days = spec.period_days

    to_ts = int(datetime.now(timezone.utc).timestamp())
    from_ts = to_ts - days * 86400

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
                # ═══ ایندکس زمانی ═══
                # epoch والکس UTC است (تأیید تجربی: ts=1791032400 → 13:00Z).
                # صریحاً utc=True می‌دهیم تا با timestampهای UTC
                # قابل مقایسه باشد.
                "time": pd.to_datetime(data["t"], unit="s", utc=True),
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
        logger.warning(f"[Wallex] parse {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای
# ═══════════════════════════════════════════════════════════
def fetch_wallex_ticker(ticker: str) -> dict | None:
    """
    دریافت قیمت لحظه‌ای از ``/v1/markets``.

    ⚠️ والکس قیمت‌ها را **رشته** می‌دهد (مثلاً '4062.51000...').
       از ``parse_number`` استفاده می‌کنیم تا فرمت‌های مختلف
       (کاما، ارقام فارسی) هم کار کنند.
    """
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
        logger.debug(f"[Wallex] «{symbol}» در markets نیست")
        return None

    try:
        stats = item.get("stats", {})

        price = parse_number(stats.get("lastPrice"))
        if price is None or price <= 0:
            return None

        return {
            "price": price,
            "change_24h": parse_number(stats.get("24h_ch")) or 0.0,
            "high": parse_number(stats.get("24h_highPrice")) or 0.0,
            "low": parse_number(stats.get("24h_lowPrice")) or 0.0,
        }
    except Exception as e:
        logger.warning(f"[Wallex] parse ticker {ticker}: {e}")
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
