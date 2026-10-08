"""
api/routers/analyze.py
Endpointهای تحلیل
============================================================
- POST /analyze              → تحلیل یک نماد (کامل)
- POST /analyze/multi        → تحلیل چند TF
- GET  /analyze/deep         → پاراگراف تحلیل عمیق
- GET  /analyze/quote        → قیمت لحظه‌ای
- GET  /analyze/fear-greed   → شاخص ترس و طمع

باگ ۶ (نسخه ۱.۵):
    بدنه‌ی همه‌ی این endpointها sync است (requests + pandas +
    SQLModel) ولی امضای آن‌ها ``async def`` بود. یعنی هر تحلیل،
    **event loop را قفل می‌کرد** و تا تمام شدنش هیچ درخواست
    دیگری — حتی ``GET /health`` — جواب نمی‌گرفت.

    حالا همه‌ی فراخوانی‌های sync با ``run_in_threadpool`` به
    thread جدا می‌روند.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from api.deps import rate_limit_for
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
router = APIRouter(prefix="/analyze", tags=["Analyze"])


# ═══════════════════════════════════════════════════════════
# POST /analyze — تحلیل کامل یک نماد
# ═══════════════════════════════════════════════════════════
@router.post("", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest, request: Request):
    """تحلیل کامل یک نماد (شامل پاراگراف، چک‌لیست، AI export)"""
    rate_limit_for(request, "analyze", limit=60, window_sec=60)

    # ─── sync → threadpool ───
    result = await run_in_threadpool(
        analyze,
        ticker=req.ticker,
        source=req.source,
        tf_name=req.timeframe,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
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
    """
    تحلیل نماد در همه تایم‌فریم‌ها (برای جدول TF).

    ⚠️ این endpoint ۶ تحلیل کامل انجام می‌دهد — سنگین‌ترین
       مسیر پروژه. ``analyze_multi_tf`` خودش هر TF را در
       thread جدا اجرا می‌کند، پس اینجا فقط یک hop لازم است.
    """
    rate_limit_for(request, "analyze_multi", limit=20, window_sec=60)

    tfs = await run_in_threadpool(
        analyze_multi_tf,
        ticker=req.ticker,
        source=req.source,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        ticker_name=req.ticker_name or req.ticker,
    )

    if not tfs:
        raise HTTPException(status_code=404, detail="تحلیل چند TF ناموفق بود")

    # ─── چک‌لیست وزنی (سبک، ولی sync) ───
    cl = await run_in_threadpool(checklist, tfs, req.timeframe)

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

    # ─── امضای deep_analysis: (ticker, name, tfs, gsr, risk_profile, tf_name) ───
    paragraph = await run_in_threadpool(
        deep_analysis,
        ticker,  # ticker
        ticker_name or ticker,  # name
        tfs,  # tfs
        None,  # gsr
        risk_profile,  # risk_profile
        timeframe,  # tf_name
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
    """
    قیمت لحظه‌ای — برای poll هر ۵ ثانیه.

    ⚠️ چون فرانت هر ۵ ثانیه poll می‌کند، این endpoint باید
       سبک بماند؛ ولی حتی همین یک ``requests.get`` هم نباید
       event loop را بگیرد — پس threadpool.
    """
    from services.analyzer_service import quote as get_quote

    # ─── سقف بالاتر چون polling مکرر است ───
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
    """
    سری قیمت برای نمودار SignalCard — سبک و سریع.

    ⚠️ چرا جدا از /analyze:
        /analyze سنگین است (۲۰+ اندیکاتور). این endpoint
        فقط close آخرین ۳۰ کندل را می‌دهد تا نمودار سریع
        بیاید، بعد از ۳۰s سیگنال کامل از WS می‌آید.
    """
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
