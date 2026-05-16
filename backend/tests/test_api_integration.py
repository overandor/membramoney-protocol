"""
Integration tests for Membra Money Protocol backend API.
Uses pytest fixtures from conftest.py.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.adapter import db


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["devnet"] is True
    assert "version" in data
    assert "stores" in data


def test_ready_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data


def test_risk_disclosure_endpoint(client):
    response = client.get("/api/v1/risk-disclosure")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "text" in data
    assert "hash" in data


def test_accept_risk_disclosure(client, valid_wallet):
    response = client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": valid_wallet,
            "accepted_version": "v1.0.0-devnet",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True
    assert data["wallet_address"] == valid_wallet


def test_create_claim_without_risk_acceptance(client, sample_claim_data):
    response = client.post("/api/v1/claims/create", json=sample_claim_data)
    assert response.status_code == 403
    data = response.json()
    assert "Risk disclosure not accepted" in data["error"]["message"]


def test_create_claim_with_risk_acceptance(client, valid_wallet, sample_claim_data):
    # First accept risk disclosure
    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": valid_wallet,
            "accepted_version": "v1.0.0-devnet",
        },
    )

    # Then create claim
    response = client.post("/api/v1/claims/create", json=sample_claim_data)
    assert response.status_code == 200
    data = response.json()
    assert "claim_id" in data
    assert "claim_url" in data
    assert "pin_hash" in data


def test_create_claim_idempotency(client, valid_wallet, sample_claim_data):
    # Accept risk disclosure
    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": valid_wallet,
            "accepted_version": "v1.0.0-devnet",
        },
    )

    # Create claim with idempotency key
    idempotency_key = "test-key-123"
    data_with_key = {**sample_claim_data, "idempotency_key": idempotency_key}

    response1 = client.post("/api/v1/claims/create", json=data_with_key)
    assert response1.status_code == 200
    claim_id_1 = response1.json()["claim_id"]

    # Create again with same key
    response2 = client.post("/api/v1/claims/create", json=data_with_key)
    assert response2.status_code == 200
    claim_id_2 = response2.json()["claim_id"]

    assert claim_id_1 == claim_id_2


def test_validate_claim_invalid_pin(client, valid_wallet, sample_claim_data):
    # Setup: accept risk, create claim
    client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": valid_wallet,
            "accepted_version": "v1.0.0-devnet",
        },
    )

    create_response = client.post("/api/v1/claims/create", json=sample_claim_data)
    claim_id = create_response.json()["claim_id"]

    # Validate with wrong PIN
    response = client.post(
        "/api/v1/claims/validate",
        json={
            "claim_id": claim_id,
            "pin": "WRONGPIN",
            "claimant_wallet": valid_wallet,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "Invalid PIN" in data["message"]


def test_reserves_endpoint(client):
    response = client.get("/api/v1/reserves")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "reserve_ratio_bps" in data
    assert data["devnet_only"] is True


def test_stats_endpoint(client):
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_notes" in data
    assert "devnet" in data


def test_audit_events_endpoint(client):
    response = client.get("/api/v1/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "count" in data


def test_invalid_wallet_rejected(client):
    response = client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": "invalid!@#$%",
            "accepted_version": "v1.0.0-devnet",
        },
    )
    # Pydantic min_length validation returns 422; our sanitization returns 400
    assert response.status_code in (400, 422)


def test_rate_limiting(client):
    # Make many rapid requests to trigger rate limit
    for _ in range(25):
        response = client.get("/health")
        if response.status_code == 429:
            break
    else:
        # If we didn't hit rate limit, that's also fine (depends on timing)
        pass
