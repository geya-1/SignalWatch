"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/services/api";

export default function AddStockForm() {
  const [symbol, setSymbol] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = symbol.trim().toUpperCase();
    if (!trimmed) {
      setError("Enter a stock symbol first");
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      await api.addToWatchlist(trimmed);
      setSuccess(`${trimmed} added to your watchlist`);
      setSymbol("");
      setTimeout(() => router.push("/"), 700);
    } catch (err) {
      // Surfaces backend validation (duplicate symbol -> 409) directly.
      setError(err instanceof ApiError ? err.message : "Something went wrong adding this symbol");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-card bg-surface p-6 shadow-card">
      <label htmlFor="symbol" className="mb-2 block text-sm font-medium text-gray-700">
        Stock symbol
      </label>
      <input
        id="symbol"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
        placeholder="e.g. RELIANCE, TCS, INFY"
        className="mb-3 w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
        disabled={submitting}
      />

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}
      {success && <p className="mb-3 text-sm text-primary">{success}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-full bg-primary px-4 py-2.5 text-sm font-medium text-white transition hover:bg-primary-dark disabled:opacity-60"
      >
        {submitting ? "Adding..." : "Add to watchlist"}
      </button>
    </form>
  );
}
