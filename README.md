# Kabadiwala Connect

Single-URL deployment: FastAPI serves both the `/api/*` endpoints and
the built React frontend from one process/port.

```
kabadiwala-connect/
├── backend/    # FastAPI + PostgreSQL API
└── frontend/   # React + Vite UI (built into frontend/dist)
```

## One-time setup

**1. Database**
Make sure PostgreSQL is running and a database exists for this app
(any name — put it in `DATABASE_URL` below).

**2. Backend**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # edit DATABASE_URL + JWT_SECRET_KEY
python scripts/create_tables.py
python scripts/seed.py
```

**3. Frontend build**
```bash
cd ../frontend
npm install
npm run build                     # outputs frontend/dist
```
Do NOT create a `.env` here for production — leave `VITE_API_BASE_URL`
unset so the app calls a relative `/api` path (same origin as the
backend). `.env.development` (see `.env.development.example`) is only
for running the frontend as its own dev server on port 5173.

## Run (single URL)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** — this one URL serves the UI, and
`http://localhost:8000/api/...` serves the API (also see
`/docs` for Swagger). No separate frontend server, no CORS needed.

Log in with a seeded account: `collector@test.com`,
`recycler@test.com`, or `admin@test.com` — the OTP field auto-fills
from the backend's dev response.

## After changing frontend code

Rebuild so the backend picks up the new static files:
```bash
cd frontend && npm run build
```
(No backend restart needed — it reads `frontend/dist` from disk on
every request.)

## Running frontend and backend separately instead (dev mode)

If you'd rather iterate on the frontend with Vite's hot-reload dev
server instead of rebuilding each time:
```bash
# terminal 1
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# terminal 2
cd frontend && cp .env.development.example .env.development && npm run dev
```
Open the Vite URL (`http://localhost:5173`) instead of :8000. CORS is
already allowed for that origin in `backend/.env.example`.

## Deploying somewhere real

Any platform that can run a long-lived Python process works (Render,
Railway, Fly.io, a VM, etc.):
1. Build the frontend (`npm run build`) as part of your deploy step.
2. Run the backend with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Point `DATABASE_URL` at a real Postgres instance (most platforms
   offer one), set a strong `JWT_SECRET_KEY`, and set
   `CORS_ORIGINS`/`ENVIRONMENT=production` appropriately (CORS mostly
   doesn't matter here since it's same-origin, but keep it accurate).
4. If your platform copies the frontend to a different path than the
   default sibling `frontend/dist`, set `FRONTEND_DIST_PATH` as an
   env var on the backend service.

See `backend/README.md` and `frontend/INTEGRATION_NOTES.md` for
endpoint-level and contract details.
