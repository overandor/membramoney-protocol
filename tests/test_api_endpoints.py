"""
Membra Money Protocol — API Endpoint Integration Tests
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app

client = TestClient(app)


def test_audit_events():
    r = client.get("/api/v1/audit/events?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert "count" in data
    assert isinstance(data["events"], list)


def test_claim_create_without_risk_acceptance():
    r = client.post(
        "/api/v1/claims/create",
        json={
            "wallet_address": "NoRiskUser123456789012345678901234567890",
            "denomination_sats": 1000,
            "expires_minutes": 30,
            "risk_version": "v1.0.0-devnet",
        },
    )
    assert r.status_code == 403


def test_brute_force_protection():
    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": "BruteUser123456789012345678901234567890",
            "accepted_version": "v1.0.0-devnet",
        },
    )
    create = client.post(
        "/api/v1/claims/create",
        json={
            "wallet_address": "BruteUser123456789012345678901234567890",
            "denomination_sats": 100,
            "expires_minutes": 30,
            "risk_version": "v1.0.0-devnet",
        },
    ).json()

    # 6 wrong attempts
    for i in range(6):
        r = client.post(
            "/api/v1/claims/validate",
            json={
                "claim_id": create["claim_id"],
                "pin": f"WRONG{i}",
                "claimant_wallet": "BruteUser123456789012345678901234567890",
            },
        )

    # 6th should be rate limited (429)
    assert r.status_code == 429
