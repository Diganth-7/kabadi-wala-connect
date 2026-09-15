"""
utils/errors.py
----------------
Defines a single custom exception, `AppError`, used throughout the app
whenever something goes wrong in a way the CLIENT should be told about
(e.g. "user not found", "invalid weight", "unauthorized").

Why one custom exception class instead of raising FastAPI's built-in
HTTPException everywhere?
- The spec requires EVERY error response to look exactly like:
    {"success": false, "error": {"code": "...", "message": "..."}}
  AppError carries a `code` (from the spec's fixed list of error codes)
  and a `message`, and a single exception handler (registered in
  main.py) turns any AppError into that exact JSON shape automatically.
  This means individual routers/services never have to think about
  response formatting — just `raise AppError(...)`.

Also provides `success_response()`, a tiny helper so every successful
endpoint returns the same {"success": true, "data": ...} shape too.
"""


class AppError(Exception):
    """
    Raise this anywhere in services or routers to signal a client-facing
    error. It gets caught by the exception handler in main.py and turned
    into a proper JSON error response with the right HTTP status code.

    Example:
        raise AppError(code="LOT_NOT_FOUND", message="Lot not found.", status_code=404)
    """

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def success_response(data):
    """
    Wraps any data in the standard success envelope:
        {"success": true, "data": <data>}
    """
    return {"success": True, "data": data}
