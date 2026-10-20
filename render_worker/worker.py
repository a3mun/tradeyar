import os
import logging
import requests
from fastapi import FastAPI
from dotenv import load_dotenv
from notifier import notify_signal

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

API_URL = "https://api.trademun.ir/backtest/history?limit=1"
last_signal_id = None

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
            # استفاده از تابع کامل notifier
            notify_signal(latest)
    except Exception as e:
        logger.error(f"API error: {e}")

@app.get("/ping")
def ping():
    check_new_signal()
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Worker is running!"}
