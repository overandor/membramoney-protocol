"""
Tests for JWT authentication.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.jwt_manager import JWTManager


def test_create_access_token():
    jwt = JWTManager(secret="test-secret")
    token = jwt.create_access_token("test-wallet", "issuer")
    assert token is not None
    assert isinstance(token, str)


def test_decode_valid_token():
    jwt = JWTManager(secret="test-secret")
    token = jwt.create_access_token("test-wallet", "issuer")
    payload = jwt.decode_token(token)
    assert payload is not None
    assert payload["sub"] == "test-wallet"
    assert payload["role"] == "issuer"
    assert payload["type"] == "access"


def test_decode_invalid_token():
    jwt = JWTManager(secret="test-secret")
    payload = jwt.decode_token("invalid-token")
    assert payload is None


def test_wallet_from_token():
    jwt = JWTManager(secret="test-secret")
    token = jwt.create_access_token("test-wallet", "viewer")
    wallet = jwt.get_wallet_from_token(token)
    assert wallet == "test-wallet"


def test_expired_token():
    import jwt as pyjwt
    jwt = JWTManager(secret="test-secret")
    # Create token with past expiry
    token = pyjwt.encode(
        {"sub": "test", "exp": 0},
        "test-secret",
        algorithm="HS256",
    )
    payload = jwt.decode_token(token)
    assert payload is None
