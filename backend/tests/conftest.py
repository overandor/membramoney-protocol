"""
Pytest fixtures for Membra Money Protocol backend tests.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_wallet():
    """A valid Solana devnet wallet address."""
    return "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL"


@pytest.fixture
def invalid_wallet():
    """An invalid wallet address with special characters."""
    return "invalid!@#$%^&*()"


@pytest.fixture
def sample_claim_data(valid_wallet):
    """Sample claim creation request data."""
    return {
        "wallet_address": valid_wallet,
        "denomination_sats": 1000000,
        "expires_minutes": 60,
        "risk_version": "v1.0.0-devnet",
    }
