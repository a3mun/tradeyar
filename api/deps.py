"""
api/deps.py
Dependencyهای مشترک FastAPI — احراز هویت و rate limiting
============================================================
اصول طراحی:
  1. **fail-closed**: اگر ``ADMIN_API_KEY`` تنظیم نشده باشد، مسدود.
  2. **مقایسه‌ی زمان-ثابت**: با ``secrets.compare_digest``.
  3. **audit log**: هر تلاش لاگ می‌شود.

🔴 فاز ۱۶.۲:
  • require_active_subscription → فقط Pro/Admin
"""

import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel import Session, select

from api.auth import get_current_user
from api.config import settings
from api.database import get_session
from api.models import Subscription, User

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# ۱. احراز هویت ادمین
# ═══════════════════════════════════════════════════════════
def _client_ip(request: Request) -> str:
    """IP واقعی — با احتساب reverse proxy"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def require_admin(
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> bool:
    """محافظت از endpointهای مخرب با هدر X-API-Key."""
    ip = _client_ip(request)
    path = request.url.path

    if not settings.ADMIN_API_KEY:
        logger.error(f"[Auth] ⛔ ADMIN_API_KEY تنظیم نشده — {path} (ip={ip})")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="عملیات مدیریتی روی این سرور غیرفعال است.",
        )

    if not x_api_key:
        logger.warning(f"[Auth] ⚠️ بدون X-API-Key: {path} (ip={ip})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="هدر X-API-Key لازم است",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    if not secrets.compare_digest(x_api_key, settings.ADMIN_API_KEY):
        logger.warning(f"[Auth] ⛔ کلید اشتباه برای {path} (ip={ip})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="کلید API نامعتبر است",
        )

    logger.info(f"[Auth] ✅ دسترسی admin تأیید شد: {path} (ip={ip})")
    return True


# ═══════════════════════════════════════════════════════════
# ۲. Rate limiting ساده
# ═══════════════════════════════════════════════════════════
_buckets: dict[str, list[float]] = defaultdict(list)


def rate_limit(key: str, limit: int, window_sec: int = 60) -> None:
    now = time.time()
    bucket = _buckets[key]

    cutoff = now - window_sec
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)

    if len(bucket) >= limit:
        retry_after = int(bucket[0] + window_sec - now) + 1
        logger.warning(f"[RateLimit] ⚠️ {key} از حد گذشت ({limit}/{window_sec}s)")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"تعداد درخواست زیاد است — {retry_after} ثانیه دیگر تلاش کن",
            headers={"Retry-After": str(retry_after)},
        )

    bucket.append(now)


def reset_rate_limits() -> None:
    _buckets.clear()


def rate_limit_for(request: Request, scope: str, limit: int, window_sec: int = 60):
    rate_limit(f"{scope}:{_client_ip(request)}", limit, window_sec)


# ═══════════════════════════════════════════════════════════
# ۳. 🔴 فاز ۱۶.۲ — بررسی اشتراک فعال (Pro)
# ═══════════════════════════════════════════════════════════
async def require_active_subscription(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    """فقط کاربران با پلن Pro فعال یا ادمین."""
    if user.is_admin:
        return user

    sub = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.created_at.desc())
    ).first()

    if not sub:
        raise HTTPException(
            status_code=403,
            detail="این بخش نیازمند اشتراک فعال است. برای تهیه، به صفحه اشتراک بروید.",
        )

    if sub.plan == "free":
        raise HTTPException(
            status_code=403,
            detail="این بخش نیازمند اشتراک حرفه‌ای است. برای ارتقا، به صفحه اشتراک بروید.",
        )

    if sub.end_date:
        end = sub.end_date
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=403,
                detail="اشتراک شما منقضی شده است. برای تمدید، به صفحه اشتراک بروید.",
            )

    return user
