import os
from pathlib import Path

# مسیر فایل دیتابیس
DB_FILE = Path(__file__).parent / "data" / "trademun.db"

if DB_FILE.exists():
    os.remove(DB_FILE)
    print(f"✅ دیتابیس {DB_FILE} با موفقیت پاک شد.")
else:
    print("⚠️ فایل دیتابیس پیدا نشد (شاید از قبل پاک شده).")

print("🚀 دیتابیس در اولین اجرای بک‌اند به صورت خودکار ساخته می‌شود.")
