"""
core/xaus_fetcher.py
منبع قیمت و کندل طلا/نقره — XAUS.com (فاز ۱۶.۴)
============================================================
🔴 مزایا:
  • رایگان
  • بدون API Key
  • قیمت لحظه‌ای (تأخیر ~۲۰ ثانیه)
  • کندل OHLCV با حجم
  • پشتیبانی از interval مستقیم (1m تا 1h)

🔴 نکته مهم:
  • برای interval=1d، باید range بزرگ (3mo یا 1y) استفاده کنیم.
  • 4h پشتیبانی نمی‌شه (باید 1h استفاده کنیم).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://xaus.com/api/v1"
TIMEOUT = 10

# ═══════════════════════════════════════════════════════════
# نقشه نماد
# ═══════════════════════════════════════════════════════════
SYMBOL_MAP = {
    "XAU-USD": "xau",  # طلا
    "XAG-USD": "xag",  # نقره
}


def is_in_xaus(ticker: str) -> bool:
    """آیا نماد در XAUS.com هست؟"""
    return ticker.upper() in SYMBOL_MAP


# ═══════════════════════════════════════════════════════════
# نقشه‌ی TF → interval
# ═══════════════════════════════════════════════════════════
_TF_TO_INTERVAL = {
    "۱ دقیقه": "1m",
    "۵ دقیقه": "5m",
    "۱۵ دقیقه": "15m",
    "۳۰ دقیقه": "30m",
    "۱ ساعت": "1h",
    "روزانه": "1d",
}


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای
# ═══════════════════════════════════════════════════════════
def fetch_xaus_ticker(ticker: str) -> Optional[dict]:
    """
    قیمت لحظه‌ای از XAUS.com.
    تأخیر: ~۲۰ ثانیه.
    """
    url = f"{BASE_URL}/spot"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[XAUS] spot {ticker}: {e}")
        return None

    if not isinstance(data, dict):
        return None

    try:
        xau = data.get("xau", {})
        price = xau.get("price")
        if not price or price <= 0:
            return None

        return {
            "price": float(price),
            "change_24h": 0.0,
            "high": 0.0,
            "low": 0.0,
        }
    except Exception as e:
        logger.warning(f"[XAUS] parse spot {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# کندل OHLCV
# ═══════════════════════════════════════════════════════════
def fetch_xaus_candles(
    ticker: str,
    tf_name: str = "۱ ساعت",
) -> Optional[pd.DataFrame]:
    """
    کندل OHLCV از XAUS.com.

    ⚠️ برای روزانه، range بزرگ (3mo) استفاده می‌کنیم تا کندل کافی داشته باشیم.
    """
    symbol = SYMBOL_MAP.get(ticker.upper())
    if not symbol:
        return None

    interval = _TF_TO_INTERVAL.get(tf_name)
    if not interval:
        return None

    # ─── range بر اساس interval ───
    # برای 1d، range بزرگ‌تر لازمه (وگرنه فقط ۵ کندل می‌ده)
    if interval == "1d":
        range_val = "1y"  # ۲۵۱ کندل روزانه
    elif interval == "1h":
        range_val = "1mo"  # ~۲۰ روز × ۲۴ = ۴۸۰ کندل
    else:
        range_val = "5d"  # برای 1m, 5m, 15m, 30m

    url = f"{BASE_URL}/chart"
    params = {
        "symbol": symbol,
        "range": range_val,
        "interval": interval,
    }

    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning(f"[XAUS] chart {ticker}/{tf_name}: {e}")
        return None

    if not isinstance(data, dict) or "points" not in data:
        return None

    try:
        points = data.get("points", [])
        if not points:
            return None

        df = pd.DataFrame(points)
        df["time"] = pd.to_datetime(df["t"], unit="s", utc=True)
        df.set_index("time", inplace=True)
        df = df.rename(
            columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        )
        df = df[["open", "high", "low", "close", "volume"]]

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df.dropna(inplace=True)
        df = df[~df.index.duplicated(keep="last")]
        df.sort_index(inplace=True)

        if len(df) < 20:
            logger.debug(f"[XAUS] {ticker}/{tf_name}: کندل کافی نیست ({len(df)} < 20)")
            return None

        return df
    except Exception as e:
        logger.warning(f"[XAUS] parse chart {ticker}: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "fetch_xaus_candles",
    "fetch_xaus_ticker",
    "is_in_xaus",
]
