import sqlite3

conn = sqlite3.connect("data/trademun.db")
c = conn.cursor()

# لیست جداول
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("--- Tables ---")
for row in c.fetchall():
    print(row)

# لیست ایندکس‌ها (اسم درست جدول: signals_log)
print("\n--- Indexes on signals_log ---")
c.execute("PRAGMA index_list(signals_log)")
for row in c.fetchall():
    print(row)

# تعداد سیگنال‌ها
print("\n--- Signal Count ---")
c.execute("SELECT COUNT(*) FROM signals_log")
print(f"Total signals: {c.fetchone()[0]}")

# چک کردن ۵ سیگنال آخر (اگر وجود داشت)
print("\n--- Last 5 signals ---")
c.execute(
    "SELECT ticker, tf, signal, source, timestamp FROM signals_log ORDER BY id DESC LIMIT 5"
)
for row in c.fetchall():
    print(row)

conn.close()
