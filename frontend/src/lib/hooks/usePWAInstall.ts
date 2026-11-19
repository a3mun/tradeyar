"use client";

import { useEffect, useState, useCallback } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export type PWAInstallState = {
  /** آیا می‌تونه نصب کنه (beforeinstallprompt دریافت شده) */
  canInstall: boolean;
  /** آیا از قبل نصب شده (standalone mode) */
  isInstalled: boolean;
  /** آیا iOS هست (Safari) */
  isIOS: boolean;
  /** آیا نصب در حال اجراست */
  isInstalling: boolean;
  /** تریگر نصب — فقط وقتی canInstall=true */
  triggerInstall: () => Promise<"accepted" | "dismissed" | "unavailable">;
};

export function usePWAInstall(): PWAInstallState {
  const [canInstall, setCanInstall] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    // تشخیص نصب بودن (standalone mode)
    const checkInstalled = () => {
      const standalone =
        window.matchMedia("(display-mode: standalone)").matches ||
        // @ts-expect-error - iOS Safari-specific
        window.navigator.standalone === true;
      setIsInstalled(standalone);
    };

    checkInstalled();

    // تشخیص iOS
    const ua = window.navigator.userAgent.toLowerCase();
    const isIOSDevice = /iphone|ipad|ipod/.test(ua) || (ua.includes("mac") && "ontouchend" in document);
    setIsIOS(isIOSDevice);

    // گوش دادن به beforeinstallprompt (فقط Chromium)
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setCanInstall(true);
    };

    window.addEventListener("beforeinstallprompt", handler);

    // گوش دادن به appinstalled
    const installedHandler = () => {
      setIsInstalled(true);
      setCanInstall(false);
      setDeferredPrompt(null);
    };
    window.addEventListener("appinstalled", installedHandler);

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", installedHandler);
    };
  }, []);

  const triggerInstall = useCallback(async () => {
    if (!deferredPrompt) return "unavailable" as const;

    setIsInstalling(true);
    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;

      if (outcome === "accepted") {
        setIsInstalled(true);
        setCanInstall(false);
      }
      setDeferredPrompt(null);
      return outcome;
    } catch {
      return "unavailable" as const;
    } finally {
      setIsInstalling(false);
    }
  }, [deferredPrompt]);

  return { canInstall, isInstalled, isIOS, isInstalling, triggerInstall };
}