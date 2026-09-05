import AddStockForm from "@/components/AddStockForm";

export default function AddStockPage() {
  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-1 text-2xl font-semibold text-gray-900">Add a stock</h1>
      <p className="mb-6 text-sm text-muted">
        Track any NSE-listed symbol. We&apos;ll remember what you see today so we can tell you what changes
        next time.
      </p>
      <AddStockForm />
    </div>
  );
}
