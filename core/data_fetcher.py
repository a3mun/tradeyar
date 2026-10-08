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
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from core.contracts import DataSource, is_ohlcv_supported
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
# ═══════════════════════════════════════════════════════════
# ردیابی منبع واقعی دیتا
# ═══════════════════════════════════════════════════════════
# چرا لازم است: زنجیره‌ی fallback بازگشتی است، پس اگر کاربر
# «والکس» بخواهد و والکس ۵ دقیقه نداشته باشد، دیتا از نوبیتکس
# می‌آید. بدون این برچسب، لایه‌ی بالاتر فکر می‌کند دیتا از
# والکس آمده و لاگ/برچسب گمراه‌کننده می‌شود.
def _tag_source(df, source: str):
    """منبع واقعی دیتا را روی دیتافریم برچسب می‌زند"""
    try:
        if df is not None:
            df.attrs["data_source"] = source
    except Exception:
        pass
    return df


def get_data_source(df, default: str = "") -> str:
    """منبع واقعی دیتا را از دیتافریم می‌خواند"""
    try:
        return (df.attrs or {}).get("data_source", default) or default
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════
# اعتبارسنجی نماد — جلوگیری از درخواست‌های محکوم به شکست
# ═══════════════════════════════════════════════════════════
# باگ ۶ (نسخه ۱.۵): نمادهایی مثل TON-USD و MATIC-USD روی نوبیتکس
# وجود ندارند و API کد 400 می‌دهد. چون هر تلاش شامل retry و
# timeout است، اسکن به‌شدت کند می‌شد.
#
# با چک کردن **قبل** از درخواست، 400ها حذف می‌شوند.
_NOBITEX_SYMBOL_SET: Optional[frozenset] = None


def _nobitex_symbol_set() -> frozenset:
    """
    مجموعه‌ی نمادهای معتبر نوبیتکس (کش‌شده در حافظه).

    🔴 باگ رفع‌شده (نسخه ۱.۷):
        پیش‌تر فقط ``NOBITEX_SYMBOLS.values()`` جمع می‌شد (مثل
        ``BTCUSDT``)، ولی ``map_symbol_to_nobitex`` برای جفت‌های
        تومانی چیزی مثل ``PAXGIRT`` برمی‌گرداند که در values
        **نیست** — در حالی که خودِ ``"PAXG-IRT"`` در **keys** است.

        نتیجه‌ی باگ: ``BTC-IRT``، ``ETH-IRT``، ``PAXG-IRT`` و
        بقیه‌ی جفت‌های تومانی **اشتباهاً نامعتبر** تشخیص داده
        می‌شدند و بدون درخواست به بیت‌پین می‌رفتند (یا با کش منفی
        بلاک می‌شدند).

    حالا **هم keys هم values** (هر دو uppercase) جمع می‌شوند تا
    هر دو شکل کار کند.
    """
    global _NOBITEX_SYMBOL_SET
    if _NOBITEX_SYMBOL_SET is not None:
        return _NOBITEX_SYMBOL_SET

    try:
        from core.nobitex_fetcher import NOBITEX_SYMBOLS

        tokens: set[str] = set()
        for key, value in NOBITEX_SYMBOLS.items():
            # ─── هر دو شکل: "PAXG-IRT" و "PAXGIRT" ───
            if key:
                tokens.add(str(key).upper())
            if value:
                tokens.add(str(value).upper())
            # ─── نسخه‌ی بدون جداکننده از کلید هم اضافه کن ───
            if key:
                tokens.add(str(key).upper().replace("-", "").replace("_", ""))

        _NOBITEX_SYMBOL_SET = frozenset(tokens)
        logger.debug(
            f"[Fetcher] {len(_NOBITEX_SYMBOL_SET)} توکن معتبر نوبیتکس بارگذاری شد"
        )
    except Exception as e:
        logger.warning(f"[Fetcher] بارگذاری نمادهای نوبیتکس: {e}")
        _NOBITEX_SYMBOL_SET = frozenset()

    return _NOBITEX_SYMBOL_SET


def is_valid_nobitex_symbol(ticker: str) -> bool:
    """
    آیا این نماد روی نوبیتکس وجود دارد؟

    دو لایه بررسی:
      ۱. بلک‌لیست پویا — نمادهایی که API برایشان InvalidSymbol
         داده بود (یادگیری از پاسخ ۴۰۰). **معتبرترین سیگنال.**
      ۲. لیست محلی NOBITEX_SYMBOLS (keys + values).

    ⚠️ این تابع «fail-open» است: اگر مطمئن نباشد، ``True``
       می‌دهد تا درخواست واقعی تصمیم بگیرد. دلیل: رد کردن
       نماد سالم (false negative) از پذیرفتن نماد نامعتبر
       (که فقط یک ۴۰۰ هزینه دارد) **بدتر** است — چون کاربر
       تحلیل نمی‌گیرد.

    Returns:
        False فقط اگر **قطعاً** نامعتبر باشد (بلک‌لیست پویا).
    """
    if not ticker:
        return False

    try:
        from core.nobitex_fetcher import (
            is_symbol_invalid,
            map_symbol_to_nobitex,
        )

        nb = map_symbol_to_nobitex(ticker)
        if not nb:
            return False

        # ─── لایه ۱: بلک‌لیست پویا — تنها منبع «قطعی» ───
        if is_symbol_invalid(nb):
            return False

        # ─── لایه ۲: لیست محلی (فقط اگر غیرخالی باشد) ───
        valid = _nobitex_symbol_set()
        if not valid:
            return True  # ─── اعتبارسنجی در دسترس نیست ───

        nb_upper = nb.upper()
        if nb_upper in valid:
            return True

        # ─── نسخه‌ی بدون جداکننده ───
        nb_compact = nb_upper.replace("-", "").replace("_", "")
        if nb_compact in valid:
            return True

        # ─── کلید اصلی ticker هم چک شود ───
        ticker_upper = ticker.upper()
        if ticker_upper in valid:
            return True

        # ─── 🔴 fail-open: نماد در لیست محلی نیست ولی بلک‌لیست
        #     هم نشده → احتمالاً لیست محلی قدیمی است.
        #     بگذار درخواست واقعی تصمیم بگیرد (اگر ۴۰۰ داد،
        #     بلک‌لیست می‌شود و بار بعد سریع رد می‌شود).
        logger.debug(
            f"[Fetcher] {ticker} (→{nb}) در لیست محلی نوبیتکس نیست "
            f"— fail-open، درخواست امتحان می‌شود"
        )
        return True

    except Exception:
        return True


def fetch_history_by_source(
    ticker: str,
    interval: str,
    period: str,
    source: str = "nobitex",
    tf_name: str = "",
    _tried: Optional[set] = None,
):
    """
    دریافت OHLCV بر اساس منبع، با زنجیره‌ی fallback **بدون بازگشت**.

    Args:
        interval: فرمت داخلی ("5m"، "1h"، "1d") — برای نوبیتکس
        period:   بازه ("5d"، "3mo") — برای نوبیتکس
        source:   نقطه‌ی شروع زنجیره
        tf_name:  نام فارسی تایم‌فریم — **اجباری برای بیت‌پین/والکس**
        _tried:   منابعی که قبلاً امتحان شده‌اند (داخلی — دست نزن)

    ⚠️ باگ ۶ — بازگشت بی‌نهایت:
        پیاده‌سازی قبلی هر fallback را با یک فراخوانی بازگشتی تازه
        انجام می‌داد:

            nobitex → (شکست) → bitpin → (شکست) → nobitex → bitpin → ...

        برای نمادهایی که روی **هیچ** صرافی‌ای نیستند (TON-USD،
        MATIC-USD) این زنجیره هرگز تمام نمی‌شد و تا
        ``RecursionError`` می‌رفت. هر دور شامل چند درخواست HTTP
        بود، پس هر نماد **۱۱۰ ثانیه** طول می‌کشید و کل `/scan`
        به ۲۷۷ ثانیه می‌رسید.

        حالا زنجیره یک **لیست صریح** است و هر منبع حداکثر
        یک بار امتحان می‌شود.
    """
    if not ticker:
        return None

    # ═══ اعتبارسنجی تایم‌فریم ═══
    if not tf_name:
        logger.error(
            f"[Fetcher] tf_name خالی برای {ticker}/{source} — "
            f"نمی‌توان تایم‌فریم درست را تعیین کرد"
        )
        return None

    # ═══ زنجیره‌ی fallback — لیست صریح، بدون بازگشت ═══
    if _tried is None:
        _tried = set()

    def _next(*candidates) -> Optional[pd.DataFrame]:
        """اولین منبع امتحان‌نشده در زنجیره را اجرا می‌کند"""
        for candidate in candidates:
            if candidate not in _tried:
                return fetch_history_by_source(
                    ticker, interval, period, candidate, tf_name, _tried
                )
        return None

    _tried.add(source)

    # ─── اگر این منبع از TF پشتیبانی نکند، به بعدی برو ───
    # ⚠️ is_ohlcv_supported فقط قیدهای **قطعی** را می‌داند
    #    (TSETMC روزانه، آبان‌تتر بدون OHLCV، والکس بدون ۳۰ دقیقه).
    #    برای بقیه‌ی ترکیب‌ها درخواست واقعی فرستاده می‌شود و پاسخ
    #    صرافی تصمیم می‌گیرد — چون پشتیبانی TF per-نماد است.
    if not is_ohlcv_supported(tf_name, source):
        logger.debug(
            f"[Fetcher] {source} از «{tf_name}» OHLCV نمی‌دهد "
            f"— به منبع بعدی می‌رویم"
        )
        return _next("nobitex", "bitpin", "wallex")

    # ═══ نوبیتکس ═══
    if source == "nobitex":
        # ─── اعتبارسنجی نماد قبل از درخواست (جلوگیری از 400) ───
        if not is_valid_nobitex_symbol(ticker):
            logger.debug(
                f"[Fetcher] {ticker} روی نوبیتکس موجود نیست "
                f"— بدون درخواست، به بیت‌پین"
            )
            return _next("bitpin")

        try:
            from core.nobitex_fetcher import fetch_nobitex_for_ticker

            df = fetch_nobitex_for_ticker(ticker, interval, period)
            if df is not None and not df.empty:
                return _tag_source(df, "nobitex")
        except Exception as e:
            logger.warning(f"[Fetcher] nobitex {ticker}: {e}")

        return _next("bitpin")

    # ═══ بیت‌پین ═══
    if source == "bitpin":
        try:
            from core.bitpin_fetcher import fetch_bitpin_candles

            df = fetch_bitpin_candles(ticker, tf_name)
            if df is not None and not df.empty:
                return _tag_source(df, "bitpin")
        except Exception as e:
            logger.warning(f"[Fetcher] bitpin {ticker}: {e}")

        return _next("wallex", "nobitex")

    # ═══ والکس ═══
    if source == "wallex":
        try:
            from core.wallex_fetcher import fetch_wallex_candles

            df = fetch_wallex_candles(ticker, tf_name)
            if df is not None and not df.empty:
                return _tag_source(df, "wallex")
        except Exception as e:
            logger.warning(f"[Fetcher] wallex {ticker}: {e}")

        return _next("nobitex", "bitpin")

    # ═══ تبدیل (Tabdeal) ═══
    #
    # 🔴 تبدیل OHLCV عمومی ندارد (فقط قیمت + عمق بازار).
    #    همان قاعده‌ی آبان‌تتر سابق: برای OHLCV **اجازه‌ی
    #    fallback** داریم (کاربر باید تحلیل بگیرد)، ولی منبع
    #    واقعی در ``df.attrs["data_source"]`` برچسب می‌خورد تا
    #    لایه‌ی سرویس آن را صادقانه گزارش کند.
    if source == "tabdeal":
        logger.debug(
            f"[Fetcher] تبدیل OHLCV ندارد — برای {ticker} "
            f"از زنجیره‌ی fallback استفاده می‌شود"
        )
        return _next("nobitex", "bitpin", "wallex")

    # ═══ بورس تهران ═══
    if source == "tsetmc":
        try:
            from core.tsetmc_fetcher import fetch_tsetmc_for_symbol

            df = fetch_tsetmc_for_symbol(ticker)
            if df is not None and not df.empty:
                return _tag_source(df, "tsetmc")
        except Exception as e:
            logger.warning(f"[Fetcher] tsetmc {ticker}: {e}")
        return None

    return None


# ═══════════════════════════════════════════════════════════
# قیمت لحظه‌ای (Quote)
# ═══════════════════════════════════════════════════════════
def fetch_quote_by_source(ticker: str, source: str = "nobitex") -> dict | None:
    """
    قیمت لحظه‌ای — **مستقل از هر صرافی**.

    ═══ قاعده‌ی طلایی (نسخه ۱.۷) ═══
    هر صرافی باید قیمت **خودش** را بدهد. اگر صرافی آن بازار را
    ندارد، ``None`` برمی‌گردد — **هرگز** قیمت صرافی دیگر را
    با برچسب خودمان برنمی‌گردانیم.

    چرا: صفحه‌ی «مقایسه قیمت صرافی‌ها» باید تفاوت واقعی و اسپرد
    بین صرافی‌ها را نشان دهد. اگر آبان‌تتر قیمت نوبیتکس را با
    برچسب خودش بدهد، کاربر فکر می‌کند بازار آبان‌تتر همان است و
    تصمیم اشتباه می‌گیرد.

    🔴 باگ رفع‌شده: پیش‌تر برای آبان‌تتر + جفت‌های تتری به نوبیتکس
       fallback می‌شد و دو ردیف قیمت یکسان نشان داده می‌شد.

    ═══ پشتیبانی واقعی هر صرافی ═══
        نوبیتکس   : USDT و IRT/RLS (هر دو)
        بیت‌پین    : USDT و IRT
        والکس     : USDT و TMN
        آبان‌تتر   : **فقط تومانی** — USDT ندارد
        TSETMC    : فقط سهام بورس تهران (ریال)
    """
    if not ticker:
        return None

    normalized = ticker.upper().replace("_USDT", "-USD").replace("_IRT", "-IRT")
    normalized = normalized.replace("_", "-")

    source = source.lower()

    # ─── تشخیص جفت تتری در برابر تومانی ───
    is_usdt_pair = normalized.endswith("-USD") or normalized.endswith("-USDT")
    is_irt_pair = normalized.endswith("-IRT") or normalized.endswith("-RLS")

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
        # ─── endpoint اختصاصی tickers (دقیق‌تر از کندل) ───
        try:
            from core.bitpin_fetcher import fetch_bitpin_ticker

            t = fetch_bitpin_ticker(normalized)
            if t and t.get("price"):
                return {
                    "ticker": normalized,
                    "price": float(t["price"]),
                    "change_pct": float(t.get("change_24h") or 0),
                    "source": "bitpin",
                }
        except Exception as e:
            logger.warning(f"[Quote] bitpin ticker {normalized}: {e}")

        # ─── fallback: آخرین close کندل ۵ دقیقه ───
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
            logger.warning(f"[Quote] bitpin candles {normalized}: {e}")
        return None

    # ═══ والکس ═══
    if source == "wallex":
        # ─── endpoint اختصاصی markets ───
        # 🔴 باگ رفع‌شده: پیش‌تر از **کندل ۵ دقیقه** استفاده می‌شد
        #    که والکس ندارد → همیشه None. یعنی قیمت والکس هرگز
        #    نمایش داده نمی‌شد.
        try:
            from core.wallex_fetcher import fetch_wallex_ticker

            t = fetch_wallex_ticker(normalized)
            if t and t.get("price"):
                return {
                    "ticker": normalized,
                    "price": float(t["price"]),
                    "change_pct": float(t.get("change_24h") or 0),
                    "source": "wallex",
                }
        except Exception as e:
            logger.warning(f"[Quote] wallex ticker {normalized}: {e}")
        return None

    # ═══ تبدیل (Tabdeal) ═══
    if source == "tabdeal":
        try:
            from core.tabdeal_fetcher import fetch_tabdeal_ticker

            t = fetch_tabdeal_ticker(normalized)
            if t and t.get("price"):
                return {
                    "ticker": normalized,
                    "price": float(t["price"]),
                    "change_pct": float(t.get("change_24h") or 0),
                    "source": "tabdeal",
                }
        except Exception as e:
            logger.warning(f"[Quote] tabdeal {normalized}: {e}")
        return None

    # ═══ بورس تهران ═══
    if source == "tsetmc":
        # 🔴 فاز ۸ — قیمت زنده (نه کندل دیروز)
        try:
            from core.tsetmc_fetcher import fetch_tsetmc_live_quote

            live = fetch_tsetmc_live_quote(normalized)
            if live and live.get("price"):
                return {
                    "ticker": live["ticker"],
                    "price": live["price"],
                    "change_pct": live.get("change_pct", 0.0),
                    "source": "tsetmc",
                }
        except Exception as e:
            logger.warning(f"[Quote] tsetmc live {normalized}: {e}")

        # ─── fallback: کندل آخر (برای مواقع تعطیلی) ───
        try:
            from core.tsetmc_fetcher import fetch_tsetmc_for_symbol

            df = fetch_tsetmc_for_symbol(normalized)
            if df is not None and not df.empty:
                last = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else last
                price = float(last["close"])
                change = (
                    (price - float(prev["close"])) / float(prev["close"]) * 100
                    if float(prev["close"])
                    else 0.0
                )
                return {
                    "ticker": normalized,
                    "price": price,
                    "change_pct": change,
                    "source": "tsetmc",
                }
        except Exception as e:
            logger.warning(f"[Quote] tsetmc candles {normalized}: {e}")
        return None


def source_has_market(ticker: str, source: str) -> bool:
    """
    آیا این صرافی **واقعاً** این بازار را دارد؟

    سبک‌تر از ``fetch_quote_by_source`` — برای تصمیم‌گیری در
    لایه‌ی نمایش (مثلاً «آبان‌تتر برای USDT خط تیره بگذار»)
    بدون درخواست شبکه.

    ⚠️ فقط محدودیت‌های **ساختاری** را چک می‌کند، نه موجود بودن
    نماد خاص. برای موجود بودن نماد باید quote گرفت.

    ═══ محدودیت‌های ساختاری (نسخه ۱.۸) ═══
        • TSETMC  → فقط سهام بورس تهران
        • تبدیل   → هم IRT هم USDT (تأیید تجربی: ۵۲۵ بازار USDT)
        • نوبیتکس/بیت‌پین/والکس → هر دو

    ⚠️ آبان‌تتر حذف شد (فقط تومانی بود و با بقیه هماهنگ نبود).
    """
    if not ticker:
        return False

    upper = ticker.upper()
    is_usdt_pair = upper.endswith("-USD") or upper.endswith("-USDT")
    is_irt_pair = upper.endswith("-IRT") or upper.endswith("-RLS")

    source = source.lower()

    # ─── TSETMC فقط سهام بورس (نماد غیر-ASCII) ───
    if source == "tsetmc":
        return not ticker[0].isascii()

    # ─── کریپتو: هم USDT هم IRT ───
    if source in ("nobitex", "bitpin", "wallex", "tabdeal"):
        return is_usdt_pair or is_irt_pair

    return False


# ═══════════════════════════════════════════════════════════
# exports
# ═══════════════════════════════════════════════════════════
__all__ = [
    "fetch_iran_prices",
    "fetch_history_by_source",
    "fetch_quote_by_source",
    "get_data_source",
    "get_default_symbol_for_source",
    "is_symbol_available_in_source",
    "is_valid_nobitex_symbol",
    "resolve_source",
    "resolve_symbol_and_source",
    "source_has_market",
]
