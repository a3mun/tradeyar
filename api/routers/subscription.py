import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from api.database import get_session
from api.auth import get_current_user
from api.models import User, Subscription, PaymentRequest
from api.schemas import PaymentRequestCreate
from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["Subscription"])


@router.get("/my")
async def get_my_subscription(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    if not sub:
        now = datetime.now(timezone.utc)
        sub = Subscription(
            user_id=user.id,
            plan="free",
            start_date=now,
            end_date=now + timedelta(days=settings.FREE_PLAN_DAYS),
            status="active",
        )
        session.add(sub)
        session.commit()
        session.refresh(sub)

    return {
        "ok": True,
        "subscription": {
            "id": sub.id,
            "plan": sub.plan,
            "start_date": sub.start_date.isoformat(),
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "status": sub.status,
        },
    }


@router.post("/request")
async def create_payment_request(
    req: PaymentRequestCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .where(PaymentRequest.status == "pending")
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="شما یک درخواست در حال بررسی دارید")

    ip = request.client.host if request.client else "نامشخص"
    user_agent = request.headers.get("user-agent", "نامشخص")

    pr = PaymentRequest(
        user_id=user.id,
        plan=req.plan,
        amount=0,
        status="pending",
        receipt_note=req.receipt_note,
        ip_address=ip,
        user_agent=user_agent,
        full_name=req.full_name,
        payment_time=req.payment_time,
    )
    session.add(pr)
    session.commit()
    session.refresh(pr)

    # 🔴 نوتیف به ادمین‌های متصل
    try:
        from api.routers.admin_ws import notify_admins

        await notify_admins(
            {
                "type": "new_payment_request",
                "id": pr.id,
                "user_phone": user.phone,
                "full_name": req.full_name or "نامشخص",
                "plan": req.plan,
                "message": f"🔔 درخواست جدید از {user.phone}",
            }
        )
    except Exception as e:
        logger.warning(f"[Notify] WebSocket admin failed: {e}")

    return {"ok": True, "message": "درخواست شما ثبت شد", "id": pr.id}
