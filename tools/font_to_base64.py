"""
tools/font_to_base64.py
تبدیل فونت به Base64 برای inline در CSS
"""

import base64
from pathlib import Path

# مسیر فایل فونت
FONT_PATH = Path(__file__).parent.parent / "fonts" / "IRANYekanXVF.woff2"

if not FONT_PATH.exists():
    print(f"❌ فایل پیدا نشد: {FONT_PATH}")
    print("لطفاً فایل IRANYekanXVF.woff2 رو توی پوشه fonts/ بذار.")
else:
    with open(FONT_PATH, "rb") as f:
        font_data = f.read()

    b64 = base64.b64encode(font_data).decode("utf-8")

    # ذخیره در فایل متنی
    output_path = Path(__file__).parent.parent / "fonts" / "IRANYekanXVF.b64.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(b64)

    print(f"✅ فایل Base64 ساخته شد: {output_path}")
    print(f"📏 حجم اصلی: {len(font_data) / 1024:.1f} KB")
    print(f"📏 حجم Base64: {len(b64) / 1024:.1f} KB")