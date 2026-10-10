"use client";

/**
 * BottomNav — منوی نوار پایین موبایل (فاز ۱۰.۲)
 * ============================================================
 * روی موبایل: ۳ دکمه (تنظیمات | حساب | راهنما)
 * روی دسکتاپ: مخفی
 *
 * ═══ تغییرات فاز ۱۰.۲ ═══
 *   • دکمه‌ها واقعاً sheet باز می‌کنن
 */

import { Settings, User, BookOpen, X } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { SettingsPanel } from "@/components/layout/SettingsPanel";
import { HelpContent } from "@/components/layout/HelpPanel";

export function BottomNav() {
  const { mobileSheet, setMobileSheet } = useAppStore();

  const open = (type: "settings" | "help" | "account") => {
    setMobileSheet(type);
  };

  const close = () => {
    setMobileSheet(null);
  };

  return (
    <>
      {/* ═══ Sheet موبایل ═══ */}
      {mobileSheet && mobileSheet !== "account" && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            onClick={close}
            aria-hidden="true"
          />

          {/* Sheet */}
          <div className="fixed bottom-16 left-0 right-0 z-50 max-h-[80vh] overflow-y-auto rounded-t-2xl border-t border-border/40 bg-background p-2 md:hidden">
            {/* دکمه بستن */}
            <div className="flex items-center justify-between px-2 pb-2">
              <span className="text-xs font-bold">
                {mobileSheet === "settings" ? "⚙️ تنظیمات" : "📖 راهنما"}
              </span>
              <button
                onClick={close}
                className="rounded-md p-1 text-muted-foreground hover:bg-muted/30 hover:text-foreground"
                aria-label="بستن"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* محتوا */}
            {mobileSheet === "settings" && <SettingsPanel />}
            {mobileSheet === "help" && <HelpContent />}
          </div>
        </>
      )}

      {/* ═══ Bottom Nav ═══ */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-30 flex border-t border-border/40 bg-background/95 backdrop-blur-md md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
      >
        <button
          onClick={() => open("settings")}
          className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors ${
            mobileSheet === "settings"
              ? "text-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
          aria-pressed={mobileSheet === "settings"}
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
        >
          <BookOpen className="h-5 w-5" />
          <span>راهنما</span>
        </button>
      </nav>

      {/* فاصله‌ی پایین */}
      <div className="h-16 md:hidden" aria-hidden="true" />
    </>
  );
}