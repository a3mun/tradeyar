"""
services/data_service.py
لایه دیتا — بدون yfinance
"""

import logging
from typing import Optional

import pandas as pd

from core.data_fetcher import (
    fetch_history_by_source,
    fetch_iran_prices,
    fetch_quote_by_source,
    resolve_symbol_and_source,
)
from core.sources import get_default_symbol_for_source

from services.cache import data_cache, quote_cache, get_ttl

logger = logging.getLogger(__name__)


TF_MAP = {
    "۱ دقیقه": ("1m", "1d"),
    "۵ دقیقه": ("5m", "5d"),
    "۱۵ دقیقه": ("15m", "5d"),
    "۳۰ دقیقه": ("30m", "1mo"),
    "۱ ساعت": ("1h", "3mo"),
    "روزانه": ("1d", "6mo"),
}


def get_tf_params(tf_name: str) -> tuple[str, str]:
    return TF_MAP.get(tf_name, ("5m", "5d"))


def fetch_ohlcv(ticker, tf_name, source="nobitex", use_cache=True):
    if not ticker:
        return None

    # ═══ TSETMC فقط دیتای روزانه داره ═══
    if source == "tsetmc" and tf_name != "روزانه":
        logger.debug(f"[DataService] TSETMC برای {tf_name} پشتیبانی نمی‌شه")
        return None

    # ═══ آبان‌تتر ۱ دقیقه نداره ═══
    if source == "abantether" and tf_name == "۱ دقیقه":
        logger.debug(f"[DataService] آبان‌تتر ۱ دقیقه نداره")
        return None

    interval, period = get_tf_params(tf_name)
    cache_key = f"ohlcv:{ticker}:{source}:{tf_name}"

    if use_cache:
        cached = data_cache.get(cache_key)
        if cached is not None:
            return cached

    final_ticker, final_source, switch_msg = resolve_symbol_and_source(ticker, source)
    if switch_msg:
        logger.info(f"[DataService] {switch_msg}")

    try:
        df = fetch_history_by_source(
            ticker=final_ticker,
            interval=interval,
            period=period,
            source=final_source,
            tf_name=tf_name,
        )
        if df is not None and not df.empty:
            data_cache.set(cache_key, df, get_ttl(tf_name))
        return df
    except Exception as e:
        logger.error(f"[DataService] {ticker}: {e}")
        return None


def fetch_quote(ticker, source="nobitex"):
    """قیمت لحظه‌ای"""
    cache_key = f"quote:{ticker}:{source}"
    cached = quote_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        result = fetch_quote_by_source(ticker, source)
        if result:
            quote_cache.set(cache_key, result, 5)
        return result
    except Exception as e:
        logger.error(f"[Quote] {ticker}: {e}")
        return None


def get_iran_prices():
    cache_key = "iran_prices"
    cached = data_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        result = fetch_iran_prices()
        data_cache.set(cache_key, result, 60)
        return result
    except Exception as e:
        logger.error(f"[DataService] iran_prices: {e}")
        return {"prices": {}, "source": "None", "timestamp": ""}


def get_default_symbol(source):
    try:
        return get_default_symbol_for_source(source)
    except Exception:
        return "BTC-USD"
