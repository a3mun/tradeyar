import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { MarketType, RiskProfile, Source, Timeframe } from "@/lib/types";

interface WatchlistItem {
  ticker: string;
  name: string;
  source: string;
}

// ═══ 🔴 فاز ۸ — سیگنال WS ═══
interface WsSignal {
  ticker: string;
  timeframe: string;
  source: string;
  data: any; // AnalyzeResponse-like
  receivedAt: number;
}

interface AppState {
  source: Source;
  ticker: string;
  tickerName: string;
  timeframe: Timeframe;
  marketType: MarketType;
  riskProfile: RiskProfile;
  watchlist: WatchlistItem[];

  // ─── سیگنال WS ───
  wsSignal: WsSignal | null;
  setWsSignal: (sig: WsSignal | null) => void;

  setSource: (s: Source) => void;
  setTicker: (t: string, name?: string) => void;
  selectSymbol: (ticker: string, name: string, source: Source) => void;
  setTimeframe: (t: Timeframe) => void;
  setMarketType: (m: MarketType) => void;
  setRiskProfile: (r: RiskProfile) => void;
  addToWatchlist: (ticker: string, name: string, source: string) => void;
  removeFromWatchlist: (ticker: string) => void;
  reset: () => void;
}

const DEFAULTS = {
  source: "nobitex" as Source,
  ticker: "BTC-USD",
  tickerName: "بیت‌کوین (USDT)",
  timeframe: "۵ دقیقه" as Timeframe,
  marketType: "futures" as MarketType,
  riskProfile: "aggressive" as RiskProfile,
  watchlist: [] as WatchlistItem[],
  wsSignal: null as WsSignal | null,
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...DEFAULTS,
      setSource: (source) => set({ source }),
      setTicker: (ticker, tickerName) =>
        set({ ticker, tickerName: tickerName || ticker }),

      selectSymbol: (ticker, tickerName, source) =>
        set({ ticker, tickerName, source }),
      setTimeframe: (timeframe) => set({ timeframe }),
      setMarketType: (marketType) => set({ marketType }),
      setRiskProfile: (riskProfile) => set({ riskProfile }),

      // ─── 🔴 فاز ۸ — سیگنال WS ───
      setWsSignal: (wsSignal) => set({ wsSignal }),

      addToWatchlist: (ticker, name, source) => {
        const current = get().watchlist;
        if (current.some((w) => w.ticker === ticker)) return;
        if (current.length >= 20) return;
        set({ watchlist: [...current, { ticker, name, source }] });
      },
      removeFromWatchlist: (ticker) => {
        set({ watchlist: get().watchlist.filter((w) => w.ticker !== ticker) });
      },
      reset: () => set(DEFAULTS),
    }),
    {
      name: "trademun-store",
      version: 4,
      partialize: (state) => ({
        source: state.source,
        ticker: state.ticker,
        tickerName: state.tickerName,
        timeframe: state.timeframe,
        marketType: state.marketType,
        riskProfile: state.riskProfile,
        watchlist: state.watchlist,
        // ⚠️ wsSignal رو persist نمی‌کنیم (داده لحظه‌ایه)
      }),
    }
  )
);