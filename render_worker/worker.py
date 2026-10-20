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
API_URL = "https://api.trademun.ir/backtest/history?limit=1"
last_signal_id = None

def send_to_telegram(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram tokens not set.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
        logger.info("Message sent to Telegram.")
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def check_new_signal():
    global last_signal_id
    try:
        resp = requests.get(API_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            return
        latest = data[0]
        signal_id = latest.get("id")
        if signal_id != last_signal_id:
            last_signal_id = signal_id
            text = (
                f"📊 <b>سیگنال جدید</b>\n"
                f"نماد: <code>{latest.get('ticker')}</code>\n"
                f"وضعیت: {latest.get('signal')}\n"
                f"قیمت: {latest.get('price')}"
            )
            send_to_telegram(text)
    except Exception as e:
        logger.error(f"API error: {e}")

@app.get("/ping")
def ping():
    check_new_signal()
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Worker is running!"}
