"""
api/schemas.py
Pydantic Schemas — ورودی/خروجی API
============================================================
"""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# ۱. درخواست تحلیل
# ═══════════════════════════════════════════════════════════
class AnalyzeRequest(BaseModel):
    """بدنه درخواست POST /analyze"""

    ticker: str = Field(..., min_length=1, max_length=50)
    source: Literal["nobitex", "bitpin", "wallex", "abantether", "tsetmc"] = "nobitex"
    timeframe: Literal[
        "۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"
    ] = "۵ دقیقه"
    market_type: Literal["spot", "futures"] = "spot"
    risk_profile: Literal["aggressive", "conservative"] = "aggressive"
    ticker_name: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# ۲. پاسخ تحلیل (کامل — هم‌راستا با Streamlit)
# ═══════════════════════════════════════════════════════════
class AnalyzeResponse(BaseModel):
    ok: bool = True
    ticker: str
    name: str = ""
    source: str
    timeframe: str
    market_type: str = "futures"
    risk_profile: str = "aggressive"

    # ═══ نتیجه تحلیل ═══
    price: float
    signal: str
    direction: str
    confidence: int
    confidence_tier: str
    consensus: str
    regime: str
    action_fa: str = ""
    explanation: str = ""

    # ═══ SL/TP ═══
    sl: Optional[float] = None
    tp: Optional[float] = None
    rr: Optional[float] = None
    atr: float = 0.0
    atr_mult_sl: float = 1.0
    atr_mult_tp: float = 1.5

    # ═══ سطوح ═══
    support: float = 0.0
    resistance: float = 0.0
    pivots: dict = Field(default_factory=dict)
    swings: dict = Field(default_factory=dict)
    fibonacci: dict = Field(default_factory=dict)

    # ═══ گروه‌ها ═══
    groups: dict[str, Any] = Field(default_factory=dict)
    votes_long: int = 0
    votes_short: int = 0
    votes_neutral: int = 0

    # ═══ متادیتا ═══
    reasons: list[str] = Field(default_factory=list)
    scenarios: list[dict] = Field(default_factory=list)
    traps: dict = Field(default_factory=dict)
    traps_summary: dict = Field(default_factory=dict)
    divergence: dict = Field(default_factory=dict)
    multi_tf_info: str = ""
    multi_tf_ok: bool = True
    neutral_explain: dict = Field(default_factory=dict)

    # ═══ جدید: پاراگراف تحلیل عمیق (متن آماده) ═══
    deep_analysis: str = ""

    # ═══ جدید: چک‌لیست وزنی ═══
    checklist: dict = Field(default_factory=dict)

    # ═══ جدید: خروجی AI (متن آماده) ═══
    ai_export: str = ""

    fingerprint: str = ""

    # ═══ زمان ═══
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════
# ۳.۵. قیمت لحظه‌ای (Quote)
# ═══════════════════════════════════════════════════════════
class QuoteResponse(BaseModel):
    """قیمت لحظه‌ای — سبک و سریع"""

    ok: bool = True
    ticker: str
    price: float
    change_pct: float = 0.0
    source: str


# ═══════════════════════════════════════════════════════════
# ۳. Fear & Greed
# ═══════════════════════════════════════════════════════════
class FearGreedResponse(BaseModel):
    """شاخص ترس و طمع"""

    ok: bool = True
    ticker: str
    value: float  # 0-100
    label: str  # «ترس شدید», «خنثی», «طمع شدید» و...
    color: str  # green/yellow/red
    icon: str


# ═══════════════════════════════════════════════════════════
# ۴. نمادها
# ═══════════════════════════════════════════════════════════
class SymbolItem(BaseModel):
    """یک نماد در لیست"""

    ticker: str
    name: str
    source: str
    emoji: str = ""


class SymbolsResponse(BaseModel):
    ok: bool = True
    total: int
    items: list[SymbolItem]


# ═══════════════════════════════════════════════════════════
# ۵. اسکنر
# ═══════════════════════════════════════════════════════════
class ScanRequest(BaseModel):
    """بدنه درخواست POST /scan"""

    category: Literal[
        "crypto", "forex", "us_stocks", "commodities", "indices", "iran_stocks"
    ] = "crypto"
    timeframe: str = "۵ دقیقه"
    market_type: Literal["spot", "futures"] = "spot"
    risk_profile: Literal["aggressive", "conservative"] = "aggressive"
    limit: int = Field(default=20, ge=1, le=100)


class ScanItem(BaseModel):
    """یک آیتم در نتایج اسکن"""

    ticker: str
    name: str
    price: float
    signal: str
    confidence: int
    direction: str


class ScanResponse(BaseModel):
    ok: bool = True
    category: str
    timeframe: str
    total: int
    items: list[ScanItem]


# ═══════════════════════════════════════════════════════════
# ۶. Backtest
# ═══════════════════════════════════════════════════════════
class BacktestStats(BaseModel):
    total: int = 0
    wins: int = 0
    losses: int = 0
    pending: int = 0
    expired: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_rr: float = 0.0


class BacktestResponse(BaseModel):
    ok: bool = True
    stats: BacktestStats
    items: list[dict] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# ۷. خطا
# ═══════════════════════════════════════════════════════════
class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
    detail: Optional[str] = None
