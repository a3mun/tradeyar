import os
import logging
import requests
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = "https://api.trademun.ir/signals/unsent"
MARK_SENT_URL = "https://api.trademun.ir/signals/mark-sent"
API_KEY = "38800"


def send_to_telegram(text: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("ok", False)
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return False


def process_unsent_signals():
    try:
        # ۱. گرفتن سیگنال‌های ارسال‌نشده
        resp = requests.get(
            API_URL,
            headers={"X-API-Key": API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        signals = resp.json()

        if not signals:
            return

        for sig in signals:
            signal_id = sig.get("id")
            if not signal_id:
                continue

            text = (
                f"📊 <b>سیگنال جدید | Trademun</b>\n\n"
                f"💎 <b>نماد:</b> <code>{sig.get('ticker')}</code>\n"
                f"🏦 <b>صرافی:</b> {sig.get('source')}\n"
                f"⏱ <b>تایم‌فریم:</b> {sig.get('tf')}\n\n"
                f"🔴 <b>وضعیت:</b> {sig.get('signal')} ({sig.get('confidence')}%)\n"
                f"💰 <b>قیمت ورود:</b> <code>{sig.get('price')}</code>\n"
                f"🎯 <b>حد سود (TP):</b> <code>{sig.get('tp')}</code>\n"
                f"🛡 <b>حد ضرر (SL):</b> <code>{sig.get('sl')}</code>\n\n"
                f"🔗 <b>سایت:</b> trademun.ir · 📢 <b>کانال:</b> @trademun"
            )

            # ۲. ارسال به تلگرام
            if send_to_telegram(text):
                # ۳. علامت‌گذاری به عنوان ارسال‌شده
                try:
                    requests.post(
                        f"{MARK_SENT_URL}/{signal_id}",
                        headers={"X-API-Key": API_KEY},
                        timeout=10,
                    )
                    logger.info(f"Signal {signal_id} sent and marked.")
                except Exception as e:
                    logger.error(f"Mark sent error: {e}")
    except Exception as e:
        logger.error(f"API error: {e}")


@app.get("/ping")
def ping():
    process_unsent_signals()
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Worker is running"}
