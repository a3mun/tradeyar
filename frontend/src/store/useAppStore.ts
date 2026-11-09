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

// ═══ 🔴 فاز ۸ — سیگنال WS ═══
interface WsSignal {
  ticker: string;
  timeframe: string;
  source: string;
  data: any;
  receivedAt: number;
}

// 🔴 فاز C — استراتژی
export type Strategy = "scalp" | "swing" | "position";

// 🔴 فاز ۱۴.۷.۲ — cache مشترک برای TF
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

  // ─── سیگنال WS ───
  wsSignal: WsSignal | null;
  setWsSignal: (sig: WsSignal | null) => void;

  // 🔴 فاز ۱۴.۷.۲ — cache مشترک TF
  tfDataCache: Record<string, TfCacheEntry>;
  setTfData: (tf: string, data: AnalyzeResponse) => void;
  getTfData: (tf: string) => AnalyzeResponse | null;
  invalidateTfCache: () => void;

  // 🔴 فاز ۱۰.۲ — bottom sheet موبایل
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
  timeframe: "۱۵ دقیقه" as Timeframe,  // 🔴 فاز ۱۴.۷.۴ — از ۵د به ۱۵د
  marketType: "futures" as MarketType,
  riskProfile: "aggressive" as RiskProfile,
  strategy: "swing" as Strategy,
  watchlist: [] as WatchlistItem[],
  wsSignal: null as WsSignal | null,
  tfDataCache: {} as Record<string, TfCacheEntry>,
  mobileSheet: null as "settings" | "help" | "account" | null,
};

// 🔴 فاز ۱۰.۲ — تشخیص نماد بورس (کد کاراکتر > ۱۲۷)
function isTsetmcTicker(ticker: string): boolean {
  return Boolean(ticker) && ticker.charCodeAt(0) > 127;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      ...DEFAULTS,

      // ─── 🔴 فاز ۱۴.۷.۲ — cache مشترک TF ───
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
        if (entry.key !== expectedKey) {
          return null;
        }

        if (Date.now() - entry.fetchedAt > TF_CACHE_TTL_MS) {
          return null;
        }

        return entry.data;
      },

      invalidateTfCache: () => set({ tfDataCache: {} }),

      setSource: (source) => {
        set({ source });
        get().invalidateTfCache();
      },

      setTicker: (ticker, tickerName) => {
        if (isTsetmcTicker(ticker)) {
          set({
            ticker,
            tickerName: tickerName || ticker,
            source: "tsetmc" as Source,
            marketType: "spot" as MarketType,
            timeframe: "روزانه" as Timeframe,
          });
        } else {
          set({ ticker, tickerName: tickerName || ticker });
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
          });
        } else {
          set({ ticker, tickerName, source });
        }
        get().invalidateTfCache();
      },

      // 🔴 فاز C — تداخل‌زدایی TF
      setTimeframe: (timeframe) => {
        const updates: Partial<AppState> = { timeframe };
        const currentStrategy = get().strategy;

        // 🔴 اسکالپ: فقط ۱د و ۵د
        if (
          currentStrategy === "scalp" &&
          !["۱ دقیقه", "۵ دقیقه"].includes(timeframe)
        ) {
          updates.strategy = "swing";
        }

        // 🔴 فاز ۱۴.۷.۴ — پوزیشن: ۳۰د، ۱س، روزانه (قبلاً فقط روزانه)
        if (
          currentStrategy === "position" &&
          !["۳۰ دقیقه", "۱ ساعت", "روزانه"].includes(timeframe)
        ) {
          updates.strategy = "swing";
        }

        set(updates);

        if (updates.strategy && updates.strategy !== currentStrategy) {
          get().invalidateTfCache();
        }
      },

      // 🔴 فاز C — تداخل‌زدایی بازار
      setMarketType: (marketType) => {
        const updates: Partial<AppState> = { marketType };
        const currentStrategy = get().strategy;

        // اسکالپ + اسپات → ناسازگار (اسکالپ فقط futures)
        if (marketType === "spot" && currentStrategy === "scalp") {
          updates.strategy = "swing";
        }

        // 🔴 فاز ۱۴.۷.۴ — position + futures معنی‌دار شد (پوزیشن می‌تونه SHORT داشته باشه)
        // پس position + futures → position می‌مونه (نه swing)

        set(updates);
        get().invalidateTfCache();
      },

      // 🔴 فاز C — تداخل‌زدایی پروفایل
      setRiskProfile: (riskProfile) => {
        const updates: Partial<AppState> = { riskProfile };
        const currentStrategy = get().strategy;

        if (riskProfile === "conservative" && currentStrategy === "scalp") {
          updates.strategy = "swing";
        }

        set(updates);
        get().invalidateTfCache();
      },

      // 🔴 فاز ۱۴.۷.۴ — تنظیم استراتژی + تنظیمات همراه
      setStrategy: (strategy) => {
        const updates: Partial<AppState> = {
          strategy,
          wsSignal: null,
        };

        const currentTf = get().timeframe;

        if (strategy === "scalp") {
          // ═══ اسکالپ: futures + aggressive + TF پایین (اجباری) ═══
          updates.marketType = "futures";
          updates.riskProfile = "aggressive";
          if (!["۱ دقیقه", "۵ دقیقه"].includes(currentTf)) {
            updates.timeframe = "۵ دقیقه";
          }
        } else if (strategy === "position") {
          // ═══ پوزیشن: فقط TF اجبار (اگر مجاز نبود)، بازار/ریسک آزاد ═══
          if (!["۳۰ دقیقه", "۱ ساعت", "روزانه"].includes(currentTf)) {
            updates.timeframe = "روزانه";
          }
          // marketType و riskProfile رو تغییر نده
        }
        // ═══ سوئینگ: هیچ اجباری ═══

        set(updates);
        get().invalidateTfCache();
      },

      // ─── 🔴 فاز ۸ — سیگنال WS ───
      setWsSignal: (wsSignal) => set({ wsSignal }),

      // ─── 🔴 فاز ۱۰.۲ — mobile sheet ───
      setMobileSheet: (mobileSheet) => set({ mobileSheet }),

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
      version: 7,  // 🔴 فاز ۱۴.۷.۴ — از 6 به 7
      migrate: (persistedState: unknown, version: number) => {
        if (version < 7) {
          const old = (persistedState ?? {}) as Record<string, unknown>;
          return {
            source: (old.source as Source) ?? "nobitex",
            ticker: (old.ticker as string) ?? "BTC-USD",
            tickerName: (old.tickerName as string) ?? "بیت‌کوین (USDT)",
            timeframe: (old.timeframe as Timeframe) ?? "۱۵ دقیقه",
            marketType: (old.marketType as MarketType) ?? "futures",
            riskProfile: (old.riskProfile as RiskProfile) ?? "aggressive",
            strategy: (old.strategy as Strategy) ?? "swing",
            watchlist: Array.isArray(old.watchlist) ? old.watchlist : [],
          };
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