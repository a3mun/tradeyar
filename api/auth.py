"""
api/auth.py
احراز هویت — JWT + OTP
============================================================
فاز ۱۱: ورود با شماره موبایل + کد یک‌بار مصرف
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from api.config import settings
from api.database import get_session
from api.models import OTPCode, User

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Bearer token
# ═══════════════════════════════════════════════════════════
_bearer = HTTPBearer(auto_error=False)


# ═══════════════════════════════════════════════════════════
# ۱. JWT
# ═══════════════════════════════════════════════════════════
def create_access_token(phone: str, is_admin: bool = False) -> str:
    """ساخت JWT برای کاربر."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": phone,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """رمزگشایی JWT — خطا در صورت نامعتبر بودن."""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as e:
        logger.warning(f"[Auth] JWT نامعتبر: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="توکن نامعتبر است",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ═══════════════════════════════════════════════════════════
# ۲. شماره موبایل
# ═══════════════════════════════════════════════════════════
def normalize_phone(phone: str) -> str:
    """تبدیل شماره به فرمت استاندارد 09xxxxxxxxx."""
    phone = "".join(c for c in phone if c.isdigit())
    if phone.startswith("98"):
        phone = "0" + phone[2:]
    if phone.startswith("9") and len(phone) == 10:
        phone = "0" + phone
    return phone


def is_valid_phone(phone: str) -> bool:
    """اعتبارسنجی شماره موبایل ایران."""
    phone = normalize_phone(phone)
    return len(phone) == 11 and phone.startswith("09")


def get_admin_phones() -> set[str]:
    """لیست شماره‌های ادمین از config."""
    return {
        normalize_phone(p.strip())
        for p in settings.ADMIN_PHONES.split(",")
        if p.strip()
    }


def is_admin_phone(phone: str) -> bool:
    return normalize_phone(phone) in get_admin_phones()


# ═══════════════════════════════════════════════════════════
# ۳. OTP
# ═══════════════════════════════════════════════════════════
def generate_otp() -> str:
    """تولید کد ۵ رقمی."""
    return f"{secrets.randbelow(90000) + 10000}"


def save_otp(
    session: Session, phone: str, code: str, ttl_seconds: int = 120
) -> OTPCode:
    """ذخیره کد در DB با انقضا."""
    # ─── حذف کامل کدهای قبلی برای این شماره ───
    old_codes = session.exec(select(OTPCode).where(OTPCode.phone == phone)).all()
    for o in old_codes:
        session.delete(o)
    session.commit()  # ⬅️ این خط خیلی مهمه تا حذف کامل بشه

    otp = OTPCode(
        phone=phone,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
    )
    session.add(otp)
    session.commit()
    session.refresh(otp)
    return otp


def verify_otp(session: Session, phone: str, code: str) -> bool:
    """تایید کد — چک انقضا و used."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(OTPCode)
        .where(OTPCode.phone == phone)
        .where(OTPCode.code == code)
        .where(OTPCode.used == False)  # noqa
        .order_by(OTPCode.created_at.desc())
    )
    otp = session.exec(stmt).first()
    if not otp:
        return False

    # ─── چک انقضا ───
    expires = otp.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires < now:
        return False

    # ─── mark as used ───
    otp.used = True
    session.add(otp)
    session.commit()
    return True


# ═══════════════════════════════════════════════════════════
# ۴. Dependencyهای FastAPI
# ═══════════════════════════════════════════════════════════
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    """
    کاربر جاری از روی Bearer token.

    Raises:
        HTTPException 401: توکن غایب یا نامعتبر
        HTTPException 403: کاربر غیرفعال
        HTTPException 404: کاربر حذف شده
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="لطفاً وارد شوید",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    phone = normalize_phone(payload.get("sub", ""))

    user = session.exec(select(User).where(User.phone == phone)).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="حساب کاربری غیرفعال است")

    return user


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """فقط ادمین."""
    if not user.is_admin:
        logger.warning(f"[Auth] دسترسی غیرمجاز ادمین: {user.phone}")
        raise HTTPException(status_code=403, detail="دسترسی فقط برای مدیران")
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """نسخه optional — برای endpointهای عمومی که اگه لاگین بود، دیتا بیشتر بدن."""
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        phone = normalize_phone(payload.get("sub", ""))
        return session.exec(select(User).where(User.phone == phone)).first()
    except HTTPException:
        return None
