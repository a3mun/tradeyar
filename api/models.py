"""
api/models.py
مدل‌های دیتابیس — SQLModel
============================================================
نسخه ۱.۵: اضافه شدن ``is_weak`` برای تفکیک سیگنال ضعیف
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """زمان UTC با timezone — سازگار با SQLModel"""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════
# ۱. لاگ سیگنال‌ها
# ═══════════════════════════════════════════════════════════
class SignalLog(SQLModel, table=True):
    __tablename__ = "signals_log"

    __table_args__ = (UniqueConstraint("dedup_key", name="uq_signals_log_dedup_key"),)

    id: Optional[int] = Field(default=None, primary_key=True)

    timestamp: datetime = Field(default_factory=_utcnow, index=True)
    ticker: str = Field(index=True)
    name: str = ""
    source: str = Field(default="nobitex", index=True)

    signal: str = Field(index=True)
    direction: str = "neutral"
    confidence: int = 0
    consensus: str = "neutral"
    regime: str = "range"

    price: float = 0.0
    sl: Optional[float] = None
    tp: Optional[float] = None
    sl_tp_type: Optional[str] = None
    rr: Optional[float] = None

    tf: str = Field(default="۵ دقیقه", index=True)
    market_type: str = "futures"
    risk_profile: str = "aggressive"

    result: Optional[str] = Field(default=None, index=True)
    result_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    expired: bool = False

    # ═══ traps ═══
    had_trap: bool = False
    trap_type: Optional[str] = None

    # ═══ dedup ═══
    dedup_key: Optional[str] = Field(default=None, index=True)

    # ═══ کارمزد و R:R واقعی (نسخه ۲.۰) ═══
    rr_net: Optional[float] = None
    fee_pct: Optional[float] = None
    fee_ratio: Optional[float] = None
    breakeven_pct: Optional[float] = None
    is_worthwhile: Optional[bool] = None
    timeframe_viable: Optional[bool] = None
    rr_decay_pct: Optional[float] = None
    execution_cost_json: Optional[str] = None
    trade_side_irt: bool = False

    # ═══ عمق بازار ═══
    orderbook_available: bool = False

    # ═══ بسته شدن با مهلت (نسخه ۲.۰) ═══
    expired_at_price: Optional[float] = None
    expired_pnl_pct: Optional[float] = None
    expired_bias: Optional[str] = None

    # ═══ پیش‌بینی روند (نسخه ۳.۰) ═══
    trend_correct: Optional[bool] = None

    # ═══ 🔴 فاز ۸.۲ — تفکیک ضعیف از قطعی ═══
    # True: سیگنال ضعیف (LONG ضعیف / SHORT ضعیف)
    # False: سیگنال قطعی (LONG / SHORT)
    # ⚠️ ضعیف‌ها توی آماری win rate حساب **نمی‌شن**
    #    ولی توی تاریخچه نشون داده می‌شن
    is_weak: bool = Field(default=False, index=True)
