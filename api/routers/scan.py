"""
api/routers/scan.py
Endpoint اسکنر بازار — نسخه ۳.۰
============================================================
🔴 تغییرات نسخه ۳.۰:
  • **دیگر سیگنال ثبت نمی‌کند** — فقط analyze می‌زند
  • کاربر با دکمه «راستی‌آزمایی» خودش تصمیم می‌گیرد
  • نتیجه: راستی‌آزمایی شلوغ نمی‌شود، بار سرور کم می‌شود
"""

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from api.deps import rate_limit_for
from api.schemas import ScanItem, ScanRequest, ScanResponse
from core.market_lists import MARKET_CATEGORIES
from services.analyzer_service import analyze

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["Scan"])

MAX_CONCURRENT = 6
SCAN_BUDGET_SEC = 30.0
MIN_CONFIDENCE = 50


def _normalize_ticker(item) -> tuple[str, str] | None:
    if isinstance(item, (list, tuple)):
        ticker = str(item[0]) if item else ""
        name = str(item[1]) if len(item) > 1 else ticker
    elif isinstance(item, dict):
        ticker = str(item.get("ticker", ""))
        name = str(item.get("name", "") or ticker)
    else:
        ticker = str(item)
        name = ticker

    if not ticker:
        return None
    return ticker, name


def _is_quality_signal(res: dict) -> bool:
    if not res:
        return False

    direction = res.get("direction")
    if direction == "neutral":
        return False

    confidence = res.get("confidence", 0)
    if confidence < MIN_CONFIDENCE:
        return False

    signal = res.get("signal", "")
    if "ضعیف" in signal:
        return False

    return True


@router.post("", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest, request: Request):
    """
    اسکن نمادها — **بدون ثبت سیگنال**.

    🔴 تغییر نسخه ۳.۰:
        این endpoint دیگر ``record_signal`` نمی‌زند. کاربر اگر
        خواست، با دکمه «راستی‌آزمایی» توی UI، خودش ثبت می‌کند.

    ═══ چرا ═══
        قبلاً هر scan ۵۰ سیگنال ثبت می‌کرد. با چند scan در روز،
        backtest با صدها سیگنال نویز پر می‌شد. حالا فقط سیگنال‌هایی
        که کاربر **عمداً** ثبت کرده، وارد راستی‌آزمایی می‌شوند.
    """
    rate_limit_for(request, "scan", limit=10, window_sec=60)

    cat_data = MARKET_CATEGORIES.get(req.category)
    if not cat_data:
        raise HTTPException(status_code=404, detail=f"دسته {req.category} پیدا نشد")

    # ═══ انتخاب source ═══
    if req.category == "iran_stocks":
        source = "tsetmc"
    elif req.source:
        source = req.source
    else:
        source = cat_data.get("source", "nobitex")

    # ═══ لیست نمادها ═══
    if req.category == "crypto":
        from core.market_lists import get_top_symbols_by_volume

        parsed = get_top_symbols_by_volume(source, limit=50)
        if not parsed:
            raw_tickers = cat_data.get("tickers", [])
            parsed = []
            for item in raw_tickers:
                norm = _normalize_ticker(item)
                if norm:
                    parsed.append(norm)
    else:
        raw_tickers = cat_data.get("tickers", [])
        if not raw_tickers:
            raise HTTPException(
                status_code=404,
                detail=f"دسته {req.category} خالی است",
            )
        parsed = []
        for item in raw_tickers:
            norm = _normalize_ticker(item)
            if norm:
                parsed.append(norm)
            if len(parsed) >= req.limit * 3:
                break

    if not parsed:
        raise HTTPException(
            status_code=404,
            detail=f"دسته {req.category} نماد معتبری ندارد",
        )

    # ═══ اسکن موازی ═══
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    deadline = time.monotonic() + SCAN_BUDGET_SEC

    async def _analyze_one(ticker: str, name: str):
        if time.monotonic() >= deadline:
            return None
        async with semaphore:
            if time.monotonic() >= deadline:
                return None
            return await run_in_threadpool(
                analyze,
                ticker=ticker,
                source=source,
                tf_name=req.timeframe,
                market_type=req.market_type,
                risk_profile=req.risk_profile,
                ticker_name=name,
                include_extras=False,
                # 🔴 جدید: در اسکن، سیگنال ثبت نکن
                skip_record=True,
            )

    raw_results = await asyncio.gather(
        *(_analyze_one(t, n) for t, n in parsed),
        return_exceptions=True,
    )

    # ═══ جمع‌آوری ═══
    results: list[ScanItem] = []
    errors = 0
    skipped = 0
    filtered = 0

    for (ticker, name), res in zip(parsed, raw_results):
        if res is None:
            skipped += 1
            continue

        if isinstance(res, BaseException):
            errors += 1
            logger.warning(f"[Scan] خطا در {ticker}: {res!r}")
            continue

        if not _is_quality_signal(res):
            filtered += 1
            continue

        price = res.get("price", 0)
        if not price or price <= 0:
            filtered += 1
            continue

        results.append(
            ScanItem(
                ticker=ticker,
                name=name,
                price=price,
                signal=res["signal"],
                confidence=res["confidence"],
                direction=res["direction"],
            )
        )

    results.sort(key=lambda x: -x.confidence)
    results = results[: req.limit]

    logger.info(
        f"[Scan] {req.category}/{source}: {len(results)} نتیجه | "
        f"{filtered} فیلترشده | {errors} خطا | {skipped} رد از {len(parsed)}"
    )

    return ScanResponse(
        category=req.category,
        timeframe=req.timeframe,
        total=len(results),
        items=results,
    )


@router.get("/categories")
async def list_categories():
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
