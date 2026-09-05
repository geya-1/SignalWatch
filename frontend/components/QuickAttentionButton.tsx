"use client";

import { useState } from "react";
import type { ChangeEvent, MarketQuote } from "@/types";

interface QuickAttentionButtonProps {
  quotes: MarketQuote[];
  changes: ChangeEvent[];
  onHighlight: (symbol: string | null) => void;
}

/**
 * Finds the single stock most worth looking at right now (highest
 * Change Engine score) and scrolls straight to it, briefly glowing the
 * card so it's obvious what just happened. Works identically in Demo
 * Mode since it only reads whatever scores are already on screen.
 */
export default function QuickAttentionButton({ quotes, changes, onHighlight }: QuickAttentionButtonProps) {
  const [message, setMessage] = useState<string | null>(null);

  if (quotes.length === 0) return null;

  function handleClick() {
    const changeBySymbol = new Map(changes.map((c) => [c.symbol, c]));
    let best: { symbol: string; score: number } | null = null;
    for (const quote of quotes) {
      const score = changeBySymbol.get(quote.symbol)?.score ?? -1;
      if (score > 0 && (best === null || score > best.score)) {
        best = { symbol: quote.symbol, score };
      }
    }

    if (!best) {
      setMessage("Everything looks quiet.");
      setTimeout(() => setMessage(null), 2200);
      return;
    }

    const target = document.getElementById(`stock-${best.symbol}`);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    onHighlight(best.symbol);
    setTimeout(() => onHighlight(null), 2800);
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-2">
      {message && (
        <div className="animate-fadein rounded-full bg-gray-900/90 px-4 py-2 text-xs font-medium text-white shadow-lg">
          {message}
        </div>
      )}
      <button
        onClick={handleClick}
        className="flex items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-semibold text-white shadow-lg transition-transform duration-150 hover:scale-105 hover:bg-primary-dark active:scale-95"
      >
        <span>⚡</span>
        Quick Attention
      </button>
    </div>
  );
}
