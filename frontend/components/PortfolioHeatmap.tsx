"use client";

import type { ChangeEvent, MarketQuote } from "@/types";

interface PortfolioHeatmapProps {
  quotes: MarketQuote[];
  changes: ChangeEvent[];
  onSelect: (symbol: string) => void;
}

const NEUTRAL_BAND = 0.1; // percent_change within +/-0.1% reads as "quiet", not a color call

function tileTone(quote: MarketQuote, change?: ChangeEvent): { dot: string; bg: string } {
  if (quote.error) return { dot: "bg-gray-300", bg: "bg-gray-50" };
  if (change?.label === "Quiet" || Math.abs(quote.percent_change ?? 0) < NEUTRAL_BAND) {
    return { dot: "bg-gray-400", bg: "bg-gray-50" };
  }
  if ((quote.percent_change ?? 0) > 0) {
    return { dot: "bg-primary", bg: "bg-primary-light" };
  }
  return { dot: "bg-danger", bg: "bg-red-50" };
}

export default function PortfolioHeatmap({ quotes, changes, onSelect }: PortfolioHeatmapProps) {
  if (quotes.length === 0) return null;
  const changeBySymbol = new Map(changes.map((c) => [c.symbol, c]));

  return (
    <div className="mb-6 rounded-card bg-surface p-5 shadow-card">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Portfolio Heatmap</h2>
      <div className="flex flex-wrap gap-2">
        {quotes.map((quote) => {
          const tone = tileTone(quote, changeBySymbol.get(quote.symbol));
          return (
            <button
              key={quote.symbol}
              onClick={() => onSelect(quote.symbol)}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium text-gray-800 transition-transform duration-150 hover:scale-105 ${tone.bg}`}
              title={`Jump to ${quote.symbol}`}
            >
              <span className={`h-2 w-2 rounded-full ${tone.dot}`} />
              {quote.symbol}
            </button>
          );
        })}
      </div>
    </div>
  );
}
