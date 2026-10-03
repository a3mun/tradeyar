"""
api/routers/analyze.py
Endpointهای تحلیل
============================================================
- POST /analyze              → تحلیل یک نماد (کامل)
- POST /analyze/multi        → تحلیل چند TF
- GET  /analyze/deep         → پاراگراف تحلیل عمیق
- GET  /analyze/fear-greed   → شاخص ترس و طمع
"""

import logging
from fastapi import APIRouter, HTTPException

from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FearGreedResponse,
    QuoteResponse,
)

from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FearGreedResponse,
)
from services.analyzer_service import (
    analyze,
    analyze_multi_tf,
    deep_analysis,
    checklist,
    fear_greed,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analyze"])


# ═══════════════════════════════════════════════════════════
# POST /analyze — تحلیل کامل یک نماد
# ═══════════════════════════════════════════════════════════
@router.post("", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest):
    """تحلیل کامل یک نماد (شامل پاراگراف، چک‌لیست، AI export)"""
    result = analyze(
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
async def analyze_multi_endpoint(req: AnalyzeRequest):
    """تحلیل نماد در همه تایم‌فریم‌ها (برای جدول TF)"""
    tfs = analyze_multi_tf(
        ticker=req.ticker,
        source=req.source,
        market_type=req.market_type,
        risk_profile=req.risk_profile,
        ticker_name=req.ticker_name or req.ticker,
    )

    if not tfs:
        raise HTTPException(status_code=404, detail="تحلیل چند TF ناموفق بود")

    # ─── چک‌لیست وزنی ───
    cl = checklist(tfs, main_tf=req.timeframe)

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
    ticker: str,
    source: str = "global",
    timeframe: str = "۵ دقیقه",
    market_type: str = "spot",
    risk_profile: str = "aggressive",
    ticker_name: str = "",
):
    """تحلیل عمیق به صورت پاراگراف (تکنیکال + روانشناسی)"""
    tfs = analyze_multi_tf(
        ticker=ticker,
        source=source,
        market_type=market_type,
        risk_profile=risk_profile,
        ticker_name=ticker_name or ticker,
    )

    if not tfs:
        raise HTTPException(status_code=404, detail="تحلیل ناموفق بود")

    paragraph = deep_analysis(
        ticker=ticker,
        name=ticker_name or ticker,
        tfs=tfs,
        risk_profile=risk_profile,
        tf_name=timeframe,
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
    ticker: str,
    source: str = "global",
):
    """قیمت لحظه‌ای — برای poll هر ۵ ثانیه"""
    from services.analyzer_service import quote as get_quote

    result = get_quote(ticker=ticker, source=source)
    if result is None:
        raise HTTPException(status_code=404, detail=f"قیمت {ticker} در دسترس نیست")

    return QuoteResponse(**result)


# ═══════════════════════════════════════════════════════════
# GET /analyze/fear-greed — شاخص ترس و طمع
# ═══════════════════════════════════════════════════════════
@router.get("/fear-greed", response_model=FearGreedResponse)
async def fear_greed_endpoint(
    ticker: str,
    source: str = "global",
):
    """شاخص ترس و طمع برای یه نماد (0-100)"""
    result = fear_greed(ticker=ticker, source=source)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"محاسبه Fear & Greed برای {ticker} ناموفق بود",
        )

    return FearGreedResponse(**result)
