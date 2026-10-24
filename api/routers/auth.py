"""
api/routers/auth.py
احراز هویت — OTP + JWT
============================================================
فاز ۱۱
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from api.auth import (
    create_access_token,
    generate_otp,
    get_current_user,
    is_admin_phone,
    is_valid_phone,
    normalize_phone,
    save_otp,
    verify_otp,
)
from api.config import settings
from api.database import get_session
from api.deps import rate_limit
from api.models import Subscription, User
from api.schemas import (
    SendOTPRequest,
    SendOTPResponse,
    TokenResponse,
    UserRead,
    VerifyOTPRequest,
)
from services.sms import send_otp_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


# ═══════════════════════════════════════════════════════════
# POST /auth/send-otp — ارسال کد
# ═══════════════════════════════════════════════════════════
@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    req: SendOTPRequest, request: Request, session: Session = Depends(get_session)
):
    """ارسال کد یک‌بار مصرف به شماره موبایل."""
    phone = normalize_phone(req.phone)

    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="شماره موبایل نامعتبر است")

    # ─── Rate limit: هر شماره ۳ بار در ۵ دقیقه ───
    rate_limit(f"otp:{phone}", limit=3, window_sec=300)

    # ─── تولید و ذخیره ───
    code = generate_otp()
    save_otp(session, phone, code, ttl_seconds=120)

    # ─── ارسال پیامک ───
    sent = send_otp_sms(phone, code)
    if not sent:
        logger.error(f"[Auth] ارسال OTP به {phone} ناموفق")
        raise HTTPException(
            status_code=500,
            detail="ارسال پیامک ناموفق بود — دوباره تلاش کنید",
        )

    logger.info(f"[Auth] OTP به {phone} ارسال شد")
    return SendOTPResponse(retry_after=60)


# ═══════════════════════════════════════════════════════════
# POST /auth/verify-otp — تایید کد + JWT
# ═══════════════════════════════════════════════════════════
@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(
    req: VerifyOTPRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    """تایید کد و دریافت JWT."""
    phone = normalize_phone(req.phone)

    # ─── Rate limit برای verify ───
    rate_limit(f"verify:{phone}", limit=10, window_sec=300)

    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="شماره موبایل نامعتبر است")

    # ─── تایید کد ───
    if not verify_otp(session, phone, req.code):
        raise HTTPException(status_code=401, detail="کد نامعتبر یا منقضی شده")

    # ─── پیدا کردن یا ساختن کاربر ───
    user = session.exec(select(User).where(User.phone == phone)).first()
    is_new = False

    if not user:
        is_new = True
        admin_flag = is_admin_phone(phone)
        user = User(
            phone=phone,
            is_active=True,
            is_admin=admin_flag,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # ─── پلن رایگان ───
        sub = Subscription(
            user_id=user.id,
            plan="free",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc)
            + timedelta(days=settings.FREE_PLAN_DAYS),
            status="active",
        )
        session.add(sub)
        session.commit()

        logger.info(
            f"[Auth] کاربر جدید: {phone} — پلن رایگان {settings.FREE_PLAN_DAYS} روزه"
        )
    else:
        # ─── آپدیت is_admin اگه توی لیست ادمین‌هاست ───
        if is_admin_phone(phone) and not user.is_admin:
            user.is_admin = True
            session.add(user)
        user.last_login = datetime.now(timezone.utc)
        session.add(user)
        session.commit()

    # ─── JWT ───
    token = create_access_token(user.phone, is_admin=user.is_admin)
    logger.info(f"[Auth] ورود موفق: {phone} (admin={user.is_admin})")

    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user, from_attributes=True),
        is_new_user=is_new,
    )


# ═══════════════════════════════════════════════════════════
# GET /auth/me — اطلاعات کاربر جاری
# ═══════════════════════════════════════════════════════════
@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """اطلاعات کاربر جاری."""
    return {
        "ok": True,
        "user": UserRead.model_validate(user, from_attributes=True).model_dump(),
    }
