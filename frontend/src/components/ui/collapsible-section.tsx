"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CollapsibleSectionProps {
  id: string;
  title: string;
  icon?: string | React.ReactNode;
  subtitle?: string;
  accentColor?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

export function CollapsibleSection({
  id,
  title,
  icon,
  subtitle,
  accentColor = "#d6ad60",
  children,
  defaultOpen = false, // 🔴 پیش‌فرض: بسته
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-border/40 bg-[#0d1b2d] overflow-hidden shadow-sm">
      {/* هدر — همیشه قابل کلیک */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex w-full items-center justify-between p-3 text-right transition-colors hover:bg-white/5"
        style={{ borderRight: `3px solid ${accentColor}` }}
      >
        <div className="flex items-center gap-2">
          {icon && (
            <span className="text-lg" style={{ color: accentColor }}>
              {icon}
            </span>
          )}
          <div>
            <h3 className="text-sm font-bold text-foreground" style={{ color: accentColor }}>
              {title}
            </h3>
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
            {/* 🔴 حداقل ارتفاع برای جلوگیری از پرش Layout Shift */}
            <div className="border-t border-border/30 p-3 min-h-[100px]">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}