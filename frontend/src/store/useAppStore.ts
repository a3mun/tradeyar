import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  AnalyzeResponse,
  MarketType,
  RiskProfile,
  Source,
  Timeframe,
} from "@/lib/types";

interface WatchlistItem {
  ticker: string;
  name: string;
  source: string;
}

interface WsSignal {
  ticker: string;
  timeframe: string;
  source: string;
  data: any;
  receivedAt: number;
}

export type Strategy = "scalp" | "swing" | "position";

interface TfCacheEntry {
  data: AnalyzeResponse;
  fetchedAt: number;
  key: string;
}

const TF_CACHE_TTL_MS = 30_000;

function buildCacheKey(
  ticker: string,
  source: string,
  tf: string,
  marketType: string,
  riskProfile: string,
  strategy: string
): string {
  return `${ticker}|${source}|${tf}|${marketType}|${riskProfile}|${strategy}`;
}

interface AppState {
  source: Source;
  ticker: string;
  tickerName: string;
  timeframe: Timeframe;
  marketType: MarketType;
  riskProfile: RiskProfile;
  strategy: Strategy;
  watchlist: WatchlistItem[];

  wsSignal: WsSignal | null;
  setWsSignal: (sig: WsSignal | null) => void;

  tfDataCache: Record<string, TfCacheEntry>;
  setTfData: (tf: string, data: AnalyzeResponse) => void;
  getTfData: (tf: string) => AnalyzeResponse | null;
  invalidateTfCache: () => void;

  mobileSheet: "settings" | "help" | "account" | null;
  setMobileSheet: (s: "settings" | "help" | "account" | null) => void;

  setSource: (s: Source) => void;
  setTicker: (t: string, name?: string) => void;
  selectSymbol: (ticker: string, name: string, source: Source) => void;
  setTimeframe: (t: Timeframe) => void;
  setMarketType: (m: MarketType) => void;
  setRiskProfile: (r: RiskProfile) => void;
  setStrategy: (s: Strategy) => void;
  addToWatchlist: (ticker: string, name: string, source: string) => void;
  removeFromWatchlist: (ticker: string) => void;
  reset: () => void;
}

const DEFAULTS = {
  source: "nobitex" as Source,
  ticker: "BTC-USD",
  tickerName: "بیت‌کوین (USDT)",
  timeframe: "۱۵ دقیقه" as Timeframe,
  marketType: "futures" as MarketType,
  riskProfile: "aggressive" as RiskProfile,
  strategy: "swing" as Strategy,
  watchlist: [] as WatchlistItem[],
  wsSignal: null as WsSignal | null,
  tfDataCache: {} as Record<string, TfCacheEntry>,
  mobileSheet: null as "settings" | "help" | "account" | null,
};

function isTsetmcTicker(ticker: string): boolean {
  return Boolean(ticker) && ticker.charCodeAt(0) > 127;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...DEFAULTS,

      // ─── cache ───
      setTfData: (tf, data) => {
        const state = get();
        const key = buildCacheKey(state.ticker, state.source, tf, state.marketType, state.riskProfile, state.strategy);
        set((prev) => ({ tfDataCache: { ...prev.tfDataCache, [tf]: { data, fetchedAt: Date.now(), key } } }));
      },
      getTfData: (tf) => {
        const state = get();
        const entry = state.tfDataCache[tf];
        if (!entry) return null;
        const expectedKey = buildCacheKey(state.ticker, state.source, tf, state.marketType, state.riskProfile, state.strategy);
        if (entry.key !== expectedKey) return null;
        if (Date.now() - entry.fetchedAt > TF_CACHE_TTL_MS) return null;
        return entry.data;
      },
      invalidateTfCache: () => set({ tfDataCache: {} }),

      // ─── Source ───
      setSource: (source) => {
        // 🔴 استفاده از as string برای رفع خطای TypeScript
        const currentSource = get().source as string;
        const newSource = source as string;

        // اگر xaus انتخاب شد، خودکار برو روی طلا
        if (newSource === "xaus") {
          set({
            source,
            ticker: "XAU-USD",
            tickerName: "🥇 انس طلا",
            marketType: "spot" as MarketType,
            timeframe: "۱ ساعت" as Timeframe,
            strategy: "swing" as Strategy,
            riskProfile: "aggressive" as RiskProfile,
          });
          get().invalidateTfCache();
          return;
        }
        
        // اگر از xaus به صرافی دیگه رفتیم، نماد بره روی بیت‌کوین
        if (currentSource === "xaus" && newSource !== "xaus") {
           set({ 
             source, 
             ticker: "BTC-USD", 
             tickerName: "بیت‌کوین (USDT)",
             timeframe: "۱۵ دقیقه" as Timeframe 
           });
           get().invalidateTfCache();
           return;
        }

        set({ source });
        get().invalidateTfCache();
      },

      setTicker: (ticker, tickerName) => {
        if (isTsetmcTicker(ticker)) {
          set({ ticker, tickerName: tickerName || ticker, source: "tsetmc" as Source, marketType: "spot" as MarketType, timeframe: "روزانه" as Timeframe });
        } else if (ticker === "XAU-USD") {
          set({ ticker, tickerName: tickerName || "🥇 انس طلا", source: "xaus" as Source, marketType: "spot" as MarketType, timeframe: "۱ ساعت" as Timeframe });
        } else {
          set({ ticker, tickerName: tickerName || ticker });
        }
        get().invalidateTfCache();
      },

      selectSymbol: (ticker, tickerName, source) => {
        if (isTsetmcTicker(ticker)) {
          set({ ticker, tickerName, source: "tsetmc" as Source, marketType: "spot" as MarketType, timeframe: "روزانه" as Timeframe });
        } else if (ticker === "XAU-USD") {
          set({ ticker, tickerName, source: "xaus" as Source, marketType: "spot" as MarketType, timeframe: "۱ ساعت" as Timeframe, strategy: "swing" as Strategy });
        } else {
          set({ ticker, tickerName, source });
        }
        get().invalidateTfCache();
      },

      // ─── تنظیمات ───
      setTimeframe: (timeframe) => {
        const updates: Partial<AppState> = { timeframe };
        const currentStrategy = get().strategy;

        if (currentStrategy === "scalp" && !["۱ دقیقه", "۵ دقیقه"].includes(timeframe)) updates.strategy = "swing";
        if (currentStrategy === "position" && !["۳۰ دقیقه", "۱ ساعت", "روزانه"].includes(timeframe)) updates.strategy = "swing";

        set(updates);
        if (updates.strategy && updates.strategy !== currentStrategy) get().invalidateTfCache();
      },

      setMarketType: (marketType) => {
        const updates: Partial<AppState> = { marketType };
        const currentStrategy = get().strategy;
        if (marketType === "spot" && currentStrategy === "scalp") updates.strategy = "swing";
        set(updates);
        get().invalidateTfCache();
      },

      setRiskProfile: (riskProfile) => {
        const updates: Partial<AppState> = { riskProfile };
        const currentStrategy = get().strategy;
        if (riskProfile === "conservative" && currentStrategy === "scalp") updates.strategy = "swing";
        set(updates);
        get().invalidateTfCache();
      },

      setStrategy: (strategy) => {
        const updates: Partial<AppState> = { strategy, wsSignal: null };
        const currentTf = get().timeframe;

        if (strategy === "scalp") {
          updates.marketType = "futures";
          updates.riskProfile = "aggressive";
          if (!["۱ دقیقه", "۵ دقیقه"].includes(currentTf)) updates.timeframe = "۵ دقیقه";
        } else if (strategy === "position") {
          if (!["۳۰ دقیقه", "۱ ساعت", "روزانه"].includes(currentTf)) updates.timeframe = "روزانه";
        }
        set(updates);
        get().invalidateTfCache();
      },

      setWsSignal: (wsSignal) => set({ wsSignal }),
      setMobileSheet: (mobileSheet) => set({ mobileSheet }),

      addToWatchlist: (ticker, name, source) => {
        const current = get().watchlist;
        if (current.some((w) => w.ticker === ticker) || current.length >= 20) return;
        set({ watchlist: [...current, { ticker, name, source }] });
      },
      removeFromWatchlist: (ticker) => set({ watchlist: get().watchlist.filter((w) => w.ticker !== ticker) }),
      reset: () => set(DEFAULTS),
    }),
    {
      name: "trademun-store",
      version: 9,
      migrate: (persistedState: any, version: number) => {
        if (version < 9) {
          return { ...DEFAULTS, ...persistedState };
        }
        return persistedState;
      },
      partialize: (state) => ({
        source: state.source,
        ticker: state.ticker,
        tickerName: state.tickerName,
        timeframe: state.timeframe,
        marketType: state.marketType,
        riskProfile: state.riskProfile,
        strategy: state.strategy,
        watchlist: state.watchlist,
      }),
    }
  )
);