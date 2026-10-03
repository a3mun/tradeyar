"""
api/models.py
مدل‌های دیتابیس — SQLModel
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """زمان UTC با timezone — سازگار با SQLModel"""
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════
# ۱. لاگ سیگنال‌ها
# ═══════════════════════════════════════════════════════════
class SignalLog(SQLModel, table=True):
    __tablename__ = "signals_log"

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

    # ═══ جدید: traps ═══
    had_trap: bool = False
    trap_type: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# ۲. تنظیمات کاربر
# ═══════════════════════════════════════════════════════════
class UserPrefs(SQLModel, table=True):
    __tablename__ = "user_prefs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="default", index=True, unique=True)

    theme: str = "dark"
    source: str = "nobitex"
    symbol: str = "BTC-USD"
    market_type: str = "futures"
    risk_profile: str = "aggressive"
    timeframe: str = "۵ دقیقه"
    refresh_seconds: int = 60

    updated_at: datetime = Field(default_factory=_utcnow)


# ═══════════════════════════════════════════════════════════
# ۳. نمادهای سفارشی
# ═══════════════════════════════════════════════════════════
class CustomSymbol(SQLModel, table=True):
    __tablename__ = "custom_symbols"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(default="default", index=True)
    ticker: str = Field(index=True)
    name: str = ""
    source: str = "nobitex"
    created_at: datetime = Field(default_factory=_utcnow)
