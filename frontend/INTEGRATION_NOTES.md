# Integration notes — frontend ↔ FastAPI backend

This frontend now talks to the real backend instead of `localStorage`.
`src/services/mock.ts` has been retired to `mock.ts.bak` (kept for
reference only — not imported anywhere).

## Setup

1. Start the backend first (see backend README): create `.env`,
   `create_tables.py`, `seed.py`, then `uvicorn app.main:app --reload`.
   It should be reachable at `http://localhost:8000`.
2. In this frontend folder:
   ```bash
   cp .env.example .env   # already done for you; edit if backend runs elsewhere
   npm install
   npm run dev
   ```
3. Log in with a seeded account, e.g. `collector@test.com`,
   `recycler@test.com`, or `admin@test.com`. The OTP field auto-fills
   from the backend's `dev_otp` (no real SMS provider is configured).

## What changed

- **`src/services/api.ts`** (new) replaces `mock.ts` behind the exact
  same exported service names, so every page's imports kept working
  unchanged, except where the contracts genuinely differ (below).
- **`src/services/index.ts`** now re-exports from `api.ts`. Switch back
  to `export * from './mock'` any time you want the old offline demo.
- JWT is stored in `localStorage` under `kbc_token` and attached as
  `Authorization: Bearer <token>` on every request automatically.

## Real contract differences from the mock (handled, but worth knowing)

- **Auth**: login takes an `identifier` (email or phone), not a fixed
  10-digit phone + hardcoded `123456` OTP. The dev backend returns
  `dev_otp` in the login response, which the Login page now auto-fills.
- **Recycler matching**: `GET /recyclers/match` requires a `lot_id`,
  not a material name — a lot must exist before matching. `Recyclers.tsx`
  was updated to pass the lot id from the URL/demo state instead of a
  material name.
- **Recycler directory** (`GET /recyclers`) doesn't include
  `distance_km` / `buying_price` / `match_score` — those only exist in
  the per-lot `/recyclers/match` result. They're defaulted to `0` when
  showing the plain directory (e.g. on the pickup-tracking screen).
- **No `estimated_value` / `final_amount` inputs**: the backend always
  computes these server-side (by design, per the backend README) — the
  frontend never sends them, matching the create-lot / create-handover
  schemas exactly.
- **No `POST /transactions`**: transactions are created automatically
  when a handover completes. `transactionService.createTransaction` is
  kept only so `Payment.tsx`'s existing call still resolves; it now
  looks up the transaction the handover already created rather than
  creating a new one.
- **Materials aren't embedded** in Lot/Price/Transaction responses —
  only `material_id` / a name string. `api.ts` fetches and caches
  `GET /materials` once and joins client-side to rebuild the full
  `Material` objects the UI expects.
- **Price history**: there's no price-history endpoint yet, so the
  7-day trend chart on the Prices page will render flat until the
  backend adds one.
- **Location fields**: `LotCreateRequest` and `PickupCreateRequest`
  require `location` / `pickup_location` (lat/lng). There's no real
  map/GPS in this prototype, so `api.ts` sends a hardcoded Bengaluru
  coordinate as a placeholder — swap `defaultLocation()` in `api.ts`
  for `navigator.geolocation` once you want real coordinates.
- **Safety guides** have no backend endpoint (by design — static
  reference content) and are still served from
  `src/data/mockData.ts`.

## Not yet wired up

- CORS: backend `.env.example` already defaults
  `CORS_ORIGINS=http://localhost:5173`, matching Vite's default port.
  Change both sides together if you run on a different port.
- Offline/PENDING_SYNC behavior from the original mock (queuing lots
  created while offline) was prototype-only and hasn't been
  reimplemented against the real API.
