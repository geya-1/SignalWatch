export function CardSkeleton() {
  return (
    <div className="animate-pulse rounded-card bg-surface p-4 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <div className="h-4 w-24 rounded bg-gray-200" />
        <div className="h-4 w-12 rounded bg-gray-200" />
      </div>
      <div className="mb-3 h-6 w-32 rounded bg-gray-200" />
      <div className="h-10 w-full rounded bg-gray-100" />
    </div>
  );
}

export function FeedSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}
