import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
import uuid
import math
import re

from api.plans import PLANS, calculate_new_end_date
from api.database import get_session
from api.auth import get_current_user
from api.models import (
    User,
    Subscription,
    PaymentRequest,
    SubscriptionLog,
    PricingSettings,
)
from api.schemas import PaymentRequestCreate
from api.config import settings
from services.sms import send_subscription_activated_sms
from services.payment_zibal import (
    create_payment_request as zibal_create_request,
    verify_payment as zibal_verify_payment,
)
from services.subscription_service import activate_or_reserve_subscription, sync_subscription_status, get_current_paid_subscription

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subscription", tags=["Subscription"])

FRONTEND_URL = getattr(settings, "FRONTEND_URL", "http://localhost:3000")


def _get_server_price(session: Session, plan: str) -> int:
    """قیمت واقعی پلن (تومان) — فقط از سمت سرور.

    اولویت: جدول PricingSettings (قابل ویرایش توسط ادمین) و سپس PLANS.
    مبلغ ارسالی از سمت کلاینت هرگز مورد اعتماد نیست.
    """
    if plan not in PLANS or plan == "free":
        raise HTTPException(status_code=400, detail="پلن نامعتبر است")
    row = session.exec(
        select(PricingSettings).where(PricingSettings.plan_id == plan)
    ).first()
    price = int(row.price) if row and row.price else int(PLANS[plan]["price"])
    if price <= 0:
        raise HTTPException(status_code=400, detail="قیمت پلن نامعتبر است")
    return price


# ═══════════════════════════════════════════════════════════
# ۱. اشتراک فعلی
# ═══════════════════════════════════════════════════════════
@router.get("/my")
async def get_my_subscription(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    if sync_subscription_status(session, user.id, now):
        session.commit()

    rows = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).all()

    def as_utc(value):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    active_rows = [
        item for item in rows
        if item.status == "active"
        and (as_utc(item.start_date) is None or as_utc(item.start_date) <= now)
        and (as_utc(item.end_date) is None or as_utc(item.end_date) > now)
    ]
    reserved_rows = [
        item for item in rows
        if item.status == "reserved"
        and (as_utc(item.start_date) is None or as_utc(item.start_date) > now)
        and (as_utc(item.end_date) is None or as_utc(item.end_date) > now)
    ]

    paid_active_rows = [item for item in active_rows if item.plan != "free"]
    if paid_active_rows:
        active_rows = paid_active_rows

    if active_rows:
        sub = max(active_rows, key=lambda item: (as_utc(item.start_date) or now, item.id or 0))
    elif reserved_rows:
        sub = min(reserved_rows, key=lambda item: (as_utc(item.start_date) or now, item.id or 0))
    elif rows:
        sub = rows[0]
    else:
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
            "start_date": sub.start_date.isoformat() if sub.start_date else None,
            "end_date": sub.end_date.isoformat() if sub.end_date else None,
            "status": sub.status,
        },
    }


# ═══════════════════════════════════════════════════════════
# ۲. تاریخچه تراکنش‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/my-transactions")
async def get_my_transactions(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from api.models import PaymentRequest, RefundRequest

    payments = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .order_by(PaymentRequest.created_at.desc())
    ).all()

    refunds = session.exec(
        select(RefundRequest)
        .where(RefundRequest.user_id == user.id)
        .order_by(RefundRequest.created_at.desc())
    ).all()

    items = []

    for p in payments:
        refund_reference = None
        refund_subscription_code = None
        if p.payment_method == "refund":
            reference_match = re.search(r"RF-\d{6}", p.admin_note or "")
            subscription_match = re.search(r"SUB-\d{6}", p.admin_note or "")
            refund_reference = reference_match.group(0) if reference_match else None
            refund_subscription_code = subscription_match.group(0) if subscription_match else None
        items.append(
            {
                "id": f"pay_{p.id}",
                "reference_code": refund_reference,
                "subscription_code": refund_subscription_code,
                "source": "payment",
                "stage_label": "عودت وجه توسط مدیر" if p.payment_method == "refund" else None,
                "plan": p.plan,
                "plan_price": p.plan_price_at_purchase
                or PLANS.get(p.plan, {}).get("price", 0),
                "amount": p.amount or 0,
                "status": p.status,
                "payment_method": p.payment_method or "card",
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "admin_note": p.admin_note,
                "receipt_note": p.receipt_note,
                "payment_time": p.payment_time,
                "zibal_ref_id": p.zibal_ref_id,
            }
        )

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
                "reference_code": f"RF-{r.id:06d}",
                "subscription_id": r.subscription_id or getattr(r, "subscription_id_snapshot", None),
                "stage_label": "درخواست عودت وجه توسط کاربر",
                "old_plan": r.old_plan,
                "new_plan": r.new_plan,
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
                "processed_by": r.processed_by,
                "plan": "refund",
                "plan_price": r.refund_amount,
                "amount": r.refund_amount,
                "status": status_map.get(r.status, r.status),
                "payment_method": "refund",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "admin_note": r.admin_note,
                "receipt_note": None,
                "payment_time": None,
                "zibal_ref_id": None,
            }
        )

    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return {"items": items}


# ═══════════════════════════════════════════════════════════
# ۳. تاریخچه اشتراک‌ها
# ═══════════════════════════════════════════════════════════
@router.get("/history")
async def get_my_subscriptions_history(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if sync_subscription_status(session, user.id):
        session.commit()

    subs = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).all()

    now = datetime.now(timezone.utc)
    items = []
    for sub in subs:
        start = sub.start_date
        end = sub.end_date
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        status = sub.status
        if end and end <= now:
            status = "expired"
        elif start and start > now and status in ("active", "reserved"):
            status = "reserved"

        items.append(
            {
                "id": sub.id,
                "plan": sub.plan,
                "start_date": sub.start_date.isoformat() if sub.start_date else None,
                "end_date": sub.end_date.isoformat() if sub.end_date else None,
                "status": status,
            }
        )

    return {"ok": True, "total": len(items), "items": items}


# ═══════════════════════════════════════════════════════════
# ۴. درگاه زیبال (پرداخت آنلاین)
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
# ۴. درگاه زیبال (پرداخت آنلاین)
# ═══════════════════════════════════════════════════════════
@router.post("/pay/zibal")
async def pay_with_zibal(
    req: PaymentRequestCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """ثبت درخواست پرداخت و هدایت به درگاه زیبال"""

    # وضعیت اشتراک‌های منقضی/رزروهای سررسیدشده را قبل از اعتبارسنجی همگام کن.
    if sync_subscription_status(session, user.id):
        session.commit()

    # 🔴 ۱. چک رزرو قبلی (قبل از رفتن به درگاه)
    existing_reserved = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "reserved")
    ).first()

    if existing_reserved:
        raise HTTPException(
            status_code=400,
            detail="شما یک اشتراک رزرو دارید. ابتدا آن را مصرف کنید یا با پشتیبانی تماس بگیرید.",
        )

    # 🔴 ۲. چک سقف ۳۶۵ روز
    current_sub = get_current_paid_subscription(session, user.id)

    if current_sub and current_sub.end_date and current_sub.plan != "free":
        now = datetime.now(timezone.utc)
        end = current_sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        days_left = math.ceil((end - now).total_seconds() / 86400)
        new_plan_days = PLANS.get(req.plan, {}).get("days", 0)

        if end > now and days_left + new_plan_days > 365:
            raise HTTPException(
                status_code=400,
                detail=f"مجموع اشتراک شما بیش از ۳۶۵ روز می‌شود (فعلی: {days_left} روز + جدید: {new_plan_days} روز). لطفاً پلن کوتاه‌تری انتخاب کنید.",
            )

    # 🔴 ۳. چک درخواست pending قبلی
    existing_pending = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .where(PaymentRequest.status == "pending")
    ).first()
    if existing_pending:
        raise HTTPException(
            status_code=400,
            detail="شما یک درخواست در حال بررسی دارید. لطفاً تا تکمیل آن صبر کنید.",
        )

    # 🔴 ۴. ثبت درخواست و هدایت به درگاه (مبلغ فقط از سرور)
    server_price = _get_server_price(session, req.plan)
    pr = PaymentRequest(
        user_id=user.id,
        plan=req.plan,
        amount=server_price,
        plan_price_at_purchase=server_price,
        payment_method="zibal",
        status="pending",
        receipt_note=req.receipt_note,
        full_name=req.full_name,
        payment_time="online",
    )
    session.add(pr)
    session.commit()
    session.refresh(pr)

    order_id = f"trademun_{pr.id}_{uuid.uuid4().hex[:8]}"
    result = zibal_create_request(
        amount=server_price * 10,  # تومان به ریال
        description=f"خرید {req.plan} - تریدمون",
        mobile=user.phone,
        order_id=order_id,
    )

    if not result["ok"]:
        pr.status = "rejected"
        pr.admin_note = f"خطای درگاه: {result['error']}"
        session.add(pr)
        session.commit()
        raise HTTPException(status_code=400, detail=result["error"])

    pr.zibal_track_id = result["track_id"]
    session.add(pr)
    session.commit()

    return {
        "ok": True,
        "payment_url": result["payment_url"],
        "track_id": result["track_id"],
        "payment_request_id": pr.id,
    }


# ═══════════════════════════════════════════════════════════
# ۵. کال‌بک زیبال (تایید پرداخت)
# ═══════════════════════════════════════════════════════════
@router.get("/verify-zibal")
async def verify_zibal_payment(
    trackId: str,
    success: str,
    status: str = None,
    session: Session = Depends(get_session),
):
    """کال‌بک زیبال: بعد از پرداخت کاربر برمی‌گردد."""
    pr = session.exec(
        select(PaymentRequest).where(PaymentRequest.zibal_track_id == trackId)
    ).first()

    if not pr:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/payment-result?status=failed&reason=not_found"
        )

    # 🔴 اگه قبلاً تایید شده، دوباره پردازش نکن
    if pr.status == "approved":
        return RedirectResponse(
            url=f"{FRONTEND_URL}/payment-result?status=success&ref={pr.zibal_ref_id or trackId}"
        )

    # بررسی وضعیت پرداخت
    if success != "1" or status != "2":
        pr.status = "rejected"
        pr.admin_note = f"پرداخت ناموفق. success={success}, status={status}"
        session.add(pr)
        session.commit()
        return RedirectResponse(
            url=f"{FRONTEND_URL}/payment-result?status=failed&reason=cancelled"
        )

    # تایید پرداخت از زیبال
    result = zibal_verify_payment(trackId)

    if not result["ok"]:
        pr.status = "rejected"
        pr.admin_note = f"خطای تایید: {result['error']}"
        session.add(pr)
        session.commit()
        return RedirectResponse(
            url=f"{FRONTEND_URL}/payment-result?status=failed&reason=verify_failed"
        )

    # 🔒 مبلغ پرداخت‌شده باید با مبلغ ثبت‌شده در سرور یکی باشد (ریال = تومان × ۱۰)
    paid_rial = result.get("amount")
    if paid_rial is None:
        logger.warning(f"[Zibal] مبلغ در پاسخ verify نبود (trackId={trackId})")
    elif int(paid_rial) != int(pr.amount or 0) * 10:
        pr.status = "rejected"
        pr.admin_note = (
            f"⚠️ مبلغ پرداختی ({paid_rial} ریال) با مبلغ مورد انتظار "
            f"({int(pr.amount or 0) * 10} ریال) یکی نیست. نیاز به بررسی دستی."
        )
        session.add(pr)
        session.commit()
        logger.error(f"[Zibal] amount mismatch trackId={trackId} paid={paid_rial}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/payment-result?status=failed&reason=amount_mismatch"
        )

    # 🔴 ثبت کد پیگیری
    ref_id = str(result.get("ref_id") or trackId)
    pr.status = "approved"
    pr.zibal_ref_id = ref_id
    pr.reviewed_at = datetime.now(timezone.utc)
    pr.reviewed_by = "zibal_gateway"

    # 🔴 فعال‌سازی یا رزرو با تابع مشترک
    activation = activate_or_reserve_subscription(session, pr.user_id, pr.plan)

    user_obj = session.get(User, pr.user_id)

    if not activation["ok"]:
        # 🔴 پرداخت موفق ولی فعال‌سازی ناموفق!
        pr.status = "rejected"
        pr.admin_note = (
            f"⚠️ پرداخت موفق ولی فعال‌سازی ناموفق: {activation['error']}. "
            f"نیاز به بررسی و عودت وجه دارد. Ref: {ref_id}"
        )
        session.add(pr)
        session.commit()

        # 🔴 اطلاع فوری به ادمین
        try:
            from api.routers.admin_ws import notify_admins

            await notify_admins(
                {
                    "type": "payment_activation_failed",
                    "user_phone": user_obj.phone if user_obj else "?",
                    "amount": pr.amount,
                    "ref_id": ref_id,
                    "reason": activation["error"],
                    "message": (
                        f"🚨 پرداخت موفق ولی فعال‌سازی ناموفق!\n"
                        f"کاربر: {user_obj.phone if user_obj else '?'}\n"
                        f"مبلغ: {pr.amount:,} تومان\n"
                        f"کد پیگیری: {ref_id}\n"
                        f"دلیل: {activation['error']}"
                    ),
                }
            )
        except Exception as e:
            logger.warning(f"[Notify] WebSocket admin failed: {e}")

        return RedirectResponse(
            url=f"{FRONTEND_URL}/payment-result?status=failed&reason={activation.get('reason', 'unknown')}"
        )

    # 🔴 فعال‌سازی موفق
    session.add(pr)
    session.commit()

    # ارسال پیامک موفقیت
    try:
        if user_obj and activation.get("new_sub_end"):
            send_subscription_activated_sms(
                user_obj.phone,
                activation["plan_info"]["title"],
                activation["new_sub_end"],
            )
    except Exception:
        pass

    return RedirectResponse(
        url=f"{FRONTEND_URL}/payment-result?status=success&ref={ref_id}"
    )


# ═══════════════════════════════════════════════════════════
# ۶. درخواست دستی (کارت به کارت)
# ═══════════════════════════════════════════════════════════
@router.post("/request")
async def create_manual_payment_request(
    req: PaymentRequestCreate,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # وضعیت اشتراک‌های منقضی/رزروهای سررسیدشده را قبل از اعتبارسنجی همگام کن.
    if sync_subscription_status(session, user.id):
        session.commit()

    # 🔴 چک: کاربر از قبل رزرو داره؟
    existing_reserved = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "reserved")
    ).first()

    if existing_reserved:
        raise HTTPException(
            status_code=400,
            detail="شما یک اشتراک رزرو دارید. ابتدا آن را مصرف کنید.",
        )

    # 🔴 چک سقف ۳۶۵ روز
    current_sub = get_current_paid_subscription(session, user.id)

    if current_sub and current_sub.end_date and current_sub.plan != "free":
        now = datetime.now(timezone.utc)
        end = current_sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        days_left = math.ceil((end - now).total_seconds() / 86400)
        new_plan_days = PLANS.get(req.plan, {}).get("days", 0)

        if end > now and days_left + new_plan_days > 365:
            raise HTTPException(
                400,
                detail=f"مجموع اشتراک شما بیش از ۳۶۵ روز می‌شود (فعلی: {days_left} روز + جدید: {new_plan_days} روز)",
            )

    # 🔴 چک درخواست pending قبلی
    existing = session.exec(
        select(PaymentRequest)
        .where(PaymentRequest.user_id == user.id)
        .where(PaymentRequest.status == "pending")
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="شما یک درخواست در حال بررسی دارید")

    ip = request.client.host if request.client else "نامشخص"
    user_agent = request.headers.get("user-agent", "نامشخص")

    server_price = _get_server_price(session, req.plan)
    pr = PaymentRequest(
        user_id=user.id,
        plan=req.plan,
        amount=server_price,
        plan_price_at_purchase=server_price,
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
