import logging

logging.basicConfig(level=logging.INFO)

from services.notifier import notify_signal

test_signal = {
    "ticker": "BTC-IRT",
    "source": "nobitex",
    "price": 7000000000,
    "tp": 7500000000,
    "sl": 6800000000,
    "signal": "LONG",
    "confidence": 75,
    "rr_net": 2.5,
    "market_type": "spot",
    "risk_profile": "aggressive",
    "tf": "۱ ساعت",
    "regime": "trend",
    "consensus": "strong",
    "had_trap": False,
    "trap_type": None,
    "scenarios": [
        {"condition": "شکست مقاومت", "action": "خرید با تایید حجم", "probability": 0.65}
    ],
    "override_reason": "",
    "neutral_explain": {},
}

print(">>> تست سیگنال...")
notify_signal(test_signal)
print(">>> Done!")
