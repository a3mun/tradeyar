"use client";

import { useEffect, useRef, useState } from "react";
import { getToken } from "@/lib/auth";

export type AdminNotification = {
  type: string;
  id?: number;
  user_phone?: string;
  full_name?: string;
  plan?: string;
  message?: string;
};

export function useAdminNotifications(onMessage: (n: AdminNotification) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const callbackRef = useRef(onMessage);
  callbackRef.current = onMessage;

  useEffect(() => {
    const token = getToken();
    if (!token) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    const wsUrl = apiUrl
      .replace("https://", "wss://")
      .replace("http://", "ws://")
      + `/admin/ws/notifications?token=${token}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // ping هر ۳۰ ثانیه برای زنده نگه‌داشتن
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
      }, 30000);
      (ws as any)._pingInterval = ping;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        callbackRef.current(data);
      } catch {}
    };

    ws.onclose = () => {
      setConnected(false);
      if ((ws as any)._pingInterval) clearInterval((ws as any)._pingInterval);
    };

    return () => {
      if ((ws as any)._pingInterval) clearInterval((ws as any)._pingInterval);
      ws.close();
    };
  }, []);

  return { connected };
}