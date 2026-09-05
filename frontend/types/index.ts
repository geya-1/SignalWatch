export interface WatchlistItem {
  id: number;
  symbol: string;
  added_at: string;
}

export interface MarketQuote {
  symbol: string;
  company_name?: string | null;
  price?: number | null;
  percent_change?: number | null;
  volume?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  prev_close?: number | null;
  chart_points: number[];
  last_updated: string;
  freshness?: "live" | "cached" | "market_closed";
  is_stale: boolean;
  error?: string | null;
}

export type ChangeLabel = "Quiet" | "Worth Checking" | "Important";

export interface ChangeEvent {
  id: number;
  symbol: string;
  score: number;
  label: ChangeLabel;
  reasons: string[];
  price_then?: number | null;
  price_now?: number | null;
  percent_change?: number | null;
  seen: boolean;
  created_at: string;
}

export interface SnapshotOut {
  id: number;
  symbol: string;
  price: number;
  volume?: number | null;
  timestamp: string;
}

export type MoodLabel = "Calm" | "Watchful" | "Active" | "Volatile";

export interface MarketMood {
  mood: MoodLabel;
  score: number;
  icon: string;
  color: string;
  important_count: number;
  worth_checking_count: number;
  explanation: string;
}

export interface ReplayPricePoint {
  symbol: string;
  price?: number | null;
}

export interface ReplayStage {
  label: string;
  prices: ReplayPricePoint[];
}

export interface ReplayOut {
  stages: ReplayStage[];
}
