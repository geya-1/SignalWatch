"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, ApiError } from "@/services/api";
import type { MarketQuote, ChangeEvent } from "@/types";
import { CardSkeleton } from "@/components/LoadingSkeleton";

export default function StockDetailPage() {
  const params = useParams<{ symbol: string }>();
  const router = useRouter();
  const symbol = decodeURIComponent(params.symbol).toUpperCase();

  const [quote, setQuote] = useState<MarketQuote | null>(null);
  const [changes, setChanges] = useState<ChangeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [quotes, allChanges] = await Promise.all([api.getMarketData(symbol), api.getChanges()]);
        if (cancelled) return;
        setQuote(quotes[0] ?? null);
        setChanges(allChanges.filter((c) => c.symbol === symbol));
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load this stock");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  if (loading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !quote) {
    return (
      <div className="rounded-card bg-surface p-6 text-center shadow-card">
        <p className="mb-4 text-sm text-danger">{error || `No data available for ${symbol}`}</p>
        <button onClick={() => router.push("/")} className="text-sm font-medium text-primary hover:underline">
          Back to your watchlist
        </button>
      </div>
    );
  }

  const isPositive = (quote.percent_change ?? 0) >= 0;
  const chartData = quote.chart_points.map((v, i) => ({ day: i + 1, price: v }));
  const latestChange = changes[0];

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => router.push("/")} className="mb-3 text-sm text-muted hover:text-gray-700">
          ← Back
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">{quote.symbol}</h1>
            <p className="text-sm text-muted">{quote.company_name}</p>
          </div>
          {quote.is_stale && (
            <span className="rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-muted">Last close</span>
          )}
        </div>
      </div>

      {quote.error ? (
        <div className="rounded-card bg-surface p-6 shadow-card">
          <p className="text-sm text-muted">
            Live data isn&apos;t available right now for this symbol. It may be delisted, invalid, or the
            provider is temporarily unreachable. Try again shortly.
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-card bg-surface p-6 shadow-card">
            <p className="text-3xl font-semibold text-gray-900">₹{quote.price?.toFixed(2)}</p>
            <p className={`text-sm font-medium ${isPositive ? "text-primary" : "text-danger"}`}>
              {isPositive ? "▲" : "▼"} {Math.abs(quote.percent_change ?? 0).toFixed(2)}% today
            </p>

            <div className="mt-4 h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F0F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis domain={["dataMin", "dataMax"]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v: number) => [`₹${v.toFixed(2)}`, "Price"]} labelFormatter={() => ""} />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke={isPositive ? "#00875A" : "#D64545"}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {latestChange && (
            <div className="rounded-card bg-surface p-6 shadow-card">
              <h2 className="mb-1 text-base font-semibold text-gray-900">Since your last visit</h2>
              <p className="mb-3 text-sm text-muted">
                {latestChange.price_then != null && latestChange.price_now != null
                  ? `₹${latestChange.price_then.toFixed(2)} → ₹${latestChange.price_now.toFixed(2)}`
                  : "No prior comparison available yet"}
              </p>
              <ul className="space-y-1.5 text-sm text-gray-700">
                {latestChange.reasons.map((reason, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="text-primary">•</span>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-card bg-surface p-6 shadow-card">
            <h2 className="mb-3 text-base font-semibold text-gray-900">Explanation timeline</h2>
            {changes.length === 0 ? (
              <p className="text-sm text-muted">No change events recorded yet for this stock.</p>
            ) : (
              <ol className="space-y-3 border-l border-gray-100 pl-4">
                {changes.map((c) => (
                  <li key={c.id} className="relative">
                    <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-primary" />
                    <p className="text-xs text-muted">{new Date(c.created_at).toLocaleString()}</p>
                    <p className="text-sm font-medium text-gray-900">{c.label} · score {c.score}</p>
                    <p className="text-xs text-muted">{c.reasons.join(" · ")}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </>
      )}
    </div>
  );
}
