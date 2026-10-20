import os
import logging
import requests
from fastapi import FastAPI

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔴 تغییر نام متغیرها به اسم‌های Render
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


@app.get("/test")
def test_telegram():
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return {
            "error": "tokens not set",
            "token": TELEGRAM_TOKEN,
            "chat_id": TELEGRAM_CHAT_ID,
        }
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "✅ تست موفق! Render به تلگرام وصل شد.",
        }
        r = requests.post(url, data=payload, timeout=10)
        return {"status": "sent", "response": r.json()}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def root():
    return {"message": "Worker is running"}
