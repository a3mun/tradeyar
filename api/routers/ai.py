"""
api/routers/ai.py
پروکسی OpenRouter — برای مشاور هوشمند (فاز ۱۵)
============================================================
"""

import logging
import os
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.deps import rate_limit_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI"])

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openrouter/free"
DEFAULT_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "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",
)

SYSTEM_PROMPT = """تو یه دوست معامله‌گر باتجربه هستی که به رفیقت مشاوره می‌دی.

قواعد:
- لحن خودمونی و صمیمی، ولی حرفه‌ای (نه خشک، نه بچه‌گانه)
- فارسی دوستانه ساده بدون اصطلاحات پیچیده
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


def _get_friendly_error(status_code: int, raw_error: str = "") -> str:
    """تبدیل کدهای خطا به پیام فارسی و پیشنهاد راه‌حل"""
    if status_code == 400:
        return "درخواست نامعتبر است. لطفاً از روش کپی داده خام استفاده کن."
    if status_code == 401:
        return "کلید API نامعتبر است. لطفاً کلید شخصی خودت رو وارد کن یا از روش کپی داده خام استفاده کن."
    if status_code == 402:
        return "اعتبار حساب تموم شده. لطفاً از کلید شخصی استفاده کن یا از روش کپی داده خام استفاده کن."
    if status_code == 403:
        return "دسترسی مسدود شده (محدودیت IP). لطفاً از روش کپی داده خام استفاده کن."
    if status_code == 429:
        return "سهمیه رایگان امروز تموم شده. لطفاً از کلید شخصی استفاده کن یا از روش کپی داده خام استفاده کن."
    if status_code in (500, 502, 503):
        return "سرویس OpenRouter موقتاً در دسترس نیست. لطفاً دوباره تلاش کن یا از روش کپی داده خام استفاده کن."

    return f"خطای OpenRouter ({status_code}): {raw_error[:100]}. لطفاً از روش کپی داده خام استفاده کن."


@router.post("", response_model=AIResponse)
async def ai_analyze(req: AIRequest, request: Request):
    rate_limit_for(request, "ai", limit=20, window_sec=60)

    api_key = (req.api_key or "").strip() or DEFAULT_KEY
    if not api_key:
        return AIResponse(
            ok=False,
            response="",
            error="کلید API موجود نیست. لطفاً کلید خودت رو توی تنظیمات وارد کن یا از روش کپی داده خام استفاده کن.",
        )

    if not req.data or len(req.data.strip()) < 50:
        return AIResponse(
            ok=False,
            response="",
            error="داده‌ای برای تحلیل دریافت نشد. لطفاً از روش کپی داده خام استفاده کن.",
        )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.data},
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
            raw_err = ""
            try:
                raw_err = resp.json().get("error", {}).get("message", "")
            except Exception:
                raw_err = resp.text[:100]

            logger.warning(f"[AI] OpenRouter error {resp.status_code}: {raw_err}")
            return AIResponse(
                ok=False,
                response="",
                error=_get_friendly_error(resp.status_code, raw_err),
            )

        data = resp.json()

        # استخراج ایمن پاسخ (مدیریت None)
        content = ""
        try:
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                if msg:
                    content = msg.get("content") or ""
        except Exception:
            pass

        if not content or not content.strip():
            logger.warning(f"[AI] پاسخ خالی از مدل.")
            return AIResponse(
                ok=False,
                response="",
                error="مدل رایگان پاسخ خالی داد. لطفاً دوباره تلاش کن یا از روش کپی داده خام استفاده کن.",
            )

        return AIResponse(ok=True, response=content.strip())

    except requests.exceptions.Timeout:
        return AIResponse(
            ok=False,
            response="",
            error="درخواست زمان‌بر شد. لطفاً دوباره تلاش کن یا از روش کپی داده خام استفاده کن.",
        )
    except requests.exceptions.ConnectionError:
        return AIResponse(
            ok=False,
            response="",
            error="اتصال به OpenRouter برقرار نشد. لطفاً اینترنتت رو چک کن یا از روش کپی داده خام استفاده کن.",
        )
    except Exception as e:
        logger.exception("[AI] خطای غیرمنتظره")
        return AIResponse(
            ok=False,
            response="",
            error=f"خطای غیرمنتظره: {str(e)[:50]}. لطفاً از روش کپی داده خام استفاده کن.",
        )
