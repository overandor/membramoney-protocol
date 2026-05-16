"""
Tests for input sanitization helpers.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import _sanitize_wallet_address, _sanitize_claim_id, _sanitize_pin


def test_sanitize_valid_wallet():
    addr = "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL"
    result = _sanitize_wallet_address(addr)
    assert result == addr


def test_sanitize_wallet_with_whitespace():
    addr = "  CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL  "
    result = _sanitize_wallet_address(addr)
    assert result == "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL"


def test_sanitize_wallet_invalid_characters():
    try:
        _sanitize_wallet_address("invalid!@#$%")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid characters" in str(e)


def test_sanitize_valid_claim_id():
    claim_id = "550e8400-e29b-41d4-a716-446655440000"
    result = _sanitize_claim_id(claim_id)
    assert result == claim_id


def test_sanitize_claim_id_with_whitespace():
    claim_id = "  550e8400-e29b-41d4-a716-446655440000  "
    result = _sanitize_claim_id(claim_id)
    assert result == "550e8400-e29b-41d4-a716-446655440000"


def test_sanitize_claim_id_too_short():
    try:
        _sanitize_claim_id("abc")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "too short" in str(e)


def test_sanitize_claim_id_invalid_chars():
    try:
        _sanitize_claim_id("550e8400-e29b-41d4-a716-44665544000!")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid characters" in str(e)


def test_sanitize_valid_pin():
    pin = "ABCD1234"
    result = _sanitize_pin(pin)
    assert result == pin


def test_sanitize_pin_with_whitespace():
    pin = "  ABCD1234  "
    result = _sanitize_pin(pin)
    assert result == "ABCD1234"


def test_sanitize_pin_invalid_chars():
    try:
        _sanitize_pin("ABCD-1234")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "alphanumeric" in str(e)
