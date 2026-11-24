"""
services/subscription_service.py
منطق مشترک فعال‌سازی/رزرو اشتراک (استفاده در subscription.py و admin.py)
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select

from api.plans import PLANS
from api.models import Subscription

logger = logging.getLogger(__name__)


def activate_or_reserve_subscription(
    session: Session,
    user_id: int,
    plan: str,
) -> dict:
    """
    منطق مشترک:
    - اگه کاربر پلن پولی فعال داره → رزرو (شروع از پایان قبلی)
    - اگه رایگان/منقضی/بدون اشتراک → فعال‌سازی فوری
    - جلوگیری از دو رزرو هم‌زمان
    - سقف ۳۶۵ روز

    Returns:
        {"ok": True, "new_sub_end": datetime, "is_reserved": bool, "plan_info": dict}
        یا
        {"ok": False, "error": str, "reason": str}
    """
    plan_info = PLANS.get(plan)
    if not plan_info:
        return {"ok": False, "error": "پلن نامعتبر است", "reason": "invalid_plan"}

    now = datetime.now(timezone.utc)

    # 🔴 ۱. چک رزرو قبلی
    existing_reserved = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status == "reserved")
    ).first()

    if existing_reserved:
        return {
            "ok": False,
            "error": "شما یک اشتراک رزرو دارید. ابتدا آن را مصرف کنید یا با پشتیبانی تماس بگیرید.",
            "reason": "already_reserved",
        }

    # 🔴 ۲. اشتراک فعال فعلی
    current_sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
    ).first()

    new_sub_end = None
    is_reserved = False

    if current_sub and current_sub.end_date and current_sub.plan != "free":
        end = current_sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if end > now:
            days_left = (end - now).days

            # چک سقف ۳۶۵ روز
            if days_left + plan_info["days"] > 365:
                return {
                    "ok": False,
                    "error": f"مجموع اشتراک شما بیش از ۳۶۵ روز می‌شود (فعلی: {days_left} روز + جدید: {plan_info['days']} روز)",
                    "reason": "365_limit",
                }

            # رزرو
            new_start = end
            new_end = new_start + timedelta(days=plan_info["days"])
            new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)

            new_sub = Subscription(
                user_id=user_id,
                plan=plan,
                start_date=new_start,
                end_date=new_end,
                status="reserved",
            )
            session.add(new_sub)
            new_sub_end = new_end
            is_reserved = True
        else:
            # منقضی شده → فعال‌سازی فوری
            current_sub.status = "expired"
            session.add(current_sub)

            new_end = now + timedelta(days=plan_info["days"])
            new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)

            new_sub = Subscription(
                user_id=user_id,
                plan=plan,
                start_date=now,
                end_date=new_end,
                status="active",
            )
            session.add(new_sub)
            new_sub_end = new_end
    else:
        # رایگان یا بدون اشتراک → فعال‌سازی فوری
        if current_sub:
            current_sub.status = "expired"
            session.add(current_sub)

        new_end = now + timedelta(days=plan_info["days"])
        new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)

        new_sub = Subscription(
            user_id=user_id,
            plan=plan,
            start_date=now,
            end_date=new_end,
            status="active",
        )
        session.add(new_sub)
        new_sub_end = new_end

    return {
        "ok": True,
        "new_sub_end": new_sub_end,
        "is_reserved": is_reserved,
        "plan_info": plan_info,
    }
