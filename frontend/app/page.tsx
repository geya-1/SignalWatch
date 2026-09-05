"use client";

import { useState } from "react";
import { useWatchlist } from "@/hooks/useWatchlist";
import { useMarket } from "@/hooks/useMarket";
import { useInsights } from "@/hooks/useInsights";
import MarketMood from "@/components/MarketMood";
import SnapshotReplay from "@/components/SnapshotReplay";
import PortfolioHeatmap from "@/components/PortfolioHeatmap";
import AttentionFeed from "@/components/AttentionFeed";
import QuickAttentionButton from "@/components/QuickAttentionButton";
import { FeedSkeleton } from "@/components/LoadingSkeleton";
import EmptyState from "@/components/EmptyState";

export default function HomePage() {
  const { items, loading: watchlistLoading, error: watchlistError, removeSymbol } = useWatchlist();
  const { quotes, changes, loading: marketLoading, error: marketError, refresh } = useMarket(items.length > 0);
  const { mood, replay, loading: insightsLoading } = useInsights(items.length > 0);

  const [highlightSymbol, setHighlightSymbol] = useState<string | null>(null);

  const loading = watchlistLoading || marketLoading;
  const importantCount = changes.filter((c) => c.label !== "Quiet").length;

  async function handleRemove(symbol: string) {
    await removeSymbol(symbol);
    await refresh();
  }

  function handleHeatmapSelect(symbol: string) {
    const target = document.getElementById(`stock-${symbol}`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlightSymbol(symbol);
    setTimeout(() => setHighlightSymbol(null), 2800);
  }

  return (
    <div>
      {!loading && items.length > 0 && (
        <>
          <MarketMood mood={mood} loading={insightsLoading} />
          <SnapshotReplay replay={replay} loading={insightsLoading} />
          <PortfolioHeatmap quotes={quotes} changes={changes} onSelect={handleHeatmapSelect} />
        </>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">What deserves your attention</h1>
        <p className="mt-1 text-sm text-muted">
          {importantCount > 0
            ? `${importantCount} stock${importantCount > 1 ? "s" : ""} changed meaningfully since your last visit.`
            : "Your watchlist is quiet right now — no major changes since you last checked."}
        </p>
      </div>

      {watchlistError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-danger">{watchlistError}</div>
      )}
      {marketError && !watchlistError && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-danger">{marketError}</div>
      )}

      {loading && <FeedSkeleton />}

      {!loading && items.length === 0 && (
        <EmptyState
          title="Your watchlist is empty"
          description="Add a stock to start tracking what actually changes, with a clear explanation every time."
          actionHref="/add"
          actionLabel="Add your first stock"
        />
      )}

      {!loading && items.length > 0 && quotes.length > 0 && (
        <AttentionFeed
          quotes={quotes}
          changes={changes}
          onRemove={handleRemove}
          highlightSymbol={highlightSymbol}
        />
      )}

      {!loading && items.length > 0 && quotes.length > 0 && (
        <QuickAttentionButton quotes={quotes} changes={changes} onHighlight={setHighlightSymbol} />
      )}
    </div>
  );
}
