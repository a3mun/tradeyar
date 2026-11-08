"""
api/schemas.py
Pydantic Schemas — ورودی/خروجی API
============================================================
نسخه ۱.۶ · فاز ۱۰.۱۰
🔴 تغییرات:
  • BacktestStats بازنویسی شد (تفکیک TP/SL/Timeout و دقت جهت)
  • بقیه کلاس‌ها بدون تغییر (سازگاری کامل عقب‌رو)
"""

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def _utcnow_aware() -> datetime:
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
    strategy: Literal["scalp", "swing", "position"] = "swing"
    ticker_name: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# ۲. پاسخ تحلیل (کامل — تمام فیلدهای لایه‌ی تحلیل)
# ═══════════════════════════════════════════════════════════
class AnalyzeResponse(BaseModel):
    ok: bool = True
    ticker: str
    name: str = ""
    source: str
    source_requested: str = ""
    source_used: str = ""
    is_fallback: bool = False
    timeframe: str
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    strategy: str = "swing"
    strategy_name: str = ""

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

    # ═══ TP Ladder + timeout ═══
    tp_levels: Optional[dict] = None
    timeout_planned_min: Optional[int] = None  # 🆕

    # ═══ کارمزد و R:R واقعی ═══
    rr_gross: Optional[float] = None
    rr_net: Optional[float] = None
    fee_pct: Optional[float] = None
    fee_ratio: Optional[float] = None
    breakeven_pct: Optional[float] = None
    is_worthwhile: Optional[bool] = None
    timeframe_viable: Optional[bool] = None
    sl_tp_scaled: bool = False
    scale_factor: Optional[float] = None
    scale_reason: Optional[str] = None
    original_sl: Optional[float] = None
    original_tp: Optional[float] = None
    rr_decay_pct: Optional[float] = None
    execution_cost: Optional[dict] = None
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
    orderbook: Optional[dict] = None
    multi_tf_info: str = ""
    multi_tf_ok: bool = True
    neutral_explain: dict = Field(default_factory=dict)

    # ═══ متون آماده ═══
    deep_analysis: str = ""
    checklist: dict = Field(default_factory=dict)
    ai_export: str = ""
    fingerprint: str = ""

    # ═══ زمان ═══
    timestamp: datetime = Field(default_factory=_utcnow_aware)

    # ═══ Pump/Dump ═══
    pump_score: float = 0.0
    dump_score: float = 0.0
    pump_warning: str = "none"
    pump_type: str = "none"

    # ═══ Suggested Entry ═══
    suggested_entry: Optional[float] = None
    suggested_entry_method: Optional[str] = None
    suggested_entry_distance_pct: Optional[float] = None


# ═══════════════════════════════════════════════════════════
# ۳.۵. قیمت لحظه‌ای (Quote)
# ═══════════════════════════════════════════════════════════
class QuoteResponse(BaseModel):
    ok: bool = True
    ticker: str
    price: float
    change_pct: float = 0.0
    source: str
    available: bool = True


# ═══════════════════════════════════════════════════════════
# ۳. Fear & Greed
# ═══════════════════════════════════════════════════════════
class FearGreedResponse(BaseModel):
    ok: bool = True
    ticker: str
    value: float
    label: str
    color: str
    icon: str


# ═══════════════════════════════════════════════════════════
# ۴. نمادها
# ═══════════════════════════════════════════════════════════
class SymbolItem(BaseModel):
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
    source: Optional[Literal["nobitex", "bitpin", "wallex", "tabdeal", "tsetmc"]] = None
    category: Literal[
        "crypto", "forex", "us_stocks", "commodities", "indices", "iran_stocks"
    ] = "crypto"
    timeframe: str = "۵ دقیقه"
    market_type: Literal["spot", "futures"] = "spot"
    risk_profile: Literal["aggressive", "conservative"] = "aggressive"
    limit: int = Field(default=20, ge=1, le=100)
    scan_mode: Literal["pre_breakout", "active", "all"] = "all"


class OrderBookLevel(BaseModel):
    price: float
    quantity: float
    orders: int | None = None


class OrderBook(BaseModel):
    ok: bool = True
    ticker: str
    source: str
    timestamp: datetime = Field(default_factory=_utcnow_aware)
    bids: list[OrderBookLevel] = Field(default_factory=list)
    asks: list[OrderBookLevel] = Field(default_factory=list)
    best_bid: float | None = None
    best_ask: float | None = None
    spread: float | None = None
    spread_pct: float | None = None
    imbalance: float | None = None


class ScanItem(BaseModel):
    ticker: str
    name: str
    price: float
    signal: str
    confidence: int
    direction: str
    is_pre_breakout: bool = False
    pre_breakout_score: float = 0.0
    pre_breakout_bias: str = "neutral"
    pump_score: float = 0.0
    dump_score: float = 0.0
    pump_warning: str = "none"
    pump_type: str = "none"


class ScanResponse(BaseModel):
    ok: bool = True
    category: str
    timeframe: str
    total: int
    items: list[ScanItem]


# ═══════════════════════════════════════════════════════════
# ۶. Backtest (🔴 نسخه ۲.۰ — فاز ۱۴.۷.۱)
# ═══════════════════════════════════════════════════════════
class BacktestStats(BaseModel):
    # ─── کلی ───
    total: int = 0
    pending: int = 0
    expired: int = 0

    # ─── تفکیک دقیق ───
    tp_hits: int = 0
    sl_hits: int = 0
    timeout_wins: int = 0
    timeout_losses: int = 0
    timeout_flats: int = 0

    # ─── معیارهای اصلی ───
    win_rate: float = 0.0  # (TP + Timeout Win) / closed
    tp_hit_rate: float = 0.0  # 🆕 فقط TP / closed
    direction_accuracy: float = 0.0  # (TP + Timeout Win) / closed

    # ─── 🆕 فاز ۱۴.۷.۱ ───
    avg_tp_level: float = 0.0  # میانگین TP لمس‌شده (1-3)

    # ─── روند ───
    trend_correct: int = 0
    trend_wrong: int = 0
    trend_accuracy: float = 0.0

    # ─── بقیه ───
    profit_factor: float = 0.0
    avg_rr: float = 0.0
    avg_rr_net: float = 0.0
    expectancy: float = 0.0


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


# ═══════════════════════════════════════════════════════════
# ۸. Sparkline
# ═══════════════════════════════════════════════════════════
class SparklineResponse(BaseModel):
    ok: bool = True
    ticker: str
    source: str
    timeframe: str
    close_series: list[float] = Field(default_factory=list)
    price: float = 0.0
    timestamp: datetime = Field(default_factory=_utcnow_aware)


# ═══════════════════════════════════════════════════════════
# ۹. احراز هویت (فاز ۱۱)
# ═══════════════════════════════════════════════════════════
class SendOTPRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=13)


class SendOTPResponse(BaseModel):
    ok: bool = True
    message: str = "کد ورود ارسال شد"
    retry_after: int = 60


class VerifyOTPRequest(BaseModel):
    phone: str
    code: str = Field(..., min_length=4, max_length=6)


class UserRead(BaseModel):
    id: int
    phone: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    has_password: bool = False


class TokenResponse(BaseModel):
    ok: bool = True
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    is_new_user: bool = False


# ═══════════════════════════════════════════════════════════
# ۱۰. اشتراک (فاز ۱۱)
# ═══════════════════════════════════════════════════════════
class SubscriptionRead(BaseModel):
    id: int
    plan: str
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str
    days_left: Optional[int] = None


class PaymentRequestCreate(BaseModel):
    plan: str
    receipt_note: Optional[str] = None
    full_name: Optional[str] = None
    payment_time: Optional[str] = None
    amount: Optional[int] = 0  # 🔴 جدید: مبلغ انتخابی کاربر
    payment_method: Optional[str] = "card"  # 🔴 جدید: "zibal" یا "card"


class PaymentRequestRead(BaseModel):
    id: int
    user_id: int
    amount: int
    plan: str
    status: str
    receipt_note: Optional[str] = None
    admin_note: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    user_phone: Optional[str] = None


class AdminUserRead(BaseModel):
    id: int
    phone: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    subscription: Optional[SubscriptionRead] = None


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None


class AdminUpdateSubscription(BaseModel):
    plan: str
    days: Optional[int] = None


class AdminReviewPayment(BaseModel):
    action: str
    admin_note: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# 🎫 فاز ۱۳ — سیستم تیکتینگ
# ═══════════════════════════════════════════════════════════
class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=5, max_length=2000)


class TicketMessageCreate(BaseModel):
    message: str = Field(default="", max_length=2000)
    attachment_path: Optional[str] = None
    attachment_name: Optional[str] = None


class TicketMessageRead(BaseModel):
    id: int
    sender_id: int
    is_admin: bool
    message: str
    attachment_path: Optional[str] = None
    attachment_name: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    sender_name: Optional[str] = None


class TicketRead(BaseModel):
    id: int
    user_id: int
    subject: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages_count: int = 0
    unread_count: int = 0  # ⬅️ جدید
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None  # ⬅️ جدید


class TicketDetail(TicketRead):
    messages: list[TicketMessageRead] = Field(default_factory=list)


class TicketStats(BaseModel):
    open_count: int = 0
    closed_count: int = 0
    unread_count: int = 0
    total_count: int = 0


# ═══════════════════════════════════════════════════════════
# 🔌 فاز ۱۴ — اسکیمای اکستنشن
# ═══════════════════════════════════════════════════════════
class ExtensionTokenResponse(BaseModel):
    token: str
    expires_in_hours: int = 24


class ExtensionVerifyResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    user_name: Optional[str] = None
    plan: Optional[str] = None
    expires_at: Optional[str] = None


TokenResponse.model_rebuild()
