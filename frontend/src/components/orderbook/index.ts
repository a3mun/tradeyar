/**
 * components/orderbook — ✅ فعال (نسخه ۱.۹)
 * ============================================================
 * ⚠️ این پوشه دیگر placeholder نیست.
 *
 * کامپوننت اصلی در `@/components/signal/OrderBookPanel` است
 * (کنار بقیه‌ی کارت‌های تحلیل).
 *
 * ═══ وضعیت ═══
 *   GET /orderbook/{ticker}          → ✅ ۲۰۰ (عمق کامل)
 *   GET /orderbook/{ticker}/summary  → ✅ ۲۰۰ (خلاصه)
 *   GET /orderbook/{ticker}/compare  → ✅ ۲۰۰ (مقایسه صرافی‌ها)
 *
 * ═══ صرافی‌های پشتیبانی‌شده ═══
 *   ✅ نوبیتکس · بیت‌پین · والکس · تبدیل
 *   ❌ TSETMC (عمق لحظه‌ای عمومی ندارد)
 *
 * ═══ ⚠️ محدودیت علمی ═══
 * imbalance **لحظه‌ای** است و بین صرافی‌ها متناقض می‌شود
 * (BTC-IRT: نوبیتکس ۰.۶۳ ولی بیت‌پین ۰.۰۷). پس با وزن کم
 * در گروه «حجم» استفاده می‌شود و هرگز تنها عامل سیگنال نیست.
 *
 * ═══ باقی‌مانده برای فاز بعد ═══
 *   • WebSocket قیمت لحظه‌ای (جای REST polling)
 *   • نمودار عمق (depth chart)
 *   • ردیابی تغییر imbalance در زمان (spoofing detection)
 */

export { OrderBookPanel } from "@/components/signal/OrderBookPanel";
