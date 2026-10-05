"""
api/schemas.py
Pydantic Schemas — ورودی/خروجی API
============================================================
نسخه ۱.۵: ``timestamp`` با timezone-aware UTC (جانشین ``utcnow()``
که در Python 3.12+ منسوخ شده و مقدار naive می‌داد).
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def _utcnow_aware() -> datetime:
    """
    UTC با timezone.

    ⚠️ پیش از این ``datetime.utcnow`` بود که (۱) منسوخ است و
       (۲) naive برمی‌گرداند. نتیجه: ``isoformat()`` بدون offset
       تولید می‌شد و ``new Date(iso)`` در مرورگر آن را به **وقت
       محلی کاربر** تفسیر می‌کرد — ۳:۳۰ ساعت خطا.
    """
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════
# ۱. درخواست تحلیل
# ═══════════════════════════════════════════════════════════
class AnalyzeRequest(BaseModel):
    """بدنه درخواست POST /analyze"""

    ticker: str = Field(..., min_length=1, max_length=50)
    source: Literal["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"] = "nobitex"
    timeframe: Literal[
        "۱ دقیقه", "۵ دقیقه", "۱۵ دقیقه", "۳۰ دقیقه", "۱ ساعت", "روزانه"
    ] = "۵ دقیقه"
    market_type: Literal["spot", "futures"] = "spot"
    risk_profile: Literal["aggressive", "conservative"] = "aggressive"
    ticker_name: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# ۲. پاسخ تحلیل (کامل — تمام فیلدهای لایه‌ی تحلیل)
# ═══════════════════════════════════════════════════════════
class AnalyzeResponse(BaseModel):
    ok: bool = True
    ticker: str
    name: str = ""
    source: str
    # ─── شفافیت fallback (نسخه ۱.۷) ───
    # source_requested: صرافی‌ای که کاربر انتخاب کرده
    # source_used:      صرافی‌ای که دیتا **واقعاً** از آن آمده
    # is_fallback:      آیا این دو متفاوتند؟
    source_requested: str = ""
    source_used: str = ""
    is_fallback: bool = False
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
    # ⚠️ `rr` برای سازگاری عقب‌رو = R:R **خام** می‌ماند.
    #    فرانت باید `rr_net` را نمایش دهد (نسخه ۱.۹).
    rr: Optional[float] = None
    atr: float = 0.0
    atr_mult_sl: float = 1.0
    atr_mult_tp: float = 1.5

    # ═══ کارمزد و R:R واقعی (نسخه ۱.۹) ═══
    # 🔴 R:R خام فریبنده است — کارمزد رفت‌وبرگشتی (۰.۴-۰.۶٪)
    #    در TF کوتاه می‌تواند کل سود را بخورد.
    rr_gross: Optional[float] = None
    rr_net: Optional[float] = None
    fee_pct: Optional[float] = None
    fee_ratio: Optional[float] = None
    breakeven_pct: Optional[float] = None
    is_worthwhile: Optional[bool] = None
    # ─── آیا این TF از نظر اقتصادی معامله‌پذیر است؟ (rr_net ≥ ۱.۳) ───
    timeframe_viable: Optional[bool] = None
    # ─── SL/TP مقیاس‌دهی‌شده برای پوشش هزینه ───
    sl_tp_scaled: bool = False
    scale_factor: Optional[float] = None
    scale_reason: Optional[str] = None
    original_sl: Optional[float] = None
    original_tp: Optional[float] = None
    rr_decay_pct: Optional[float] = None
    execution_cost: Optional[dict] = None
    # ═══ کارمزد — نسخه ۳.۰ ═══
    # ─── کارمزد از روی ticker و market_type ───
    trade_side_irt: bool = False
    sl_tp_type: Optional[str] = None

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
    # ─── عمق بازار (نسخه ۱.۹) ───
    # imbalance، spread، دیوار سفارش — برای گروه «حجم»
    orderbook: Optional[dict] = None
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
    timestamp: datetime = Field(default_factory=_utcnow_aware)


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
    # ─── آیا این صرافی واقعاً این بازار را دارد؟ ───
    # False یعنی «این صرافی این جفت‌ارز را ندارد» (نه خطای شبکه)
    available: bool = True


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

    # ─── صرافی (نسخه ۲.۰) ───
    # اگر نیاد، از پیش‌فرض category استفاده می‌شود
    source: Optional[Literal["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"]] = None
    category: Literal[
        "crypto", "forex", "us_stocks", "commodities", "indices", "iran_stocks"
    ] = "crypto"
    timeframe: str = "۵ دقیقه"
    market_type: Literal["spot", "futures"] = "spot"
    risk_profile: Literal["aggressive", "conservative"] = "aggressive"
    limit: int = Field(default=20, ge=1, le=100)


# ═══════════════════════════════════════════════════════════
# ۵.۵ عمق بازار — فاز ۶.۵ (placeholder)
# ═══════════════════════════════════════════════════════════
# ⚠️ این schema فقط قرارداد است. پیاده‌سازی در فاز ۶.۵.
class OrderBookLevel(BaseModel):
    """یک سطح قیمت در عمق بازار"""

    price: float
    quantity: float
    # ─── اختیاری: تعداد سفارش در این سطح ───
    orders: int | None = None


class OrderBook(BaseModel):
    """
    عمق بازار (Order Book).

    ═══ کاربرد در فاز ۶.۵ ═══
      • Imbalance خرید/فروش: نسبت حجم bids به asks
      • اسپرد واقعی: best_ask - best_bid
      • دیوار سفارش: سطحی با حجم غیرعادی
      • جذب/توزیع دقیق‌تر در گروه «حجم»
    """

    ok: bool = True
    ticker: str
    source: str
    timestamp: datetime = Field(default_factory=_utcnow_aware)

    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)

    # ─── محاسبات مشتق (فاز ۶.۵) ───
    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    spread_pct: float | None = None
    imbalance: float | None = None  # 0..1 — بالای ۰.۵ فشار خرید


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
    avg_rr_net: float = 0.0
    expectancy: float = 0.0
    # ═══ پیش‌بینی روند (نسخه ۳.۰) ═══
    trend_correct: int = 0
    trend_wrong: int = 0
    trend_accuracy: float = 0.0
    expired_win: int = 0
    expired_loss: int = 0
    expired_flat: int = 0


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
