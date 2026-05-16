"""OpenTelemetry tracing stub for Membra Money Protocol.
Production: install opentelemetry-api, opentelemetry-sdk, opentelemetry-instrumentation-fastapi
"""

from contextlib import contextmanager
from typing import Optional


class NoOpTracer:
    """No-op tracer when OpenTelemetry is not installed."""

    @contextmanager
    def start_as_current_span(self, name: str, attributes: Optional[dict] = None):
        class NoOpSpan:
            def set_attribute(self, key, value):
                pass
            def add_event(self, name, attributes=None):
                pass
            def record_exception(self, exception):
                pass
        yield NoOpSpan()

    def start_span(self, name: str, context=None):
        return NoOpTracer()


def get_tracer(name: str = "membramoney"):
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return NoOpTracer()


def trace_span(name: str):
    """Decorator to trace a function call."""
    def decorator(func):
        tracer = get_tracer()
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(name) as span:
                if hasattr(span, "set_attribute"):
                    span.set_attribute("function.name", func.__name__)
                return func(*args, **kwargs)
        return wrapper
    return decorator
