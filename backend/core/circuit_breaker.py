"""
Circuit breaker pattern for external API calls.
Prevents cascading failures when downstream services are unhealthy.
"""

import time
from enum import Enum
from typing import Optional, Callable, Any
from datetime import datetime, timezone


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Usage:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        result = breaker.call(lambda: requests.get("https://api.example.com"))
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute func with circuit breaker protection."""
        self.total_calls += 1

        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN. Last failure: {self.last_failure_time}"
                )

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' HALF_OPEN limit reached."
                )
            self.half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        self.total_successes += 1
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.half_open_calls = 0

    def _on_failure(self):
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "last_failure_time": self.last_failure_time,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breakers
_solana_rpc_breaker = CircuitBreaker("solana_rpc", failure_threshold=3, recovery_timeout=10)
_external_api_breaker = CircuitBreaker("external_api", failure_threshold=5, recovery_timeout=30)


def get_breaker(name: str) -> CircuitBreaker:
    """Get a circuit breaker by name."""
    if name == "solana_rpc":
        return _solana_rpc_breaker
    if name == "external_api":
        return _external_api_breaker
    raise ValueError(f"Unknown circuit breaker: {name}")
