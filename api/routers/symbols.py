"""
api/routers/symbols.py
Endpointهای نمادها
============================================================
- GET /symbols              → لیست همه نمادها
- GET /symbols/popular      → نمادهای محبوب
- GET /symbols/iran-prices  → قیمت‌های ایران
"""

import logging
from fastapi import APIRouter

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
async def search_symbols(q: str = "", limit: int = 10):
    """
    جستجوی نماد در همه منابع.
    - انگلیسی: BTC, ETH, PAXG
    - فارسی: بیت‌کوین, فولاد, تتر
    """
    if not q or len(q.strip()) < 2:
        return {"ok": True, "total": 0, "items": []}

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
            pass

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
            pass

    return {"ok": True, "total": len(results), "items": results}


# ═══════════════════════════════════════════════════════════
# GET /symbols/iran-prices — قیمت‌های ایران
# ═══════════════════════════════════════════════════════════
@router.get("/iran-prices")
async def iran_prices():
    """قیمت‌های لحظه‌ای ایران (AlanChand/TGJU)"""
    return get_iran_prices()
