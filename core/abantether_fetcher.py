"""
core/abantether_fetcher.py
صرافی آبان‌تتر — فقط قیمت تومانی (بدون OHLCV، بدون USDT)
"""

import logging
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.abantether.com"
TIMEOUT = 15
HEADERS = {"User-Agent": "TraderBot/Trademun-1.0.0", "Accept": "application/json"}


def map_symbol_to_abantether(ticker: str) -> str | None:
    """BTC-IRT → BTCIRT | USDT-IRT → USDTIRT | BTC-USD → None"""
    if not ticker:
        return None
    upper = ticker.upper()
    if upper == "USDT-IRT":
        return "USDTIRT"
    if upper.endswith("-USD") or upper.endswith("-USDT"):
        return None
    if upper.endswith("-IRT"):
        return upper.replace("-IRT", "IRT")
    return None


def fetch_abantether_prices() -> dict:
    """همه قیمت‌های آبان‌تتر یکجا"""
    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/manager/otc/ticker", headers=HEADERS, timeout=TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", {}).get("markets", {})
    except Exception as e:
        logger.warning(f"[Abantether] prices: {e}")
        return {}


def fetch_abantether_price(ticker: str) -> float | None:
    """
    قیمت لحظه‌ای — فقط تومانی.
    BTC-USD → None (پشتیبانی نمی‌شه)
    BTC-IRT → قیمت به تومان
    """
    symbol = map_symbol_to_abantether(ticker)
    if not symbol:
        logger.debug(f"[Abantether] {ticker} → فقط تومانی پشتیبانی می‌شه")
        return None

    markets = fetch_abantether_prices()
    if not markets:
        return None

    item = markets.get(symbol)
    if not item:
        # جستجو بر اساس symbol داخلی
        base = ticker.split("-")[0].upper()
        for k, v in markets.items():
            if v.get("symbol") == base and k.endswith("IRT"):
                item = v
                break

    if not item:
        return None

    try:
        buy = float(item.get("buy_price", 0))
        sell = float(item.get("sell_price", 0))
        if buy > 0 and sell > 0:
            price = (buy + sell) / 2
        else:
            price = buy or sell
        # ═══ آبان‌تتر همه قیمت‌ها رو به تومان می‌ده (نه ریال) ═══
        # پس تقسیم نمی‌کنیم
        return price

    except (TypeError, ValueError):
        return None
