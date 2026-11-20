"use client";

import { useState } from "react";
import { ChevronDown, Lock } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CollapsibleSectionProps {
  id: string;
  title: string;
  icon?: string | React.ReactNode;
  subtitle?: string;
  accentColor?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  isLocked?: boolean; // 🔴 نشانگر قفل در هدر
}

export function CollapsibleSection({
  id,
  title,
  icon,
  subtitle,
  accentColor = "#d6ad60",
  children,
  defaultOpen = false,
  isLocked = false,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-white/10 bg-[#051118] shadow-md overflow-hidden transition-all hover:bg-[#051117]">
      {/* هدر — همیشه قابل کلیک */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex w-full items-center justify-between p-3 text-right transition-colors hover:bg-white/5"
      >
        <div className="flex items-center gap-2">
          {icon && (
            <span className="text-lg text-[#d6ad60]">
              {icon}
            </span>
          )}
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-foreground">
                {title}
              </h3>
              {/* 🔴 بج Pro برای کاربر رایگان */}
              {isLocked && (
                <span className="flex items-center gap-1 rounded-md bg-[#d6ad60]/10 px-1.5 py-0.5 text-[9px] font-bold text-[#d6ad60] border border-[#d6ad60]/30">
                  <Lock className="h-2.5 w-2.5" /> Pro
                </span>
              )}
            </div>
            {subtitle && (
              <p className="mt-0.5 text-[10px] text-muted-foreground">
                {subtitle}
              </p>
            )}
          </div>
        </div>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>
  
      {/* محتوا */}
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-border/30 p-3 min-h-[100px]">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}