"use client";

import { useEffect, useState } from "react";

/**
 * useDeviceType — تشخیص موبایل vs دسکتاپ
 * ============================================================
 * بر اساس `(hover: hover)` که:
 *   • دسکتاپ → hover داره
 *   • موبایل/تبلت → hover نداره (لمسی)
 */
export function useIsTouchDevice(): boolean {
  const [isTouch, setIsTouch] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(hover: none)");
    const update = () => setIsTouch(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  return isTouch;
}