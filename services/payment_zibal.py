import logging
import requests
from api.config import settings

logger = logging.getLogger(__name__)

ZIBAL_GATEWAY_URL = "https://gateway.zibal.ir"


def create_payment_request(amount: int, description: str, mobile: str, order_id: str):
    """درخواست پرداخت جدید در زیبال"""
    url = f"{ZIBAL_GATEWAY_URL}/v1/request"
    payload = {
        "merchant": settings.ZIBAL_MERCHANT,
        "amount": amount,
        "callbackUrl": settings.ZIBAL_CALLBACK_URL,
        "description": description,
        "mobile": mobile,
        "orderId": order_id,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()

        if data.get("result") == 100 and data.get("trackId"):
            track_id = data["trackId"]
            payment_url = f"{ZIBAL_GATEWAY_URL}/start/{track_id}"
            return {"ok": True, "track_id": track_id, "payment_url": payment_url}

        error_msg = data.get("message", "خطا در ارتباط با درگاه زیبال")
        logger.error(
            f"[Zibal] Request failed: result={data.get('result')}, message={error_msg}"
        )
        return {"ok": False, "error": error_msg}
    except Exception as e:
        logger.error(f"[Zibal] Request error: {e!r}")
        return {"ok": False, "error": "خطا در ارتباط با درگاه"}


def verify_payment(track_id: str):
    """تایید پرداخت زیبال بعد از بازگشت کاربر"""
    url = f"{ZIBAL_GATEWAY_URL}/v1/verify"
    payload = {
        "merchant": settings.ZIBAL_MERCHANT,
        "trackId": track_id,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()

        if data.get("result") == 100 or data.get("result") == 201:
            return {
                "ok": True,
                "ref_id": data.get("refNumber") or track_id,  # 🔴 fallback
                "amount": data.get("amount"),
                "message": "پرداخت با موفقیت تایید شد",
            }

        error_msg = data.get("message", "پرداخت ناموفق یا قبلاً تایید شده")
        logger.error(
            f"[Zibal] Verify failed: result={data.get('result')}, message={error_msg}"
        )
        return {"ok": False, "error": error_msg}
    except Exception as e:
        logger.error(f"[Zibal] Verify error: {e!r}")
        return {"ok": False, "error": "خطا در تایید پرداخت"}
