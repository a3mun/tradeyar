"""
api/models.py
مدل‌های دیتابیس — SQLModel
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    had_trap: bool = False
    trap_type: Optional[str] = None
    dedup_key: Optional[str] = Field(default=None, index=True)
    rr_net: Optional[float] = None
    fee_pct: Optional[float] = None
    fee_ratio: Optional[float] = None
    breakeven_pct: Optional[float] = None
    is_worthwhile: Optional[bool] = None
    timeframe_viable: Optional[bool] = None
    rr_decay_pct: Optional[float] = None
    execution_cost_json: Optional[str] = None
    trade_side_irt: bool = False
    orderbook_available: bool = False
    expired_at_price: Optional[float] = None
    expired_pnl_pct: Optional[float] = None
    expired_bias: Optional[str] = None
    trend_correct: Optional[bool] = None
    is_weak: bool = Field(default=False, index=True)


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    email: Optional[str] = None  # ⬅️ اضافه شد
    hashed_password: Optional[str] = None  # ⬅️ اضافه شد
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)
    last_login: Optional[datetime] = None
    last_ip: Optional[str] = None
    last_user_agent: Optional[str] = None


class OTPCode(SQLModel, table=True):
    __tablename__ = "otp_codes"
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(index=True)
    code: str
    expires_at: datetime
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    plan: str = "free"
    start_date: datetime = Field(default_factory=_utcnow)
    end_date: Optional[datetime] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=_utcnow)


class PaymentRequest(SQLModel, table=True):
    __tablename__ = "payment_requests"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    amount: int = 0
    plan: str = "1_month"
    status: str = "pending"
    receipt_note: Optional[str] = None
    admin_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    full_name: Optional[str] = None
    payment_time: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    reviewed_at: Optional[datetime] = None
