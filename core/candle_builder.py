"""
core/candle_builder.py
سازنده‌ی کندل از قیمت‌های لحظه‌ای (فاز ۱۶.۴)
============================================================
🔴 برای صرافی‌هایی که OHLCV ندارن (مثل تبدیل) — کندل رو از
   قیمت‌های لحظه‌ای می‌سازیم و توی دیتابیس ذخیره می‌کنیم.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# مسیر ذخیره‌سازی (فایل‌های JSONL، سبک و سریع)
CANDLES_DIR = Path("data/candles")
CANDLES_DIR.mkdir(parents=True, exist_ok=True)

# تایم‌فریم‌های پشتیبانی‌شده (دقیقه)
_TF_MINUTES = {
    "۱ دقیقه": 1,
    "۵ دقیقه": 5,
    "۱۵ دقیقه": 15,
    "۳۰ دقیقه": 30,
    "۱ ساعت": 60,
    "روزانه": 1440,
}

# کش در حافظه (برای سرعت)
_candles_cache: dict[str, list[dict]] = {}


def _round_to_tf(dt: datetime, tf_minutes: int) -> datetime:
    """گرد کردن زمان به شروع TF (مثلاً ۱۵:۳۲ → ۱۵:۳۰ برای ۵ دقیقه)"""
    minute = (dt.minute // tf_minutes) * tf_minutes
    return dt.replace(minute=minute, second=0, microsecond=0)


def _get_candle_file(source: str, ticker: str, tf_name: str) -> Path:
    """مسیر فایل ذخیره"""
    ticker_clean = ticker.replace("/", "_").replace("-", "_")
    tf_clean = tf_name.replace(" ", "_").replace("ی", "i").replace("د", "d")
    return CANDLES_DIR / f"{source}_{ticker_clean}_{tf_clean}.jsonl"


def _load_candles(source: str, ticker: str, tf_name: str, days: int = 30) -> list[dict]:
    """بارگذاری کندل‌ها از فایل (اختیاری، برای backtest)"""
    cache_key = f"{source}_{ticker}_{tf_name}"
    if cache_key in _candles_cache:
        return _candles_cache[cache_key]

    file_path = _get_candle_file(source, ticker, tf_name)
    if not file_path.exists():
        _candles_cache[cache_key] = []
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    candles = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    c = json.loads(line.strip())
                    ts = datetime.fromisoformat(c["timestamp"])
                    if ts >= cutoff:
                        candles.append(c)
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"[CandleBuilder] load {file_path}: {e}")

    _candles_cache[cache_key] = candles
    return candles


def _append_candle(source: str, ticker: str, tf_name: str, candle: dict) -> None:
    """ذخیره‌ی کندل جدید در فایل"""
    file_path = _get_candle_file(source, ticker, tf_name)
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(candle, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[CandleBuilder] save {file_path}: {e}")


def update_candle(
    source: str,
    ticker: str,
    price: float,
    volume: float = 0.0,
) -> None:
    """
    🔴 به‌روزرسانی کندل‌ها با قیمت جدید — برای همه TFها
    از WebSocket تبدیل (یا هر صرافی دیگه‌ای) صدا زده می‌شه.
    """
    if not price or price <= 0:
        return

    now = datetime.now(timezone.utc)
    cache_key_base = f"{source}_{ticker}"

    for tf_name, tf_min in _TF_MINUTES.items():
        cache_key = f"{cache_key_base}_{tf_name}"
        candle_start = _round_to_tf(now, tf_min)
        candle_start_iso = candle_start.isoformat()

        # ─── لیست کندل‌ها توی کش ───
        candles = _candles_cache.get(cache_key, [])

        # ─── کندل جدید یا به‌روزرسانی کندل فعلی؟ ───
        if not candles or candles[-1]["timestamp"] != candle_start_iso:
            # کندل جدید
            new_candle = {
                "timestamp": candle_start_iso,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
            candles.append(new_candle)
            _append_candle(source, ticker, tf_name, new_candle)
            
            # فقط ۵۰۰ کندل آخر رو نگه دار (برای جلوگیری از رشد بی‌نهایت)
            if len(candles) > 500:
                candles = candles[-500:]
        else:
            # به‌روزرسانی کندل فعلی
            current = candles[-1]
            current["high"] = max(current["high"], price)
            current["low"] = min(current["low"], price)
            current["close"] = price
            current["volume"] = current["volume"] + volume

        _candles_cache[cache_key] = candles


def get_candles(
    source: str,
    ticker: str,
    tf_name: str,
    limit: int = 200,
) -> Optional[list[dict]]:
    """
    🔴 دریافت کندل‌های ساخته‌شده از فایل/کش
    خروجی: [{"timestamp", "open", "high", "low", "close", "volume"}, ...]
    """
    cache_key = f"{source}_{ticker}_{tf_name}"
    candles = _candles_cache.get(cache_key) or _load_candles(source, ticker, tf_name)

    if not candles:
        return None

    return candles[-limit:]