"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Clock,
  User,
  LogOut,
  LayoutDashboard,
  ShieldCheck,
  LogIn,
  ChevronDown,
  HelpCircle,
} from "lucide-react";
import { HelpPanel } from "./HelpPanel";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { AnimatedLogo } from "@/components/ui/animated-logo";

// 🔴 استایل مشترک برای دکمه‌های هدر (مدرن و یکدست)
const HEADER_BTN_CLASS =
  "flex items-center justify-center gap-1.5 h-9 rounded-xl border border-white/5 bg-white/5 text-[11px] font-medium text-gray-300 transition-all duration-200 hover:bg-white/10 hover:border-white/10 hover:text-white";

function ClockDisplay() {
  const [time, setTime] = useState<string>("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "Asia/Tehran",
        }).format(now)
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={`${HEADER_BTN_CLASS} px-2.5 md:px-3 cursor-default`}>
      <Clock className="h-3 w-3 md:h-3.5 md:w-3.5 text-[#d6ad60]/80" />
      <span className="num tabular-nums text-gray-200" style={{ fontFamily: "monospace" }}>
        {time || "--:--:--"}
      </span>
      <span className="text-[9px] text-gray-500">TEH</span>
    </div>
  );
}

export function Header() {
  const router = useRouter();
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [user, setUserData] = useState<any>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isLoggedIn = !!getToken();

  useEffect(() => {
    const u = getUser();
    setUserData(u);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () =>
      document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleGoToDashboard = () => {
    setIsAccountOpen(false);
    router.push("/dashboard");
  };

  const handleGoToAdmin = () => {
    setIsAccountOpen(false);
    router.push("/admin");
  };

  const handleLogin = () => {
    setIsAccountOpen(false);
    router.push("/login");
  };

  const handleLogout = () => {
    removeToken();
    setIsAccountOpen(false);
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/5 bg-[#051118]/80 backdrop-blur-xl transition-all duration-300">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* لوگو */}
        <Link
          href="/"
          className="group flex items-center gap-3 transition-opacity hover:opacity-90"
        >
          <AnimatedLogo
            width={50}
            height={50}
            imgWidth={40}
            imgHeight={40}
            src="/icon-192.png"
            showParticles={true}
          />
          <div className="flex flex-col justify-center leading-none">
            <h1 className="font-display text-[18px] font-bold leading-none text-white transition-colors group-hover:text-[#d6ad60]">
              تریدمون
            </h1>
            <p className="mt-1 text-[10px] font-medium tracking-[0.03em] leading-none text-[#d6ad60]/90">
              Trademun.ir
            </p>
          </div>
        </Link>

        {/* ابزارها */}
        <div className="flex items-center gap-2">
          {/* راهنما */}
          <div className="hidden md:flex">
            <HelpPanel />
          </div>

          {/* حساب کاربری */}
          <div className="relative hidden md:block" ref={dropdownRef}>
            <button
              onClick={() => setIsAccountOpen(!isAccountOpen)}
              className={`${HEADER_BTN_CLASS} px-3`}
            >
              <User className="h-3.5 w-3.5 text-[#d6ad60]/80" />
              <span>حساب کاربری</span>
              <ChevronDown
                className={`h-3 w-3 transition-transform duration-200 ${
                  isAccountOpen ? "rotate-180" : ""
                }`}
              />
            </button>

            <AnimatePresence>
              {isAccountOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.96 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute left-0 z-50 mt-2 w-64 rounded-xl border border-white/10 bg-[#051118] p-3 shadow-2xl"
                >
                  {isLoggedIn && user ? (
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 border-b border-white/5 pb-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#d6ad60]/30 bg-[#d6ad60]/10">
                          <User className="h-5 w-5 text-[#d6ad60]" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-[12px] font-bold text-white">
                            {user.full_name || "کاربر تریدمون"}
                          </p>
                          <p className="num mt-0.5 truncate text-[10px] text-gray-400 font-mono dir-ltr">
                            {user.phone}
                          </p>
                        </div>
                      </div>

                      <div className="space-y-1.5">
                        <Button
                          onClick={handleGoToDashboard}
                          className="h-9 w-full justify-start gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[12px] font-bold text-[#101827] hover:opacity-90"
                        >
                          <LayoutDashboard className="h-4 w-4" />
                          رفتن به داشبورد
                        </Button>
                        {user.is_admin && (
                          <Button
                            onClick={handleGoToAdmin}
                            variant="outline"
                            className="h-9 w-full justify-start gap-2 border-[#d6ad60]/30 text-[12px] font-bold text-[#d6ad60] hover:bg-[#d6ad60]/10"
                          >
                            <ShieldCheck className="h-4 w-4" />
                            پنل مدیریت
                          </Button>
                        )}
                        <Button
                          onClick={handleLogout}
                          variant="destructive"
                          className="h-9 w-full justify-start gap-2 text-[12px] font-bold"
                        >
                          <LogOut className="h-4 w-4" />
                          خروج از حساب
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3 text-center">
                      <p className="text-[11px] text-gray-400 leading-relaxed">
                        برای دسترسی به داشبورد وارد شوید.
                      </p>
                      <Button
                        onClick={handleLogin}
                        className="h-9 w-full gap-2 bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[12px] font-bold text-[#101827] hover:opacity-90"
                      >
                        <LogIn className="h-4 w-4" />
                        ورود به حساب
                      </Button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ساعت */}
          <ClockDisplay />
        </div>
      </div>
    </header>
  );
}