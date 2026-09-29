"""
core/nobitex_auth.py
اتصال امن به API اختصاصی نوبیتکس — نسخه ۱.۰
============================================================
از کلید API اختصاصی برای:
  - دریافت عمق کامل Order Book
  - OHLCV با کیفیت بالاتر
  - دسترسی به اندپوینت‌های خصوصی

نکته: این ماژول optional هست. اگه کلید نباشه، fallback به public.
"""

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Optional

import requests

NOBITEX_BASE = "https://apiv2.nobitex.ir"
API_KEYS_FILE = Path("api-keys nobitex.txt")
TIMEOUT = 15


# ═══════════════════════════════════════════════════════════
# بارگذاری کلیدها
# ═══════════════════════════════════════════════════════════
_keys_cache: Optional[dict] = None


def load_api_keys() -> Optional[dict]:
    """بارگذاری کلیدهای API از فایل"""
    global _keys_cache
    if _keys_cache is not None:
        return _keys_cache

    try:
        if not API_KEYS_FILE.exists():
            return None

        with open(API_KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        api_key = data.get("apiKey", "")
        secret = data.get("secretKey", "")

        if api_key and secret:
            _keys_cache = {"api_key": api_key, "secret": secret}
            return _keys_cache
    except Exception as e:
        print(f"[NobitexAuth] خطا در بارگذاری کلیدها: {e}")

    return None


def has_api_keys() -> bool:
    return load_api_keys() is not None


# ═══════════════════════════════════════════════════════════
# امضا (Signature) برای درخواست‌های خصوصی
# ═══════════════════════════════════════════════════════════
def _generate_signature(secret: str, message: str) -> str:
    """تولید امضای HMAC-SHA256"""
    try:
        secret_bytes = base64.b64decode(secret)
        message_bytes = message.encode("utf-8")
        signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).digest()
        return base64.b64encode(signature).decode("utf-8")
    except Exception as e:
        print(f"[NobitexAuth] خطا در امضا: {e}")
        return ""


def _get_auth_headers(method: str, url_path: str, body: str = "") -> dict:
    """ساخت هدرهای احراز هویت"""
    keys = load_api_keys()
    if not keys:
        return {}

    try:
        api_key = keys["api_key"]
        secret = keys["secret"]

        # timestamp به میلی‌ثانیه
        timestamp = str(int(time.time() * 1000))
        message = f"{api_key}{timestamp}{method.upper()}{url_path}{body}"

        signature = _generate_signature(secret, message)

        return {
            "Authorization": f"Token {api_key}",
            "x-timestamp": timestamp,
            "x-signature": signature,
            "Content-Type": "application/json",
        }
    except Exception as e:
        print(f"[NobitexAuth] خطا در headers: {e}")
        return {}


# ═══════════════════════════════════════════════════════════
# درخواست احراز هویت‌شده
# ═══════════════════════════════════════════════════════════
def authenticated_get(url_path: str, params: dict = None) -> Optional[dict]:
    """GET با احراز هویت"""
    if not has_api_keys():
        return None

    url = f"{NOBITEX_BASE}{url_path}"
    headers = _get_auth_headers("GET", url_path, "")

    if not headers:
        return None

    try:
        r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[NobitexAuth] Timeout: {url_path}")
    except requests.exceptions.HTTPError as e:
        print(f"[NobitexAuth] HTTP {e.response.status_code}: {url_path}")
    except requests.exceptions.RequestException as e:
        print(f"[NobitexAuth] Request: {e}")
    except ValueError as e:
        print(f"[NobitexAuth] JSON: {e}")
    return None


def authenticated_post(url_path: str, body: dict = None) -> Optional[dict]:
    """POST با احراز هویت"""
    if not has_api_keys():
        return None

    url = f"{NOBITEX_BASE}{url_path}"
    body_str = json.dumps(body or {}, separators=(",", ":"))
    headers = _get_auth_headers("POST", url_path, body_str)

    if not headers:
        return None

    try:
        r = requests.post(url, data=body_str, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        print(f"[NobitexAuth] Timeout: {url_path}")
    except requests.exceptions.HTTPError as e:
        print(f"[NobitexAuth] HTTP {e.response.status_code}: {url_path}")
    except requests.exceptions.RequestException as e:
        print(f"[NobitexAuth] Request: {e}")
    except ValueError as e:
        print(f"[NobitexAuth] JSON: {e}")
    return None


# ═══════════════════════════════════════════════════════════
# دریافت داده‌های اضافی
# ═══════════════════════════════════════════════════════════
def fetch_full_orderbook(symbol: str) -> Optional[dict]:
    """
    دریافت Order Book کامل (۱۰۰ سطح) — فقط با API اختصاصی
    """
    if has_api_keys():
        # اندپوینت خصوصی
        result = authenticated_get(f"/v2/orderbook/{symbol}")
        if result and result.get("status") == "ok":
            return result

    # fallback به عمومی
    try:
        r = requests.get(
            f"{NOBITEX_BASE}/v2/orderbook/{symbol}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def fetch_user_profile() -> Optional[dict]:
    """دریافت پروفایل کاربر (فقط با API اختصاصی)"""
    return authenticated_post("/users/profile")


def fetch_user_orders() -> Optional[dict]:
    """دریافت سفارشات کاربر"""
    return authenticated_post("/users/orders/list")


# ═══════════════════════════════════════════════════════════
# تست
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("تست core/nobitex_auth.py")
    print("=" * 60)
    print()

    keys = load_api_keys()
    if keys:
        print(f"✅ کلیدها بارگذاری شد")
        print(f"   API Key: {keys['api_key'][:20]}...")
        print()
        print("دریافت پروفایل کاربر:")
        profile = fetch_user_profile()
        if profile:
            print(f"   Status: {profile.get('status')}")
        else:
            print("   ❌ خطا (شاید کلید تستی نیست)")
    else:
        print("❌ کلیدها پیدا نشد")
    print()
    print("[OK]")
