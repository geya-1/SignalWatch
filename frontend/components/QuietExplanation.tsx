interface QuietExplanationProps {
  reasons: string[];
}

/** Renders the Change Engine's deterministic reasons for a Quiet stock.
 * Every line comes straight from the backend's price/volume/breakout
 * checks -- nothing here is generated. */
export default function QuietExplanation({ reasons }: QuietExplanationProps) {
  if (!reasons.length) return null;

  return (
    <div className="mt-3 rounded-lg bg-gray-50 px-3 py-2">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted">Why Quiet?</p>
      <ul className="space-y-0.5 text-xs text-muted">
        {reasons.map((reason, idx) => (
          <li key={idx}>• {reason}</li>
        ))}
      </ul>
    </div>
  );
}
