"""
Tests for wallet authentication service.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.wallet_auth import WalletAuthService


def test_generate_nonce():
    auth = WalletAuthService()
    nonce = auth.generate_nonce("test-wallet")
    assert nonce is not None
    assert len(nonce) == 32  # hex string of 16 bytes


def test_verify_valid_nonce():
    auth = WalletAuthService()
    nonce = auth.generate_nonce("test-wallet")
    assert auth.verify_nonce("test-wallet", nonce) is True


def test_verify_invalid_nonce():
    auth = WalletAuthService()
    assert auth.verify_nonce("test-wallet", "wrong-nonce") is False


def test_verify_reused_nonce():
    auth = WalletAuthService()
    nonce = auth.generate_nonce("test-wallet")
    auth.verify_nonce("test-wallet", nonce)
    assert auth.verify_nonce("test-wallet", nonce) is False  # Already used


def test_authenticate_with_valid_signature():
    auth = WalletAuthService()
    wallet = "test-wallet"
    nonce = auth.generate_nonce(wallet)
    # Simulate valid signature
    signature = f"{wallet}:{nonce}"
    tokens = auth.authenticate(wallet, nonce, signature)
    assert tokens is not None
    access, refresh = tokens
    assert access is not None
    assert refresh is not None


def test_authenticate_with_invalid_nonce():
    auth = WalletAuthService()
    tokens = auth.authenticate("test-wallet", "wrong-nonce", "sig")
    assert tokens is None
