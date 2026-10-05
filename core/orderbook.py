"""
core/orderbook.py
عمق بازار — نرمال‌سازی یکسان برای همه‌ی صرافی‌ها
============================================================
نسخه ۱.۰ · فاز ۶.۹

═══ چرا این ماژول لازم شد ═══

هر صرافی عمق بازار را **فرمت متفاوتی** می‌دهد:

    نوبیتکس : {last_price, best_bid, best_ask, spread, bids, asks}
              🔴 bid و ask برعکس! (best_bid > best_ask)
    بیت‌پین : {bids, asks}                    ← فقط خام
    والکس   : {bids, asks}                    ← فقط خام
    تبدیل   : {bids, asks, imbalance, ...}    ← کامل‌ترین

بدون نرمال‌سازی، مقایسه‌ی صرافی‌ها و استفاده در تحلیل **غلط**
می‌شود.

═══ خروجی یکسان ═══

    {
      "ok": True,
      "ticker": "BTC-USD",
      "source": "nobitex",
      "bids": [{"price": .., "quantity": ..}, ...],   # نزولی
      "asks": [{"price": .., "quantity": ..}, ...],   # صعودی
      "best_bid": float,
      "best_ask": float,
      "mid": float,
      "spread": float,
      "spread_pct": float,
      "imbalance": float,          # 0..1 — بالای ۰.۵ فشار خرید
      "bid_volume": float,
      "ask_volume": float,
      "depth_usd": float,          # ارزش کل سطوح
      "wall": {...} | None,        # دیوار سفارش
      "pressure_fa": str,          # «فشار خرید» / ...
    }

═══ نکته‌ی علمی درباره‌ی imbalance ═══

``imbalance = bid_volume / (bid_volume + ask_volume)`` روی **N سطح
اول** — نه کل دفتر. دلیل: سطوح دور از قیمت به معامله‌ی فعلی
ربطی ندارند و فقط نویز اضافه می‌کنند.

⚠️ **محدودیت مهم:** imbalance **لحظه‌ای** است و می‌تواند با
   یک سفارش بزرگ (spoofing) دستکاری شود. پس در تحلیل با وزن
   کم استفاده می‌شود و **تنها** عامل سیگنال نیست.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── تعداد سطح پیش‌فرض برای محاسبه ───
DEFAULT_DEPTH = 20

# ─── آستانه‌ی دیوار سفارش ───
# اگر حجم یک سطح > این ضریب × میانگین حجم سطوح باشد، دیوار است
WALL_MULTIPLIER = 4.0

# ─── آستانه‌های فشار ───
IMBALANCE_STRONG_BUY = 0.65  # فشار خرید قوی
IMBALANCE_BUY = 0.55
IMBALANCE_SELL = 0.45
IMBALANCE_STRONG_SELL = 0.35


def _parse_levels(raw, limit: int = DEFAULT_DEPTH) -> list[dict]:
    """
    نرمال‌سازی سطوح خام به ``[{"price", "quantity"}, ...]``.

    ورودی‌های ممکن:
      • ``[[price, qty], ...]``  (اکثر صرافی‌ها)
      • ``[{"price": .., "quantity": ..}, ...]``
      • ``[{"price": .., "amount": ..}, ...]``
    """
    if not raw:
        return []

    out: list[dict] = []
    for item in raw[:limit]:
        try:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                p, q = float(item[0]), float(item[1])
            elif isinstance(item, dict):
                p = float(item.get("price") or 0)
                q = float(
                    item.get("quantity")
                    or item.get("amount")
                    or item.get("qty")
                    or 0
                )
            else:
                continue

            if p > 0 and q > 0:
                out.append({"price": p, "quantity": q})
        except (TypeError, ValueError):
            continue

    return out


def _detect_wall(levels: list[dict], side: str) -> Optional[dict]:
    """
    تشخیص «دیوار سفارش» — سطحی با حجم غیرعادی.

    ═══ چرا مهم است ═══
    دیوار سفارش یعنی یک بازیگر بزرگ در آن قیمت سفارش گذاشته.
    این می‌تواند:
      • حمایت/مقاومت **واقعی** باشد (اگر پایدار بماند)
      • «spoofing» باشد (اگر سریع برداشته شود)

    ⚠️ چون از یک snapshot قابل تشخیص نیست کدام است، فقط
       **اطلاع‌رسانی** می‌کنیم، نه سیگنال.
    """
    if len(levels) < 5:
        return None

    volumes = [x["quantity"] for x in levels]
    avg = sum(volumes) / len(volumes)
    if avg <= 0:
        return None

    biggest = max(levels, key=lambda x: x["quantity"])
    ratio = biggest["quantity"] / avg

    if ratio >= WALL_MULTIPLIER:
        return {
            "side": side,
            "price": biggest["price"],
            "quantity": biggest["quantity"],
            "ratio": round(ratio, 2),
        }
    return None


def normalize_orderbook(
    ticker: str,
    source: str,
    raw: dict,
    depth: int = DEFAULT_DEPTH,
) -> Optional[dict]:
    """
    نرمال‌سازی یک عمق بازار خام به فرمت یکسان.

    ═══ 🔴 کشف مهم: بعضی صرافی‌ها bids/asks را جابه‌جا می‌دهند ═══

    نوبیتکس (تأیید تجربی ۱۴۰۵/۰۷) در پاسخش:
        ``bids`` → قیمت‌های **فروش** (باید نزولی باشد، صعودی است)
        ``asks`` → قیمت‌های **خرید**  (باید صعودی باشد، نزولی است)
        ``best_bid`` (۸۴۸۳۶) > ``best_ask`` (۸۴۵۳۰)  ← غیرممکن

    این باعث spread **منفی** می‌شد.

    ═══ راه‌حل: به برچسب‌ها اعتماد نکن ═══

    ریاضی نمی‌تواند غلط باشد:
      • **همیشه** بالاترین قیمت خرید = best_bid
      • **همیشه** پایین‌ترین قیمت فروش = best_ask

    پس دو مجموعه را با هم ادغام می‌کنیم، min/max می‌گیریم و
    بر اساس آن‌ها بازچینش می‌کنیم. این روش برای **همه‌ی**
    صرافی‌ها کار می‌کند — چه برچسب‌ها درست باشند چه جابه‌جا.

    Args:
        ticker: نماد استاندارد ما (``BTC-USD``)
        source: کلید صرافی
        raw:    پاسخ خام fetcher
        depth:  تعداد سطح برای محاسبه

    Returns:
        dict نرمال‌شده، یا ``None`` اگر داده‌ی کافی نبود.
    """
    if not raw or not isinstance(raw, dict):
        return None

    bids = _parse_levels(raw.get("bids"), depth)
    asks = _parse_levels(raw.get("asks"), depth)

    if not bids or not asks:
        return None

    # ═══ مرتب‌سازی ═══
    bids.sort(key=lambda x: x["price"], reverse=True)  # نزولی
    asks.sort(key=lambda x: x["price"])  # صعودی

    best_bid = bids[0]["price"]
    best_ask = asks[0]["price"]

    # ═══ 🔴 تشخیص و اصلاح برچسب برعکس ═══
    #
    # اگر «bid» از «ask» بالاتر باشد، برچسب‌ها قطعاً جابه‌جا
    # هستند — چون خرید همیشه زیر فروش است.
    if best_bid >= best_ask:
        # ─── ادغام هر دو مجموعه و تفکیک بر اساس mid ───
        all_levels = bids + asks
        all_levels.sort(key=lambda x: x["price"], reverse=True)

        true_best_bid = all_levels[0]["price"]
        true_best_ask = all_levels[-1]["price"]

        # ─── امنیت: اگر داده واقعاً خراب بود، رد کن ───
        if true_best_bid <= true_best_ask:
            logger.warning(
                f"[OrderBook] {source}/{ticker}: داده‌ی عمق نامعتبر "
                f"({true_best_bid} <= {true_best_ask}) — رد شد"
            )
            return None

        logger.debug(
            f"[OrderBook] {source}/{ticker}: bids/asks جابه‌جا بودند "
            f"({best_bid} >= {best_ask}) — اصلاح شد"
        )
        # ─── جابه‌جایی نقش‌ها ───
        bids, asks = asks, bids
        # ─── بازمرتب‌سازی ───
        bids.sort(key=lambda x: x["price"], reverse=True)
        asks.sort(key=lambda x: x["price"])
        best_bid = bids[0]["price"]
        best_ask = asks[0]["price"]

    mid = (best_bid + best_ask) / 2
    spread = best_ask - best_bid
    spread_pct = (spread / mid * 100) if mid else 0.0

    bid_volume = sum(x["quantity"] for x in bids)
    ask_volume = sum(x["quantity"] for x in asks)
    total_volume = bid_volume + ask_volume

    imbalance = (bid_volume / total_volume) if total_volume > 0 else 0.5

    # ─── فشار ───
    if imbalance >= IMBALANCE_STRONG_BUY:
        pressure_fa = "فشار خرید قوی"
    elif imbalance >= IMBALANCE_BUY:
        pressure_fa = "فشار خرید"
    elif imbalance <= IMBALANCE_STRONG_SELL:
        pressure_fa = "فشار فروش قوی"
    elif imbalance <= IMBALANCE_SELL:
        pressure_fa = "فشار فروش"
    else:
        pressure_fa = "متعادل"

    # ─── ارزش کل (برای مقایسه‌ی نقدینگی) ───
    depth_value = sum(x["price"] * x["quantity"] for x in bids + asks)

    # ─── دیوار سفارش ───
    wall = _detect_wall(bids, "bid") or _detect_wall(asks, "ask")

    return {
        "ok": True,
        "ticker": ticker,
        "source": source,
        "bids": bids,
        "asks": asks,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": mid,
        "spread": spread,
        "spread_pct": round(spread_pct, 4),
        "imbalance": round(imbalance, 4),
        "bid_volume": bid_volume,
        "ask_volume": ask_volume,
        "depth_value": depth_value,
        "wall": wall,
        "pressure_fa": pressure_fa,
    }


def get_orderbook(ticker: str, source: str, depth: int = DEFAULT_DEPTH) -> Optional[dict]:
    """
    عمق بازار نرمال‌شده از صرافی مشخص.

    ⚠️ این تابع **شبکه می‌زند** — در مسیر تحلیل با احتیاط
       استفاده کن (کش یا ``to_thread`` لازم است).

    Returns:
        dict نرمال‌شده یا ``None``.
    """
    raw = _fetch_raw(ticker, source, depth)
    if raw is None:
        return None

    # ─── بعضی fetcherها خودشان نرمال می‌کنند ───
    if raw.get("imbalance") is not None and raw.get("best_bid"):
        # ─── ولی باز هم اعتبارسنجی کن ───
        if raw.get("best_bid", 0) >= raw.get("best_ask", 0):
            raw = dict(raw)
            raw["best_bid"], raw["best_ask"] = raw["best_ask"], raw["best_bid"]
            raw["spread"] = abs(raw["best_ask"] - raw["best_bid"])

    return normalize_orderbook(ticker, source, raw, depth)


def _fetch_raw(ticker: str, source: str, depth: int) -> Optional[dict]:
    """دریافت پاسخ خام از fetcher صرافی مربوطه"""
    src = (source or "").lower()

    try:
        if src == "nobitex":
            from core.nobitex_fetcher import fetch_nobitex_orderbook_for_ticker

            return fetch_nobitex_orderbook_for_ticker(ticker)

        if src == "bitpin":
            from core.bitpin_fetcher import fetch_bitpin_orderbook

            return fetch_bitpin_orderbook(ticker)

        if src == "wallex":
            from core.wallex_fetcher import fetch_wallex_orderbook

            return fetch_wallex_orderbook(ticker)

        if src == "tabdeal":
            from core.tabdeal_fetcher import fetch_tabdeal_orderbook

            return fetch_tabdeal_orderbook(ticker, depth=depth)
    except Exception as e:
        logger.warning(f"[OrderBook] {source}/{ticker}: {e}")
        return None

    return None


def imbalance_vote(imbalance: float) -> tuple[int, float]:
    """
    تبدیل imbalance به رأی و امتیاز برای گروه «حجم».

    ═══ منطق ═══
        imbalance ≥ ۰.۶۵  →  رأی +۱ (فشار خرید قوی)
        imbalance ≥ ۰.۵۵  →  رأی +۱ (فشار خرید)
        ۰.۴۵ < i < ۰.۵۵   →  رأی ۰  (متعادل)
        imbalance ≤ ۰.۴۵  →  رأی -۱ (فشار فروش)
        imbalance ≤ ۰.۳۵  →  رأی -۱ (فشار فروش قوی)

    ⚠️ امتیاز (score) عمداً **کم** است (حداکثر ۰.۵) چون:
       ۱. imbalance لحظه‌ای است، نه روند
       ۲. با spoofing قابل دستکاری است
       ۳. تنها باید **تأییدکننده** باشد، نه تعیین‌کننده
    """
    if imbalance >= IMBALANCE_STRONG_BUY:
        return 1, 0.5
    if imbalance >= IMBALANCE_BUY:
        return 1, 0.3
    if imbalance <= IMBALANCE_STRONG_SELL:
        return -1, -0.5
    if imbalance <= IMBALANCE_SELL:
        return -1, -0.3
    return 0, 0.0


def execution_cost_pct(
    spread_pct: float,
    fee_rate: float,
    slippage_pct: float = 0.05,
) -> dict:
    """
    هزینه‌ی **واقعی** ورود و خروج.

    ═══ چرا مهم است ═══
    R:R خام فقط کارمزد را حساب می‌کند، ولی هزینه‌ی واقعی شامل:
        • کارمزد (fee)
        • **نصف اسپرد** در هر طرف (اگر market بزنی)
        • اسلیپیج (لغزش قیمت)

    هر سه با هم می‌توانند ۱-۲٪ باشند — که در TF کوتاه **کل
    سود** را می‌خورد.

    Returns:
        dict با ``fee_pct``, ``spread_cost_pct``, ``slippage_pct``,
        ``total_pct``
    """
    fee_pct = fee_rate * 100

    # ─── نصف اسپرد در هر طرف: یک بار ورود، یک بار خروج ───
    # (با market order، نیمی از اسپرد را در هر معامله می‌پردازی)
    spread_cost = spread_pct  # نصف + نصف = یک اسپرد کامل

    total = fee_pct + spread_cost + (slippage_pct * 2)

    return {
        "fee_pct": round(fee_pct, 4),
        "spread_cost_pct": round(spread_cost, 4),
        "slippage_pct": round(slippage_pct * 2, 4),
        "total_pct": round(total, 4),
    }


__all__ = [
    "DEFAULT_DEPTH",
    "execution_cost_pct",
    "get_orderbook",
    "imbalance_vote",
    "normalize_orderbook",
]
