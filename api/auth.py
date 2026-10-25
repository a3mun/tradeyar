"""
api/auth.py
احراز هویت OTP/JWT و کنترل دسترسی
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from api.config import settings
from api.database import get_session
from api.models import OTPCode, User

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


def create_access_token(phone: str, is_admin: bool = False) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": normalize_phone(phone),
        "is_admin": bool(is_admin),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        if not isinstance(payload.get("sub"), str) or not payload["sub"]:
            raise JWTError("Missing subject")
        return payload
    except JWTError as exc:
        logger.warning("[Auth] JWT validation failed")
        raise HTTPException(
            status_code=401, detail="توکن نامعتبر یا منقضی شده است"
        ) from exc


def normalize_phone(phone: str) -> str:
    if not isinstance(phone, str):
        return ""
    digit_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    phone = phone.translate(digit_map)
    phone = "".join(c for c in phone if c.isascii() and c.isdigit())
    if phone.startswith("0098"):
        phone = "0" + phone[4:]
    elif phone.startswith("98"):
        phone = "0" + phone[2:]
    elif phone.startswith("9") and len(phone) == 10:
        phone = "0" + phone
    return phone


def is_valid_phone(phone: str) -> bool:
    phone = normalize_phone(phone)
    return (
        len(phone) == 11
        and phone.startswith("09")
        and phone.isascii()
        and phone.isdigit()
    )


def get_admin_phones() -> set[str]:
    raw = settings.ADMIN_PHONES or ""
    result: set[str] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        normalized = normalize_phone(item)
        if is_valid_phone(normalized):
            result.add(normalized)
    return result


def is_admin_phone(phone: str) -> bool:
    normalized = normalize_phone(phone)
    return is_valid_phone(normalized) and normalized in get_admin_phones()


def generate_otp() -> str:
    return f"{secrets.randbelow(90000) + 10000}"


def save_otp(
    session: Session, phone: str, code: str, ttl_seconds: int = 120
) -> OTPCode:
    phone = normalize_phone(phone)
    old_codes = session.exec(select(OTPCode).where(OTPCode.phone == phone)).all()
    for old_code in old_codes:
        session.delete(old_code)
    session.flush()
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
    phone = normalize_phone(phone)
    now = datetime.now(timezone.utc)
    stmt = (
        select(OTPCode)
        .where(OTPCode.phone == phone)
        .where(OTPCode.code == code)
        .where(OTPCode.used == False)
        .order_by(OTPCode.created_at.desc())
    )
    otp = session.exec(stmt).first()
    if not otp:
        return False
    expires = otp.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        return False
    otp.used = True
    session.add(otp)
    session.commit()
    return True


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="لطفاً وارد شوید")
    payload = decode_token(credentials.credentials)
    phone = normalize_phone(payload.get("sub", ""))
    if not is_valid_phone(phone):
        raise HTTPException(status_code=401, detail="توکن نامعتبر است")
    user = session.exec(select(User).where(User.phone == phone)).first()
    if not user:
        raise HTTPException(status_code=401, detail="کاربر یافت نشد")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="حساب کاربری غیرفعال است")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """کنترل دسترسی بدون تغییر نقش — فقط ادمین اصلی"""
    allowed_by_config = is_admin_phone(user.phone)
    if not allowed_by_config or not bool(user.is_admin):
        raise HTTPException(status_code=403, detail="دسترسی فقط برای مدیران اصلی")
    return user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        phone = normalize_phone(payload.get("sub", ""))
        if not is_valid_phone(phone):
            return None
        user = session.exec(select(User).where(User.phone == phone)).first()
        if not user or not user.is_active:
            return None
        return user
    except HTTPException:
        return None
