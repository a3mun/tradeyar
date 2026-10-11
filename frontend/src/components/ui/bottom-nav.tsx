"use client";

/**
 * BottomNav — منوی نوار پایین موبایل (فاز ۱۰.۳)
 * ============================================================
 * موبایل: ۳ دکمه (تنظیمات | حساب | راهنما)
 * دسکتاپ: مخفی
 *
 * ═══ تغییرات فاز ۱۰.۳ ═══
 *   • BottomNav در z-50 (بالای Backdrop، همیشه دیده می‌شه)
 *   • Sheet تنظیمات از راست، راهنما از چپ
 *   • Sheet حساب کاربری → Bottom Sheet (از پایین کشویی)
 *   • انیمیشن نرم برای هر دو نوع Sheet
 *   • aria-label و role برای دسترس‌پذیری
 */

import { Settings, User, BookOpen, X } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { SettingsPanel } from "@/components/layout/SettingsPanel";
import { HelpContent } from "@/components/layout/HelpPanel";

export function BottomNav() {
  const mobileSheet = useAppStore((s) => s.mobileSheet);
  const setMobileSheet = useAppStore((s) => s.setMobileSheet);

  const open = (type: "settings" | "help" | "account") => {
    setMobileSheet(type);
  };

  const close = () => {
    setMobileSheet(null);
  };

  const isSideSheet = mobileSheet === "settings" || mobileSheet === "help";
  const isBottomSheet = mobileSheet === "account";

  const sideTitle =
    mobileSheet === "settings" ? "⚙️ تنظیمات" : "📖 راهنما";

  return (
    <>
      {/* ═══ Backdrop مشترک ═══ */}
      {mobileSheet && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={close}
          aria-hidden="true"
        />
      )}

      {/* ═══ Sheet کناری — تنظیمات (راست) / راهنما (چپ) ═══ */}
      {isSideSheet && (
        <div
          className={`fixed top-0 bottom-16 z-50 flex w-[85%] max-w-sm flex-col bg-background shadow-2xl transition-transform duration-300 md:hidden ${
            mobileSheet === "settings"
              ? "right-0 border-r border-border/40 rounded-l-2xl"
              : "left-0 border-l border-border/40 rounded-r-2xl"
          }`}
          role="dialog"
          aria-modal="true"
          aria-label={sideTitle}
        >
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
            <span className="text-sm font-bold">{sideTitle}</span>
            <button
              onClick={close}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
              aria-label="بستن"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {mobileSheet === "settings" && <SettingsPanel />}
            {mobileSheet === "help" && <HelpContent />}
          </div>
        </div>
      )}

      {/* ═══ Bottom Sheet — حساب کاربری (از پایین) ═══ */}
      {isBottomSheet && (
        <div
          className="fixed bottom-16 left-0 right-0 z-50 flex max-h-[70vh] flex-col rounded-t-2xl border-t border-border/40 bg-background shadow-2xl transition-transform duration-300 md:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="حساب کاربری"
        >
          {/* دستگیره‌ی بالا */}
          <div className="flex justify-center pt-2">
            <div className="h-1 w-10 rounded-full bg-muted-foreground/30" />
          </div>

          {/* هدر */}
          <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
            <span className="text-sm font-bold">👤 حساب کاربری</span>
            <button
              onClick={close}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
              aria-label="بستن"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* محتوا */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-3 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border border-primary/20 bg-primary/5">
                <User className="h-8 w-8 text-primary" />
              </div>
              <div>
                <p className="text-sm font-bold">حساب کاربری</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  به‌زودی — ثبت‌نام و ورود فعال می‌شه
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Bottom Nav — بالای Backdrop ═══ */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-border/40 bg-background/95 backdrop-blur-md md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
        aria-label="منوی پایین"
      >
        <button
          onClick={() => open("settings")}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors ${
            mobileSheet === "settings"
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-pressed={mobileSheet === "settings"}
          aria-label="تنظیمات"
        >
          <Settings className="h-5 w-5" />
          <span>تنظیمات</span>
        </button>

        <button
          onClick={() => open("account")}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors ${
            mobileSheet === "account"
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-pressed={mobileSheet === "account"}
          aria-label="حساب کاربری"
        >
          <User className="h-5 w-5" />
          <span>حساب کاربری</span>
        </button>

        <button
          onClick={() => open("help")}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors ${
            mobileSheet === "help"
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-pressed={mobileSheet === "help"}
          aria-label="راهنما"
        >
          <BookOpen className="h-5 w-5" />
          <span>راهنما</span>
        </button>
      </nav>

      {/* فاصله‌ی پایین برای محتوای صفحه */}
      <div className="h-16 md:hidden" aria-hidden="true" />
    </>
  );
}