"""
api/routers/ai.py
پروکسی OpenRouter مستقیم — برای مشاور هوشمند (فاز ۱۵)
============================================================
"""

import logging
import os
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool  # 🔴 برای جلوگیری از بلاک شدن سرور
from pydantic import BaseModel

from api.deps import rate_limit_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"
DEFAULT_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """تو یه دوست معامله‌گر باتجربه هستی که به رفیقت مشاوره می‌دی.

قواعد:
- لحن دوستانه، ولی حرفه‌ای (نه خشک، نه بچه‌گانه)
- فارسی عامیانه ساده بدون اصطلاحات پیچیده
- خیلی توضیح نده و خلاصه بگو و نهایت 250 کلمه جمعش کن
- توصیه‌محور: آخرش یه جمله «الان چیکار کنم؟»
- اگه سیگنال ضعیفه، صریح بگو «الان نخر، صبر کن»
- اگه تله‌ای هست، هشدار بده
- از اعداد مشخص استفاده کن (قیمت، درصد)
- قبل از دادن پیام کامل پاسخ رو دبل چک کن که مفهوم باشه از نظر نگارش فارسی
- **هیچ‌وقت از markdown مثل ** یا ## استفاده نکن**"""


class AIRequest(BaseModel):
    data: str
    api_key: Optional[str] = None


class AIResponse(BaseModel):
    ok: bool
    response: str
    error: Optional[str] = None


# 🔴 دیکشنری پیام‌های خطای کاربرپسند
def _get_friendly_error(status_code: int, raw_error: str = "") -> str:
    if status_code == 401:
        return "کلید API نامعتبر است. لطفاً کلید شخصی خودت رو توی تنظیمات وارد کن."
    if status_code == 402:
        return "اعتبار حساب تموم شده. لطفاً از کلید شخصی خودت استفاده کن."
    if status_code == 403:
        return "دسترسی مسدود شده (محدودیت IP). لطفاً از روش «کپی داده خام» استفاده کن."
    if status_code == 404:
        return "مدل در دسترس نیست. لطفاً چند دقیقه دیگه دوباره تلاش کن."
    if status_code == 429:
        return "سهمیه رایگان امروز تموم شده. لطفاً از کلید شخصی خودت استفاده کن یا فردا دوباره تلاش کن."
    if status_code in (500, 502, 503):
        return "سرویس OpenRouter موقتاً در دسترس نیست. لطفاً دوباره تلاش کن."

    return f"خطای OpenRouter ({status_code}): {raw_error[:100]}"


def _sync_call_openrouter(api_key: str, data: str) -> AIResponse:
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": data},
        ],
        "temperature": 0.7,
        "max_tokens": 500,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://trademun.ir",
        "X-Title": "Trademun",
    }

    try:
        resp = requests.post(OPENROUTER_API, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.warning(
                f"[AI] OpenRouter error {resp.status_code}: {resp.text[:200]}"
            )
            try:
                raw_err = resp.json().get("error", {}).get("message", "")
            except Exception:
                raw_err = f"HTTP {resp.status_code}"

            return AIResponse(
                ok=False,
                response="",
                error=_get_friendly_error(resp.status_code, raw_err),
            )

        data_json = resp.json()
        content = (
            data_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        if not content or not content.strip():
            return AIResponse(
                ok=False,
                response="",
                error="مدل رایگان پاسخ خالی داد. لطفاً دوباره تلاش کن یا از کلید شخصی خودت استفاده کن.",
            )
        return AIResponse(ok=True, response=content.strip())

    except requests.exceptions.Timeout:
        return AIResponse(
            ok=False,
            response="",
            error="درخواست زمان‌بر شد. لطفاً دوباره تلاش کن یا از کلید شخصی خودت استفاده کن.",
        )
    except requests.exceptions.ConnectionError:
        return AIResponse(
            ok=False,
            response="",
            error="اتصال به OpenRouter برقرار نشد. لطفاً اینترنتت رو چک کن.",
        )
    except Exception as e:
        logger.exception("[AI] خطا")
        return AIResponse(ok=False, response="", error=f"خطای غیرمنتظره: {str(e)[:50]}")


@router.post("", response_model=AIResponse)
async def ai_analyze(req: AIRequest, request: Request):
    rate_limit_for(request, "ai", limit=20, window_sec=60)

    api_key = req.api_key or DEFAULT_KEY
    if not api_key:
        return AIResponse(
            ok=False,
            response="",
            error="کلید API موجود نیست. لطفاً کلید شخصی خودت رو توی تنظیمات وارد کن.",
        )

    if not req.data or len(req.data.strip()) < 50:
        return AIResponse(
            ok=False,
            response="",
            error="داده‌ای برای تحلیل دریافت نشد. لطفاً صبر کن تا داده‌ها لود بشن.",
        )

    # 🔴 اجرای درخواست در threadpool (جلوگیری از بلاک شدن سرور)
    return await run_in_threadpool(_sync_call_openrouter, api_key, req.data)
