"""
api/routers/analyze.py
Endpointهای تحلیل
============================================================
- POST /analyze              → تحلیل یک نماد (کامل)
- POST /analyze/multi        → تحلیل چند TF
- GET  /analyze/deep         → پاراگراف تحلیل عمیق
- GET  /analyze/quote        → قیمت لحظه‌ای
- GET  /analyze/fear-greed   → شاخص ترس و طمع
- GET  /analyze/sparkline    → نمودار سبک
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.concurrency import run_in_threadpool

from api.deps import rate_limit_for, require_access
from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FearGreedResponse,
    QuoteResponse,
    SparklineResponse,
)
from services.analyzer_service import (
    analyze,
    analyze_multi_tf,
    checklist,
    deep_analysis,
    fear_greed,
    sparkline,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analyze"], dependencies=[Depends(require_access)])


# ═══════════════════════════════════════════════════════════
# POST /analyze — تحلیل کامل یک نماد
# ═══════════════════════════════════════════════════════════
@router.post("", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest, request: Request):
    """تحلیل کامل یک نماد (شامل پاراگراف، چک‌لیست، AI export)"""
    rate_limit_for(request, "analyze", limit=60, window_sec=60)

    result = await run_in_threadpool(
        analyze,
        ticker=req.ticker,
        source=req.source,
        tf_name=req.timeframe,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        strategy=req.strategy,  # 🔴 فاز C
        ticker_name=req.ticker_name or req.ticker,
        include_extras=True,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"تحلیل برای {req.ticker} امکان‌پذیر نبود — دیتا کافی نیست",
        )

    return AnalyzeResponse(**result)


# ═══════════════════════════════════════════════════════════
# POST /analyze/multi — تحلیل چند TF
# ═══════════════════════════════════════════════════════════
@router.post("/multi")
async def analyze_multi_endpoint(req: AnalyzeRequest, request: Request):
    """تحلیل نماد در همه تایم‌فریم‌ها (برای جدول TF)."""
    rate_limit_for(request, "analyze_multi", limit=500, window_sec=60)

    tfs = await run_in_threadpool(
        analyze_multi_tf,
        ticker=req.ticker,
        source=req.source,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        strategy=req.strategy,  # 🔴 فاز C
        ticker_name=req.ticker_name or req.ticker,
        main_tf=req.timeframe,  # 🔴 جدید
    )

    if not tfs:
        raise HTTPException(status_code=404, detail="تحلیل چند TF ناموفق بود")

    cl = await run_in_threadpool(
        checklist,
        tfs,
        req.timeframe,
        req.strategy,
    )

    return {
        "ok": True,
        "ticker": req.ticker,
        "name": req.ticker_name or req.ticker,
        "timeframes": tfs,
        "checklist": cl,
    }


# ═══════════════════════════════════════════════════════════
# GET /analyze/deep — پاراگراف تحلیل عمیق
# ═══════════════════════════════════════════════════════════
@router.get("/deep")
async def deep_analyze_endpoint(
    request: Request,
    ticker: str,
    source: str = "nobitex",
    timeframe: str = "۵ دقیقه",
    market_type: str = "spot",
    risk_profile: str = "aggressive",
    ticker_name: str = "",
):
    """تحلیل عمیق به صورت پاراگراف (تکنیکال + روانشناسی)"""
    rate_limit_for(request, "analyze_deep", limit=20, window_sec=60)

    tfs = await run_in_threadpool(
        analyze_multi_tf,
        ticker=ticker,
        source=source,
        market_type=market_type,
        risk_profile=risk_profile,
        ticker_name=ticker_name or ticker,
    )

    if not tfs:
        raise HTTPException(status_code=404, detail="تحلیل ناموفق بود")

    paragraph = await run_in_threadpool(
        deep_analysis,
        ticker,
        ticker_name or ticker,
        tfs,
        None,
        risk_profile,
        timeframe,
    )

    return {
        "ok": True,
        "ticker": ticker,
        "name": ticker_name or ticker,
        "paragraph": paragraph,
    }


# ═══════════════════════════════════════════════════════════
# GET /analyze/quote — قیمت لحظه‌ای (سبک)
# ═══════════════════════════════════════════════════════════
@router.get("/quote", response_model=QuoteResponse)
async def quote_endpoint(
    request: Request,
    ticker: str,
    source: str = "nobitex",
):
    """قیمت لحظه‌ای — برای poll هر ۵ ثانیه."""
    from services.analyzer_service import quote as get_quote

    rate_limit_for(request, "quote", limit=180, window_sec=60)

    result = await run_in_threadpool(get_quote, ticker=ticker, source=source)
    if result is None:
        raise HTTPException(status_code=404, detail=f"قیمت {ticker} در دسترس نیست")

    return QuoteResponse(**result)


# ═══════════════════════════════════════════════════════════
# GET /analyze/fear-greed — شاخص ترس و طمع
# ═══════════════════════════════════════════════════════════
@router.get("/fear-greed", response_model=FearGreedResponse)
async def fear_greed_endpoint(
    request: Request,
    ticker: str,
    source: str = "nobitex",
):
    """شاخص ترس و طمع برای یه نماد (0-100)"""
    rate_limit_for(request, "fear_greed", limit=60, window_sec=60)

    result = await run_in_threadpool(fear_greed, ticker, source)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"محاسبه Fear & Greed برای {ticker} ناموفق بود",
        )

    return FearGreedResponse(**result)


# ═══════════════════════════════════════════════════════════
# GET /analyze/sparkline — نمودار سبک (فاز ۸)
# ═══════════════════════════════════════════════════════════
@router.get("/sparkline", response_model=SparklineResponse)
async def sparkline_endpoint(
    request: Request,
    ticker: str,
    source: str = "nobitex",
    timeframe: str = "۵ دقیقه",
):
    """سری قیمت برای نمودار SignalCard — سبک و سریع."""
    rate_limit_for(request, "sparkline", limit=120, window_sec=60)

    result = await run_in_threadpool(
        sparkline, ticker=ticker, source=source, tf_name=timeframe
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"سری قیمت برای {ticker} در دسترس نیست",
        )

    return SparklineResponse(**result)


from fastapi.responses import StreamingResponse
import json


@router.post("/multi-stream")
async def analyze_multi_stream_endpoint(req: AnalyzeRequest, request: Request):
    """
    🔴 فاز ۱۶.۹ — استریم موازی و بهینه
    """
    from services.analyzer_service import analyze
    from core.contracts import TF_NAMES
    from core.strategies import get_strategy

    # فیلتر TFهای مجاز
    strategy_cfg = get_strategy(req.strategy)
    allowed_tfs = strategy_cfg.get("recommended_tfs", list(TF_NAMES))

    # اولویت‌بندی: تایم‌فریم انتخابی کاربر اول باشه
    if req.timeframe in allowed_tfs:
        allowed_tfs.remove(req.timeframe)
        allowed_tfs.insert(0, req.timeframe)

    async def event_generator():
        import asyncio
        from fastapi.concurrency import run_in_threadpool

        # 🔴 محدودیت ۳ پردازش همزمان (برای جلوگیری از فشار به صرافی)
        semaphore = asyncio.Semaphore(3)

        async def process_tf(tf: str, is_priority: bool = False):
            async with semaphore:
                try:
                    # 🔴 فاز ۱۶.۹ — بهینه‌سازی سرعت multi-stream
                    # فقط برای تایم‌فریم اصلی (main_tf) دیتای سنگین (extras) محاسبه شود
                    # تایم‌فریم‌های فرعی فقط دیتای پایه لازم دارند
                    needs_extras = tf == req.timeframe

                    res = await run_in_threadpool(
                        analyze,
                        ticker=req.ticker,
                        source=req.source,
                        tf_name=tf,
                        market_type=req.market_type,
                        risk_profile=req.risk_profile,
                        strategy=req.strategy,
                        ticker_name=req.ticker_name,
                        include_extras=needs_extras,
                    )
                    if res:
                        return (
                            tf,
                            f"data: {json.dumps({tf: res}, ensure_ascii=False)}\n\n",
                        )
                except Exception as e:
                    logger.error(f"[Stream] {tf} failed: {e}")
                return (tf, None)

        # 🔴 مرحله ۱: تایم‌فریم اصلی رو فوراً بفرست (بدون معطلی)
        main_tf = allowed_tfs[0]
        rest_tfs = allowed_tfs[1:]

        main_result = await process_tf(main_tf, is_priority=True)
        if main_result[1]:
            yield main_result[1]

        # 🔴 مرحله ۲: بقیه رو موازی بفرست (هر کدوم زودتر آماده شد، زودتر بره)
        tasks = [asyncio.create_task(process_tf(tf)) for tf in rest_tfs]

        for future in asyncio.as_completed(tasks):
            tf, result = await future
            if result:
                yield result

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
