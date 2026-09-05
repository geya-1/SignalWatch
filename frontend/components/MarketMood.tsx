"use client";

import type { MarketMood as MarketMoodType } from "@/types";
import Badge from "./Badge";

interface MarketMoodProps {
  mood: MarketMoodType | null;
  loading: boolean;
}

const toneForColor: Record<string, "grey" | "blue" | "orange" | "red"> = {
  grey: "grey",
  blue: "blue",
  orange: "orange",
  red: "red",
};

export default function MarketMood({ mood, loading }: MarketMoodProps) {
  if (loading) {
    return <div className="mb-6 h-24 animate-pulse rounded-card bg-surface shadow-card" />;
  }
  if (!mood) return null;

  return (
    <div className="mb-6 flex items-center gap-4 rounded-card bg-surface p-5 shadow-card">
      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary-light text-3xl">
        {mood.icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-gray-900">Market Mood: {mood.mood}</h2>
          <Badge label={`${mood.score}/100`} tone={toneForColor[mood.color] ?? "grey"} />
        </div>
        <p className="mt-0.5 text-sm text-muted">{mood.explanation}</p>
      </div>
    </div>
  );
}
