"use client";

import type { ChangeEvent, MarketQuote } from "@/types";
import StockCard from "./StockCard";

interface AttentionFeedProps {
  quotes: MarketQuote[];
  changes: ChangeEvent[];
  onRemove: (symbol: string) => void;
  highlightSymbol?: string | null;
}

/**
 * Homepage feed: splits the watchlist into "Priority Cards" (anything
 * Worth Checking or Important) and a compact "Quiet Watchlist" below it,
 * so the stocks that actually deserve attention aren't competing for
 * space with ones that don't. Both groups are still sorted by score,
 * highest first.
 */
export default function AttentionFeed({ quotes, changes, onRemove, highlightSymbol }: AttentionFeedProps) {
  const changeBySymbol = new Map(changes.map((c) => [c.symbol, c]));

  const bySymbolScore = (a: MarketQuote, b: MarketQuote) => {
    const scoreA = changeBySymbol.get(a.symbol)?.score ?? -1;
    const scoreB = changeBySymbol.get(b.symbol)?.score ?? -1;
    return scoreB - scoreA;
  };

  const priority = quotes
    .filter((q) => q.error || (changeBySymbol.get(q.symbol)?.label ?? "Quiet") !== "Quiet")
    .sort(bySymbolScore);
  const quiet = quotes
    .filter((q) => !q.error && (changeBySymbol.get(q.symbol)?.label ?? "Quiet") === "Quiet")
    .sort(bySymbolScore);

  return (
    <div className="space-y-8">
      {priority.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Priority Cards</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {priority.map((quote) => (
              <StockCard
                key={quote.symbol}
                quote={quote}
                change={changeBySymbol.get(quote.symbol)}
                onRemove={onRemove}
                highlighted={highlightSymbol === quote.symbol}
              />
            ))}
          </div>
        </div>
      )}

      {quiet.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Quiet Watchlist</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {quiet.map((quote) => (
              <StockCard
                key={quote.symbol}
                quote={quote}
                change={changeBySymbol.get(quote.symbol)}
                onRemove={onRemove}
                highlighted={highlightSymbol === quote.symbol}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
