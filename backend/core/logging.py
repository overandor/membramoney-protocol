"""
Structured logging configuration for Membra Money Protocol backend.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict


def log_structured(
    level: str,
    message: str,
    extra: Dict[str, Any] = None,
    request_id: str = None,
):
    """
    Emit a structured JSON log line to stderr.
    In production, this would route to a log aggregator (Datadog, Splunk, etc.)
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "service": "membramoney-backend",
        "version": "0.1.0-devnet",
        "env": "devnet",
    }
    if request_id:
        entry["request_id"] = request_id
    if extra:
        entry["extra"] = extra

    print(json.dumps(entry), file=sys.stderr, flush=True)


def log_info(message: str, **kwargs):
    log_structured("INFO", message, **kwargs)


def log_warn(message: str, **kwargs):
    log_structured("WARN", message, **kwargs)


def log_error(message: str, **kwargs):
    log_structured("ERROR", message, **kwargs)
