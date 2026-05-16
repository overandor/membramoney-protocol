"""
Audit logging middleware — records every request/response to the audit log.
"""

import time
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with method, path, status, latency, client IP, and request ID.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        # Capture response
        response = await call_next(request)
        latency_ms = round((time.time() - start) * 1000, 2)

        # Get client IP (handles proxies)
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")

        # Structured log line
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
            "client_ip": client_ip.split(",")[0].strip(),
            "user_agent": request.headers.get("User-Agent", ""),
            "env": getattr(request.app.state, "env", "devnet"),
        }

        # In production this would go to a structured log aggregator
        # For devnet we print to stderr
        import sys
        import json
        print(json.dumps({"audit": log_entry}), file=sys.stderr, flush=True)

        return response
