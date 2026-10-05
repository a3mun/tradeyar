"""
api/deps.py
Dependencyهای مشترک FastAPI — احراز هویت و rate limiting
============================================================
باگ ۴: عملیات مخرب (DELETE /backtest/reset) نیازمند هدر ``X-API-Key``
است. تا فاز ۷ که JWT کامل می‌آید، این لایه‌ی ساده کافی است.

اصول طراحی:
  1. **fail-closed**: اگر ``ADMIN_API_KEY`` روی سرور تنظیم نشده باشد،
     عملیات admin کاملاً مسدود می‌شود (۵۰۳) — نه اینکه باز بماند.
  2. **مقایسه‌ی زمان-ثابت**: با ``secrets.compare_digest`` تا از
     timing attack جلوگیری شود.
  3. **audit log**: هر تلاش (موفق یا ناموفق) لاگ می‌شود.
"""

import logging
import secrets
import time
from collections import defaultdict
from typing import Optional

from fastapi import Header, HTTPException, Request, status

from api.config import settings

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
    """
    محافظت از endpointهای مخرب با هدر ``X-API-Key``.

    Raises:
        HTTPException 503: اگر ADMIN_API_KEY روی سرور تنظیم نشده باشد
        HTTPException 401: اگر هدر غایب باشد
        HTTPException 403: اگر کلید اشتباه باشد

    Returns:
        True در صورت موفقیت — تا به‌عنوان dependency استفاده شود.
    """
    ip = _client_ip(request)
    path = request.url.path

    # ─── fail-closed: بدون کلید تنظیم‌شده، هیچ‌کس دسترسی ندارد ───
    if not settings.ADMIN_API_KEY:
        logger.error(
            f"[Auth] ⛔ ADMIN_API_KEY تنظیم نشده — "
            f"دسترسی به {path} مسدود شد (ip={ip})"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "عملیات مدیریتی روی این سرور غیرفعال است. "
                "ادمین باید ADMIN_API_KEY را تنظیم کند."
            ),
        )

    # ─── هدر غایب ───
    if not x_api_key:
        logger.warning(f"[Auth] ⚠️ درخواست بدون X-API-Key: {path} (ip={ip})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="هدر X-API-Key لازم است",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    # ─── مقایسه‌ی زمان-ثابت ───
    if not secrets.compare_digest(x_api_key, settings.ADMIN_API_KEY):
        logger.warning(f"[Auth] ⛔ کلید اشتباه برای {path} (ip={ip})")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="کلید API نامعتبر است",
        )

    logger.info(f"[Auth] ✅ دسترسی admin تأیید شد: {path} (ip={ip})")
    return True


# ═══════════════════════════════════════════════════════════
# ۲. Rate limiting ساده (in-memory)
# ═══════════════════════════════════════════════════════════
# ⚠️ برای چند worker باید به Redis منتقل شود (فاز ۷).
_buckets: dict[str, list[float]] = defaultdict(list)


def rate_limit(key: str, limit: int, window_sec: int = 60) -> None:
    """
    محدودیت نرخ sliding-window.

    Args:
        key: کلید باکت (معمولاً "endpoint:ip")
        limit: حداکثر تعداد در بازه
        window_sec: طول بازه به ثانیه

    Raises:
        HTTPException 429 با هدر Retry-After
    """
    now = time.time()
    bucket = _buckets[key]

    # ─── پاک‌سازی پنجره ───
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
    """پاک‌سازی کامل باکت‌ها — برای تست"""
    _buckets.clear()


def rate_limit_for(request: Request, scope: str, limit: int, window_sec: int = 60):
    """میان‌بر: rate_limit با کلید ساخته‌شده از IP و scope"""
    rate_limit(f"{scope}:{_client_ip(request)}", limit, window_sec)
