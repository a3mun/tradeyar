"""
api/routers/orderbook.py
عمق بازار (Order Book) — ✅ فعال (فاز ۶.۹)
============================================================
قبلاً placeholder با ۵۰۱ بود. الان پیاده شده.

═══ کاربرد ═══
  • Imbalance خرید/فروش — نسبت حجم bids به asks
  • اسپرد واقعی — هزینه‌ی واقعی ورود و خروج
  • دیوار سفارش — سطحی با حجم غیرعادی

⚠️ **محدودیت علمی مهم:**
    imbalance **لحظه‌ای** است و می‌تواند با یک سفارش بزرگ
    (spoofing) دستکاری شود. تأیید تجربی نشان داد بین صرافی‌ها
    هم متناقض است:

        BTC-IRT → نوبیتکس ۰.۶۳ (خرید) ولی بیت‌پین ۰.۰۷ (فروش)

    پس در تحلیل با **وزن کم** استفاده می‌شود و هرگز تنها
    عامل سیگنال نیست.

═══ صرافی‌های پشتیبانی‌شده ═══
    ✅ نوبیتکس · بیت‌پین · والکس · تبدیل
    ❌ TSETMC (بورس عمق لحظه‌ای عمومی ندارد)
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.concurrency import run_in_threadpool

from api.deps import rate_limit_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orderbook", tags=["OrderBook"])

# ─── صرافی‌های دارای عمق بازار ───
ORDERBOOK_SOURCES = frozenset({"nobitex", "bitpin", "wallex", "tabdeal"})


# ═══════════════════════════════════════════════════════════
# GET /orderbook/{ticker} — عمق بازار کامل
# ═══════════════════════════════════════════════════════════
@router.get("/{ticker}")
async def get_orderbook(
    ticker: str,
    request: Request,
    source: str = Query(default="nobitex", description="صرافی"),
    depth: int = Query(default=20, ge=5, le=100, description="تعداد سطوح"),
):
    """
    عمق بازار نرمال‌شده یک نماد.

    Returns::

        {
          "ok": true,
          "ticker": "BTC-USD",
          "source": "nobitex",
          "bids": [{"price": 84650.0, "quantity": 0.01}, ...],
          "asks": [{"price": 84738.0, "quantity": 0.02}, ...],
          "best_bid": 84650.01,
          "best_ask": 84738.0,
          "mid": 84694.0,
          "spread": 87.99,
          "spread_pct": 0.104,
          "imbalance": 0.448,
          "bid_volume": 1.2,
          "ask_volume": 1.5,
          "depth_value": 250000.0,
          "wall": {"side": "bid", "price": ..., "ratio": 4.2},
          "pressure_fa": "فشار فروش"
        }

    ⚠️ عمق بازار **لحظه‌ای** است — برای تازه‌نگه‌داشتن،
       فرانت باید هر ۱۰-۲۰ ثانیه poll کند.
    """
    rate_limit_for(request, "orderbook", limit=60, window_sec=60)

    src = (source or "").lower()

    if src not in ORDERBOOK_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"صرافی «{source}» عمق بازار ندارد. "
                f"صرافی‌های پشتیبانی‌شده: {', '.join(sorted(ORDERBOOK_SOURCES))}"
            ),
        )

    from core.orderbook import get_orderbook as fetch_ob

    # ─── sync (requests) → threadpool ───
    ob = await run_in_threadpool(fetch_ob, ticker, src, depth)

    if ob is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"عمق بازار {ticker} در {source} در دسترس نیست "
                f"— نماد یا بازار موجود نیست"
            ),
        )

    return ob


# ═══════════════════════════════════════════════════════════
# GET /orderbook/{ticker}/summary — خلاصه‌ی سبک
# ═══════════════════════════════════════════════════════════
@router.get("/{ticker}/summary")
async def get_orderbook_summary(
    ticker: str,
    request: Request,
    source: str = Query(default="nobitex"),
):
    """
    خلاصه‌ی عمق بازار — برای نمایش سبک در SignalCard.

    Returns::

        {
          "ok": true,
          "ticker": "BTC-USD",
          "source": "nobitex",
          "imbalance": 0.448,
          "spread_pct": 0.104,
          "pressure_fa": "فشار فروش",
          "has_bid_wall": false,
          "has_ask_wall": false,
          "execution_cost": {...},
          "sources_agree": null
        }
    """
    rate_limit_for(request, "orderbook_summary", limit=60, window_sec=60)

    src = (source or "").lower()
    if src not in ORDERBOOK_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"صرافی «{source}» عمق بازار ندارد",
        )

    from core.contracts import get_fee_rate
    from core.orderbook import execution_cost_pct, get_orderbook as fetch_ob

    ob = await run_in_threadpool(fetch_ob, ticker, src, 20)

    if ob is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"عمق بازار {ticker} در {source} در دسترس نیست",
        )

    wall = ob.get("wall") or {}
    cost = execution_cost_pct(ob["spread_pct"], get_fee_rate(src))

    return {
        "ok": True,
        "ticker": ticker,
        "source": src,
        "imbalance": ob["imbalance"],
        "spread_pct": ob["spread_pct"],
        "pressure_fa": ob["pressure_fa"],
        "has_bid_wall": wall.get("side") == "bid",
        "has_ask_wall": wall.get("side") == "ask",
        "wall": wall or None,
        "execution_cost": cost,
    }


# ═══════════════════════════════════════════════════════════
# GET /orderbook/{ticker}/compare — مقایسه‌ی عمق بین صرافی‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/{ticker}/compare")
async def compare_orderbooks(
    ticker: str,
    request: Request,
    depth: int = Query(default=20, ge=5, le=50),
):
    """
    مقایسه‌ی عمق بازار بین صرافی‌ها.

    🔴 **چرا مهم است (نکته‌ی علم اقتصادی):**

    کاربر پرسید: «چرا یک نماد در یک صرافی SHORT و در صرافی
    دیگر LONG است؟ جهت بازار باید یکی باشد.»

    پاسخ: جهت **کلان** یکی است، ولی **عمق محلی** متفاوت.
    این endpoint آن تفاوت را شفاف می‌کند:

      • اگر همه هم‌جهت‌اند → سیگنال **قابل اتکا**
      • اگر متناقضند → نقدینگی محلی غالب است، **احتیاط**
    """
    rate_limit_for(request, "orderbook_compare", limit=20, window_sec=60)

    from core.orderbook import get_orderbook as fetch_ob

    async def one(src: str):
        try:
            return src, await run_in_threadpool(fetch_ob, ticker, src, depth)
        except Exception:
            return src, None

    import asyncio

    results = await asyncio.gather(*(one(s) for s in sorted(ORDERBOOK_SOURCES)))

    items = []
    imbalances = []
    for src, ob in results:
        if ob:
            items.append(
                {
                    "source": src,
                    "imbalance": ob["imbalance"],
                    "spread_pct": ob["spread_pct"],
                    "pressure_fa": ob["pressure_fa"],
                    "best_bid": ob["best_bid"],
                    "best_ask": ob["best_ask"],
                }
            )
            imbalances.append(ob["imbalance"])

    # ─── آیا صرافی‌ها هم‌جهت‌اند؟ ───
    agree = None
    if len(imbalances) >= 2:
        above = sum(1 for i in imbalances if i > 0.5)
        below = sum(1 for i in imbalances if i < 0.5)
        agree = above == 0 or below == 0

    return {
        "ok": True,
        "ticker": ticker,
        "total": len(items),
        "items": items,
        # ─── شفافیت: آیا صرافی‌ها هم‌نظرند؟ ───
        "sources_agree": agree,
        "spread_min_pct": min((i["spread_pct"] for i in items), default=None),
        "spread_max_pct": max((i["spread_pct"] for i in items), default=None),
        "imbalance_min": min(imbalances, default=None),
        "imbalance_max": max(imbalances, default=None),
    }
