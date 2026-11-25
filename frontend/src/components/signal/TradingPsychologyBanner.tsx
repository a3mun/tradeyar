"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { TRADING_PSYCHOLOGY_QUOTES } from "@/lib/trading-psychology";

export function TradingPsychologyBanner() {
  const [quote, setQuote] = useState<string>("");
  const [key, setKey] = useState<number>(0);

  useEffect(() => {
    const randomIndex = Math.floor(Math.random() * TRADING_PSYCHOLOGY_QUOTES.length);
    setQuote(TRADING_PSYCHOLOGY_QUOTES[randomIndex]);
    setKey((prev) => prev + 1);
  }, []);

  if (!quote) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      // 🔴 پدینگ و min-h کاهش یافت
      className="relative overflow-hidden rounded-lg border border-[#d6ad60]/20 bg-gradient-to-l from-[#d6ad60]/5 via-[#051118] to-[#d6ad60]/5 px-3 py-2 shadow-sm sm:px-4 sm:py-2.5 min-h-[56px] sm:min-h-[63px] flex flex-col justify-center"
    >
      <div className="pointer-events-none absolute -top-8 right-0 h-24 w-24 rounded-full bg-[#d6ad60]/10 blur-2xl" />
      <div className="pointer-events-none absolute -bottom-8 left-0 h-24 w-24 rounded-full bg-[#d6ad60]/10 blur-2xl" />

      <div className="relative z-10 flex flex-col items-center justify-center text-center">
        <div className="flex items-center gap-1.5 mb-0.5">
          <Sparkles className="h-2.5 w-2.5 text-[#d6ad60]" />
          <span className="text-[8px] font-bold text-[#d6ad60]/80 sm:text-[11px]">
            یادآوری روانشناسی معامله‌گری
          </span>
          <Sparkles className="h-2.5 w-2.5 text-[#d6ad60]" />
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={key}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.3 }}
            className="text-[10px] leading-snug text-gray-300 sm:text-[12px] max-w-3xl"
          >
            «{quote}»
          </motion.p>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}