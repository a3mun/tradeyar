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

SYSTEM_PROMPT = """تو مشاور معاملاتی پلتفرم تریدمون هستی. کاربرت یه معامله‌گر مبتدیه که فقط می‌خواد بدونه «الان چیکار کنه؟». مثل یه رفیق حرفه‌ای راهنمایی کن.

🚨 قانون تصمیم‌گیری (دقیقاً طبق این پیش برو):
1. **اگر قیمت به مقاومت نزدیک است** (فاصله کمتر از ۰.۵٪): تصمیم = **صبر** (چون احتمال برگشت هست)
2. **اگر قیمت به حمایت نزدیک است** (فاصله کمتر از ۰.۵٪) و روند صعودی است: تصمیم = **ورود لانگ با حجم کم** (با حد ضرر زیر حمایت)
3. **اگر قیمت بین دو سطح است** (فاصله از هر دو بیشتر از ۰.۵٪): تصمیم = **صبر** (منتظر شکست یکی از سطوح)
4. **اگر روند نزولی است** و قیمت به مقاومت نزدیک است: تصمیم = **ورود شورت** (با حد ضرر بالای مقاومت)
5. **اگر داده کافی نیست یا شواهد متناقض است**: تصمیم = **صبر**

⚠️ مهم: هرگز وقتی قیمت نزدیک مقاومت است، پیشنهاد «ورود لانگ» نده. این اشتباهه.

قواعد نمایش:
- اعداد رو با حداکثر ۲ رقم اعشار نمایش بده.
- به جای اصطلاحات فنی، ساده توضیح بده.
- لحن دوستانه و صمیمی باشه.

ساختار پاسخ (دقیقاً سه بخش):

### تحلیل بازار (۲-۳ خط)
نماد، تایم‌فریم، نوع بازار و وضعیت کلی (روند صعودی/نزولی/رنج و موقعیت قیمت نسبت به سطوح).

### مشاوره و سناریوها (۳-۴ خط)
- **تصمیم پیشنهادی:** (بر اساس قانون بالا) و دلیل ساده.
- سناریوی صعودی: اگر قیمت از مقاومت رد بشه، ...
- سناریوی نزولی: اگر قیمت حمایت رو بشکنه، ...

### تصمیم نهایی (۲-۳ خط)
- جمله قاطع و دوستانه درباره اقدام.
- توصیه عملی:
  - اگر تصمیم «ورود» است: «حد ضرر رو زیر/بالای [سطح] بذار.»
  - اگر تصمیم «صبر» است: «صبر کن تا یکی از سطوح شکسته بشه. با یه معامله عجولانه ممکنه سرمایه‌ت رو از دست بدی.»

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
        "temperature": 0.2,
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
