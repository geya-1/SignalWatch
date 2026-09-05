"use client";

import { useState } from "react";
import type { ReplayOut } from "@/types";

interface SnapshotReplayProps {
  replay: ReplayOut | null;
  loading: boolean;
}

export default function SnapshotReplay({ replay, loading }: SnapshotReplayProps) {
  const [activeIdx, setActiveIdx] = useState(0);

  if (loading) {
    return <div className="mb-6 h-40 animate-pulse rounded-card bg-surface shadow-card" />;
  }
  if (!replay || replay.stages.length === 0) return null;

  const activeStage = replay.stages[Math.min(activeIdx, replay.stages.length - 1)];

  return (
    <div className="mb-6 rounded-card bg-surface p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Today&apos;s Replay</h2>
        <div className="flex gap-1 rounded-full bg-gray-100 p-1">
          {replay.stages.map((stage, idx) => (
            <button
              key={stage.label}
              onClick={() => setActiveIdx(idx)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors duration-200 ${
                idx === activeIdx ? "bg-primary text-white shadow-sm" : "text-muted hover:text-gray-900"
              }`}
            >
              {stage.label}
            </button>
          ))}
        </div>
      </div>

      <div key={activeStage.label} className="flex flex-wrap gap-3 animate-fadein">
        {activeStage.prices.map((p) => (
          <div key={p.symbol} className="min-w-[96px] flex-1 rounded-lg bg-gray-50 px-3 py-2">
            <p className="text-xs font-medium text-muted">{p.symbol}</p>
            <p className="text-sm font-semibold text-gray-900">
              {p.price != null ? `₹${p.price.toFixed(2)}` : "—"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
