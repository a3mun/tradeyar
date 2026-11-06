import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from api.plans import PLANS
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

    now = datetime.now(timezone.utc)
    actual_status = "active"
    if sub.end_date:
        end = sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end < now:
            actual_status = "expired"

    return {
        "ok": True,
        "subscription": {
            "id": sub.id,
            "plan": sub.plan,
            "start_date": sub.start_date.isoformat(),
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "status": actual_status,
        },
    }


# 🔴 اندپوینت جدید برای تاریخچه تراکنش‌های کاربر
@router.get("/my-transactions")
async def get_my_transactions(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from api.models import PaymentRequest, RefundRequest
    from api.plans import PLANS
    from sqlmodel import select

    # ۱. تراکنش‌های پرداخت
    payments = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .order_by(PaymentRequest.created_at.desc())
    ).all()

    # ۲. درخواست‌های عودت
    refunds = session.exec(
        select(RefundRequest)
        .where(RefundRequest.user_id == user.id)
        .order_by(RefundRequest.created_at.desc())
    ).all()

    items = []

    # اضافه کردن پرداخت‌ها
    for p in payments:
        items.append(
            {
                "id": f"pay_{p.id}",
                "source": "payment",
                "plan": p.plan,
                "plan_price": PLANS.get(p.plan, {}).get("price", 0),
                "amount": p.amount or 0,
                "status": p.status,
                "payment_method": p.payment_method or "card",
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "admin_note": p.admin_note,
                "receipt_note": p.receipt_note,
                "payment_time": p.payment_time,
            }
        )

    # اضافه کردن درخواست‌های عودت
    for r in refunds:
        status_map = {
            "pending": "pending",
            "refunded": "refunded",
            "rejected": "rejected",
        }
        items.append(
            {
                "id": f"refund_{r.id}",
                "source": "refund_request",
                "plan": "refund",
                "plan_price": r.refund_amount,
                "amount": r.refund_amount,
                "status": status_map.get(r.status, r.status),
                "payment_method": "refund",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "admin_note": r.admin_note,
                "receipt_note": None,
                "payment_time": None,
            }
        )

    # مرتب‌سازی بر اساس تاریخ
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return {"items": items}


@router.post("/request")
async def create_payment_request(
    req: PaymentRequestCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):

    # 🔴 چک قانون: سقف ۳۶۵ روز و جلوگیری از خرید تکراری هم‌پوشان
    current_sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    if current_sub and current_sub.end_date:
        now = datetime.now(timezone.utc)
        end = current_sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        days_left = (end - now).days

        # محاسبه روزهای پلن جدید
        from api.plans import PLANS

        new_plan_days = PLANS.get(req.plan, {}).get("days", 0)

        # اگر روزهای باقی‌مانده > 30 و پلن جدید (ارتقا) نیست:
        if days_left > 30 and new_plan_days <= days_left:
            raise HTTPException(
                400,
                detail="شما اشتراک فعال دارید. برای تمدید، فقط در ۳۰ روز آخر می‌توانید اقدام کنید.",
            )

        # سقف ۳۶۵ روز
        if days_left + new_plan_days > 365:
            raise HTTPException(
                400, detail="مجموع اشتراک شما نمی‌تواند بیش از ۳۶۵ روز باشد."
            )

    existing = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .where(PaymentRequest.status == "pending")
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="شما یک درخواست در حال بررسی دارید")

    ip = request.client.host if request.client else "نامشخص"
    user_agent = request.headers.get("user-agent", "نامشخص")

    # 🔴 اضافه شدن مبلغ و روش پرداخت
    pr = PaymentRequest(
        user_id=user.id,
        plan=req.plan,
        amount=req.amount or 0,
        payment_method=req.payment_method or "card",
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
