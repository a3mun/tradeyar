
"use client";

import { useEffect, useState, useCallback } from "react";
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
  Clock,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { useAppStore } from "@/store/useAppStore";
import { SettingsPanel } from "@/components/layout/SettingsPanel";
import { HelpContent } from "@/components/layout/HelpPanel";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";

// ترجمه نام پلن‌ها
function getPlanName(plan: string) {
  const map: Record<string, string> = {
    "1_month": "یک ماهه",
    "3_months": "سه ماهه",
    "6_months": "شش ماهه",
    "12_months": "یک ساله",
    free: "رایگان",
    monthly: "ماهانه",
  };

  return map[plan] || plan;
}

// بررسی اعتبار اشتراک
function isSubscriptionActive(subData: any): boolean {
  if (
    !subData ||
    subData.status !== "active" ||
    !subData.end_date
  ) {
    return false;
  }

  const endDate = new Date(subData.end_date);

  if (Number.isNaN(endDate.getTime())) {
    return false;
  }

  return endDate.getTime() > Date.now();
}

const panelVariants = {
  hidden: {
    opacity: 0,
    y: 24,
    scale: 0.98,
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
  },
  exit: {
    opacity: 0,
    y: 18,
    scale: 0.98,
  },
};

const sidePanelVariants = {
  hidden: {
    opacity: 0,
    x: 24,
  },
  visible: {
    opacity: 1,
    x: 0,
  },
  exit: {
    opacity: 0,
    x: 24,
  },
};

export function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();

  const mobileSheet = useAppStore((s) => s.mobileSheet);
  const setMobileSheet = useAppStore((s) => s.setMobileSheet);

  const [user, setUser] = useState<any>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [subData, setSubData] = useState<any>(null);

  const [authLoaded, setAuthLoaded] = useState(false);
  const [accountLoaded, setAccountLoaded] = useState(false);

  // دریافت اطلاعات حساب و اشتراک
  const loadAccountData = useCallback(() => {
    try {
      const token = getToken();
      const currentUser = getUser();

      setIsLoggedIn(!!token);
      setUser(currentUser);

      if (!token || !currentUser) {
        setSubData(null);
      } else {
        const subStr = localStorage.getItem(
          "trademun_subscription"
        );

        if (subStr) {
          const parsedData = JSON.parse(subStr);

          setSubData(
            parsedData &&
              typeof parsedData === "object" &&
              !Array.isArray(parsedData)
              ? parsedData
              : null
          );
        } else {
          setSubData(null);
        }
      }
    } catch (error) {
      console.error("Error loading account data:", error);
      setSubData(null);
    } finally {
      setAccountLoaded(true);
      setAuthLoaded(true);
    }
  }, []);

  // بارگذاری اولیه و همگام‌سازی اطلاعات
  useEffect(() => {
    loadAccountData();

    // هنگام بازگشت به پنجره
    const handleFocus = () => {
      loadAccountData();
    };

    // هنگام بازگشت به تب
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        loadAccountData();
      }
    };

    // تغییر localStorage در تب‌های دیگر
    const handleStorage = (event: StorageEvent) => {
      if (
        event.key === "trademun_subscription" ||
        event.key === null
      ) {
        loadAccountData();
      }
    };

    window.addEventListener("focus", handleFocus);
    window.addEventListener("storage", handleStorage);

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange
    );

    return () => {
      window.removeEventListener("focus", handleFocus);
      window.removeEventListener("storage", handleStorage);

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange
      );
    };
  }, [pathname, loadAccountData]);

  // بستن پنل هنگام تغییر مسیر
  useEffect(() => {
    setMobileSheet(null);
  }, [pathname, setMobileSheet]);

  // صفحه ورود منوی پایین ندارد
  if (pathname === "/login") return null;

  // جلوگیری از نمایش اشتباه منو قبل از دریافت اطلاعات ورود
  if (!authLoaded) return null;

  const isHome = pathname === "/";

  const isSideSheet =
    mobileSheet === "settings" ||
    mobileSheet === "help";

  const isBottomSheet = mobileSheet === "account";

  // کاربر مهمان در صفحه اصلی منوی پایین نمی‌خواهد
  if (!isLoggedIn && isHome) return null;

  // باز و بسته کردن پنل‌ها
  const open = (type: "settings" | "help" | "account") => {
    setMobileSheet(mobileSheet === type ? null : type);
  };

  const close = () => {
    setMobileSheet(null);
  };

  // رفتن به صفحه اصلی
  const handleGoHome = () => {
    close();
    router.push("/");
  };

  // رفتن به داشبورد
  const handleGoToDashboard = () => {
    close();
    router.push("/dashboard");
  };

  // رفتن به پنل مدیریت
  const handleGoToAdmin = () => {
    close();
    router.push("/admin");
  };

  // ورود
  const handleLogin = () => {
    close();
    router.push("/login");
  };

  // خروج
  const handleLogout = () => {
    removeToken();

    setUser(null);
    setSubData(null);
    setIsLoggedIn(false);

    close();

    router.push("/login");
  };

  const sideTitle =
    mobileSheet === "settings" ? "تنظیمات" : "راهنما";

  const validSubscription = isSubscriptionActive(subData);

  const subscriptionEndDate = validSubscription
    ? new Date(subData.end_date)
    : null;

  return (
    <>
      {/* پس‌زمینه تار هنگام باز بودن پنل */}
      <AnimatePresence>
        {mobileSheet && isLoggedIn && (
          <motion.div
            key="mobile-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-[60] bg-black/65 backdrop-blur-[3px] md:hidden"
            onClick={close}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* پنل تنظیمات و راهنما */}
      <AnimatePresence mode="wait">
        {isLoggedIn && isSideSheet && (
          <motion.div
            key={mobileSheet}
            variants={sidePanelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            transition={{
              duration: 0.25,
              ease: [0.22, 1, 0.36, 1],
            }}
            className={`fixed top-0 bottom-16 z-[70] flex w-[85%] max-w-sm flex-col bg-[#051118] shadow-2xl md:hidden ${
              mobileSheet === "settings"
                ? "right-0 rounded-l-2xl border-r border-white/10"
                : "left-0 rounded-r-2xl border-l border-white/10"
            }`}
            role="dialog"
            aria-modal="true"
            aria-label={sideTitle}
          >
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
              <div className="flex items-center gap-2">
                {mobileSheet === "settings" ? (
                  <Settings className="h-4 w-4 text-[#d6ad60]" />
                ) : (
                  <BookOpen className="h-4 w-4 text-[#d6ad60]" />
                )}

                <span className="text-sm font-bold text-gray-100">
                  {sideTitle}
                </span>
              </div>

              <button
                type="button"
                onClick={close}
                className="rounded-xl border border-white/5 bg-white/5 p-2 text-gray-400 transition-colors hover:bg-white/10 hover:text-white active:scale-95"
                aria-label="بستن"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {mobileSheet === "settings" && <SettingsPanel />}
              {mobileSheet === "help" && <HelpContent />}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* پنل حساب کاربری */}
      <AnimatePresence>
        {isLoggedIn && isBottomSheet && (
          <motion.div
            key="account-sheet"
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            transition={{
              duration: 0.28,
              ease: [0.22, 1, 0.36, 1],
            }}
            className="fixed bottom-[calc(4.8rem+env(safe-area-inset-bottom,0px))] left-0 right-0 z-[70] mx-auto flex max-h-[75vh] w-full max-w-xl flex-col overflow-hidden rounded-t-[28px] border border-white/10 border-b-0 bg-[#051118] shadow-[0_-15px_60px_rgba(0,0,0,0.45)] md:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="حساب کاربری"
          >
            {/* دستگیره پنل */}
            <div className="flex justify-center pt-3">
              <div className="h-1.5 w-11 rounded-full bg-white/15" />
            </div>

            {/* سربرگ */}
            <div className="flex items-center justify-between border-b border-white/5 px-5 py-3">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-[#d6ad60]" />

                <span className="text-sm font-bold text-gray-100">
                  حساب کاربری
                </span>
              </div>

              <button
                type="button"
                onClick={close}
                className="rounded-xl bg-white/5 p-2 text-gray-400 transition-colors hover:bg-white/10 hover:text-white active:scale-95"
                aria-label="بستن"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto overscroll-contain p-5">
              {user ? (
                <div className="space-y-5">

                  {/* اطلاعات کاربر */}
                  <div className="relative overflow-hidden rounded-2xl border border-[#d6ad60]/15 bg-gradient-to-br from-[#051118] to-[#0b1c24] p-4">
                    <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-[#d6ad60]/5 blur-2xl" />

                    <div className="relative flex items-center gap-3">
                      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-[#d6ad60]/30 bg-[#d6ad60]/10 shadow-inner">
                        <User className="h-7 w-7 text-[#d6ad60]" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-bold text-white">
                          {user.full_name || "کاربر تریدمون"}
                        </p>

                        <p className="num mt-1 truncate text-xs text-gray-400 font-mono dir-ltr text-right">
                          {user.phone}
                        </p>

                        {/* وضعیت اشتراک */}
                        {user.is_admin ? (
                          <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-[#d6ad60]/20 bg-[#d6ad60]/10 px-2.5 py-1 text-[10px] font-medium text-[#e5c47f]">
                            <ShieldCheck className="h-3 w-3" />
                            دسترسی نامحدود مدیر
                          </div>
                        ) : !accountLoaded ? (
                          <div className="mt-2 text-[10px] text-gray-400">
                            در حال بررسی اشتراک...
                          </div>
                        ) : validSubscription ? (
                          <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/15 bg-emerald-500/10 px-2.5 py-1 text-[10px] text-emerald-300">
                            <Clock className="h-3 w-3" />

                            {getPlanName(subData.plan)} تا{" "}

                            {new Intl.DateTimeFormat("fa-IR").format(
                              subscriptionEndDate!
                            )}
                          </div>
                        ) : (
                          <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-red-500/15 bg-red-500/10 px-2.5 py-1 text-[10px] text-red-300">
                            <Clock className="h-3 w-3" />
                            اشتراک منقضی شده
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* دکمه‌های حساب */}
                  <div className="space-y-2.5">
                    <Button
                      onClick={handleGoToDashboard}
                      className="h-12 w-full justify-center gap-2 rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#101827] shadow-[0_5px_20px_rgba(214,173,96,0.16)] transition-all hover:brightness-110 active:scale-[0.98]"
                    >
                      <LayoutDashboard className="h-5 w-5" />
                      رفتن به داشبورد
                    </Button>

                    <Button
                      onClick={handleGoHome}
                      variant="outline"
                      className="h-12 w-full justify-center gap-2 rounded-xl border-white/10 bg-white/[0.03] text-sm font-bold text-gray-200 transition-all hover:bg-white/[0.08] hover:text-white active:scale-[0.98]"
                    >
                      <Home className="h-5 w-5" />
                      صفحه اصلی
                    </Button>

                    {user.is_admin && (
                      <Button
                        onClick={handleGoToAdmin}
                        variant="outline"
                        className="h-12 w-full justify-center gap-2 rounded-xl border-[#d6ad60]/25 bg-[#d6ad60]/5 text-sm font-bold text-[#e4c17d] transition-all hover:bg-[#d6ad60]/10 active:scale-[0.98]"
                      >
                        <ShieldCheck className="h-5 w-5" />
                        پنل مدیریت
                      </Button>
                    )}

                    <Button
                      onClick={handleLogout}
                      variant="outline"
                      className="h-12 w-full justify-center gap-2 rounded-xl border-red-500/15 bg-red-500/[0.04] text-sm font-bold text-red-300 transition-all hover:bg-red-500/10 hover:text-red-200 active:scale-[0.98]"
                    >
                      <LogOut className="h-5 w-5" />
                      خروج از حساب
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[220px] flex-col items-center justify-center gap-4 text-center">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-[#d6ad60]/20 bg-[#d6ad60]/10">
                    <User className="h-8 w-8 text-[#d6ad60]" />
                  </div>

                  <div>
                    <p className="text-sm font-bold text-white">
                      حساب کاربری
                    </p>

                    <p className="mt-1 text-xs text-gray-400">
                      برای دسترسی به امکانات حساب وارد شوید.
                    </p>
                  </div>

                  <Button
                    onClick={handleLogin}
                    className="h-12 w-full gap-2 rounded-xl bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-sm font-bold text-[#101827] hover:brightness-110 active:scale-[0.98]"
                  >
                    <LogIn className="h-5 w-5" />
                    ورود به حساب
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* منوی پایین کاربران مهمان */}
      {!isLoggedIn && (
        <>
          <nav
            className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-center border-t border-white/[0.06] bg-[#071820]/95 px-4 pt-2 pb-[calc(0.55rem+env(safe-area-inset-bottom,0px))] shadow-[0_-8px_30px_rgba(0,0,0,0.2)] backdrop-blur-xl md:hidden"
            aria-label="منوی پایین"
          >
            <motion.button
              type="button"
              whileTap={{ scale: 0.9 }}
              onClick={handleGoHome}
              className="flex flex-col items-center gap-1 text-[#e5c47f]"
              aria-label="صفحه اصلی"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[#f0d28f]/60 bg-gradient-to-br from-[#f0d28f] to-[#bd8b3d] text-[#102027] shadow-[0_5px_18px_rgba(214,173,96,0.3)]">
                <Home className="h-6 w-6" />
              </div>

              <span className="text-[10px] font-bold">
                صفحه اصلی
              </span>
            </motion.button>
          </nav>

          <div
            className="h-[calc(5.2rem+env(safe-area-inset-bottom,0px))] md:hidden"
            aria-hidden="true"
          />
        </>
      )}

      {/* منوی پایین کاربران واردشده */}
      {isLoggedIn && (
        <>
          <nav
            className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-white/[0.06] bg-[#071820]/95 px-3 pt-2 pb-[calc(0.55rem+env(safe-area-inset-bottom,0px))] shadow-[0_-8px_30px_rgba(0,0,0,0.22)] backdrop-blur-xl md:hidden"
            aria-label="منوی پایین"
          >
            {/* تنظیمات */}
            <motion.button
              type="button"
              whileTap={{ scale: 0.88 }}
              onClick={() => open("settings")}
              className={`relative flex min-w-0 flex-1 flex-col items-center justify-center gap-1 py-1 transition-colors ${
                mobileSheet === "settings"
                  ? "text-[#e5c47f]"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              aria-pressed={mobileSheet === "settings"}
              aria-label="تنظیمات"
            >
              <motion.span
                animate={{
                  scale: mobileSheet === "settings" ? 1.12 : 1,
                  rotate: mobileSheet === "settings" ? 45 : 0,
                }}
                transition={{ duration: 0.2 }}
              >
                <Settings className="h-[21px] w-[21px]" />
              </motion.span>

              <span className="text-[10px] font-medium">
                تنظیمات
              </span>

              {mobileSheet === "settings" && (
                <motion.span
                  layoutId="bottom-nav-indicator"
                  className="absolute -bottom-1 h-1 w-5 rounded-full bg-[#d6ad60]"
                />
              )}
            </motion.button>

            {/* حساب کاربری */}
            <div className="relative flex flex-1 items-center justify-center">
              <motion.button
                type="button"
                whileTap={{ scale: 0.9, y: 1 }}
                onClick={() => open("account")}
                className="relative -mt-8 flex flex-col items-center gap-1"
                aria-pressed={mobileSheet === "account"}
                aria-label="حساب کاربری"
              >
                <motion.div
                  animate={{
                    scale: mobileSheet === "account" ? 1.06 : 1,
                    rotate: mobileSheet === "account" ? -8 : 0,
                  }}
                  transition={{
                    type: "spring",
                    stiffness: 320,
                    damping: 18,
                  }}
                  className={`relative flex h-[52px] w-[52px] items-center justify-center rounded-full border-[4px] border-[#071820] bg-gradient-to-br from-[#f2d697] via-[#d6ad60] to-[#b98234] text-[#102027] shadow-[0_5px_22px_rgba(214,173,96,0.3)] ${
                    mobileSheet === "account"
                      ? "ring-2 ring-[#d6ad60]/30"
                      : ""
                  }`}
                >
                  <User
                    className="h-7 w-7"
                    strokeWidth={2.2}
                  />

                  <span className="absolute -bottom-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-[#071820] bg-[#102027]">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  </span>
                </motion.div>

                <span
                  className={`text-[10px] font-bold transition-colors ${
                    mobileSheet === "account"
                      ? "text-[#e5c47f]"
                      : "text-gray-300"
                  }`}
                >
                  حساب کاربری
                </span>
              </motion.button>
            </div>

            {/* راهنما */}
            <motion.button
              type="button"
              whileTap={{ scale: 0.88 }}
              onClick={() => open("help")}
              className={`relative flex min-w-0 flex-1 flex-col items-center justify-center gap-1 py-1 transition-colors ${
                mobileSheet === "help"
                  ? "text-[#e5c47f]"
                  : "text-gray-400 hover:text-gray-200"
              }`}
              aria-pressed={mobileSheet === "help"}
              aria-label="راهنما"
            >
              <motion.span
                animate={{
                  scale: mobileSheet === "help" ? 1.12 : 1,
                  rotate: mobileSheet === "help" ? -5 : 0,
                }}
                transition={{ duration: 0.2 }}
              >
                <BookOpen className="h-[21px] w-[21px]" />
              </motion.span>

              <span className="text-[10px] font-medium">
                راهنما
              </span>

              {mobileSheet === "help" && (
                <motion.span
                  layoutId="bottom-nav-indicator"
                  className="absolute -bottom-1 h-1 w-5 rounded-full bg-[#d6ad60]"
                />
              )}
            </motion.button>
          </nav>

          <div
            className="h-[calc(5.2rem+env(safe-area-inset-bottom,0px))] md:hidden"
            aria-hidden="true"
          />
        </>
      )}
    </>
  );
}
