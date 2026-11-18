import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  AnalyzeResponse,
  MarketType,
  RiskProfile,
  Source,
  Timeframe,
} from "@/lib/types";

import { sourceSupportsPair } from "@/lib/sources";

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

const TF_CACHE_TTL_MS = 120_000;

// 🔴 لیست نمادهای فارکس (یک‌جا تعریف شده تا تکرار نشه)
const FOREX_TICKERS = new Set([
  "XAU-USD", "XAG-USD", "USOIL-USD", "UKOIL-USD",
  "DXY-USD", "US500-USD", "US30-USD", "USTEC-USD",
  "EUR-USD", "DE30-USD",
]);

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
  // 🔴 اکشن جدید: انتخاب اجباری نماد (برای تب‌ها و کلیک روی آیتم‌ها)
  forceSelectSymbol: (ticker: string, name: string, source: Source) => void;
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

function isForexTicker(ticker: string): boolean {
  return FOREX_TICKERS.has(ticker);
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...DEFAULTS,

      // ─── cache ───
      setTfData: (tf, data) => {
        const state = get();
        const key = buildCacheKey(
          state.ticker,
          state.source,
          tf,
          state.marketType,
          state.riskProfile,
          state.strategy
        );
        set((prev) => ({
          tfDataCache: {
            ...prev.tfDataCache,
            [tf]: { data, fetchedAt: Date.now(), key },
          },
        }));
      },
      getTfData: (tf) => {
        const state = get();
        const entry = state.tfDataCache[tf];
        if (!entry) return null;
        const expectedKey = buildCacheKey(
          state.ticker,
          state.source,
          tf,
          state.marketType,
          state.riskProfile,
          state.strategy
        );
        if (entry.key !== expectedKey) return null;
        if (Date.now() - entry.fetchedAt > TF_CACHE_TTL_MS) return null;
        return entry.data;
      },
      invalidateTfCache: () => set({ tfDataCache: {} }),

      // ─── Source ───
      setSource: (source) => {
        const currentSource = get().source as string;
        const newSource = source as string;

        // اگر forex انتخاب شد، خودکار برو روی طلا
        if (newSource === "forex") {
          set({
            source,
            ticker: "XAU-USD",
            tickerName: "🥇 انس طلا",
            marketType: "futures" as MarketType,
            timeframe: "۱ ساعت" as Timeframe,
            strategy: "swing" as Strategy,
            riskProfile: "aggressive" as RiskProfile,
            wsSignal: null,
          });
          get().invalidateTfCache();
          return;
        }

        // اگر از forex به صرافی دیگه رفتیم، نماد بره روی بیت‌کوین
        if (currentSource === "forex" && newSource !== "forex") {
          set({
            source,
            ticker: "BTC-USD",
            tickerName: "بیت‌کوین (USDT)",
            timeframe: "۱۵ دقیقه" as Timeframe,
            wsSignal: null,
          });
          get().invalidateTfCache();
          return;
        }

        set({ source });
        get().invalidateTfCache();
      },

      // ─── انتخاب نماد با منطق هوشمند (keepCurrentSource) ───
      // این برای جستجوی دستی و ورود ticker خالیه
      setTicker: (ticker, tickerName) => {
        const finalName = tickerName || ticker;

        if (isTsetmcTicker(ticker)) {
          set({
            ticker,
            tickerName: finalName,
            source: "tsetmc" as Source,
            marketType: "spot" as MarketType,
            timeframe: "روزانه" as Timeframe,
            strategy: "swing" as Strategy,
            wsSignal: null,
          });
        } else if (isForexTicker(ticker)) {
          set({
            ticker,
            tickerName: finalName,
            source: "forex" as Source,
            marketType: "futures" as MarketType,
            timeframe: "۱ ساعت" as Timeframe,
            strategy: "swing" as Strategy,
            wsSignal: null,
          });
        } else {
          set({ ticker, tickerName: finalName, wsSignal: null });
        }
        get().invalidateTfCache();
      },

      selectSymbol: (ticker, tickerName, source) => {
        if (isTsetmcTicker(ticker)) {
          set({
            ticker,
            tickerName,
            source: "tsetmc" as Source,
            marketType: "spot" as MarketType,
            timeframe: "روزانه" as Timeframe,
            strategy: "swing" as Strategy,
            wsSignal: null,
          });
        } else if (isForexTicker(ticker)) {
          set({
            ticker,
            tickerName: tickerName || ticker,
            source: "forex" as Source,
            marketType: "futures" as MarketType,
            timeframe: "۱ ساعت" as Timeframe,
            strategy: "swing" as Strategy,
            wsSignal: null,
          });
        } else {
          // کریپتو: اگر source فعلی از این نماد پشتیبانی می‌کنه، نگهش دار
          const currentSource = get().source as string;
          const wasSpecialSource =
            currentSource === "tsetmc" || currentSource === "xaus";

          const keepCurrentSource = sourceSupportsPair(currentSource, ticker);
          const finalSource = keepCurrentSource ? currentSource : source;

          set({
            ticker,
            tickerName,
            source: finalSource as Source,
            wsSignal: null,
            ...(wasSpecialSource
              ? {
                  marketType: "futures" as MarketType,
                  timeframe: "۱۵ دقیقه" as Timeframe,
                  strategy: "swing" as Strategy,
                }
              : {}),
          });
        }
        get().invalidateTfCache();
      },

      // 🔴 جدید: انتخاب اجباری — همیشه source صریح رو ست می‌کنه
      // برای کلیک روی آیتم‌های لیست و تغییر تب استفاده می‌شه
      // 🔴 جدید: انتخاب اجباری — همیشه source صریح رو ست می‌کنه
      // برای کلیک روی آیتم‌های لیست و تغییر تب استفاده می‌شه
      forceSelectSymbol: (ticker, tickerName, source) => {
        const currentSource = get().source as string;
        const wasForex = currentSource === "forex";
        const wasTsetmc = currentSource === "tsetmc";
        const willBeForex = isForexTicker(ticker) || source === "forex";
        const willBeTsetmc = isTsetmcTicker(ticker) || source === "tsetmc";

        if (willBeTsetmc) {
          set({
            ticker,
            tickerName,
            source: "tsetmc" as Source,
            marketType: "spot" as MarketType,
            timeframe: "روزانه" as Timeframe,
            strategy: "swing" as Strategy,
            wsSignal: null,
          });
        } else if (willBeForex) {
          // 🔴 فاز ۱۶.۵ — اگه کاربر از قبل توی فارکس بود، TF/استراتژی رو نگه دار
          if (wasForex) {
            set({
              ticker,
              tickerName: tickerName || ticker,
              source: "forex" as Source,
              marketType: "futures" as MarketType,
              // ⚠️ timeframe و strategy رو عوض نکن
              wsSignal: null,
            });
          } else {
            // کاربر تازه وارد فارکس شده — TF/استراتژی پیش‌فرض
            set({
              ticker,
              tickerName: tickerName || ticker,
              source: "forex" as Source,
              marketType: "futures" as MarketType,
              timeframe: "۱ ساعت" as Timeframe,
              strategy: "swing" as Strategy,
              wsSignal: null,
            });
          }
        } else {
          // کریپتو (nobitex/bitpin/wallex/tabdeal)
          // 🔴 فاز ۱۶.۵ — اگه کاربر از قبل توی کریپتو بود، TF/استراتژی رو نگه دار
          const wasCrypto = !wasForex && !wasTsetmc;
          if (wasCrypto) {
            set({
              ticker,
              tickerName,
              source,
              marketType: "futures" as MarketType,
              // ⚠️ timeframe و strategy رو عوض نکن
              wsSignal: null,
            });
          } else {
            // کاربر تازه وارد کریپتو شده
            set({
              ticker,
              tickerName,
              source,
              marketType: "futures" as MarketType,
              timeframe: "۱۵ دقیقه" as Timeframe,
              strategy: "swing" as Strategy,
              wsSignal: null,
            });
          }
        }
        get().invalidateTfCache();
      },
      
      // ─── تنظیمات ───
      setTimeframe: (timeframe) => {
        const updates: Partial<AppState> = { timeframe };
        const currentStrategy = get().strategy;

        if (
          currentStrategy === "scalp" &&
          !["۱ دقیقه", "۵ دقیقه"].includes(timeframe)
        )
          updates.strategy = "swing";
        if (
          currentStrategy === "position" &&
          !["۳۰ دقیقه", "۱ ساعت", "روزانه"].includes(timeframe)
        )
          updates.strategy = "swing";

        set(updates);
        if (updates.strategy && updates.strategy !== currentStrategy)
          get().invalidateTfCache();
      },

      setMarketType: (marketType) => {
        const updates: Partial<AppState> = { marketType };
        const currentStrategy = get().strategy;
        if (marketType === "spot" && currentStrategy === "scalp")
          updates.strategy = "swing";
        set(updates);
        get().invalidateTfCache();
      },

      setRiskProfile: (riskProfile) => {
        const updates: Partial<AppState> = { riskProfile };
        const currentStrategy = get().strategy;
        if (riskProfile === "conservative" && currentStrategy === "scalp")
          updates.strategy = "swing";
        set(updates);
        get().invalidateTfCache();
      },

      setStrategy: (strategy) => {
        const updates: Partial<AppState> = { strategy, wsSignal: null };
        const currentTf = get().timeframe;

        if (strategy === "scalp") {
          updates.marketType = "futures";
          updates.riskProfile = "aggressive";
          if (!["۱ دقیقه", "۵ دقیقه"].includes(currentTf))
            updates.timeframe = "۵ دقیقه";
        } else if (strategy === "position") {
          if (!["۳۰ دقیقه", "۱ ساعت", "روزانه"].includes(currentTf))
            updates.timeframe = "روزانه";
        }
        set(updates);
        get().invalidateTfCache();
      },

      setWsSignal: (wsSignal) => set({ wsSignal }),
      setMobileSheet: (mobileSheet) => set({ mobileSheet }),

      addToWatchlist: (ticker, name, source) => {
        const current = get().watchlist;
        if (
          current.some((w) => w.ticker === ticker) ||
          current.length >= 20
        )
          return;
        set({ watchlist: [...current, { ticker, name, source }] });
      },
      removeFromWatchlist: (ticker) =>
        set({
          watchlist: get().watchlist.filter((w) => w.ticker !== ticker),
        }),
      reset: () => set(DEFAULTS),
    }),
    {
      name: "trademun-store",
      version: 10, // 🔴 نسخه بالا رفت چون رفتار عوض شد
      migrate: (persistedState: any, version: number) => {
        if (version < 10) {
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