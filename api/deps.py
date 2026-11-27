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
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select

from api.auth import _bearer, decode_token, get_current_user, normalize_phone
from api.config import settings
from api.database import engine, get_session
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


# ═══════════════════════════════════════════════════════════
# ۴. 🔒 قفل دسترسی — ورود + اشتراک معتبر (شامل دوره رایگان)
# ═══════════════════════════════════════════════════════════
# با ENFORCE_AUTH=false هیچ‌چیز بسته نمی‌شود (رفتار قبلی).
# قاعده‌ی دسترسی دقیقاً همان منطق /subscription/my است:
# هر ردیف اشتراک با status=active که شروعش گذشته و پایانش نرسیده باشد
# (پلن free هم حساب می‌شود) → دسترسی دارد. ادمین همیشه دسترسی دارد.
SUBSCRIPTION_REQUIRED_DETAIL = (
    "SUBSCRIPTION_REQUIRED: اشتراک شما پایان یافته است. "
    "برای ادامه، به صفحه اشتراک بروید."
)

_ACCESS_CACHE_TTL = 60  # ثانیه — فقط نتیجه‌ی «مجاز» کش می‌شود
_access_cache: dict[int, float] = {}


def clear_access_cache() -> None:
    _access_cache.clear()


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def user_has_access(user: User, session: Session) -> bool:
    if user.is_admin:
        return True

    now_ts = time.time()
    cached_until = _access_cache.get(user.id)
    if cached_until and cached_until > now_ts:
        return True

    from services.subscription_service import sync_subscription_status

    now = datetime.now(timezone.utc)
    if sync_subscription_status(session, user.id, now):
        session.commit()

    rows = session.exec(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .where(Subscription.status == "active")
    ).all()

    best_remaining: Optional[float] = None
    allowed = False
    for sub in rows:
        start = _as_utc(sub.start_date)
        end = _as_utc(sub.end_date)
        if start is not None and start > now:
            continue
        if end is not None and end <= now:
            continue
        allowed = True
        remaining = float("inf") if end is None else (end - now).total_seconds()
        if best_remaining is None or remaining > best_remaining:
            best_remaining = remaining

    if allowed:
        if len(_access_cache) > 5000:
            _access_cache.clear()
        ttl = min(_ACCESS_CACHE_TTL, best_remaining if best_remaining is not None else _ACCESS_CACHE_TTL)
        _access_cache[user.id] = now_ts + ttl
    return allowed


def require_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """dependency مشترک مسیرهای تحلیل/داده. (sync → در threadpool اجرا می‌شود)"""
    if not settings.ENFORCE_AUTH:
        return None
    user = get_current_user(credentials, session)  # 401 اگر وارد نشده
    if not user_has_access(user, session):
        raise HTTPException(status_code=403, detail=SUBSCRIPTION_REQUIRED_DETAIL)
    return user


def ws_access_code(token: str) -> int:
    """برای WebSocket: 0=مجاز · 4401=ورود لازم/توکن نامعتبر · 4403=اشتراک لازم"""
    if not settings.ENFORCE_AUTH:
        return 0
    if not token:
        return 4401
    try:
        payload = decode_token(token)
        phone = normalize_phone(payload.get("sub", ""))
        with Session(engine) as session:
            user = session.exec(select(User).where(User.phone == phone)).first()
            if not user or not user.is_active:
                return 4401
            return 0 if user_has_access(user, session) else 4403
    except Exception:
        return 4401
