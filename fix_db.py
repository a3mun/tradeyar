import sqlite3
import os

# مسیر دیتابیس
db_path = "data/trademun.db"

if not os.path.exists(db_path):
    print(f"دیتابیس پیدا نشد در مسیر: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        # پیدا کردن ایندکس‌های یکتا
        c.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='signallog' AND sql LIKE '%UNIQUE%'"
        )
        indexes = c.fetchall()

        dropped = False
        for (idx_name,) in indexes:
            if "dedup" in idx_name.lower() or "uq" in idx_name.lower():
                c.execute(f'DROP INDEX IF EXISTS "{idx_name}"')
                print(f"Dropped index: {idx_name}")
                dropped = True

        if not dropped:
            print(
                "هیچ ایندکس یکتایی با نام dedup یا uq پیدا نشد (شاید از قبل پاک شده)."
            )

        conn.commit()
        print("OK: Done.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
