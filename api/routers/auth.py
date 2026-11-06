"""
api/routers/auth.py
ورود و ثبت‌نام با OTP + ورود با رمز عبور
"""

import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlmodel import Session, select
from passlib.context import CryptContext

from api.auth import (
    create_access_token,
    generate_otp,
    get_current_user,
    is_admin_phone,
    is_valid_phone,
    normalize_phone,
    save_otp,
    verify_otp,
    verify_password,
    get_password_hash,
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
    UpdateProfileRequest,
)
from services.sms import send_otp_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    req: SendOTPRequest, request: Request, session: Session = Depends(get_session)
):
    phone = normalize_phone(req.phone)
    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="شماره نامعتبر")
    rate_limit(f"otp:{phone}", limit=3, window_sec=300)
    code = generate_otp()
    save_otp(session, phone, code, ttl_seconds=300)
    sent = send_otp_sms(phone, code)
    if not sent:
        raise HTTPException(status_code=503, detail="ارسال پیامک ناموفق بود")
    return SendOTPResponse(retry_after=60)


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(
    req: VerifyOTPRequest, request: Request, session: Session = Depends(get_session)
):
    phone = normalize_phone(req.phone)
    if not is_valid_phone(phone):
        raise HTTPException(status_code=400, detail="شماره نامعتبر")
    rate_limit(f"verify:{phone}", limit=10, window_sec=300)
    if not verify_otp(session, phone, req.code):
        raise HTTPException(status_code=401, detail="کد نامعتبر")

    user = session.exec(select(User).where(User.phone == phone)).first()
    is_new = user is None
    now = datetime.now(timezone.utc)
    ip = request.client.host if request.client else "نامشخص"
    user_agent = request.headers.get("user-agent", "نامشخص")
    admin_by_config = is_admin_phone(phone)

    if user is None:
        # ساخت کاربر جدید + پلن رایگان
        user = User(
            phone=phone,
            is_active=True,
            is_admin=admin_by_config,
            last_login=now,
            last_ip=ip,
            last_user_agent=user_agent,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        sub = Subscription(
            user_id=user.id,
            plan="free",
            start_date=now,
            end_date=now + timedelta(days=settings.FREE_PLAN_DAYS),
            status="active",
        )
        session.add(sub)
        session.commit()

        try:
            from api.routers.admin_ws import notify_admins

            await notify_admins(
                {
                    "type": "new_user",
                    "id": user.id,
                    "user_phone": phone,
                    "full_name": user.full_name or "نامشخص",
                    "message": f"👤 کاربر جدید ثبت‌نام کرد: {phone}",
                }
            )
        except Exception as e:
            logger.warning(f"[Notify] WebSocket admin failed: {e}")

    else:
        user.is_admin = admin_by_config
        user.last_login = now
        user.last_ip = ip
        user.last_user_agent = user_agent
        session.add(user)
        session.commit()
        session.refresh(user)

    token = create_access_token(user.phone, is_admin=admin_by_config)
    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user, from_attributes=True),
        is_new_user=is_new,
    )


# ═══════════════════════════════════════════════════════════
# 🔴 اندپوینت جدید: ورود با رمز عبور
# ═══════════════════════════════════════════════════════════
@router.post("/login", response_model=TokenResponse)
async def login_with_password(
    phone: str = Body(...),
    password: str = Body(...),
    session: Session = Depends(get_session),
):
    phone = normalize_phone(phone)
    user = session.exec(select(User).where(User.phone == phone)).first()

    if (
        not user
        or not user.hashed_password
        or not verify_password(password, user.hashed_password)
    ):
        raise HTTPException(status_code=401, detail="شماره یا رمز عبور اشتباه است")

    token = create_access_token(user.phone, is_admin=user.is_admin)

    return TokenResponse(
        access_token=token,
        user=UserRead.model_validate(user, from_attributes=True),
        is_new_user=False,
    )


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "has_password": bool(user.hashed_password),  # 🔴 برگردوندن وضعیت رمز
        },
    }


@router.put("/me")
async def update_profile(
    req: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """آپدیت نام نمایشی، ایمیل و رمز عبور (بدون نیاز به رمز فعلی)"""
    if req.full_name is not None:
        user.full_name = req.full_name

    if req.email is not None:
        if req.email and ("@" not in req.email or "." not in req.email):
            raise HTTPException(status_code=400, detail="ایمیل نامعتبر است")
        user.email = req.email

    if req.new_password:
        if len(req.new_password) < 6:
            raise HTTPException(
                status_code=400, detail="رمز جدید باید حداقل ۶ حرف باشد"
            )

        # 🔴 ذخیره رمز جدید (بدون نیاز به رمز فعلی)
        user.hashed_password = get_password_hash(req.new_password)

    session.add(user)
    session.commit()
    session.refresh(user)

    # 🔴 برگردوندن has_password بعد از ویرایش
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "phone": user.phone,
            "full_name": user.full_name,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "has_password": bool(user.hashed_password),
        },
    }

    return {
        "ok": True,
        "user": UserRead.model_validate(user, from_attributes=True).model_dump(),
    }
