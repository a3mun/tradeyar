"""
api/plans.py
تعریف پلن‌های اشتراک — فاز ۱۲
"""

PLANS = {
    "1_month": {
        "id": "1_month",
        "title": "اشتراک یک ماهه",
        "price": 390000,  # ⬅️ قیمت جدید (تخفیف‌خورده)
        "old_price": 590000,
        "days": 30,
    },
    "3_months": {
        "id": "3_months",
        "title": "اشتراک سه ماهه",
        "price": 1050000,
        "old_price": 1770000,
        "days": 90,
    },
    "6_months": {
        "id": "6_months",
        "title": "اشتراک شش ماهه",
        "price": 1870000,
        "old_price": 3540000,
        "days": 180,
    },
    "12_months": {
        "id": "12_months",
        "title": "اشتراک یک ساله",
        "price": 3270000,
        "old_price": 7080000,
        "days": 365,
    },
}
