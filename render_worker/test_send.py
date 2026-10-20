# render_worker/test_send.py
from notifier import notify_signal

test_data = {
    "ticker": "TEST-USD",
    "source": "nobitex",
    "price": 100,
    "tp": 110,
    "sl": 90,
    "signal": "LONG",
    "confidence": 80,
    "rr_net": 2.0,
    "market_type": "futures",
    "risk_profile": "aggressive",
    "tf": "۱ ساعت",
    "regime": "trend",
    "consensus": "strong",
    "had_trap": False,
    "trap_type": None,
    "scenarios": [],
    "override_reason": "",
    "neutral_explain": {},
}
notify_signal(test_data)
print("Test sent!")
