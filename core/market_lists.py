"""
core/market_lists.py
لیست نمادهای هر بازار — برای اسکنر
نسخه ۱.۰
"""

# ═══════════════════════════════════════════════════════════
# دسته‌بندی بازارها
# ═══════════════════════════════════════════════════════════
MARKET_CATEGORIES = {
    "crypto": {
        "name": "💰 کریپتو",
        "icon": "💰",
        "description": "ارزهای دیجیتال — پرنوسان‌ترین بازار",
        "tickers": [
            ("BTC-USD", "بیت‌کوین"),
            ("ETH-USD", "اتریوم"),
            ("SOL-USD", "سولانا"),
            ("XRP-USD", "ریپل"),
            ("BNB-USD", "بایننس کوین"),
            ("ADA-USD", "کاردانو"),
            ("DOGE-USD", "دوج‌کوین"),
            ("TON-USD", "تون‌کوین"),
            ("AVAX-USD", "آوالانچ"),
            ("DOT-USD", "پولکادات"),
            ("MATIC-USD", "ماتیک"),
            ("LINK-USD", "چین‌لینک"),
            ("LTC-USD", "لایت‌کوین"),
            ("ATOM-USD", "کازماس"),
            ("NEAR-USD", "نیر"),
            ("TRX-USD", "ترون"),
        ],
    },
    "forex": {
        "name": "💱 فارکس",
        "icon": "💱",
        "description": "جفت‌ارزهای اصلی و فرعی",
        "tickers": [
            ("EURUSD=X", "یورو/دلار"),
            ("GBPUSD=X", "پوند/دلار"),
            ("USDJPY=X", "دلار/ین"),
            ("AUDUSD=X", "استرالیا/دلار"),
            ("USDCAD=X", "دلار/کانادا"),
            ("USDCHF=X", "دلار/فرانک"),
            ("NZDUSD=X", "نیوزلند/دلار"),
            ("EURGBP=X", "یورو/پوند"),
            ("EURJPY=X", "یورو/ین"),
            ("GBPJPY=X", "پوند/ین"),
            ("XAUUSD=X", "طلا/دلار"),
            ("XAGUSD=X", "نقره/دلار"),
        ],
    },
    "us_stocks": {
        "name": "📈 سهام آمریکا",
        "icon": "📈",
        "description": "سهام‌های برتر بورس آمریکا",
        "tickers": [
            ("AAPL", "اپل"),
            ("TSLA", "تسلا"),
            ("NVDA", "انویدیا"),
            ("MSFT", "مایکروسافت"),
            ("GOOGL", "گوگل"),
            ("AMZN", "آمازون"),
            ("META", "متا"),
            ("NFLX", "نتفلیکس"),
            ("AMD", "AMD"),
            ("INTC", "اینتل"),
            ("JPM", "جی‌پی مورگان"),
            ("V", "ویزا"),
            ("DIS", "دیزنی"),
            ("BA", "بوئینگ"),
            ("XOM", "اکسون‌موبیل"),
        ],
    },
    "commodities": {
        "name": "🥇 کالا",
        "icon": "🥇",
        "description": "طلا، نقره، نفت، گاز و محصولات کشاورزی",
        "tickers": [
            ("GC=F", "طلا (آتی)"),
            ("SI=F", "نقره"),
            ("BZ=F", "نفت برنت"),
            ("CL=F", "نفت WTI"),
            ("NG=F", "گاز طبیعی"),
            ("HG=F", "مس"),
            ("PL=F", "پلاتین"),
            ("PA=F", "پالادیوم"),
            ("ZC=F", "ذرت"),
            ("ZW=F", "گندم"),
            ("ZS=F", "سویا"),
            ("KC=F", "قهوه"),
        ],
    },
    "indices": {
        "name": "📊 شاخص‌ها",
        "icon": "📊",
        "description": "شاخص‌های اصلی بازارهای جهانی",
        "tickers": [
            ("^GSPC", "S&P 500"),
            ("^IXIC", "نزدک"),
            ("^DJI", "داو جونز"),
            ("^VIX", "VIX (ترس)"),
            ("^FTSE", "FTSE 100"),
            ("^GDAXI", "DAX آلمان"),
            ("^N225", "نیکی ۲۲۵"),
            ("^HSI", "هنگ‌سنگ"),
            ("DX-Y.NYB", "شاخص دلار (DXY)"),
            ("^TNX", "بازده ۱۰ ساله آمریکا"),
        ],
    },
    "iran_stocks": {
        "name": "🇮🇷 سهام ایران",
        "icon": "🇮🇷",
        "description": "سهام بورس تهران (به‌زودی)",
        "tickers": [
            # yfinance از سهام ایران پشتیبانی نمی‌کنه
            # در آینده از TGJU یا AlanChand استفاده می‌کنیم
        ],
    },
}


# ═══════════════════════════════════════════════════════════
# توابع کمکی
# ═══════════════════════════════════════════════════════════
def get_category(category_key: str) -> dict | None:
    """دریافت اطلاعات یه دسته"""
    return MARKET_CATEGORIES.get(category_key)


def get_category_tickers(category_key: str) -> list[tuple]:
    """دریافت لیست نمادهای یه دسته (شامل خالی‌ها)"""
    cat = MARKET_CATEGORIES.get(category_key)
    if not cat:
        return []
    return cat.get("tickers", [])


def get_all_categories() -> dict:
    """دریافت همه دسته‌ها"""
    return MARKET_CATEGORIES


def get_categories_with_tickers() -> dict:
    """دسته‌هایی که نماد دارن (غیرخالی)"""
    return {
        k: v for k, v in MARKET_CATEGORIES.items()
        if v.get("tickers")
    }