import logging

logging.basicConfig(level=logging.DEBUG)

from services.analyzer_service import analyze
from api.models import SignalLog
from sqlmodel import Session, select
from api.database import engine

with Session(engine) as s:
    for r in s.exec(select(SignalLog)).all():
        s.delete(r)
    s.commit()
print("DB cleared.")

print("--- First analyze (ETH-USD, 1h) ---")
r1 = analyze(ticker="ETH-USD", source="nobitex", tf_name="۱ ساعت", skip_record=False)
print(f"Signal: {r1.get('signal') if r1 else 'None'}")
print(f"Confidence: {r1.get('confidence') if r1 else 0}")
with Session(engine) as s:
    count1 = len(s.exec(select(SignalLog)).all())
print(f"Count after first: {count1}")

print("--- Second analyze (cache) ---")
r2 = analyze(ticker="ETH-USD", source="nobitex", tf_name="۱ ساعت", skip_record=False)
with Session(engine) as s:
    count2 = len(s.exec(select(SignalLog)).all())
print(f"Count after second: {count2}")
