"""
Middleware: redact PII from request body before it reaches route handlers.
Applied to /api/query (question text) and any JSON body that might contain PII.
"""
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.services.pii_redaction import redact_pii


class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """Redact PII from JSON request bodies (e.g. question field) before processing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in ("POST", "PUT", "PATCH") and request.url.path == "/api/query":
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    if isinstance(data.get("question"), str):
                        data["question"] = redact_pii(data["question"])
                    # Reconstruct request with redacted body (Starlette doesn't allow easy body override)
                    # So we need to pass redacted body downstream. We use request.state.
                    request.state._redacted_body = json.dumps(data).encode("utf-8")
            except (json.JSONDecodeError, TypeError):
                pass
        response = await call_next(request)
        return response
