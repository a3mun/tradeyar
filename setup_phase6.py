"""
setup_phase6.py
ساخت خودکار ساختار پوشه‌ها و فایل‌های فاز ۶ (FastAPI Backend)
============================================================
اجرا: python setup_phase6.py
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════
# ساختار فاز ۶
# ═══════════════════════════════════════════════════════════
STRUCTURE = {
    # ─── Backend API ───
    "api": [
        "__init__.py",
        "main.py",
        "config.py",
        "database.py",
        "models.py",
        "schemas.py",
        "scheduler.py",
    ],
    "api/routers": [
        "__init__.py",
        "analyze.py",
        "symbols.py",
        "scan.py",
        "backtest.py",
    ],
    # ─── Services ───
    "services": [
        "__init__.py",
        "analyzer_service.py",
        "data_service.py",
    ],
    # ─── Tests ───
    "tests": [
        "__init__.py",
        "test_analyze.py",
        "test_symbols.py",
    ],
    # ─── Data (اگه نبود) ───
    "data": [],
}


def create_structure():
    print("=" * 60)
    print("ساخت ساختار فاز ۶ — Trademun")
    print("=" * 60)
    print()

    created_dirs = 0
    created_files = 0
    skipped_files = 0

    for folder, files in STRUCTURE.items():
        folder_path = BASE_DIR / folder

        # ساخت پوشه
        if not folder_path.exists():
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 ساخته شد: {folder}/")
            created_dirs += 1
        else:
            print(f"📁 موجود بود: {folder}/")

        # ساخت فایل‌ها
        for file_name in files:
            file_path = folder_path / file_name
            if not file_path.exists():
                file_path.write_text("", encoding="utf-8")
                print(f"   📄 ساخته شد: {folder}/{file_name}")
                created_files += 1
            else:
                print(f"   📄 موجود بود: {folder}/{file_name}")
                skipped_files += 1

    # ─── .env از .env.example ───
    env_example = BASE_DIR / ".env.example"
    env_file = BASE_DIR / ".env"

    if not env_example.exists():
        env_example.write_text(
            "# ═══════════════════════════════════════════════════════════\n"
            "# Trademun — Environment Variables (فاز ۶)\n"
            "# ═══════════════════════════════════════════════════════════\n"
            "\n"
            "# ─── App ───\n"
            "DEBUG=True\n"
            "HOST=0.0.0.0\n"
            "PORT=8000\n"
            "\n"
            "# ─── Database ───\n"
            "# DATABASE_URL=sqlite:///./data/trademun.db\n"
            "# DATABASE_URL=postgresql://user:pass@host/db\n"
            "\n"
            "# ─── CORS ───\n"
            '# CORS_ORIGINS=["http://localhost:3000"]\n'
            "\n"
            "# ─── Scheduler ───\n"
            "SCHEDULER_ENABLED=True\n"
            "BACKTEST_INTERVAL_MINUTES=30\n"
            "\n"
            "# ─── Nobitex (فاز ۷) ───\n"
            "NOBITEX_API_KEY=\n"
            "\n"
            "# ─── Telegram (فاز ۷) ───\n"
            "TELEGRAM_BOT_TOKEN=\n"
            "\n"
            "# ─── JWT (فاز ۷) ───\n"
            "JWT_SECRET=change-me-in-production\n",
            encoding="utf-8",
        )
        print()
        print("📄 ساخته شد: .env.example")
        created_files += 1

    if not env_file.exists():
        env_file.write_text(
            env_example.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        print("📄 ساخته شد: .env (کپی از .env.example)")
        created_files += 1

    # ─── گزارش ───
    print()
    print("=" * 60)
    print(f"✅ پوشه ساخته‌شده: {created_dirs}")
    print(f"✅ فایل ساخته‌شده: {created_files}")
    print(f"⏭  فایل موجود (رد شد): {skipped_files}")
    print("=" * 60)
    print()
    print("🎯 قدم بعدی: منتظر پیام سوم (محتوای فایل‌ها) باش.")


if __name__ == "__main__":
    create_structure()
