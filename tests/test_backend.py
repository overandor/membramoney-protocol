"""
Membra Money Protocol — Backend Unit Tests
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app

client = TestClient(app)


# ------------------------------------------------------------------
# 1. Health endpoint
# ------------------------------------------------------------------
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["devnet"] is True
    assert "timestamp" in data


# ------------------------------------------------------------------
# 2. Ready endpoint
# ------------------------------------------------------------------
def test_ready():
    r = client.get("/ready")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"


# ------------------------------------------------------------------
# 3. Risk disclosure endpoint
# ------------------------------------------------------------------
def test_risk_disclosure():
    r = client.get("/api/v1/risk-disclosure")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "text" in data
    assert "hash" in data
    assert "devnet" in data["version"].lower() or "experimental" in data["text"].lower()


# ------------------------------------------------------------------
# 4. Risk disclosure acceptance
# ------------------------------------------------------------------
def test_risk_disclosure_accept():
    r = client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": "TestWallet1234567890123456789012345678901",
            "accepted_version": "v1.0.0-devnet",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["accepted"] is True
    assert data["wallet_address"] == "TestWallet1234567890123456789012345678901"
    assert data["version"] == "v1.0.0-devnet"


# ------------------------------------------------------------------
# 5. Claim creation validation
# ------------------------------------------------------------------
def test_claim_create():
    # Must accept risk first
    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": "ClaimCreator123456789012345678901234567",
            "accepted_version": "v1.0.0-devnet",
        },
    )
    r = client.post(
        "/api/v1/claims/create",
        json={
            "wallet_address": "ClaimCreator123456789012345678901234567",
            "denomination_sats": 5000,
            "expires_minutes": 30,
            "risk_version": "v1.0.0-devnet",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "claim_id" in data
    assert "claim_url" in data
    assert "pin_hash" in data
    assert "devnet_warning" in data


# ------------------------------------------------------------------
# 6. Claim validation wrong PIN
# ------------------------------------------------------------------
def test_claim_validate_wrong_pin():
    # Setup
    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": "WrongPinUser1234567890123456789012345678",
            "accepted_version": "v1.0.0-devnet",
        },
    )
    create = client.post(
        "/api/v1/claims/create",
        json={
            "wallet_address": "WrongPinUser1234567890123456789012345678",
            "denomination_sats": 1000,
            "expires_minutes": 30,
            "risk_version": "v1.0.0-devnet",
        },
    ).json()

    r = client.post(
        "/api/v1/claims/validate",
        json={
            "claim_id": create["claim_id"],
            "pin": "WRONGPIN",
            "claimant_wallet": "WrongPinUser1234567890123456789012345678",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert "invalid" in data["message"].lower() or "Invalid" in data["message"]


# ------------------------------------------------------------------
# 7. Claim expiration
# ------------------------------------------------------------------
def test_claim_expiration():
    from unittest.mock import patch
    from datetime import datetime, timezone, timedelta

    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": "ExpiredUser12345678901234567890123456789",
            "accepted_version": "v1.0.0-devnet",
        },
    )
    r_create = client.post(
        "/api/v1/claims/create",
        json={
            "wallet_address": "ExpiredUser12345678901234567890123456789",
            "denomination_sats": 100,
            "expires_minutes": 1,
            "risk_version": "v1.0.0-devnet",
        },
    )
    assert r_create.status_code == 200, f"Claim creation failed: {r_create.text}"
    create = r_create.json()

    # Simulate time passing by patching datetime.now to return a time far in the future
    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    with patch("main.datetime") as mock_dt:
        mock_dt.now.return_value = future
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        # Try to validate after expiry
        r = client.post(
            "/api/v1/claims/validate",
            json={
                "claim_id": create["claim_id"],
                "pin": "doesntmatter",
                "claimant_wallet": "ExpiredUser12345678901234567890123456789",
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is False
    assert "expired" in data["message"].lower()


# ------------------------------------------------------------------
# 8. Reserves endpoint
# ------------------------------------------------------------------
def test_reserves():
    r = client.get("/api/v1/reserves")
    assert r.status_code == 200
    data = r.json()
    assert data["devnet_only"] is True
    assert "disclaimer" in data
    assert data["reserve_ratio_bps"] == 10_000


# ------------------------------------------------------------------
# 9. Stats endpoint
# ------------------------------------------------------------------
def test_stats():
    r = client.get("/api/v1/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_notes" in data
    assert "redeemed_notes" in data
    assert "active_claims" in data
    assert data["devnet"] is True
