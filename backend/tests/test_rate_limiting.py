"""
Tests for rate limiting and brute force protection.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import _check_brute_force, _record_brute_force, MAX_BRUTE_FORCE_ATTEMPTS


def test_brute_force_under_limit():
    key = "test-wallet-1"
    # Should allow attempts under the limit
    assert _check_brute_force(key) is False


def test_brute_force_at_limit():
    key = "test-wallet-2"
    # Record max attempts
    for _ in range(MAX_BRUTE_FORCE_ATTEMPTS):
        _record_brute_force(key)
    # Should now be blocked
    assert _check_brute_force(key) is True


def test_brute_force_window_expires():
    import time
    key = "test-wallet-3"
    # Record one attempt
    _record_brute_force(key)
    # Should not be blocked yet
    assert _check_brute_force(key) is False
