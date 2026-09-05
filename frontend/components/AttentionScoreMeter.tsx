interface AttentionScoreMeterProps {
  score: number;
}

/** Green = high confidence (Important), orange = worth checking, grey = quiet.
 * Mirrors the Change Engine's own label thresholds (30 / 60) so the bar
 * color always agrees with the badge next to it. */
function toneForScore(score: number): { bar: string; text: string } {
  if (score >= 60) return { bar: "bg-primary", text: "text-primary-dark" };
  if (score >= 30) return { bar: "bg-amber-500", text: "text-amber-700" };
  return { bar: "bg-gray-300", text: "text-muted" };
}

export default function AttentionScoreMeter({ score }: AttentionScoreMeterProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const { bar, text } = toneForScore(clamped);

  return (
    <div className="flex items-center gap-2" title={`Attention score: ${clamped}/100`}>
      <div className="h-1.5 w-full min-w-0 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full ${bar} transition-all duration-500 ease-out`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      <span className={`w-7 shrink-0 text-right text-[11px] font-semibold tabular-nums ${text}`}>{clamped}</span>
    </div>
  );
}
