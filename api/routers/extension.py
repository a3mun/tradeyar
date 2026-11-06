"""
api/routers/extension.py
اکستنشن کروم — دانلود، توکن اختصاصی و بررسی وضعیت
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from api.auth import get_current_user
from api.config import BASE_DIR
from api.database import get_session
from api.models import ExtensionDownloadLog, ExtensionToken, Subscription, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/extension", tags=["Extension"])


@router.get("/download")
async def download_extension(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # 🔴 چک کردن پلن (ادمین‌ها همیشه دسترسی دارن)
    if not user.is_admin:
        sub = session.exec(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.created_at.desc())
        ).first()

        now = datetime.now(timezone.utc)
        is_valid = (
            sub and sub.plan != "free" and (sub.end_date is None or sub.end_date > now)
        )
        if not is_valid:
            raise HTTPException(
                status_code=403,
                detail="برای دانلود افزونه، به اشتراک حرفه‌ای (Pro) نیاز دارید.",
            )

    # 🔴 ثبت لاگ
    ip = request.client.host if request.client else "نامشخص"
    ua = request.headers.get("user-agent", "نامشخص")
    log = ExtensionDownloadLog(
        user_id=user.id,
        ip_address=ip,
        user_agent=ua,
    )
    session.add(log)
    session.commit()

    # 🔴 ارسال فایل از مسیر data
    file_path = BASE_DIR / "data" / "trademun-extension.zip"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="فایل افزونه یافت نشد")

    return FileResponse(
        path=file_path,
        filename="trademun-extension.zip",
        media_type="application/zip",
    )


@router.post("/token")
async def create_extension_token_endpoint(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    old_tokens = session.exec(
        select(ExtensionToken).where(ExtensionToken.user_id == user.id)
    ).all()
    for old in old_tokens:
        session.delete(old)
    session.flush()

    ext_token = ExtensionToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(ext_token)
    session.commit()

    return {"ok": True, "token": raw_token, "expires_in_hours": 24}


@router.post("/verify")
async def verify_extension_token_endpoint(
    raw_token: str,
    session: Session = Depends(get_session),
):
    from api.auth import verify_extension_token

    user_id = verify_extension_token(session, raw_token)
    if not user_id:
        return {"ok": True, "valid": False, "reason": "توکن نامعتبر یا منقضی شده است"}

    user = session.get(User, user_id)
    if not user or not user.is_active:
        return {"ok": True, "valid": False, "reason": "حساب کاربری غیرفعال است"}

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.created_at.desc())
    ).first()

    now = datetime.now(timezone.utc)
    plan = sub.plan if sub else "free"
    expires_at = sub.end_date.isoformat() if sub and sub.end_date else None
    is_valid = plan != "free" and (sub.end_date is None or sub.end_date > now)

    if not is_valid:
        return {"ok": True, "valid": False, "reason": "اشتراک حرفه‌ای فعال نیست"}

    return {
        "ok": True,
        "valid": True,
        "user_name": user.full_name or user.phone,
        "plan": plan,
        "expires_at": expires_at,
    }
