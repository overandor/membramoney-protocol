"""
Tests for circuit breaker pattern.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


def test_circuit_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.state.value == "closed"


def test_circuit_opens_after_failures():
    cb = CircuitBreaker("test", failure_threshold=3)
    for _ in range(3):
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass
    assert cb.state.value == "open"


def test_circuit_rejects_when_open():
    cb = CircuitBreaker("test", failure_threshold=1)
    try:
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
    except Exception:
        pass
    try:
        cb.call(lambda: "success")
        assert False, "Should have raised CircuitBreakerOpenError"
    except CircuitBreakerOpenError:
        pass


def test_circuit_closes_on_success():
    cb = CircuitBreaker("test")
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state.value == "closed"


def test_half_open_allows_limited_calls():
    cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=0)
    try:
        cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
    except Exception:
        pass
    # Force half-open by waiting
    import time
    time.sleep(0.1)
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state.value == "closed"
