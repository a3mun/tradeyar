"""
api/routers/symbols.py
Endpointهای نمادها
============================================================
- GET /symbols              → لیست همه نمادها
- GET /symbols/popular      → نمادهای محبوب
- GET /symbols/search       → جستجوی هوشمند
- GET /symbols/iran-prices  → قیمت‌های ایران

باگ ۶ (نسخه ۱.۵): ``get_iran_prices`` دو درخواست HTTP اسکرپینگ
(AlanChand + TGJU) می‌زند و ``search_symbols`` ممکن است
``NOBITEX_SYMBOLS`` را بارگذاری کند — هر دو sync. پس threadpool.
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


# ═══════════════════════════════════════════════════════════
# GET /symbols — همه نمادها
# ═══════════════════════════════════════════════════════════
@router.get("", response_model=SymbolsResponse)
async def list_symbols(source: str = ""):
    """لیست همه نمادهای شناخته‌شده"""
    items = []

    for ticker, name in SYMBOLS.items():
        # ─── فیلتر بر اساس منبع ───
        if source:
            if source == "nobitex" and "-IRT" not in ticker and "-USD" not in ticker:
                continue
            if source == "global" and any(x in ticker for x in ["-IRT", "TSETMC"]):
                continue

        # ─── تشخیص منبع ───
        if "-IRT" in ticker:
            src = "nobitex"
        elif ticker.endswith("=F") or ticker.startswith("^"):
            src = "global"
        else:
            src = "global"

        items.append(SymbolItem(ticker=ticker, name=name, source=src))

    return SymbolsResponse(total=len(items), items=items)


# ═══════════════════════════════════════════════════════════
# GET /symbols/popular — محبوب‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/popular", response_model=SymbolsResponse)
async def popular_symbols():
    """۶ نماد محبوب پیش‌فرض"""
    items = []
    for ticker, name, source in POPULAR_SYMBOLS:
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
# GET /symbols/search — جستجوی هوشمند
# ═══════════════════════════════════════════════════════════
@router.get("/search")
async def search_symbols(
    request: Request,
    q: str = "",
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    جستجوی نماد در همه منابع.
    - انگلیسی: BTC, ETH, PAXG
    - فارسی: بیت‌کوین, فولاد, تتر
    """
    if not q or len(q.strip()) < 2:
        return {"ok": True, "total": 0, "items": []}

    rate_limit_for(request, "symbols_search", limit=120, window_sec=60)

    # ─── جستجو در thread جدا (ممکن است بارگذاری JSON و لاگ کند باشد) ───
    return await run_in_threadpool(_search_sync, q, limit)


def _search_sync(q: str, limit: int) -> dict:
    """بدنه‌ی sync جستجو — در threadpool اجرا می‌شود"""
    query = q.strip().lower()
    results: list[dict] = []
    seen: set[str] = set()

    def _add(ticker: str, name: str, source: str):
        if ticker in seen:
            return
        seen.add(ticker)
        results.append({"ticker": ticker, "name": name, "source": source})

    # ═══ ۱. SYMBOLS (دیکشنری contracts) ═══
    for ticker, name in SYMBOLS.items():
        if len(results) >= limit:
            break
        if query in ticker.lower() or query in name.lower():
            src = "nobitex" if ("-USD" in ticker or "-IRT" in ticker) else "global"
            _add(ticker, name, src)

    # ═══ ۲. TSETMC (بورس تهران) ═══
    if len(results) < limit:
        try:
            from core.market_lists import get_iran_stock_map

            for symbol, name in get_iran_stock_map().items():
                if len(results) >= limit:
                    break
                if query in symbol.lower() or query in name.lower():
                    _add(symbol, f"{symbol} — {name}", "tsetmc")
        except Exception:
            logger.warning("[Symbols] جستجوی TSETMC ناموفق", exc_info=True)

    # ═══ ۳. نوبیتکس (نمادهای اضافی) ═══
    if len(results) < limit:
        try:
            from core.nobitex_fetcher import NOBITEX_SYMBOLS

            for ticker, nb_sym in NOBITEX_SYMBOLS.items():
                if len(results) >= limit:
                    break
                if query in ticker.lower() or query in nb_sym.lower():
                    display = ticker.replace("-IRT", "/تومان").replace("-USD", "/USDT")
                    _add(ticker, display, "nobitex")
        except Exception:
            logger.warning("[Symbols] جستجوی نوبیتکس ناموفق", exc_info=True)

    return {"ok": True, "total": len(results), "items": results}


# ═══════════════════════════════════════════════════════════
# GET /symbols/sources — لیست صرافی‌ها با وضعیت
# ═══════════════════════════════════════════════════════════
@router.get("/sources")
async def list_sources():
    """
    لیست همه‌ی صرافی‌ها — فعال و برنامه‌ریزی‌شده.

    برای پر کردن SettingsPanel استفاده می‌شود. صرافی‌های
    ``planned=True`` باید در فرانت غیرفعال با بج «به‌زودی»
    نمایش داده شوند.
    """
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
# GET /symbols/iran-prices — قیمت‌های ایران
# ═══════════════════════════════════════════════════════════
@router.get("/iran-prices")
async def iran_prices(request: Request):
    """
    قیمت‌های لحظه‌ای ایران (AlanChand/TGJU).

    ⚠️ این تابع تا ۲ درخواست HTTP اسکرپینگ با timeout=20 می‌زند.
       در event loop یعنی قفل تا ۴۰ ثانیه. پس threadpool.
    """
    rate_limit_for(request, "iran_prices", limit=30, window_sec=60)
    return await run_in_threadpool(get_iran_prices)
