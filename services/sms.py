"""
services/sms.py
ارسال پیامک از فراز — با پکیج رسمی + فال‌بک برای تست لوکال
"""

import logging
from farazsms import FarazSMS, FarazError
from api.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)


def send_otp_sms(phone: str, code: str) -> bool:
    """ارسال کد OTP با پترن فراز"""
    if not settings.FARAZ_API_KEY or not settings.FARAZ_PATTERN_CODE:
        logger.warning(f"[SMS] ⚠️ تنظیمات فراز کامل نیست. کد تست برای {phone}: {code}")
        return True

    try:
        sms = FarazSMS(settings.FARAZ_API_KEY.strip())
        sms.send_pattern(
            settings.FARAZ_PATTERN_CODE.strip(), phone.strip(), {"code": code}
        )
        logger.info(f"[SMS] ✅ فراز → {phone} — ارسال موفق")
        return True

    except FarazError as e:
        # ⚠️ فال‌بک: اگه پترن تایید نشده بود، کد رو چاپ کن تا بتونی تست کنی
        logger.error(f"[SMS] ❌ خطای فراز: status={e.status} body={e.body}")
        logger.warning(f"[SMS] 🔧 کد تست برای {phone}: {code}")  # ⬅️ این خط اضافه شد
        return False
    except Exception as e:
        logger.exception(f"[SMS] ❌ خطای غیرمنتظره: {e}")
        logger.warning(f"[SMS] 🔧 کد تست برای {phone}: {code}")
        return False


def send_subscription_activated_sms(
    phone: str, plan_name: str, end_date: datetime
) -> bool:
    if not settings.FARAZ_API_KEY:
        return True

    # کد پترن تایید اشتراک که از پنل فراز گرفتی
    pattern_code = "UbxTobUlAT"

    try:
        sms = FarazSMS(settings.FARAZ_API_KEY.strip())
        date_str = end_date.strftime("%Y/%m/%d")

        # ارسال متغیرها طبق پترن %plan% و %date%
        sms.send_pattern(
            pattern_code, phone.strip(), {"plan": plan_name, "date": date_str}
        )
        logger.info(f"[SMS] ✅ پیامک تایید اشتراک به {phone} ارسال شد")
        return True
    except Exception as e:
        logger.error(f"[SMS] ❌ خطا در ارسال پیامک تایید: {e}")
        return False
