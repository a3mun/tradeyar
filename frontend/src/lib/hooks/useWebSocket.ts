/**
 * useWebSocket — re-export از Provider
 * ============================================================
 * برای import تمیزتر:
 *   import { useWebSocket } from "@/lib/hooks/useWebSocket";
 * جای:
 *   import { useWebSocket } from "@/lib/hooks/useWebSocketProvider";
 */

export {
  useWebSocket,
  WebSocketProvider,
  type QuoteData,
  type OrderBookData,
  type WSStatus,
} from "./useWebSocketProvider";