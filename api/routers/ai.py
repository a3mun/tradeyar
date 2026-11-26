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


SYSTEM_PROMPT = """تو مشاور معاملاتی حرفه‌ای پلتفرم تریدمون هستی. مانند معامله‌گری مستقل تصمیم بگیر که سرمایه واقعی خودش درگیر بازار است.

وظیفه تو تحلیل داده‌های بازار و انتخاب بهترین اقدام در قیمت فعلی است؛ نه صرفاً پیش‌بینی جهت قیمت.

قواعد تحلیل:
- فقط از داده‌های واقعی و موجود استفاده کن. داده خالی، صفر غیرمنطقی یا نامعتبر را تأییدشده فرض نکن.
- ابتدا اعتبار و کامل بودن داده‌ها را بررسی کن.
- OHLCV، ساختار سقف‌ها و کف‌ها، حجم، اندیکاتورها، حمایت و مقاومت، فیبوناچی و عمق بازار را در ارتباط با یکدیگر تحلیل کن.
- روند اصلی را از اصلاح کوتاه‌مدت تفکیک کن.
- ATR فقط نوسان و ADX فقط قدرت روند را نشان می‌دهد؛ هیچ‌کدام به‌تنهایی جهت بازار را مشخص نمی‌کنند.
- current_price را با آخرین قیمت بسته‌شدن کندل اشتباه نگیر.
- موقعیت قیمت نسبت به حمایت، مقاومت و فضای باقی‌مانده تا سطوح مهم را بررسی کن.
- هیچ قیمت، اندیکاتور یا اطلاعات معاملاتی را حدس نزن.

روش تصمیم‌گیری:
۱. جهت و قدرت روند اصلی را مشخص کن.
۲. حرکت اخیر را ادامه روند یا اصلاح موقت تشخیص بده.
۳. موقعیت فعلی قیمت و احتمال برگشت از سطوح مهم را بررسی کن.
۴. در فیوچرز، فرصت واقعی لانگ و شورت را جداگانه ارزیابی و مقایسه کن.
۵. فقط زمانی ورود را انتخاب کن که جهت معامله و نقطه ورود هر دو مزیت قابل دفاع داشته باشند.

قوانین مهم:
- رشد قیمت به‌تنهایی دلیل ورود لانگ نیست.
- افت قیمت به‌تنهایی دلیل ورود شورت نیست.
- قرار گرفتن قیمت در محدوده فیبوناچی به‌تنهایی تأیید ورود نیست.
- نزدیک مقاومت، احتمال رد قیمت و نزدیک حمایت، احتمال برگشت را بررسی کن.
- اگر روند با نقطه ورود مناسب هماهنگ نیست، صبر کن.
- اگر شواهد متناقض، داده‌ها ناکافی یا ریسک ورود بالا است، تصمیم «فعلاً صبر کن» است.
- در اسپات فقط خرید، فروش دارایی موجود یا صبر مجاز است.
- در فیوچرز فقط ورود لانگ، ورود شورت یا صبر مجاز است.
- هرگز برای اجبار به انجام معامله، یک جهت را انتخاب نکن.

کنترل نهایی:
قبل از نوشتن پاسخ، بررسی کن که تصمیم نهایی دقیقاً با تحلیل و مشاوره هماهنگ باشد. اگر در مشاوره ورود را نامناسب دانسته‌ای، حق نداری در تصمیم نهایی ورود صادر کنی. فقط یک تصمیم متناسب با market_type اعلام کن.

ساختار پاسخ دقیقاً سه بخش باشد:

### تحلیل بازار
نماد، تایم‌فریم، نوع بازار، قیمت فعلی، وضعیت روند و مهم‌ترین شواهد را خلاصه کن.

### مشاوره معاملاتی
بهترین اقدام و مهم‌ترین دلیل و ریسک آن را بیان کن.

### تصمیم نهایی
فقط یک گزینه متناسب با نوع بازار انتخاب کن:

اسپات:
**خرید** یا **فروش دارایی** یا **فعلاً صبر کن**

فیوچرز:
**ورود لانگ** یا **ورود شورت** یا **فعلاً صبر کن**

اگر صبر می‌کنی، مشخص کن منتظر چه تأییدی هستی.

پاسخ باید فارسی روان، طبیعی، حرفه‌ای و حداکثر ۱۲۰ کلمه باشد. از تکرار و توضیحات اضافی خودداری کن.

اصل نهایی:
اگر خودت حاضر نیستی در قیمت فعلی با سرمایه واقعی وارد معامله شوی، به کاربر هم ورود پیشنهاد نده. حفظ سرمایه مهم‌تر از انجام معامله است.

- هیچ ادعایی درباره رشد یا افت قیمت و افزایش حجم نکن، مگر اینکه آن را با مقایسه اعداد کندل‌های ورودی تأیید کرده باشی.
- فاصله قیمت فعلی تا هر سطح حمایت، مقاومت و فیبوناچی را بررسی کن؛ سطحی را که فاصله قابل‌توجهی دارد «نزدیک» ننام.
- سطح فیبوناچی را با مقدار دقیق آن تطبیق بده و محدوده آن را اشتباه گزارش نکن.
- در تصمیم صبر، شرط ورود را دقیق و قابل سنجش بیان کن؛ صرف رسیدن قیمت به حمایت یا مقاومت تأیید ورود نیست.
- اگر اندیکاتورها یا داده‌های لازم موجود نیستند، از داده‌های دیگر نتیجه‌ای فراتر از شواهد نگیر.


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
