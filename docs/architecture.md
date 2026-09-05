# Architecture

See `architecture.svg` for the visual diagram (open it in a browser — vector, so it stays crisp at any zoom; a `.png` render isn't included because the sandbox this was built in had no `rsvg`/`cairosvg` available to rasterize it, but any browser or `docs/screenshots/` export will do).

```
Frontend (Next.js, Vercel)
        │  REST / JSON
        ▼
FastAPI (Render)
        │
        ├──► Watchlist Service  ──┐
        ├──► Change Engine        ├──► PostgreSQL (Supabase-compatible)
        ├──► Insights (Mood/Replay)
        └──► Market Adapter ──► Twelve Data (falls back to Demo Mode with no API key)
```

## Layers

- **Frontend** — Next.js App Router. Three routes (`/`, `/add`, `/stock/[symbol]`), each backed by a hook (`useWatchlist`, `useMarket`, `useInsights`) that owns loading/error state so pages stay declarative. The homepage composes Market Mood, Today's Replay, and a Portfolio Heatmap on top of the existing Attention Feed, all reading data the backend already computes — no new client-side scoring logic.
- **API layer** — FastAPI routers are intentionally thin: they validate input, call a service function, and shape the response. No business logic lives in a router. `routers/insights.py` follows the same pattern for the two new read-only endpoints (`/mood`, `/replay`).
- **Watchlist Service** — CRUD against the `watchlist` table, the orchestration step that ties a fresh snapshot to a recomputed change event, and (new) `get_market_mood` / `get_daily_replay`, which are pure rollups over ChangeEvents/Snapshots the service already owns.
- **Change Engine** — Pure functions operating on two `BaselineSnapshot`/`MarketQuoteData` values. Zero I/O, so it's fully unit-testable (`backend/tests/test_change_engine.py`) without a database or network. The Quiet-labeled path now returns a deterministic, data-driven explanation (`_build_quiet_reasons`) instead of a generic message.
- **Market Adapter** — The only file that talks to an external provider (Twelve Data). Wraps every call in error handling, one automatic retry, and a short TTL cache. Falls back to a deterministic synthetic Demo Mode when no API key is configured, which the Daily Replay feature also reuses so it works without any real market history.
- **Database** — PostgreSQL in production (Supabase works as-is), SQLite for local zero-config dev.

## Key trade-offs

| Decision | Why |
|---|---|
| Deterministic scoring instead of an LLM | Auditable, free, instant, reproducible — matches "transparent explanation" requirement exactly |
| Snapshot-on-request instead of a background worker | Keeps the hackathon deployment to two services (Vercel + Render), no queue/worker infra needed to demo |
| Single default user, multi-user schema | Auth was out of scope for the time budget, but `user_id` foreign keys mean adding it later is additive, not a rewrite |
| SQLite fallback | Anyone cloning the repo can run the backend with zero setup; swapping in `DATABASE_URL` for Postgres/Supabase requires no code change |
| In-memory TTL cache instead of Redis | One process, one deploy — Redis would be premature infrastructure at this scale, but the cache is behind an interface so swapping it in later is a one-file change |
| Demo Mode instead of a hard dependency on a paid API key | Judges/reviewers can run the full app, including the Attention Feed and Daily Replay, with zero setup; the same code path (`market_adapter.py`) drives both, so demo and live behavior never diverge |
| Mood/Replay derived from existing tables, no new tables | `ChangeEvent` and `Snapshot` already hold everything both features need — adding storage for them would be duplicated state that could drift out of sync |

## Scaling this beyond a hackathon

1. **Batch market requests** — group all distinct symbols across all users' watchlists into one fetch cycle instead of per-user calls.
2. **Redis cache** — replace the in-process `QuoteCache` with Redis once running more than one API instance, so cache hits are shared.
3. **Background workers** — move snapshotting off the request path onto a scheduled job (cron / Celery / a queue), so page loads never wait on yfinance.
4. **Precomputed change events** — the worker recomputes scores right after each scheduled snapshot; the API becomes read-only for `/changes`, which is much easier to scale and cache.
5. **Horizontal scaling** — FastAPI holds no in-request state beyond the cache, so once the cache and DB are shared, more instances can sit behind a load balancer.
6. **DB indexing** — already in place on `(symbol, timestamp)` and `(symbol, created_at)`, the two hot query paths, so lookups stay fast as snapshot history grows.
