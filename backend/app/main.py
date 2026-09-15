"""
main.py
-------
This is the entry point of the backend. Running `uvicorn app.main:app`
starts the FastAPI server defined here.

In this Phase 1, we only set up:
- The FastAPI app itself
- CORS (so the React frontend on localhost:5173 can call this API)
- A health check endpoint at GET /api/health

In later phases, we will `include_router(...)` for auth, materials,
prices, lots, etc. — but none of that exists yet.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.errors import AppError, success_response

app = FastAPI(
    title="Kabadiwala Connect API",
    description="Backend API for Kabadiwala Connect (SIH26229) - e-waste collection platform.",
    version="0.1.0",
)

# ------------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing)
# ------------------------------------------------------------------
# By default, browsers block a frontend on one origin (e.g.
# http://localhost:5173) from calling an API on a different origin
# (e.g. http://localhost:8000). CORS middleware tells the browser which
# origins are allowed to call this API.
#
# IMPORTANT: We read allowed origins from settings (.env), NOT a
# hard-coded "*", so that in production we can restrict this to only
# our real frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Exception handlers
# ------------------------------------------------------------------
# These three handlers guarantee EVERY error response from this API —
# no matter where it's raised — comes back in the exact shape the spec
# requires:
#   {"success": false, "error": {"code": "...", "message": "..."}}
# and NEVER leaks a Python stack trace to the client.

@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    """Handles our own custom errors (raised deliberately in services/routers)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    """
    Defensive fallback: if anything (ours or a library) raises a plain
    FastAPI/Starlette HTTPException instead of our AppError, this still
    reformats it into our standard error shape instead of leaking
    FastAPI's default {"detail": "..."} format.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": {"code": "ERROR", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic/FastAPI request validation errors — e.g. a required
    field is missing, or a field has the wrong type. FastAPI would
    normally return its own JSON shape for these; we override it to
    match our standard error format instead.
    """
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request data failed validation. Please check your input.",
            },
        },
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches anything else that goes wrong unexpectedly (a bug, a database
    error, etc.). We log the real error server-side for debugging, but
    NEVER send the actual Python error/stack trace back to the client —
    that could leak sensitive info about our code or database.
    """
    print(f"[UNHANDLED ERROR] {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "SERVER_ERROR", "message": "An unexpected error occurred."},
        },
    )


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    """
    Simple endpoint to confirm the server is up and responding.
    Useful for deployment platforms / uptime monitors to check the
    service is alive.
    """
    return success_response({"status": "healthy"})


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
from app.routers import auth, materials, prices, lots, recyclers, pickups, handovers, transactions, payments, earnings, notifications, admin  # noqa: E402  (imported here, after app/middleware setup, to avoid circular imports)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(materials.router, prefix="/api/materials", tags=["Materials"])
app.include_router(prices.router, prefix="/api/prices", tags=["Prices"])
app.include_router(lots.router, prefix="/api/lots", tags=["Lots"])
app.include_router(recyclers.router, prefix="/api/recyclers", tags=["Recyclers"])
app.include_router(pickups.router, prefix="/api/pickups", tags=["Pickups"])
app.include_router(handovers.router, prefix="/api/handovers", tags=["Handovers"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
app.include_router(earnings.router, prefix="/api/earnings", tags=["Earnings"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# All routers for all 11 functional phases are now registered.
# Phase 12 (final testing, Swagger check, security review) does not
# add new routers -- it verifies everything above.

# ------------------------------------------------------------------
# Serve the built frontend (single-URL deployment)
# ------------------------------------------------------------------
# When you run `npm run build` in the frontend, Vite outputs static
# files to frontend/dist. If that folder exists, this FastAPI process
# serves it directly, so the API and the UI live on ONE URL/port --
# no separate frontend server, no CORS needed in production.
#
# Assumes the sibling-folder layout:
#   kabadiwala-connect/
#   ├── backend/   (this app)
#   └── frontend/  (dist/ created by `npm run build`)
# Override with the FRONTEND_DIST_PATH env var if your layout differs.
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"),
)

if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        """
        Serves the React SPA's index.html for any route that isn't an
        API/docs route, so React Router's client-side routes work on
        refresh or direct navigation (e.g. /collector/lots).
        """
        if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    print(f"[INFO] Frontend build not found at {FRONTEND_DIST} -- running API-only. "
          f"Run `npm run build` in the frontend, or set FRONTEND_DIST_PATH.")

