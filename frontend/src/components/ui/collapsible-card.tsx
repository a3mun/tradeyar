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
  isLocked?: boolean;
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
    <div
      className={`group rounded-xl border bg-[#051118] shadow-md overflow-hidden transition-all duration-300 ${
        isOpen
          ? "border-[#d6ad60]/50 bg-[#0a1a2f] shadow-[0_0_20px_rgba(214,173,96,0.15)]"
          : "border-white/10 hover:border-[#d6ad60]/40 hover:bg-[#0a1a2f] hover:shadow-[0_0_15px_rgba(214,173,96,0.1)]"
      }`}
    >
      <button
        onClick={() => setIsOpen((v) => !v)}
        className={`flex w-full items-center justify-between p-3 text-right transition-colors duration-300 ${
          isOpen ? "bg-[#d6ad60]/5" : "hover:bg-[#d6ad60]/5"
        }`}
      >
        <div className="flex items-center gap-2">
          {icon && (
            <span className="flex items-center justify-center text-[#d6ad60] transition-transform duration-300 group-hover:scale-110">
              {icon}
            </span>
          )}
          <div>
            <div className="flex items-center gap-2">
              <h3 className={`text-sm font-bold transition-colors duration-300 ${isOpen ? "text-[#d6ad60]" : "text-foreground group-hover:text-[#d6ad60]"}`}>
                {title}
              </h3>
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
          className={`h-4 w-4 shrink-0 transition-all duration-300 ${
            isOpen ? "rotate-180 text-[#d6ad60]" : "text-muted-foreground group-hover:text-[#d6ad60]"
          }`}
        />
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="border-t border-[#d6ad60]/10 p-3 min-h-[100px]">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}