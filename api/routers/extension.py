"""
api/routers/extension.py
مدیریت توکن و احراز هویت اکستنشن مرورگر
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlmodel import Session, select
from typing import Optional

from api.auth import (
    create_extension_token,
    verify_extension_token,
    get_current_user,
)
from api.database import get_session
from api.models import User, Subscription
from api.deps import rate_limit
from api.schemas import ExtensionTokenResponse, ExtensionVerifyResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/extension", tags=["Extension"])


@router.post("/token", response_model=ExtensionTokenResponse)
async def generate_token(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """صدور توکن ۲۴ ساعته برای اکستنشن (نیاز به JWT سایت دارد)"""
    raw_token = create_extension_token(session, user.id)
    return ExtensionTokenResponse(token=raw_token, expires_in_hours=24)


# در api/routers/extension.py
@router.get("/verify", response_model=ExtensionVerifyResponse)
async def verify_token(
    x_extension_token: Optional[str] = Header(default=None, alias="X-Extension-Token"),
    session: Session = Depends(get_session),
):
    if not x_extension_token:
        return ExtensionVerifyResponse(valid=False, reason="missing_token")

    user_id = verify_extension_token(session, x_extension_token)
    if not user_id:
        return ExtensionVerifyResponse(valid=False, reason="invalid_or_expired_token")

    user = session.get(User, user_id)
    if not user or not user.is_active:
        return ExtensionVerifyResponse(valid=False, reason="user_inactive")

    now = datetime.now(timezone.utc)
    stmt = (
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "active")
        .where(Subscription.end_date > now)
    )
    sub = session.exec(stmt).first()

    # 👈 ماسک کردن شماره تلفن برای نمایش
    masked_phone = user.phone
    if len(user.phone) >= 11:
        masked_phone = f"{user.phone[:4]}***{user.phone[-4:]}"

    display_name = user.full_name if user.full_name else f"کاربر {masked_phone}"

    if not sub:
        last_sub_stmt = (
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(Subscription.end_date.desc())
        )
        last_sub = session.exec(last_sub_stmt).first()

        # 👈 ارسال تاریخ به صورت رشته تمیز
        if last_sub and last_sub.end_date:
            exp_str = last_sub.end_date.strftime("%Y-%m-%d")
            reason = f"expired_at:{exp_str}"
        else:
            reason = "no_active_subscription"

        return ExtensionVerifyResponse(valid=False, reason=reason)

    return ExtensionVerifyResponse(
        valid=True,
        user_name=display_name,
        plan=sub.plan,
        expires_at=sub.end_date.strftime("%Y-%m-%d") if sub.end_date else None,
    )
