"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  Settings,
  User,
  BookOpen,
  X,
  LayoutDashboard,
  LogIn,
  ShieldCheck,
  LogOut,
  Home,
} from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { SettingsPanel } from "@/components/layout/SettingsPanel";
import { HelpContent } from "@/components/layout/HelpPanel";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const mobileSheet = useAppStore((s) => s.mobileSheet);
  const setMobileSheet = useAppStore((s) => s.setMobileSheet);

  if (pathname === "/login") return null;

  const user = getUser();
  const isLoggedIn = !!getToken();
  const isHome = pathname === "/";

  if (!isLoggedIn && isHome) return null;

  const open = (type: "settings" | "help" | "account") => {
    if (mobileSheet === type) {
      setMobileSheet(null);
    } else {
      setMobileSheet(type);
    }
  };

  const close = () => {
    setMobileSheet(null);
  };

  const handleGoHome = () => {
    close();
    router.push("/");
  };

  const isSideSheet = mobileSheet === "settings" || mobileSheet === "help";
  const isBottomSheet = mobileSheet === "account";

  const sideTitle =
    mobileSheet === "settings" ? "⚙️ تنظیمات" : "📖 راهنما";

  const handleGoToDashboard = () => {
    close();
    router.push("/dashboard");
  };

  const handleGoToAdmin = () => {
    close();
    router.push("/admin");
  };

  const handleLogin = () => {
    close();
    router.push("/login");
  };

  const handleLogout = () => {
    removeToken();
    close();
    router.push("/login");
  };

  return (
    <>
      {/* ═══════════════════════════════════════════════
          🔴 کاربر لاگین‌نکرده → فقط دکمه خانه
      ═══════════════════════════════════════════════ */}
      {!isLoggedIn ? (
        <>
          <nav
            className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-white/5 bg-[#051118]/80 backdrop-blur-md md:hidden"
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
            aria-label="منوی پایین"
          >
            <button
              onClick={handleGoHome}
              className="flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] text-gray-400 transition-colors hover:text-white"
              aria-label="صفحه اصلی"
            >
              <Home className="h-5 w-5" />
              <span>صفحه اصلی</span>
            </button>
          </nav>

          <div className="h-16 md:hidden" aria-hidden="true" />
        </>
      ) : (
        <>
          {/* ═══════════════════════════════════════════════
              کاربر لاگین‌کرده → همه چیز
          ═══════════════════════════════════════════════ */}

          {mobileSheet && (
            <div
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
              onClick={close}
              aria-hidden="true"
            />
          )}

          {/* Sheet کناری — تنظیمات/راهنما */}
          {isSideSheet && (
            <div
              className={`fixed top-0 bottom-16 z-50 flex w-[85%] max-w-sm flex-col bg-[#051118] shadow-2xl transition-transform duration-300 md:hidden ${
                mobileSheet === "settings"
                  ? "right-0 border-r border-white/5 rounded-l-2xl"
                  : "left-0 border-l border-white/5 rounded-r-2xl"
              }`}
              role="dialog"
              aria-modal="true"
              aria-label={sideTitle}
            >
              <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
                <span className="text-sm font-bold text-gray-100">{sideTitle}</span>
                <button
                  onClick={close}
                  className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
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

          {/* Bottom Sheet — حساب کاربری */}
          {isBottomSheet && (
            <div
              className="fixed bottom-16 left-0 right-0 z-50 flex max-h-[70vh] flex-col rounded-t-2xl border-t border-white/5 bg-[#051118] shadow-2xl transition-transform duration-300 md:hidden"
              role="dialog"
              aria-modal="true"
              aria-label="حساب کاربری"
            >
              <div className="flex justify-center pt-2">
                <div className="h-1 w-10 rounded-full bg-white/10" />
              </div>

              <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
                <span className="text-sm font-bold text-gray-100">👤 حساب کاربری</span>
                <button
                  onClick={close}
                  className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-white/5 hover:text-white"
                  aria-label="بستن"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {user ? (
                  <div className="space-y-4">
                    <div className="flex flex-col items-center justify-center gap-2 text-center py-4">
                      <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/5">
                        <User className="h-8 w-8 text-[#d6ad60]" />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-100">
                          {user.full_name || "کاربر تریدمون"}
                        </p>
                        <p className="mt-1 text-xs text-gray-400 font-mono dir-ltr">
                          {user.phone}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Button
                        onClick={handleGoHome}
                        variant="outline"
                        className="w-full h-12 gap-2 text-base font-bold border-white/5 text-gray-300 hover:bg-white/5"
                      >
                        <Home className="h-5 w-5" /> صفحه اصلی
                      </Button>

                      <Button
                        onClick={handleGoToDashboard}
                        className="w-full h-12 gap-2 text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90"
                      >
                        <LayoutDashboard className="h-5 w-5" /> رفتن به داشبورد
                      </Button>

                      {user.is_admin && (
                        <Button
                          onClick={handleGoToAdmin}
                          variant="outline"
                          className="w-full h-12 gap-2 text-base font-bold border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10"
                        >
                          <ShieldCheck className="h-5 w-5" /> پنل مدیریت
                        </Button>
                      )}

                      <Button
                        onClick={handleLogout}
                        variant="destructive"
                        className="w-full h-12 gap-2 text-base font-bold"
                      >
                        <LogOut className="h-5 w-5" /> خروج از حساب
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-3 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/5">
                      <User className="h-8 w-8 text-[#d6ad60]" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-gray-100">حساب کاربری</p>
                      <p className="mt-1 text-xs text-gray-400">
                        برای دسترسی به داشبورد وارد شوید.
                      </p>
                    </div>
                    <Button
                      onClick={handleLogin}
                      className="w-full h-12 gap-2 text-base font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90"
                    >
                      <LogIn className="h-5 w-5" /> ورود به حساب
                    </Button>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Bottom Nav */}
          <nav
            className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-white/5 bg-[#051118]/80 backdrop-blur-md md:hidden"
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0)" }}
            aria-label="منوی پایین"
          >
            {!isHome && (
              <button
                onClick={handleGoHome}
                className="flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] text-gray-400 transition-colors hover:text-white"
                aria-label="صفحه اصلی"
              >
                <Home className="h-5 w-5" />
                <span>خانه</span>
              </button>
            )}

            <button
              onClick={() => open("settings")}
              className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors ${
                mobileSheet === "settings"
                  ? "text-[#d6ad60]"
                  : "text-gray-400 hover:text-white"
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
                  ? "text-[#d6ad60]"
                  : "text-gray-400 hover:text-white"
              }`}
              aria-pressed={mobileSheet === "account"}
              aria-label="حساب کاربری"
            >
              <User className="h-5 w-5" />
              <span>حساب</span>
            </button>

            <button
              onClick={() => open("help")}
              className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-[10px] transition-colors ${
                mobileSheet === "help"
                  ? "text-[#d6ad60]"
                  : "text-gray-400 hover:text-white"
              }`}
              aria-pressed={mobileSheet === "help"}
              aria-label="راهنما"
            >
              <BookOpen className="h-5 w-5" />
              <span>راهنما</span>
            </button>
          </nav>

          <div className="h-16 md:hidden" aria-hidden="true" />
        </>
      )}
    </>
  );
}