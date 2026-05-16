"""
Request ID middleware — injects X-Request-ID into every request/response.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Injects a unique request ID into every incoming request.
    - Reads X-Request-ID from client if present
    - Generates UUID4 if absent
    - Adds X-Request-ID to response headers
    - Stores request_id on request.state for downstream use
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
