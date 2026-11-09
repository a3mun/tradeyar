"use client";

import { useEffect, useState } from "react";
import { Info } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

interface InfoToastProps {
  message: string | null;
  duration?: number;
  onClose: () => void;
}

export function InfoToast({ message, duration = 5000, onClose }: InfoToastProps) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(() => onClose(), duration);
    return () => clearTimeout(t);
  }, [message, duration, onClose]);

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.2 }}
          className="fixed top-20 left-1/2 z-50 -translate-x-1/2 w-[92%] max-w-md"
        >
          <div className="flex items-start gap-2 rounded-lg border border-[#d6ad60]/40 bg-[#0d1b2d] px-3 py-2 shadow-lg">
            <Info className="h-4 w-4 shrink-0 text-[#d6ad60] mt-0.5" />
            <p className="text-[10px] text-gray-200 leading-relaxed whitespace-pre-line">
              {message}
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
