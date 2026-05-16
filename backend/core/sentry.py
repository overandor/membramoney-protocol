"""
Sentry error tracking integration for Membra Money Protocol.
Disabled by default on devnet. Enable by setting SENTRY_DSN.
"""

import os
from typing import Optional


class SentryClient:
    """Stub Sentry client for devnet. Production would use sentry-sdk."""

    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("SENTRY_DSN")
        self.enabled = bool(self.dsn)
        self.environment = os.getenv("ENV", "devnet")

    def capture_exception(self, exception: Exception, **kwargs):
        """Capture an exception."""
        if not self.enabled:
            return
        # In production, this would call sentry_sdk.capture_exception
        print(f"[SENTRY] Exception: {exception}")

    def capture_message(self, message: str, level: str = "info", **kwargs):
        """Capture a message."""
        if not self.enabled:
            return
        print(f"[SENTRY] [{level}] {message}")

    def set_context(self, name: str, context: dict):
        """Set context for current scope."""
        if not self.enabled:
            return
        print(f"[SENTRY] Context {name}: {context}")


# Global instance
sentry = SentryClient()
