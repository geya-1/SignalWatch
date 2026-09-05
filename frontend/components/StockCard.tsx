"use client";

import Link from "next/link";
import type { MarketQuote, ChangeEvent } from "@/types";
import MiniChart from "./MiniChart";
import Badge from "./Badge";
import AttentionScoreMeter from "./AttentionScoreMeter";
import QuietExplanation from "./QuietExplanation";

interface StockCardProps {
  quote: MarketQuote;
  change?: ChangeEvent;
  onRemove?: (symbol: string) => void;
  highlighted?: boolean;
}

const freshnessLabel: Record<string, string> = {
  cached: "Cached",
  market_closed: "Last close",
};

export default function StockCard({ quote, change, onRemove, highlighted }: StockCardProps) {
  const isPositive = (quote.percent_change ?? 0) >= 0;
  const anchorId = `stock-${quote.symbol}`;

  if (quote.error) {
    return (
      <div id={anchorId} className="rounded-card bg-surface p-4 shadow-card">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-gray-900">{quote.symbol}</span>
          {onRemove && (
            <button onClick={() => onRemove(quote.symbol)} className="text-xs text-muted hover:text-danger">
              Remove
            </button>
          )}
        </div>
        <p className="mt-2 text-sm text-muted">
          Live data isn&apos;t available right now for this symbol. It may be delisted, invalid, or the market
          data provider is temporarily unreachable.
        </p>
      </div>
    );
  }

  const freshnessTag = quote.freshness && quote.freshness !== "live" ? freshnessLabel[quote.freshness] : null;
  const isQuiet = !change || change.label === "Quiet";

  return (
    <div
      id={anchorId}
      className={`rounded-card bg-surface p-4 shadow-card transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg ${
        highlighted ? "ring-2 ring-primary ring-offset-2 ring-offset-background animate-glow" : ""
      }`}
    >
      <div className="mb-2 flex items-start justify-between">
        <div>
          <Link href={`/stock/${quote.symbol}`} className="font-semibold text-gray-900 hover:underline">
            {quote.symbol}
          </Link>
          <p className="truncate text-xs text-muted">{quote.company_name}</p>
        </div>
        {change && <Badge label={change.label} />}
      </div>

      <div className="mb-2 flex items-end justify-between">
        <div>
          <p className="text-xl font-semibold text-gray-900">
            {quote.price != null ? `₹${quote.price.toFixed(2)}` : "—"}
          </p>
          <p className={`text-sm font-medium ${isPositive ? "text-primary" : "text-danger"}`}>
            {isPositive ? "▲" : "▼"} {Math.abs(quote.percent_change ?? 0).toFixed(2)}%
          </p>
        </div>
        {freshnessTag && <Badge label={freshnessTag} tone="grey" />}
      </div>

      <MiniChart points={quote.chart_points} positive={isPositive} />

      {change && (
        <div className="mt-3 border-t border-gray-100 pt-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className="text-[11px] font-medium text-muted">Attention Score</span>
            <div className="w-28">
              <AttentionScoreMeter score={change.score} />
            </div>
          </div>

          {isQuiet ? (
            <QuietExplanation reasons={change.reasons} />
          ) : (
            change.reasons.length > 0 && (
              <ul className="space-y-1 text-xs text-muted">
                {change.reasons.slice(0, 3).map((reason, idx) => (
                  <li key={idx}>• {reason}</li>
                ))}
              </ul>
            )
          )}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-[11px] text-muted">
        <span>Updated {new Date(quote.last_updated).toLocaleTimeString()}</span>
        {onRemove && (
          <button onClick={() => onRemove(quote.symbol)} className="hover:text-danger">
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
