"""
api/routers/ai.py
پروکسی Cloudflare Workers AI — برای مشاور هوشمند
============================================================
"""

import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()
from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from api.deps import rate_limit_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])

# 🔴 تنظیمات Cloudflare
CF_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
CF_MODEL = "@cf/meta/llama-3.1-8b-instruct"
CF_API_URL = (
    f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_MODEL}"
)


SYSTEM_PROMPT = """تو یک تحلیل‌گر ارشد و مشاور معاملاتی حرفه‌ای در پلتفرم «تریدمون» هستی.
وظیفه‌ی تو بررسی داده‌های خام تکنیکال (قیمت، اندیکاتورها، سطوح، عمق بازار، سیگنال و...) و ارائه یک تحلیل شفاف، عملی و بدون تعارف به کاربر است.

🔴 قواعد بسیار مهم:
۱. لحن تو باید دوستانه، حرفه‌ای و قاطع باشد (مثل یک تریدر باتجربه که به شاگردش مشاوره می‌دهد).
۲. به هیچ عنوان از Markdown (مثل ** یا # یا -) استفاده نکن. فقط متن ساده و پاراگراف‌بندی شده بنویس.
۳. حداکثر ۳۰۰ کلمه جواب بده. حاشیه نرو و از اعداد زیاد و طولانی استفاده نکن .
۴. از اعداد دقیق موجود در داده‌ها (قیمت، درصد، سطوح) استفاده کن.
۵. اگر سیگنال ضعیف است یا بازار خنثی است، صریح بگو «الان جای ورود نیست، صبر کن».
۶. خروجی تو باید دقیقاً شامل این ۵ بخش باشد:

تیتر حتما بنویس کدوم نماد و چه تایم فریمی رو داری بررسی میکنی
بخش ۱: وضعیت کلی و پیش‌بینی روند (آیا روند صعودی، نزولی یا رنج است؟)
بخش ۲: وضعیت پوزیشن (آیا الان جای ورود به لانگ است یا شورت؟ اگر نه، چرا؟)
بخش ۳: سطوح کلیدی (نزدیک‌ترین حمایت و مقاومت با اعداد نهایت 2 رقم اعشار)
بخش ۴: مدیریت ریسک (حد ضرر پیشنهادی و حد سود، با توجه به R:R موجود)
بخش ۵: جمله پایانی (خلاصه‌ی تصمیم: الان چیکار کنم؟)

در انتها حتما جملاتت رو کامل 2 بار چک کن فارسی و به زبان ساده و گویا باشه و طولانی هم نشه
📊 داده‌های ورودی:
"""


class AIRequest(BaseModel):
    data: str
    api_key: str | None = None


class AIResponse(BaseModel):
    ok: bool
    response: str
    error: str | None = None


def _sync_call_cloudflare(data: str) -> AIResponse:
    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        return AIResponse(
            ok=False, response="", error="تنظیمات Cloudflare در سرور کامل نیست."
        )

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": data},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }

    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(CF_API_URL, json=payload, headers=headers, timeout=30)
        resp_json = resp.json()

        if not resp_json.get("success"):
            errors = resp_json.get("errors", [])
            err_msg = (
                errors[0].get("message", "خطای ناشناخته") if errors else "خطای ناشناخته"
            )
            logger.warning(f"[AI] Cloudflare error: {err_msg}")
            return AIResponse(
                ok=False, response="", error=f"خطای Cloudflare: {err_msg}"
            )

        content = resp_json.get("result", {}).get("response", "")
        if not content or not content.strip():
            return AIResponse(
                ok=False, response="", error="پاسخ خالی از مدل دریافت شد."
            )

        return AIResponse(ok=True, response=content.strip())

    except requests.exceptions.Timeout:
        return AIResponse(
            ok=False, response="", error="درخواست زمان‌بر شد. دوباره تلاش کن."
        )
    except requests.exceptions.ConnectionError:
        return AIResponse(
            ok=False, response="", error="اتصال به Cloudflare برقرار نشد."
        )
    except Exception as e:
        logger.exception("[AI] خطا")
        return AIResponse(ok=False, response="", error=f"خطای غیرمنتظره: {str(e)[:50]}")


@router.post("", response_model=AIResponse)
async def ai_analyze(req: AIRequest, request: Request):
    rate_limit_for(request, "ai", limit=20, window_sec=60)

    if not req.data or len(req.data.strip()) < 50:
        return AIResponse(ok=False, response="", error="داده‌ای برای تحلیل دریافت نشد.")

    return await run_in_threadpool(_sync_call_cloudflare, req.data)
