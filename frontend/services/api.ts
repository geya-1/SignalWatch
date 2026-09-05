/**
 * Thin API client for the SignalWatch backend.
 *
 * Centralized here so every request goes through one place that sets
 * the base URL, handles non-2xx responses consistently, and gives
 * callers a typed, predictable result -- rather than each component
 * doing its own fetch + error handling.
 */
import type { WatchlistItem, MarketQuote, ChangeEvent, SnapshotOut, MarketMood, ReplayOut } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (err) {
    // Network failure / backend unreachable -- surface a friendly error
    // instead of letting an uncaught fetch rejection break the UI.
    throw new ApiError("Could not reach the SignalWatch server. Is the backend running?", 0);
  }

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response body wasn't JSON -- keep the generic message
    }
    throw new ApiError(detail, res.status);
  }

  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export const api = {
  getWatchlist: () => request<WatchlistItem[]>("/watchlist"),

  addToWatchlist: (symbol: string) =>
    request<WatchlistItem>("/watchlist", {
      method: "POST",
      body: JSON.stringify({ symbol }),
    }),

  removeFromWatchlist: (symbol: string) =>
    request<{ detail: string }>(`/watchlist/${encodeURIComponent(symbol)}`, {
      method: "DELETE",
    }),

  getMarketData: (symbol?: string) =>
    request<MarketQuote[]>(symbol ? `/market?symbol=${encodeURIComponent(symbol)}` : "/market"),

  createSnapshot: (symbols?: string[]) =>
    request<SnapshotOut[]>("/snapshot", {
      method: "POST",
      body: JSON.stringify({ symbols }),
    }),

  getChanges: (unseenOnly = false) =>
    request<ChangeEvent[]>(`/changes${unseenOnly ? "?unseen_only=true" : ""}`),

  markSeen: (opts: { symbol?: string; changeEventId?: number; markAll?: boolean }) =>
    request<{ marked_seen: number }>("/mark-seen", {
      method: "POST",
      body: JSON.stringify({
        symbol: opts.symbol,
        change_event_id: opts.changeEventId,
        mark_all: opts.markAll ?? false,
      }),
    }),

  getMarketMood: () => request<MarketMood>("/mood"),

  getReplay: () => request<ReplayOut>("/replay"),
};
