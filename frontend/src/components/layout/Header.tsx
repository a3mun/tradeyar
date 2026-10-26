"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Clock, User, LogOut, LayoutDashboard, ShieldCheck, LogIn, ChevronDown } from "lucide-react";
import { HelpPanel } from "./HelpPanel";
import { getUser, getToken, removeToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";

export function Header() {
  const router = useRouter();
  const [time, setTime] = useState<string>("");
  const [isAccountOpen, setIsAccountOpen] = useState(false);
  const [user, setUserData] = useState<any>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isLoggedIn = !!getToken();

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
    
    const u = getUser();
    setUserData(u);
    
    return () => clearInterval(id);
  }, []);

  // بستن منو با کلیک بیرون
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsAccountOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
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
    <header className="sticky top-0 z-50 w-full border-b border-[#d6ad60]/10 bg-[#07111f]/80 backdrop-blur-xl">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        
        <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-80">
          {/* ⬅️ لوگوی جدید */}
          <img src="/icon-192.png" alt="Trademun" className="h-10 w-10 rounded-xl object-contain" />
          <div>
            <h1 className="text-lg font-bold leading-none text-white">تریدمون</h1>
            <p className="text-[10px] text-[#d6ad60]">Trademun</p>
          </div>
        </Link>

        <div className="flex items-center gap-2">
          {/* راهنما */}
          <div className="hidden md:flex items-center rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 h-9">
            <HelpPanel />
          </div>

          {/* حساب کاربری (Dropdown) */}
          <div className="relative hidden md:block" ref={dropdownRef}>
            <button
              onClick={() => setIsAccountOpen(!isAccountOpen)}
              className="num inline-flex h-9 items-center gap-1.5 px-3 rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 text-[13px] font-medium text-[#d6ad60] hover:bg-[#d6ad60]/10 transition-colors"
            >
              <User className="h-3.5 w-3.5" />
              <span>حساب کاربری</span>
              <ChevronDown className={`h-3.5 w-3.5 transition-transform ${isAccountOpen ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence>
              {isAccountOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                  className="absolute left-0 mt-2 w-64 rounded-xl border border-[#d6ad60]/20 bg-[#0d1b2d] p-4 shadow-2xl z-50"
                >
                  {isLoggedIn && user ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-3 border-b border-white/10 pb-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[#d6ad60]/30 bg-[#d6ad60]/10">
                          <User className="h-5 w-5 text-[#d6ad60]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-bold text-white truncate">{user.full_name || "کاربر تریدمون"}</p>
                          <p className="text-xs text-gray-400 font-mono dir-ltr truncate">{user.phone}</p>
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        <Button onClick={handleGoToDashboard} className="w-full h-9 gap-2 text-sm font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90 justify-start">
                          <LayoutDashboard className="h-4 w-4" /> رفتن به داشبورد
                        </Button>
                        {user.is_admin && (
                          <Button onClick={handleGoToAdmin} variant="outline" className="w-full h-9 gap-2 text-sm font-bold border-[#d6ad60]/30 text-[#d6ad60] hover:bg-[#d6ad60]/10 justify-start">
                            <ShieldCheck className="h-4 w-4" /> پنل مدیریت
                          </Button>
                        )}
                        <Button onClick={handleLogout} variant="destructive" className="w-full h-9 gap-2 text-sm font-bold justify-start">
                          <LogOut className="h-4 w-4" /> خروج از حساب
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4 text-center">
                      <p className="text-sm text-gray-400">برای دسترسی به داشبورد وارد شوید.</p>
                      <Button onClick={handleLogin} className="w-full h-9 gap-2 text-sm font-bold bg-gradient-to-l from-[#c89a49] to-[#e2c17e] text-[#101827] hover:opacity-90">
                        <LogIn className="h-4 w-4" /> ورود به حساب
                      </Button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ساعت */}
          <div className="num flex items-center gap-1.5 rounded-xl border border-[#d6ad60]/20 bg-[#d6ad60]/5 px-2.5 py-1 text-[11px] font-medium tabular-nums text-[#d6ad60] md:px-3 md:py-1.5 md:text-[13px] h-9">
            <Clock className="h-3 w-3 md:h-3.5 md:w-3.5" />
            <span style={{ fontFamily: "monospace" }}>{time || "--:--:--"}</span>
            <span className="text-[9px] opacity-70">TEH</span>
          </div>
        </div>
      </div>
    </header>
  );
}