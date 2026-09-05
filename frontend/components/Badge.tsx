interface BadgeProps {
  label: string;
  tone?: "red" | "orange" | "grey" | "green" | "blue";
  className?: string;
}

const toneStyles: Record<NonNullable<BadgeProps["tone"]>, string> = {
  red: "bg-red-50 text-danger",
  orange: "bg-amber-50 text-amber-700",
  grey: "bg-gray-100 text-muted",
  green: "bg-primary-light text-primary-dark",
  blue: "bg-blue-50 text-blue-700",
};

/** Maps a Change Engine label straight to the tone the rest of the app
 * already used for it, so callers don't have to know the mapping. */
const labelTone: Record<string, BadgeProps["tone"]> = {
  Important: "red",
  "Worth Checking": "orange",
  Quiet: "grey",
};

export default function Badge({ label, tone, className = "" }: BadgeProps) {
  const resolvedTone = tone ?? labelTone[label] ?? "grey";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${toneStyles[resolvedTone]} ${className}`}
    >
      {label}
    </span>
  );
}
