import os
import logging
import requests
from fastapi import FastAPI

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_URL = "https://api.trademun.ir/backtest/history?limit=1"

# ذخیره آخرین timestamp برای جلوگیری از ارسال تکراری
last_timestamp = None


def send_to_telegram(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
        logger.info("Message sent to Telegram.")
    except Exception as e:
        logger.error(f"Telegram error: {e}")


def check_new_signal():
    global last_timestamp
    try:
        resp = requests.get(API_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            return
        latest = data[0]
        ts = latest.get("timestamp")
        if ts and ts != last_timestamp:
            last_timestamp = ts
            # ساخت متن ساده برای تلگرام
            text = (
                f"📊 <b>سیگنال جدید | Trademun</b>\n\n"
                f"💎 <b>نماد:</b> <code>{latest.get('ticker')}</code>\n"
                f"🏦 <b>صرافی:</b> {latest.get('source')}\n"
                f"⏱ <b>تایم‌فریم:</b> {latest.get('tf')}\n\n"
                f"🔴 <b>وضعیت:</b> {latest.get('signal')} ({latest.get('confidence')}%)\n"
                f"💰 <b>قیمت ورود:</b> <code>{latest.get('price')}</code>\n"
                f"🎯 <b>حد سود (TP):</b> <code>{latest.get('tp')}</code>\n"
                f"🛡 <b>حد ضرر (SL):</b> <code>{latest.get('sl')}</code>\n\n"
                f"🔗 <b>سایت:</b> trademun.ir · 📢 <b>کانال:</b> @trademun"
            )
            send_to_telegram(text)
    except Exception as e:
        logger.error(f"API error: {e}")


@app.get("/ping")
def ping():
    """این مسیر برای بیدار نگه داشتن Render + چک سیگنال جدید است."""
    check_new_signal()
    return {"status": "ok"}


@app.get("/test")
def test_telegram():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return {"error": "tokens not set"}
    try:
        send_to_telegram("✅ تست موفق! Render به تلگرام وصل شد.")
        return {"status": "sent"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def root():
    return {"message": "Worker is running"}
