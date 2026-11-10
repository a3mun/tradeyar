"""
api/routers/scan.py
Endpoint اسکنر بازار — نسخه ۵.۰ · فاز ۱۵
============================================================
🔴 تغییرات نسخه ۵.۰:
  • پشتیبانی از ۴ حالت اسکن (همه، آماده پامپ، آماده ریزش، سیگنال فعال)
  • اعمال محدودیت روزانه (۱۰ بار در روز برای هر IP)
  • اضافه شدن تایم‌فریم ۵ دقیقه به لیست مجاز
  • تمرکز روی استراتژی سوئینگ
  • کاهش بار سرور با کش داخلی (سمت فرانت) و اسکن موازی سبک
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
MIN_CONFIDENCE = 50  # 🔴 فقط سیگنال‌های قوی


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


def _compute_quality_score(res: dict) -> float:
    score = 0.0
    conf = res.get("confidence", 0)
    score += min(40, conf * 0.6)

    trend = (res.get("groups") or {}).get("trend", {})
    trend_score = trend.get("score", 0.0)
    direction = res.get("direction", "neutral")

    if direction == "long" and trend_score > 0.3:
        score += min(25, trend_score * 30)
    elif direction == "short" and trend_score < -0.3:
        score += min(25, abs(trend_score) * 30)

    traps = res.get("traps") or {}
    active_traps = [
        k for k, v in traps.items() if isinstance(v, dict) and v.get("active")
    ]
    if not active_traps:
        score += 15

    consensus = res.get("consensus", "neutral")
    if consensus == "strong":
        score += 10
    elif consensus == "normal":
        score += 6
    elif consensus == "weak":
        score += 2

    adx = res.get("adx", 0)
    if adx > 30:
        score += 10
    elif adx > 20:
        score += 5

    return round(score, 1)


def _is_quality_signal(res: dict) -> tuple[bool, float]:
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

    traps = res.get("traps") or {}
    active_traps = [
        k for k, v in traps.items() if isinstance(v, dict) and v.get("active")
    ]
    if active_traps:
        return False, 0.0

    trend = (res.get("groups") or {}).get("trend", {})
    trend_score = trend.get("score", 0.0)

    if direction == "long" and trend_score < -0.5:
        return False, 0.0
    if direction == "short" and trend_score > 0.5:
        return False, 0.0

    score = _compute_quality_score(res)
    if score < 35:
        return False, score

    return True, score


@router.post("", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest, request: Request):
    # 🔴 محدودیت ۱۰ بار در روز (86400 ثانیه) برای هر IP
    rate_limit_for(request, "scan_daily", limit=10, window_sec=86400)

    cat_data = MARKET_CATEGORIES.get(req.category)
    if not cat_data:
        raise HTTPException(status_code=404, detail=f"دسته {req.category} پیدا نشد")

    if req.category == "iran_stocks":
        source = "tsetmc"
    elif req.source:
        source = req.source
    else:
        source = cat_data.get("source", "nobitex")

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
            raise HTTPException(status_code=404, detail=f"دسته {req.category} خالی است")
        parsed = []
        for item in raw_tickers:
            norm = _normalize_ticker(item)
            if norm:
                parsed.append(norm)
            if len(parsed) >= req.limit * 3:
                break

    scan_mode = getattr(req, "scan_mode", "all")

    if not parsed:
        raise HTTPException(
            status_code=404, detail=f"دسته {req.category} نماد معتبری ندارد"
        )

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
                strategy="swing",  # 🔴 اجباری سوئینگ
                ticker_name=name,
                include_extras=False,
                skip_record=True,
            )

    raw_results = await asyncio.gather(
        *(_analyze_one(t, n) for t, n in parsed),
        return_exceptions=True,
    )

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
            continue

        pb = res.get("pre_breakout") or {}
        pb_score = float(pb.get("score", 0))
        pb_bias = str(pb.get("direction_bias", "neutral"))
        is_pb_up = bool(pb.get("is_pre_breakout", False))
        is_pb_down = bool(pb.get("is_pre_breakout_down", False))

        price = res.get("price", 0)
        if not price or price <= 0:
            filtered += 1
            continue

        # ─── فیلتر حالت اسکن ───
        if scan_mode == "pre_breakout":
            if not is_pb_up:
                filtered += 1
                continue
            # در حالت پامپ، فقط سیگنال‌های صعودی/خنثی مهمن، ولی ما همه رو نشون میدیم تا کیفیت دیده بشه
        elif scan_mode == "dump":
            if not is_pb_down:
                filtered += 1
                continue
        elif scan_mode == "active":
            if is_pb_up or is_pb_down:
                filtered += 1
                continue
            passed, _ = _is_quality_signal(res)
            if not passed:
                filtered += 1
                continue
        # "all" → همه چی

        quality_score = _compute_quality_score(res)
        final_score = quality_score
        if is_pb_up or is_pb_down:
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
                    is_pre_breakout=is_pb_up,
                    is_pre_breakout_down=is_pb_down,
                    pre_breakout_score=pb_score,
                    pre_breakout_bias=pb_bias,
                ),
            )
        )

    scored.sort(key=lambda x: -x[0])
    results = [item for _, item in scored[: req.limit]]

    logger.info(
        f"[Scan/{scan_mode}] {req.category}/{source}: {len(results)} نتیجه | "
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
