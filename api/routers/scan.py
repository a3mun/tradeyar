"""
api/routers/scan.py
Endpoint اسکنر بازار
============================================================
- POST /scan → اسکن یک دسته

تغییرات:
  - استفاده از MARKET_CATEGORIES به جای MARKET_LISTS
  - پشتیبانی از ساختار tickers (لیست tuple)
"""

import logging
from fastapi import APIRouter, HTTPException

from api.schemas import ScanRequest, ScanResponse, ScanItem
from core.market_lists import MARKET_CATEGORIES
from services.analyzer_service import analyze

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["Scan"])


# ═══════════════════════════════════════════════════════════
# POST /scan — اسکن یک دسته
# ═══════════════════════════════════════════════════════════
@router.post("", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest):
    """اسکن نمادهای یک دسته و برگرداندن سیگنال‌های قوی"""
    category = req.category

    # ─── دریافت دسته ───
    cat_data = MARKET_CATEGORIES.get(category)
    if not cat_data:
        raise HTTPException(status_code=404, detail=f"دسته {category} پیدا نشد")

    tickers = cat_data.get("tickers", [])
    source = cat_data.get("source", "nobitex")

    # ─── اگه دسته iran_stocks هست، حتماً TSETMC ───
    if category == "iran_stocks":
        source = "tsetmc"

    if not tickers:
        raise HTTPException(status_code=404, detail=f"دسته {category} خالی است")

    results = []

    # ═══ اسکن ═══
    for item in tickers[: req.limit * 3]:
        # ─── پشتیبانی از tuple و dict ───
        if isinstance(item, tuple):
            ticker, name = item[0], item[1] if len(item) > 1 else item[0]
        elif isinstance(item, dict):
            ticker = item.get("ticker", "")
            name = item.get("name", ticker)
        else:
            ticker = str(item)
            name = ticker

        if not ticker:
            continue

        try:
            r = analyze(
                ticker=ticker,
                source=source,
                tf_name=req.timeframe,
                market_type=req.market_type,
                risk_profile=req.risk_profile,
                ticker_name=name,
            )
            if r and r["direction"] != "neutral":
                results.append(
                    ScanItem(
                        ticker=ticker,
                        name=name,
                        price=r["price"],
                        signal=r["signal"],
                        confidence=r["confidence"],
                        direction=r["direction"],
                    )
                )
        except Exception as e:
            logger.warning(f"[Scan] خطا در {ticker}: {e}")

        if len(results) >= req.limit:
            break

    # ─── مرتب‌سازی بر اساس اطمینان ───
    results.sort(key=lambda x: -x.confidence)

    return ScanResponse(
        category=category,
        timeframe=req.timeframe,
        total=len(results),
        items=results,
    )


# ═══════════════════════════════════════════════════════════
# GET /scan/categories — لیست دسته‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/categories")
async def list_categories():
    """لیست همه دسته‌های اسکن"""
    items = []
    for key, data in MARKET_CATEGORIES.items():
        items.append(
            {
                "key": key,
                "name": data.get("name", key),
                "icon": data.get("icon", ""),
                "description": data.get("description", ""),
                "source": data.get("source", "global"),
                "count": len(data.get("tickers", [])),
            }
        )
    return {"ok": True, "total": len(items), "items": items}
