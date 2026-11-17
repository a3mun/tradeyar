"use client";

/**
 * useWebSocketProvider — اتصال WebSocket مرکزی
 * ============================================================
 * نسخه ۲.۱ · فاز ۱۶.۵
 *
 * 🔴 تغییرات نسخه ۲.۱:
 *   • رفع باگ closure در sendSubscribe (استفاده از useRef)
 *   • استفاده از NEXT_PUBLIC_WS_URL در صورت وجود
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useAppStore } from "@/store/useAppStore";
import { useDataLoop } from "./useDataLoop"; // مسیر رو چک کن فایل useDataLoop.ts رو کجا ساختی

// ═══ Types ═══
export interface QuoteData {
  ticker: string;
  price: number;
  change_pct: number;
  source: string;
}

export interface OrderBookData {
  ok: boolean;
  ticker: string;
  source: string;
  imbalance: number;
  spread_pct: number;
  pressure_fa: string;
  has_bid_wall: boolean;
  has_ask_wall: boolean;
  wall?: {
    side: string;
    price: number;
    quantity: number;
    ratio: number;
  } | null;
  execution_cost?: {
    fee_pct: number;
    spread_cost_pct: number;
    slippage_pct: number;
    total_pct: number;
  };
}

export type WSStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

interface WSContextValue {
  quote: QuoteData | null;
  orderbook: OrderBookData | null;
  status: WSStatus;
}

const WSContext = createContext<WSContextValue>({
  quote: null,
  orderbook: null,
  status: "idle",
});

// ═══ Backoff ═══
const BACKOFF_STEPS = [1000, 2000, 4000, 8000, 16000, 30000];
const PING_INTERVAL = 25_000;

// ═══ WS URL ═══
function buildWsUrl(): string {
  // اگر متغیر NEXT_PUBLIC_WS_URL تنظیم شده باشد، از آن استفاده کن
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  // در غیر این صورت از NEXT_PUBLIC_API_URL بساز
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const wsBase = apiUrl.replace(/^http/, "ws");
  return `${wsBase}/api/ws/live`;
}

// ═══ Provider ═══
export function WebSocketProvider({ children }: { children: ReactNode }) {
  const { ticker, tickerName, source, timeframe, marketType, riskProfile, strategy } =
    useAppStore();
  
  const [quote, setQuote] = useState<QuoteData | null>(null);
  const [orderbook, setOrderbook] = useState<OrderBookData | null>(null);
  const [status, setStatus] = useState<WSStatus>("idle");

  const wsRef = useRef<WebSocket | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffIdxRef = useRef(0);
  const mountedRef = useRef(false);

  // ─── ticker فعلی برای فیلتر پیام‌ها ───
  const tickerRef = useRef(ticker);
  useEffect(() => {
    tickerRef.current = ticker;
  }, [ticker]);

  // ─── ارسال subscribe ───
  const sendSubscribe = useCallback(
    (ws: WebSocket) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      ws.send(
        JSON.stringify({
          type: "subscribe",
          ticker,
          source,
          timeframe,
          market_type: marketType,
          risk_profile: riskProfile,
          ticker_name: tickerName,
          strategy, // 🔴 فاز ۱۶.۵ — پاس دادن strategy تا بک‌اند هم‌خوان با TFTable تحلیل کنه
        })
      );
    },
    [ticker, source, timeframe, marketType, riskProfile, tickerName, strategy]
  );
  
  // 🔴 رفع باگ: نگهداری آخرین نسخه از sendSubscribe در یک Ref
  const sendSubscribeRef = useRef(sendSubscribe);
  useEffect(() => {
    sendSubscribeRef.current = sendSubscribe;
  }, [sendSubscribe]);

  // ─── اتصال ───
  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    setStatus(backoffIdxRef.current === 0 ? "connecting" : "reconnecting");

    const url = buildWsUrl();
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      setStatus("disconnected");
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      backoffIdxRef.current = 0;
      setStatus("connected");

      // 🔴 استفاده از آخرین نسخه sendSubscribe از Ref
      sendSubscribeRef.current(ws);

      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      pingTimerRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (e) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(e.data);
        const currentTicker = tickerRef.current;

        if (msg.type === "quote") {
          if (msg.data?.ticker && msg.data.ticker !== currentTicker) return;
          setQuote(msg.data);
        } else if (msg.type === "orderbook") {
          if (msg.data?.ticker && msg.data.ticker !== currentTicker) return;
          setOrderbook(msg.data);
        }
        // 🔴 فاز ۱۶.۵ — handler سیگنال حذف شد
        // دلیل: WS signal باعث باگ close/open loop و تناقض با TFTable می‌شد.
        // حالا SignalCard خودش analyze_multi polling می‌کنه (هم‌خوان با TFTable).
      } catch {
        // JSON نامعتبر → نادیده
      }
    };
    
    ws.onclose = () => {
      if (pingTimerRef.current) {
        clearInterval(pingTimerRef.current);
        pingTimerRef.current = null;
      }
      if (!mountedRef.current) return;

      const wasClean =
        ws.readyState === WebSocket.CLOSED && backoffIdxRef.current === 0;

      if (wasClean) {
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, 100);
      } else {
        const idx = Math.min(backoffIdxRef.current, BACKOFF_STEPS.length - 1);
        const delay = BACKOFF_STEPS[idx];
        backoffIdxRef.current = idx + 1;

        setStatus("reconnecting");
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) connect();
        }, delay);
      }
    };
  }, []); // 🔴 connect دیگر به sendSubscribe وابسته نیست

  // ═══ mount: باز کردن اتصال ═══
  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          // نادیده
        }
        wsRef.current = null;
      }
    };
  }, [connect]);

  // ═══ تغییر تنظیمات: پاک کردن + subscribe جدید ═══
  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    setQuote(null);
    setOrderbook(null);

    // 🔴 ارسال subscribe جدید با نسخه به‌روز از sendSubscribe
    sendSubscribeRef.current(ws);
  }, [sendSubscribe]); // این useEffect با تغییر تنظیمات اجرا می‌شود


  // 🔴 فاز ۱۶.۵ — شروع حلقه مرکزی دیتا
  useDataLoop();

  return (
    <WSContext.Provider value={{ quote, orderbook, status }}>
      {children}
    </WSContext.Provider>
  );

}

// ═══ Hook مصرف‌کننده ═══
export function useWebSocket(): WSContextValue {
  return useContext(WSContext);
}