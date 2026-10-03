import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { MarketType, RiskProfile, Source, Timeframe } from "@/lib/types";

interface WatchlistItem {
  ticker: string;
  name: string;
  source: string;
}

interface AppState {
  source: Source;
  ticker: string;
  tickerName: string;
  timeframe: Timeframe;
  marketType: MarketType;
  riskProfile: RiskProfile;
  refreshSeconds: number;
  watchlist: WatchlistItem[];

  setSource: (s: Source) => void;
  setTicker: (t: string, name?: string) => void;
  selectSymbol: (ticker: string, name: string, source: Source) => void;
  setTimeframe: (t: Timeframe) => void;
  setMarketType: (m: MarketType) => void;
  setRiskProfile: (r: RiskProfile) => void;
  setRefreshSeconds: (s: number) => void;
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
  refreshSeconds: 60,
  watchlist: [] as WatchlistItem[],
};

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...DEFAULTS,
      setSource: (source) => set({ source }),
      setTicker: (ticker, tickerName) =>
        set({ ticker, tickerName: tickerName || ticker }),

      // ─── انتخاب همزمان نماد + منبع ───
      selectSymbol: (ticker, tickerName, source) =>
        set({ ticker, tickerName, source }),
      setTimeframe: (timeframe) => set({ timeframe }),
      setMarketType: (marketType) => set({ marketType }),
      setRiskProfile: (riskProfile) => set({ riskProfile }),
      setRefreshSeconds: (refreshSeconds) => set({ refreshSeconds }),
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
      version: 3,
      partialize: (state) => ({
        source: state.source,
        ticker: state.ticker,
        tickerName: state.tickerName,
        timeframe: state.timeframe,
        marketType: state.marketType,
        riskProfile: state.riskProfile,
        refreshSeconds: state.refreshSeconds,
        watchlist: state.watchlist,
      }),
    }
  )
);