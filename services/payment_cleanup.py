"""
services/payment_cleanup.py
پاکسازی تراکنش‌های pending زیبال که بعد از ۱۵ دقیقه تایید نشدن
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select

from api.database import engine
from api.models import PaymentRequest

logger = logging.getLogger(__name__)


def cleanup_stale_zibal_payments():
    """تراکنش‌های pending زیبال که بیش از ۱۵ دقیقه ازشون گذشته رو rejected کن"""
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=15)

        stale = session.exec(
            select(PaymentRequest)
            .where(PaymentRequest.payment_method == "zibal")
            .where(PaymentRequest.status == "pending")
        ).all()

        cleaned = 0
        for pr in stale:
            # 🔴 created_at ممکنه timezone نداشته باشه (SQLite)
            created = pr.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            if created < cutoff:
                # 🔴 قبل از reject، با زیبال چک کن که آیا واقعاً پرداخت شده یا نه
                from services.payment_zibal import verify_payment

                if pr.zibal_track_id:
                    result = verify_payment(pr.zibal_track_id)
                    if result["ok"]:
                        # 🔴 پرداخت واقعاً موفق بوده ولی کال‌بک نرسیده!
                        logger.warning(
                            f"[Cleanup] تراکنش {pr.id} واقعاً پرداخت شده ولی pending مونده. "
                            f"Ref: {result.get('ref_id')}"
                        )
                        pr.status = "approved"
                        pr.zibal_ref_id = str(result.get("ref_id") or pr.zibal_track_id)
                        pr.admin_note = "تایید خودکار توسط cleanup (کال‌بک نرسیده بود)"
                        # 🔴 فعال‌سازی اشتراک
                        from services.subscription_service import (
                            activate_or_reserve_subscription,
                        )

                        activation = activate_or_reserve_subscription(
                            session, pr.user_id, pr.plan
                        )
                        if not activation["ok"]:
                            logger.error(
                                f"[Cleanup] فعال‌سازی ناموفق برای {pr.id}: {activation['error']}"
                            )
                        session.add(pr)
                        cleaned += 1
                        continue

                # 🔴 پرداخت واقعاً انجام نشده بود
                pr.status = "rejected"
                pr.admin_note = "پرداخت در درگاه زیبال تایید نشد (بیش از ۱۵ دقیقه)"
                session.add(pr)
                cleaned += 1

        if cleaned:
            session.commit()
            logger.info(f"[Cleanup] {cleaned} تراکنش pending زیبال پردازش شد")
