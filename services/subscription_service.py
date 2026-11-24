"""
Shared subscription lifecycle and activation/reservation logic.

All timestamps are stored as UTC-aware datetimes. A subscription is considered
current only when its persisted state and date window agree.
"""
import logging
import math
from datetime import datetime, timezone, timedelta

from sqlmodel import Session, select

from api.models import Subscription, User
from api.plans import PLANS

logger = logging.getLogger(__name__)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def sync_subscription_status(
    session: Session,
    user_id: int,
    now: datetime | None = None,
) -> bool:
    """
    Reconcile elapsed subscriptions, due reservations and legacy inconsistent
    rows for one user.

    Legacy repair: the old admin adjust-days endpoint could mark every active
    row expired while leaving its future date range intact. If no valid active
    row exists, the most recently-started expired row whose date window still
    covers now is restored to active. This does not reactivate genuinely
    expired rows because their end date is already past.
    """
    now = _utc(now or datetime.now(timezone.utc))
    rows = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.start_date.asc(), Subscription.created_at.asc())
    ).all()

    changed = False
    for sub in rows:
        start = _utc(sub.start_date)
        end = _utc(sub.end_date)

        if sub.status == "active":
            if start and start > now:
                sub.status = "reserved"
                changed = True
            elif end and end <= now:
                sub.status = "expired"
                changed = True
        elif sub.status == "reserved":
            if (end and end <= now) or (start and end and end <= start):
                sub.status = "expired"
                changed = True
        elif sub.status == "expired":
            # Repair a future-dated row incorrectly expired by the old
            # "expire all active subscriptions" admin logic.
            if start and start > now and end and end > start:
                sub.status = "reserved"
                changed = True

    active = [
        s for s in rows
        if s.status == "active"
        and (_utc(s.start_date) is None or _utc(s.start_date) <= now)
        and (_utc(s.end_date) is None or _utc(s.end_date) > now)
    ]

    if not active:
        recoverable_expired = [
            s for s in rows
            if s.status == "expired"
            and (_utc(s.start_date) is None or _utc(s.start_date) <= now)
            and _utc(s.end_date) is not None
            and _utc(s.end_date) > now
            and (
                _utc(s.start_date) is None
                or _utc(s.end_date) > _utc(s.start_date)
            )
        ]
        if recoverable_expired:
            recoverable_expired.sort(
                key=lambda s: (_utc(s.start_date) or now, s.id or 0),
                reverse=True,
            )
            recoverable_expired[0].status = "active"
            changed = True
        else:
            due_reserved = [
                s for s in rows
                if s.status == "reserved"
                and (_utc(s.start_date) is None or _utc(s.start_date) <= now)
                and (_utc(s.end_date) is None or _utc(s.end_date) > now)
            ]
            if due_reserved:
                due_reserved.sort(
                    key=lambda s: (_utc(s.start_date) or now, s.id or 0)
                )
                due_reserved[0].status = "active"
                changed = True

    if changed:
        session.add_all(rows)
        session.flush()
    return changed


def get_current_paid_subscription(
    session: Session,
    user_id: int,
    now: datetime | None = None,
) -> Subscription | None:
    """Return the valid paid subscription covering the current instant."""
    now = _utc(now or datetime.now(timezone.utc))
    rows = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.status == "active")
    ).all()
    candidates = [
        sub for sub in rows
        if sub.plan != "free"
        and sub.end_date is not None
        and (_utc(sub.start_date) is None or _utc(sub.start_date) <= now)
        and _utc(sub.end_date) > now
    ]
    return max(candidates, key=lambda sub: _utc(sub.end_date)) if candidates else None

def activate_or_reserve_subscription(
    session: Session,
    user_id: int,
    plan: str,
) -> dict:
    """
    Add a paid subscription:
    - reserve after the end of the current valid paid subscription;
    - otherwise activate immediately;
    - reject a second unconsumed reservation;
    - enforce the 365-day cap against exact remaining duration.

    The function does not commit; the payment caller commits the payment and
    subscription together.
    """
    plan_info = PLANS.get(plan)
    if not plan_info:
        return {"ok": False, "error": "پلن نامعتبر است", "reason": "invalid_plan"}

    # Serialize concurrent approvals for the same account on PostgreSQL.
    user = session.exec(
        select(User).where(User.id == user_id).with_for_update()
    ).first()
    if not user:
        return {"ok": False, "error": "کاربر یافت نشد", "reason": "user_not_found"}

    now = datetime.now(timezone.utc)
    sync_subscription_status(session, user_id, now)

    rows = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.end_date.desc(), Subscription.created_at.desc())
    ).all()

    existing_reserved = next(
        (
            s for s in rows
            if s.status == "reserved"
            and (_utc(s.end_date) is None or _utc(s.end_date) > now)
        ),
        None,
    )
    if existing_reserved:
        return {
            "ok": False,
            "error": "شما یک اشتراک رزرو دارید. ابتدا آن را مصرف کنید یا با پشتیبانی تماس بگیرید.",
            "reason": "already_reserved",
        }

    current_sub = get_current_paid_subscription(session, user_id, now)

    is_reserved = False
    if current_sub:
        end = _utc(current_sub.end_date)
        remaining_days = max(0, math.ceil((end - now).total_seconds() / 86400))
        plan_days = int(plan_info.get("days") or 0)
        if remaining_days + plan_days > 365:
            return {
                "ok": False,
                "error": (
                    f"مجموع اشتراک شما بیش از ۳۶۵ روز می‌شود "
                    f"(فعلی: {remaining_days} روز + جدید: {plan_days} روز)"
                ),
                "reason": "365_limit",
            }

        new_start = end
        new_end = new_start + timedelta(days=plan_days)
        new_end = new_end.replace(hour=23, minute=59, second=59, microsecond=0)
        new_sub = Subscription(
            user_id=user_id,
            plan=plan,
            start_date=new_start,
            end_date=new_end,
            status="reserved",
        )
        is_reserved = True
    else:
        plan_days = int(plan_info.get("days") or 0)
        new_start = now
        new_end = (now + timedelta(days=plan_days)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        new_sub = Subscription(
            user_id=user_id,
            plan=plan,
            start_date=new_start,
            end_date=new_end,
            status="active",
        )

    session.add(new_sub)
    session.flush()
    return {
        "ok": True,
        "new_sub_end": new_end,
        "is_reserved": is_reserved,
        "plan_info": plan_info,
        "subscription_id": new_sub.id,
    }
