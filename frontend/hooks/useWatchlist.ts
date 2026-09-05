"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/services/api";
import type { WatchlistItem } from "@/types";

/**
 * Loads and mutates the user's watchlist. Keeps loading/error state local
 * so pages can render skeletons and error banners without duplicating
 * that logic everywhere a watchlist is displayed.
 */
export function useWatchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWatchlist();
      setItems(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const addSymbol = useCallback(
    async (symbol: string) => {
      await api.addToWatchlist(symbol);
      await refresh();
    },
    [refresh]
  );

  const removeSymbol = useCallback(
    async (symbol: string) => {
      await api.removeFromWatchlist(symbol);
      await refresh();
    },
    [refresh]
  );

  return { items, loading, error, refresh, addSymbol, removeSymbol };
}
