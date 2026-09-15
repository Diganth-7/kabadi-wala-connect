# Kabadiwala Connect — Backend

Backend API for **Kabadiwala Connect** (SIH26229) — an e-waste / scrap
collection platform connecting Collectors, Recyclers, and Admins.

Tech stack: **FastAPI + PostgreSQL + SQLAlchemy + JWT**

> Status: Phase 11 (admin APIs) complete — all functional phases done. Only Phase 12 (final review) remains. See "Development Phases" below.

## Setup

1. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate      # on Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and set your real PostgreSQL connection string and a
   strong `JWT_SECRET_KEY`. Never commit `.env` to git.

4. **Make sure PostgreSQL is running** and the database named in
   `DATABASE_URL` exists.

5. **Create the database tables**:
   ```bash
   python scripts/create_tables.py
   ```

6. **(Optional) Seed demo data** — collectors, recyclers, admin, materials, prices, sample lots/transactions:
   ```bash
   python scripts/seed.py
   ```
   This is safe to re-run any time; it clears old demo data first.

   Demo accounts created: `collector@test.com`, `recycler@test.com`, `admin@test.com`
   (no passwords — login uses mock OTP, see "Trying out authentication" below).

## Running the server

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- http://localhost:8000/api/health — health check
- http://localhost:8000/docs — Swagger UI (interactive API docs)
- http://localhost:8000/redoc — ReDoc API docs

## Project structure

```
backend/
├── app/
│   ├── main.py         # FastAPI app, CORS, health check
│   ├── config.py        # Environment variable loading (pydantic-settings)
│   ├── database.py      # SQLAlchemy engine/session setup
│   ├── models/           # SQLAlchemy ORM models        (Phase 2+)
│   ├── schemas/          # Pydantic request/response schemas (Phase 3+)
│   ├── routers/          # FastAPI route handlers        (Phase 3+)
│   ├── services/         # Business logic                (Phase 3+)
│   ├── auth/              # JWT + auth dependencies       (Phase 3)
│   └── utils/             # Shared helpers (error formatting, etc.)
├── tests/                 # Pytest test suite
├── .env.example           # Template for environment variables
├── requirements.txt
└── README.md
```

## Trying out authentication (Phase 3)

This is mock OTP login — no real SMS is sent. In development mode, the
OTP is returned directly in the `/login` response (as `dev_otp`) so you
can test the whole flow via Swagger without any SMS provider.

1. `POST /api/auth/login` with `{"identifier": "collector@test.com"}`
   → response includes `dev_otp`.
2. `POST /api/auth/verify-otp` with `{"identifier": "collector@test.com", "otp": "<dev_otp>"}`
   → response includes `access_token`.
3. In Swagger, click "Authorize" and paste the token (just the token,
   no "Bearer " prefix needed — Swagger adds that itself), or send it
   manually as a header: `Authorization: Bearer <access_token>`.
4. `GET /api/auth/me` → returns your logged-in profile.

Demo accounts (from `scripts/seed.py`): `collector@test.com`,
`recycler@test.com`, `admin@test.com`.

## Running tests

```bash
pytest tests/ -v
```

Tests hit your real configured database, so make sure PostgreSQL is
running and you've run `scripts/seed.py` first.

## Development phases


This backend is being built incrementally:

1. ✅ Project setup, FastAPI, config, DB connection, health check
2. ✅ SQLAlchemy models, relationships, seed data
3. ✅ Authentication (JWT, mock OTP, roles)
4. ✅ Materials & Prices
5. ✅ Scrap Lots
6. ✅ Recyclers & matching algorithm
7. ✅ Pickups & status transitions
8. ✅ Handover & Transactions
9. ✅ Simulated Payments & Earnings
10. ✅ Notifications
11. ✅ Admin APIs
12. ✅ Testing, error handling, security review


## Phase 12 - Final verification

Before frontend integration, run the full backend verification once.

### 1. Create your local environment

Copy `.env.example` to `.env` and set your PostgreSQL password and a long JWT secret. Never commit `.env`.

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Create tables and seed demo data

```bash
python scripts/create_tables.py
python scripts/seed.py
```

### 4. Run all tests

```bash
pytest tests/ -v
```

### 5. Run the API

```bash
uvicorn app.main:app --reload
```

Then verify:

- `http://localhost:8000/api/health`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

### 6. Manual business-flow check

```text
Login
  -> Create lot
  -> Match recycler
  -> Request pickup
  -> Accept
  -> Assign
  -> On the way
  -> Arrived
  -> Handover
  -> Transaction
  -> Payment
  -> Earnings
  -> Notification
```

Phase 12 does not add offline sync, AI, or a real payment gateway. Those remain future enhancements.
