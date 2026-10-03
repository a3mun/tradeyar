"""
core/data_fetcher.py
لایه دریافت داده — نسخه ۶.۰ (فقط صرافی‌های ایرانی)
============================================================
تغییرات نسخه ۶.۰:
  - حذف کامل yfinance
  - اضافه Bitpin, Wallex
  - نگه‌داشتن AlanChand/TGJU برای قیمت‌های ایران
  - fallback خودکار بین صرافی‌ها
"""

import logging
import re
from datetime import datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from core.contracts import DataSource
from core.sources import (
    get_default_symbol_for_source,
    is_symbol_available_in_source,
    resolve_source,
    resolve_symbol_and_source,
)
from core.utils import parse_number, to_english_digits

logger = logging.getLogger(__name__)

ALANCHAND_URL = "https://alanchand.com/"
TGJU_URL = "https://www.tgju.org/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
}

TIMEOUT = 20


# ═══════════════════════════════════════════════════════════
# قیمت‌های ایران (AlanChand + TGJU)
# ═══════════════════════════════════════════════════════════
def fetch_html(url, timeout=TIMEOUT, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            if attempt == retries:
                logger.warning(f"[Fetcher] {url}: {e}")
                return None
    return None


def extract_alanchand(html):
    if not html:
        return {}
    results = {}
    try:
        soup = BeautifulSoup(html, "html.parser")
        name_map = {
            "گرم طلای 18": "geram18",
            "گرم طلای ۱۸": "geram18",
            "آبشده": "mesghal",
            "مثقال": "mesghal",
            "سکه امامی": "sekee",
            "انس طلا": "ons",
        }
        for card in soup.find_all(class_="goldCard"):
            card_text = to_english_digits(card.get_text(" ", strip=True))
            for name, key in name_map.items():
                if name in card_text and key not in results:
                    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(تومان|\$)", card_text)
                    if m:
                        price = parse_number(m.group(1))
                        if price:
                            results[key] = price
                    break
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue
                first = to_english_digits(cells[0].get_text(strip=True))
                if "دلار آمریکا" in first and "dollar" not in results:
                    sell = parse_number(cells[2].get_text(strip=True))
                    if sell:
                        results["dollar"] = sell
                    break
    except Exception as e:
        logger.warning(f"[Fetcher] AlanChand: {e}")
    return results


def extract_tgju(html):
    if not html:
        return {}
    results = {}
    try:
        soup = BeautifulSoup(html, "html.parser")
        key_map = {
            "geram18": "geram18",
            "mesghal": "mesghal",
            "sekee": "sekee",
            "price_dollar_rl": "dollar",
            "ons": "ons",
        }
        for row in soup.find_all("tr", attrs={"data-market-row": True}):
            raw_key = row.get("data-market-row", "").strip()
            if raw_key not in key_map:
                continue
            key = key_map[raw_key]
            if key in results:
                continue
            nf_cells = row.find_all("td", class_="nf")
            if not nf_cells:
                continue
            price = parse_number(nf_cells[0].get_text(strip=True))
            if price:
                if key != "ons":
                    price = price / 10
                results[key] = price
    except Exception as e:
        logger.warning(f"[Fetcher] TGJU: {e}")
    return results


def fetch_iran_prices():
    result = {
        "prices": {},
        "source": "None",
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }
    html = fetch_html(ALANCHAND_URL)
    if html:
        prices = extract_alanchand(html)
        if len(prices) >= 3:
            result["prices"] = prices
            result["source"] = "AlanChand"
            return result
    html = fetch_html(TGJU_URL)
    if html:
        prices = extract_tgju(html)
        if len(prices) >= 3:
            result["prices"] = prices
            result["source"] = "TGJU"
            return result
    return result


# ═══════════════════════════════════════════════════════════
# سوییچ اصلی
# ═══════════════════════════════════════════════════════════
def fetch_history_by_source(
    ticker: str,
    interval: str,
    period: str,
    source: str = "nobitex",
    tf_name: str = "",
):
    """
    دریافت OHLCV بر اساس منبع.
    source: nobitex, abantether, bitpin, wallex, tsetmc
    """
    if not ticker:
        return None

    # ═══ نوبیتکس ═══
    if source == "nobitex":
        try:
            from core.nobitex_fetcher import fetch_nobitex_for_ticker

            df = fetch_nobitex_for_ticker(ticker, interval, period)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"[Fetcher] nobitex {ticker}: {e}")
        # fallback به بیت‌پین
        return fetch_history_by_source(ticker, interval, period, "bitpin", tf_name)

    # ═══ بیت‌پین ═══
    if source == "bitpin":
        try:
            from core.bitpin_fetcher import fetch_bitpin_candles

            df = fetch_bitpin_candles(ticker, tf_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"[Fetcher] bitpin {ticker}: {e}")
        # fallback به والکس
        return fetch_history_by_source(ticker, interval, period, "wallex", tf_name)

    # ═══ والکس ═══
    if source == "wallex":
        try:
            from core.wallex_fetcher import fetch_wallex_candles

            df = fetch_wallex_candles(ticker, tf_name)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.warning(f"[Fetcher] wallex {ticker}: {e}")
        # fallback به نوبیتکس
        try:
            from core.nobitex_fetcher import fetch_nobitex_for_ticker

            df = fetch_nobitex_for_ticker(ticker, interval, period)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
        return None

    # ═══ آبان‌تتر — OHLCV نداره، fallback به نوبیتکس ═══
    if source == "abantether":
        # ─── فقط TF های >= 5m رو پشتیبانی کن ───
        if interval == "1m":
            logger.info(f"[Fetcher] آبان‌تتر ۱ دقیقه نداره → None")
            return None
        try:
            from core.nobitex_fetcher import fetch_nobitex_for_ticker

            return fetch_nobitex_for_ticker(ticker, interval, period)
        except Exception as e:
            logger.warning(f"[Fetcher] abantether→nobitex {ticker}: {e}")
            return None

    # ═══ بورس تهران ═══
    if source == "tsetmc":
        try:
            from core.tsetmc_fetcher import fetch_tsetmc_for_symbol

            df = fetch_tsetmc_for_symbol(ticker)
            if df is not None and not df.empty:
                if interval == "1d":
                    return df
                return df  # fallback: استفاده از روزانه
        except Exception as e:
            logger.warning(f"[Fetcher] tsetmc {ticker}: {e}")
        return None

    return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای (Quote)
# ═══════════════════════════════════════════════════════════
def fetch_quote_by_source(ticker: str, source: str = "nobitex") -> dict | None:
    """
    قیمت لحظه‌ای — همیشه از صرافی انتخاب‌شده.
    اگه صرافی مورد نظر جواب نداد، None برگردون (نه fallback).
    """
    if not ticker:
        return None

    normalized = ticker.upper().replace("_USDT", "-USD").replace("_IRT", "-IRT")
    normalized = normalized.replace("_", "-")

    source = source.lower()

    # ═══ نوبیتکس ═══
    if source == "nobitex":
        try:
            from core.nobitex_fetcher import fetch_nobitex_stats_for_ticker

            stats = fetch_nobitex_stats_for_ticker(normalized)
            if stats and stats.get("price"):
                return {
                    "ticker": normalized,
                    "price": float(stats["price"]),
                    "change_pct": float(stats.get("change_24h") or 0),
                    "source": "nobitex",
                }
        except Exception as e:
            logger.warning(f"[Quote] nobitex {normalized}: {e}")
        return None

    # ═══ بیت‌پین ═══
    if source == "bitpin":
        try:
            from core.bitpin_fetcher import fetch_bitpin_candles

            df = fetch_bitpin_candles(normalized, "۵ دقیقه")
            if df is not None and not df.empty:
                return {
                    "ticker": normalized,
                    "price": float(df["close"].iloc[-1]),
                    "change_pct": 0.0,
                    "source": "bitpin",
                }
        except Exception as e:
            logger.warning(f"[Quote] bitpin {normalized}: {e}")
        return None

    # ═══ والکس ═══
    if source == "wallex":
        try:
            from core.wallex_fetcher import fetch_wallex_candles

            df = fetch_wallex_candles(normalized, "۵ دقیقه")
            if df is not None and not df.empty:
                return {
                    "ticker": normalized,
                    "price": float(df["close"].iloc[-1]),
                    "change_pct": 0.0,
                    "source": "wallex",
                }
        except Exception as e:
            logger.warning(f"[Quote] wallex {normalized}: {e}")
        return None

    # ═══ آبان‌تتر — فقط تومانی ═══
    if source == "abantether":
        # اگه نماد USDT/USD هست، آبان‌تتر نداره → نوبیتکس
        if normalized.upper().endswith("-USD") or normalized.upper().endswith("-USDT"):
            try:
                from core.nobitex_fetcher import fetch_nobitex_stats_for_ticker

                stats = fetch_nobitex_stats_for_ticker(normalized)
                if stats and stats.get("price"):
                    return {
                        "ticker": normalized,
                        "price": float(stats["price"]),
                        "change_pct": float(stats.get("change_24h") or 0),
                        "source": "abantether",  # ← برچسب آبان‌تتر (کاربر اینو انتخاب کرده)
                    }
            except Exception as e:
                logger.warning(f"[Quote] abantether→nobitex {normalized}: {e}")
            return None

        # تومانی → از خود آبان‌تتر
        try:
            from core.abantether_fetcher import fetch_abantether_price

            price = fetch_abantether_price(normalized)
            if price:
                return {
                    "ticker": normalized,
                    "price": float(price),
                    "change_pct": 0.0,
                    "source": "abantether",
                }
        except Exception as e:
            logger.warning(f"[Quote] abantether {normalized}: {e}")
        return None

    return None


# ═══════════════════════════════════════════════════════════
# exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "fetch_iran_prices",
    "fetch_history_by_source",
    "fetch_quote_by_source",
    "get_default_symbol_for_source",
    "is_symbol_available_in_source",
    "resolve_source",
    "resolve_symbol_and_source",
]
