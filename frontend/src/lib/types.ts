/**
 * TypeScript types — هم‌راستا با Pydantic schemas (api/schemas.py)
 */

export type Source =
  | "nobitex"
  | "bitpin"
  | "wallex"
  | "abantether"
  | "tsetmc";
export type MarketType = "spot" | "futures";
export type RiskProfile = "aggressive" | "conservative";

export type Timeframe =
  | "۱ دقیقه"
  | "۵ دقیقه"
  | "۱۵ دقیقه"
  | "۳۰ دقیقه"
  | "۱ ساعت"
  | "روزانه";

// ═══ Analyze ═══
export interface AnalyzeRequest {
  ticker: string;
  source: Source;
  timeframe: Timeframe;
  market_type: MarketType;
  risk_profile: RiskProfile;
  ticker_name?: string;
}

export interface AnalyzeResponse {
  ok: boolean;
  ticker: string;
  name: string;
  source: string;
  timeframe: string;
  market_type: string;
  risk_profile: string;
    close_series?: number[];

  // ═══ تحلیل ═══
  price: number;
  signal: string;
  direction: "long" | "short" | "neutral";
  confidence: number;
  confidence_tier: string;
  consensus: string;
  regime: string;
  action_fa: string;
  explanation: string;

  // ═══ SL/TP ═══
  sl: number | null;
  tp: number | null;
  rr: number | null;
  atr: number;
  atr_mult_sl: number;
  atr_mult_tp: number;

  // ═══ سطوح ═══
  support: number;
  resistance: number;
  pivots: Record<string, number>;
  swings: Record<string, unknown>;
  fibonacci: Record<string, unknown>;

  // ═══ گروه‌ها ═══
  groups: Record<string, GroupData>;
  votes_long: number;
  votes_short: number;
  votes_neutral: number;

  // ═══ متادیتا ═══
  reasons: string[];
  scenarios: Scenario[];
  traps: Record<string, TrapInfo>;
  traps_summary: Record<string, unknown>;
  divergence: { has_divergence: boolean; reason: string };
  multi_tf_info: string;
  multi_tf_ok: boolean;
  neutral_explain: { short?: string; long?: string; hint?: string };

  // ═══ extras ═══
  deep_analysis: string;
  checklist: ChecklistData;
  ai_export: string;
  fingerprint: string;

  timestamp: string;
}

export interface GroupData {
  vote: number;
  score: number;
  weight: number;
  strength: string;
  strength_fa: string;
  reasons: string[];
}

export interface Scenario {
  condition: string;
  action: string;
  probability: number;
  color: string;
  type: string;
  icon: string;
}

export interface TrapInfo {
  active: boolean;
  reason: string;
  severity: number;
}

// ═══ Checklist ═══
export interface ChecklistItem {
  group: string;
  label: string;
  icon: string;
  detail: string;
  reasons?: string[];
  score: number;
  weight: number;
  color: "green" | "red" | "yellow";
  vote?: number;
}

export interface ChecklistData {
  items: ChecklistItem[];
  percentage: number;
  final: string;
  final_color: "green" | "red" | "yellow";
}

// ═══ Fear & Greed ═══
export interface FearGreedResponse {
  ok: boolean;
  ticker: string;
  value: number;
  label: string;
  color: "red" | "yellow" | "green";
  icon: string;
}

// ═══ Symbols ═══
export interface SymbolItem {
  ticker: string;
  name: string;
  source: string;
  emoji?: string;
}

export interface SymbolsResponse {
  ok: boolean;
  total: number;
  items: SymbolItem[];
}

// ═══ Scan ═══
export interface ScanRequest {
  category:
    | "crypto"
    | "forex"
    | "us_stocks"
    | "commodities"
    | "indices"
    | "iran_stocks";
  timeframe: Timeframe;
  market_type: MarketType;
  risk_profile: RiskProfile;
  limit: number;
}

export interface ScanResponse {
  ok: boolean;
  category: string;
  timeframe: string;
  total: number;
  items: ScanItem[];
}

export interface ScanItem {
  ticker: string;
  name: string;
  price: number;
  signal: string;
  confidence: number;
  direction: "long" | "short" | "neutral";
}

// ═══ Backtest ═══
export interface BacktestStats {
  total: number;
  wins: number;
  losses: number;
  pending: number;
  expired: number;
  win_rate: number;
  profit_factor: number;
  avg_rr: number;
}

export interface BacktestResponse {
  ok: boolean;
  stats: BacktestStats;
  items: Record<string, unknown>[];
}