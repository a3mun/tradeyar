import sqlite3

conn = sqlite3.connect("data/trademun.db")
c = conn.cursor()

# چک کردن سیگنال‌های PAXG-USD ۳۰ دقیقه
c.execute("""
    SELECT id, ticker, tf, signal, source, timestamp, result, expired, dedup_key 
    FROM signals_log 
    WHERE ticker='PAXG-USD' AND tf='۳۰ دقیقه' 
    ORDER BY id DESC LIMIT 5
""")

print("--- PAXG-USD 30m signals ---")
rows = c.fetchall()
if not rows:
    print("No signals found.")
for row in rows:
    print(
        f"ID: {row[0]}, Signal: {row[2]}, Source: {row[3]}, Time: {row[4]}, Result: {row[5]}, Expired: {row[6]}"
    )
    print(f"  Dedup: {row[7]}")
    print()

conn.close()
