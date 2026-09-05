"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/services/api";
import type { MarketQuote, ChangeEvent } from "@/types";

/**
 * Drives the Home / Attention Feed page:
 * 1. Snapshot the watchlist (persists a fresh data point + computes change events)
 * 2. Load live quotes for the cards
 * 3. Load change events, sorted by score, for the attention feed
 *
 * Each step fails independently -- e.g. if snapshotting fails we still
 * try to show whatever live quotes we can get, rather than blanking the
 * whole page.
 */
export function useMarket(hasWatchlist: boolean) {
  const [quotes, setQuotes] = useState<MarketQuote[]>([]);
  const [changes, setChanges] = useState<ChangeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!hasWatchlist) {
      setQuotes([]);
      setChanges([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);

    try {
      await api.createSnapshot();
    } catch {
      // Non-fatal: we can still show live quotes even if snapshotting
      // (and therefore change-event computation) failed this round.
    }

    const results = await Promise.allSettled([api.getMarketData(), api.getChanges()]);

    if (results[0].status === "fulfilled") {
      setQuotes(results[0].value);
    } else {
      setError(
        results[0].reason instanceof ApiError
          ? results[0].reason.message
          : "Failed to load market data"
      );
    }

    if (results[1].status === "fulfilled") {
      setChanges(results[1].value);
    }

    setLoading(false);
  }, [hasWatchlist]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { quotes, changes, loading, error, refresh };
}
