import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from api.database import get_session
from api.auth import require_admin
from api.models import User, Subscription, PaymentRequest
from api.plans import PLANS
from services.sms import send_subscription_activated_sms

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/payments")
async def list_payments(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payments = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.status == "pending")
        .order_by(PaymentRequest.created_at.desc())
    ).all()
    result = []
    for p in payments:
        user = session.get(User, p.user_id)
        result.append(
            {
                "id": p.id,
                "user_phone": user.phone if user else "ناشناس",
                "user_joined_at": (
                    user.created_at.isoformat() if user and user.created_at else None
                ),
                "user_last_login": (
                    user.last_login.isoformat() if user and user.last_login else None
                ),
                "plan": p.plan,
                "receipt_note": p.receipt_note,
                "created_at": p.created_at.isoformat(),
                "ip_address": p.ip_address or "نامشخص",
                "user_agent": p.user_agent or "نامشخص",
                "full_name": p.full_name or "نامشخص",  # ⬅️ اضافه شد
                "payment_time": p.payment_time or "نامشخص",  # ⬅️ اضافه شد
            }
        )
    return {"ok": True, "items": result}


@router.post("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payment = session.get(PaymentRequest, payment_id)
    if not payment or payment.status != "pending":
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    user = session.get(User, payment.user_id)
    plan_info = PLANS.get(payment.plan)
    if not plan_info:
        raise HTTPException(status_code=400, detail="پلن نامعتبر است")

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()
    now = datetime.now(timezone.utc)

    if sub:
        start_date = max(sub.end_date, now) if sub.end_date else now
        sub.plan = payment.plan
        sub.start_date = now
        sub.end_date = start_date + timedelta(days=plan_info["days"])
        sub.status = "active"
        session.add(sub)
    else:
        sub = Subscription(
            user_id=user.id,
            plan=payment.plan,
            start_date=now,
            end_date=now + timedelta(days=plan_info["days"]),
            status="active",
        )
        session.add(sub)

    payment.status = "approved"
    payment.reviewed_at = now
    payment.reviewed_by = admin.phone
    session.add(payment)
    session.commit()

    try:
        send_subscription_activated_sms(user.phone, plan_info["title"], sub.end_date)
    except Exception:
        pass

    return {"ok": True, "message": "پرداخت تایید و اشتراک فعال شد"}


@router.post("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: int,
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    payment = session.get(PaymentRequest, payment_id)
    if not payment or payment.status != "pending":
        raise HTTPException(status_code=404, detail="درخواست یافت نشد")

    payment.status = "rejected"
    payment.reviewed_at = datetime.now(timezone.utc)
    payment.reviewed_by = admin.phone
    session.add(payment)
    session.commit()
    return {"ok": True, "message": "پرداخت رد شد"}


@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
    session: Session = Depends(get_session),
):
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    result = []
    for u in users:
        sub = session.exec(
            select(Subscription)
            .where(Subscription.user_id == u.id)
            .order_by(Subscription.created_at.desc())
        ).first()
        result.append(
            {
                "id": u.id,
                "phone": u.phone,
                "full_name": u.full_name or "نامشخص",
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat(),
                "plan": sub.plan if sub else "بدون اشتراک",
                "end_date": sub.end_date.isoformat() if sub and sub.end_date else None,
            }
        )
    return {"ok": True, "items": result}
