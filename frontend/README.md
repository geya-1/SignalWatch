# SignalWatch — Frontend

Next.js 15 (App Router) + TypeScript + Tailwind CSS + Recharts.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm run dev
```

Runs at http://localhost:3000. Requires the backend API running (see `../backend/README.md` inline docs in `main.py`) at the URL set in `NEXT_PUBLIC_API_BASE_URL`.

## Structure

- `app/` — routes: `/` (Attention Feed / Home), `/add` (Add Stock), `/stock/[symbol]` (Stock Detail)
- `components/` — presentational + form components (StockCard, AttentionFeed, MiniChart, AddStockForm, EmptyState, LoadingSkeleton)
- `hooks/` — `useWatchlist`, `useMarket` encapsulate data fetching + loading/error state
- `services/api.ts` — single typed fetch client for the backend
- `types/` — shared TypeScript interfaces mirroring the backend's Pydantic schemas

## Testing

```bash
npm test
```

A `StockCard` component test lives in `__tests__/`. It is intentionally small; the goal is to prove the render + error-state paths work, not to exhaustively cover the UI.

## Deployment

Deploy to Vercel. Set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend's URL (e.g. a Render service) as an environment variable in the Vercel project settings.
