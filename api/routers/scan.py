"""
api/routers/scan.py
Endpoint اسکنر بازار — نسخه ۴.۰ · فاز ۱۰.۳
============================================================
🔴 تغییرات نسخه ۴.۰:
  • فیلتر کیفیت پیشرفته (trend + trap + confidence)
  • امتیاز کیفیت (quality_score) برای هر سیگنال
  • مرتب‌سازی بر اساس احتمال موفقیت
  • حذف سیگنال‌های پرخطر
"""

import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from api.deps import rate_limit_for
from api.schemas import ScanItem, ScanRequest, ScanResponse
from core.market_lists import MARKET_CATEGORIES
from services.analyzer_service import analyze

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["Scan"])

MAX_CONCURRENT = 6
SCAN_BUDGET_SEC = 45.0
MIN_CONFIDENCE = 50


def _normalize_ticker(item) -> tuple[str, str] | None:
    """نرمال‌سازی ticker از فرمت‌های مختلف."""
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


def _compute_quality_score(res: dict) -> float:
    """
    امتیاز کیفیت سیگنال (۰-۱۰۰).

    ═══ معیارها ═══
      ۱. Confidence پایه (۰-۴۰)
      ۲. Trend تأییدکننده (۰-۲۵)
      ۳. Trap نبودن (۰-۱۵)
      ۴. Consensus (۰-۱۰)
      ۵. ADX رژیم (۰-۱۰)
    """
    score = 0.0

    # ─── ۱. Confidence (0-40) ───
    conf = res.get("confidence", 0)
    score += min(40, conf * 0.6)

    # ─── ۲. Trend تأیید (0-25) ───
    trend = (res.get("groups") or {}).get("trend", {})
    trend_score = trend.get("score", 0.0)
    direction = res.get("direction", "neutral")

    if direction == "long" and trend_score > 0.3:
        score += min(25, trend_score * 30)
    elif direction == "short" and trend_score < -0.3:
        score += min(25, abs(trend_score) * 30)

    # ─── ۳. Trap نبودن (0-15) ───
    traps = res.get("traps") or {}
    active_traps = [
        k for k, v in traps.items() if isinstance(v, dict) and v.get("active")
    ]
    if not active_traps:
        score += 15

    # ─── ۴. Consensus (0-10) ───
    consensus = res.get("consensus", "neutral")
    if consensus == "strong":
        score += 10
    elif consensus == "normal":
        score += 6
    elif consensus == "weak":
        score += 2

    # ─── ۵. ADX (0-10) ───
    adx = res.get("adx", 0)
    if adx > 30:
        score += 10
    elif adx > 20:
        score += 5

    return round(score, 1)


def _is_quality_signal(res: dict) -> tuple[bool, float]:
    """
    آیا این سیگنال «قابل نمایش» است؟

    Returns:
        (پاس می‌شه؟, امتیاز کیفیت)
    """
    if not res:
        return False, 0.0

    direction = res.get("direction")
    if direction == "neutral":
        return False, 0.0

    confidence = res.get("confidence", 0)
    if confidence < MIN_CONFIDENCE:
        return False, 0.0

    signal = res.get("signal", "")
    if "ضعیف" in signal:
        return False, 0.0

    # ─── trap فعال → رد کن ───
    traps = res.get("traps") or {}
    active_traps = [
        k for k, v in traps.items() if isinstance(v, dict) and v.get("active")
    ]
    if active_traps:
        return False, 0.0

    # ─── trend معکوس → رد کن ───
    trend = (res.get("groups") or {}).get("trend", {})
    trend_score = trend.get("score", 0.0)

    if direction == "long" and trend_score < -0.5:
        return False, 0.0
    if direction == "short" and trend_score > 0.5:
        return False, 0.0

    # ─── امتیاز ───
    score = _compute_quality_score(res)

    # ─── امتیاز کمتر از ۳۵ → رد ───
    if score < 35:
        return False, score

    return True, score


@router.post("", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest, request: Request):
    """
    اسکن نمادها — نسخه ۴.۰.

    ═══ تغییرات نسخه ۴.۰ ═══
    • فیلتر چندگانه (trend + trap + confidence + quality score)
    • مرتب‌سازی بر اساس امتیاز کیفیت (نه فقط confidence)
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

    # 🔴 فاز ۱۰.۳ — فیلتر بر اساس scan_mode
    scan_mode = getattr(req, "scan_mode", "all")

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
                skip_record=True,
            )

    raw_results = await asyncio.gather(
        *(_analyze_one(t, n) for t, n in parsed),
        return_exceptions=True,
    )

    # ═══ جمع‌آوری با امتیاز کیفیت ═══
    scored: list[tuple[float, ScanItem]] = []
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

        # ─── فیلتر کیفیت ───
        passed, quality_score = _is_quality_signal(res)
        if not passed:
            filtered += 1
            continue

        price = res.get("price", 0)
        if not price or price <= 0:
            filtered += 1
            continue

        # 🔴 فاز ۱۰.۳ — Pre-breakout data
        pb = res.get("pre_breakout") or {}
        pb_score = float(pb.get("score", 0))
        pb_bias = str(pb.get("direction_bias", "neutral"))
        is_pb = bool(pb.get("is_pre_breakout", False))

        # ─── Pre-breakout bonus به امتیاز ───
        final_score = quality_score
        if is_pb:
            final_score += min(20, pb_score * 0.2)

        scored.append(
            (
                final_score,
                ScanItem(
                    ticker=ticker,
                    name=name,
                    price=price,
                    signal=res["signal"],
                    confidence=res["confidence"],
                    direction=res["direction"],
                    is_pre_breakout=is_pb,
                    pre_breakout_score=pb_score,
                    pre_breakout_bias=pb_bias,
                ),
            )
        )

        # ─── pre-breakout flag ───
        pb = res.get("pre_breakout") or {}
        is_pre = pb.get("is_pre_breakout", False)

        # ─── اضافه به ScanItem ───
        item = ScanItem(
            ticker=ticker,
            name=name,
            price=price,
            signal=res["signal"],
            confidence=res["confidence"],
            direction=res["direction"],
            is_pre_breakout=is_pre,  # ← جدید
            pre_breakout_score=pb.get("score", 0),  # ← جدید
        )

        # ─── فیلتر بر اساس scan_mode ───
        is_pb = bool(pb.get("is_pre_breakout", False))

        if scan_mode == "pre_breakout" and not is_pb:
            filtered += 1
            continue
        if scan_mode == "active" and is_pb:
            filtered += 1
            continue
        # "all" → هر دو

    # ═══ مرتب‌سازی بر اساس امتیاز کیفیت (نزولی) ═══
    scored.sort(key=lambda x: -x[0])
    results = [item for _, item in scored[: req.limit]]

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
