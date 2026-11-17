"""
api/routers/symbols.py
Endpointهای نمادها — نسخه ۱۶.۹
============================================================
🔴 تغییرات:
  • افزودن جستجوی فارکس (XAU-USD, XAG-USD, ...)
  • فیلتر GC=F و نمادهای Yahoo
"""

import logging

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool

from api.deps import rate_limit_for
from api.schemas import SymbolItem, SymbolsResponse
from core.contracts import POPULAR_SYMBOLS, SYMBOLS
from services.data_service import get_iran_prices

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/symbols", tags=["Symbols"])


# ═══════════════════════════════════════════════════════════════
# 🔴 لیست ثابت فارکس — همون ۱۰ نماد تب فارکس فرانت
# ═══════════════════════════════════════════════════════════════
FOREX_SYMBOLS = [
    {"ticker": "XAU-USD", "name": "انس طلا", "source": "forex", "type": "کالا"},
    {"ticker": "XAG-USD", "name": "انس نقره", "source": "forex", "type": "کالا"},
    {"ticker": "USOIL-USD", "name": "نفت WTI", "source": "forex", "type": "کالا"},
    {"ticker": "UKOIL-USD", "name": "نفت برنت", "source": "forex", "type": "کالا"},
    {"ticker": "DXY-USD", "name": "شاخص دلار", "source": "forex", "type": "شاخص"},
    {"ticker": "US500-USD", "name": "S&P 500", "source": "forex", "type": "شاخص"},
    {"ticker": "US30-USD", "name": "داوجونز", "source": "forex", "type": "شاخص"},
    {"ticker": "USTEC-USD", "name": "نزدک ۱۰۰", "source": "forex", "type": "شاخص"},
    {"ticker": "EUR-USD", "name": "یورو/دلار", "source": "forex", "type": "فارکس"},
    {
        "ticker": "BTC-USD",
        "name": "بیت‌کوین (جهانی)",
        "source": "forex",
        "type": "کریپتو",
    },
]


def _is_bad_symbol(ticker: str) -> bool:
    if not ticker:
        return True
    return "=" in ticker or ticker.startswith("^")


def _normalize(s: str) -> str:
    return (
        (s or "")
        .strip()
        .replace("\u200c", "")
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace(" ", "")
        .lower()
    )


# ═══════════════════════════════════════════════════════════
# GET /symbols — همه نمادها
# ═══════════════════════════════════════════════════════════
@router.get("", response_model=SymbolsResponse)
async def list_symbols(source: str = ""):
    items = []

    for ticker, name in SYMBOLS.items():
        if _is_bad_symbol(ticker):
            continue
        if source:
            if source == "nobitex" and "-IRT" not in ticker and "-USD" not in ticker:
                continue
            if source == "global" and any(x in ticker for x in ["-IRT", "TSETMC"]):
                continue
        src = "nobitex" if "-IRT" in ticker else "global"
        items.append(SymbolItem(ticker=ticker, name=name, source=src))

    return SymbolsResponse(total=len(items), items=items)


# ═══════════════════════════════════════════════════════════
# GET /symbols/popular
# ═══════════════════════════════════════════════════════════
@router.get("/popular", response_model=SymbolsResponse)
async def popular_symbols():
    items = []
    for ticker, name, source in POPULAR_SYMBOLS:
        if _is_bad_symbol(ticker):
            continue
        items.append(
            SymbolItem(
                ticker=ticker,
                name=name,
                source=source,
                emoji=name.split()[0] if name else "",
            )
        )
    return SymbolsResponse(total=len(items), items=items)


# ═══════════════════════════════════════════════════════════
# GET /symbols/search — جستجو (کریپتو + بورس + فارکس)
# ═══════════════════════════════════════════════════════════
@router.get("/search")
async def search_symbols(
    request: Request,
    q: str = "",
    limit: int = Query(default=15, ge=1, le=50),
):
    if not q or len(q.strip()) < 2:
        return {"ok": True, "total": 0, "items": []}

    rate_limit_for(request, "symbols_search", limit=120, window_sec=60)

    try:
        return await run_in_threadpool(_search_sync, q, limit)
    except Exception as e:
        logger.error(f"[Symbols] search crashed: {e!r}", exc_info=True)
        return {"ok": False, "total": 0, "items": []}


def _search_sync(q: str, limit: int) -> dict:
    query = _normalize(q)
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def _add(ticker, name, source, item_type=None):
        if _is_bad_symbol(ticker):
            return
        key = (ticker, source)
        if key in seen:
            return
        seen.add(key)
        item = {"ticker": ticker, "name": name, "source": source}
        if item_type:
            item["type"] = item_type
        results.append(item)

    # ═══ ۱. فارکس (لیست ثابت) — اولویت اول ═══
    for it in FOREX_SYMBOLS:
        if len(results) >= limit:
            break
        if query in _normalize(it["name"]) or query in _normalize(it["ticker"]):
            _add(it["ticker"], it["name"], "forex", it.get("type"))

    # ═══ ۲. SYMBOLS ═══
    for ticker, name in SYMBOLS.items():
        if len(results) >= limit:
            break
        if _is_bad_symbol(ticker):
            continue
        if query in _normalize(ticker) or query in _normalize(name):
            src = "nobitex" if ("-USD" in ticker or "-IRT" in ticker) else "global"
            _add(ticker, name, src)

    # ═══ ۳. TSETMC ═══
    if len(results) < limit:
        try:
            from core.market_lists import get_iran_stock_map

            for symbol, name in get_iran_stock_map().items():
                if len(results) >= limit:
                    break
                if query in _normalize(symbol) or query in _normalize(name):
                    _add(symbol, f"{symbol} — {name}", "tsetmc")
        except Exception:
            logger.warning("[Symbols] TSETMC search failed", exc_info=True)

    # ═══ ۴. نوبیتکس ═══
    if len(results) < limit:
        try:
            from core.nobitex_fetcher import NOBITEX_SYMBOLS

            for ticker, nb_sym in NOBITEX_SYMBOLS.items():
                if len(results) >= limit:
                    break
                if _is_bad_symbol(ticker):
                    continue
                if query in _normalize(ticker) or query in _normalize(nb_sym):
                    display = ticker.replace("-IRT", "/تومان").replace("-USD", "/USDT")
                    _add(ticker, display, "nobitex")
        except Exception:
            logger.warning("[Symbols] Nobitex search failed", exc_info=True)

    return {"ok": True, "total": len(results), "items": results}


# ═══════════════════════════════════════════════════════════
# GET /symbols/forex — لیست کامل فارکس
# ═══════════════════════════════════════════════════════════
@router.get("/forex")
async def list_forex():
    return {"ok": True, "total": len(FOREX_SYMBOLS), "items": FOREX_SYMBOLS}


# ═══════════════════════════════════════════════════════════
# GET /symbols/iran-stocks
# ═══════════════════════════════════════════════════════════
@router.get("/iran-stocks")
async def iran_stocks():
    popular_stocks = [
        {"ticker": "فولاد", "name": "فولاد مبارکه", "source": "tsetmc"},
        {"ticker": "فملی", "name": "ملی صنایع مس", "source": "tsetmc"},
        {"ticker": "شپنا", "name": "پالایش نفت اصفهان", "source": "tsetmc"},
        {"ticker": "وبصادر", "name": "بانک صادرات", "source": "tsetmc"},
        {"ticker": "وتجارت", "name": "بانک تجارت", "source": "tsetmc"},
        {"ticker": "خودرو", "name": "ایران خودرو", "source": "tsetmc"},
        {"ticker": "خساپا", "name": "سایپا", "source": "tsetmc"},
        {"ticker": "فارس", "name": "پتروشیمی فارس", "source": "tsetmc"},
        {"ticker": "شتران", "name": "پالایش نفت تهران", "source": "tsetmc"},
        {"ticker": "طلا", "name": "صندوق طلا (پارسیان)", "source": "tsetmc"},
        {"ticker": "عیار", "name": "صندوق عیار", "source": "tsetmc"},
        {"ticker": "شاخص", "name": "شاخص کل", "source": "tsetmc"},
    ]
    return {"ok": True, "total": len(popular_stocks), "items": popular_stocks}


# ═══════════════════════════════════════════════════════════
# GET /symbols/sources
# ═══════════════════════════════════════════════════════════
@router.get("/sources")
async def list_sources():
    from core.sources import get_all_sources_info

    items = get_all_sources_info()
    return {
        "ok": True,
        "total": len(items),
        "items": items,
        "active_count": sum(1 for i in items if i["active"]),
        "planned_count": sum(1 for i in items if i["planned"]),
    }


# ═══════════════════════════════════════════════════════════
# GET /symbols/iran-prices
# ═══════════════════════════════════════════════════════════
@router.get("/iran-prices")
async def iran_prices(request: Request):
    rate_limit_for(request, "iran_prices", limit=30, window_sec=60)
    return await run_in_threadpool(get_iran_prices)
