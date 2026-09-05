"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/services/api";
import type { MarketMood, ReplayOut } from "@/types";

/**
 * Loads Market Mood and Today's Replay. Both are cheap, read-only
 * rollups of data the watchlist/market hooks already trigger the
 * computation for, so this hook just displays them -- it doesn't
 * duplicate any snapshotting or scoring logic.
 */
export function useInsights(hasWatchlist: boolean) {
  const [mood, setMood] = useState<MarketMood | null>(null);
  const [replay, setReplay] = useState<ReplayOut | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!hasWatchlist) {
      setMood(null);
      setReplay(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const results = await Promise.allSettled([api.getMarketMood(), api.getReplay()]);
    if (results[0].status === "fulfilled") setMood(results[0].value);
    if (results[1].status === "fulfilled") setReplay(results[1].value);
    setLoading(false);
  }, [hasWatchlist]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { mood, replay, loading, refresh };
}
