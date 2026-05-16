"""
Membra Money Protocol — Backend Unit Tests
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app

client = TestClient(app)


def accept_risk(wallet: str):
    return client.post(
        "/api/v1/risk-disclosure/accept",
        json={
            "wallet_address": wallet,
            "accepted_version": "v1.0.0-devnet",
        },
    )


def create_micropayment(wallet: str, **overrides):
    accept_risk(wallet)
    payload = {
        "sender_wallet": wallet,
        "usd_cents": 1,
        "asset": "SOLANA_DEVNET_USDC",
        "delivery_channel": "qr",
        "expires_minutes": 30,
        "risk_version": "v1.0.0-devnet",
    }
    payload.update(overrides)
    return client.post("/api/v1/micropayments", json=payload)


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
    r = accept_risk("TestWallet1234567890123456789012345678901")
    assert r.status_code == 200
    data = r.json()
    assert data["accepted"] is True
    assert data["wallet_address"] == "TestWallet1234567890123456789012345678901"
    assert data["version"] == "v1.0.0-devnet"


# ------------------------------------------------------------------
# 5. Claim creation validation
# ------------------------------------------------------------------
def test_claim_create():
    accept_risk("ClaimCreator123456789012345678901234567")
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
    accept_risk("WrongPinUser1234567890123456789012345678")
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
    accept_risk("ExpiredUser12345678901234567890123456789")
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

    future = datetime.now(timezone.utc) + timedelta(minutes=5)
    with patch("main.datetime") as mock_dt:
        mock_dt.now.return_value = future
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
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
    assert "total_micropayments" in data
    assert data["devnet"] is True


# ------------------------------------------------------------------
# 10. Payment rails must be honest
# ------------------------------------------------------------------
def test_payment_rails_are_honest():
    r = client.get("/api/v1/rails")
    assert r.status_code == 200
    data = r.json()
    assert data["minimum_usd_cents"] == 1
    assert data["primary"] == "SOLANA_DEVNET_USDC"
    assert data["rails"]["BTC_L1"]["available"] is False
    assert data["rails"]["BTC_LIGHTNING"]["available"] is False
    assert "No private keys" in data["custody_disclaimer"]


# ------------------------------------------------------------------
# 11. Micropayment creation with $0.01 minimum and QR/link payload
# ------------------------------------------------------------------
def test_micropayment_create_minimum_cent_qr_link():
    r = create_micropayment("MicroSender11111111111111111111111111")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["usd_cents"] == 1
    assert data["asset"] == "SOLANA_DEVNET_USDC"
    assert data["status"] == "awaiting_funding"
    assert data["funding_status"] == "awaiting_escrow_funding"
    assert data["qr_payload"] == data["claim_url"]
    assert "secret=" in data["claim_url"]
    assert "No private keys" in data["custody_disclaimer"]

    preview = client.get(f"/api/v1/claims/{data['claim_id']}")
    assert preview.status_code == 200
    preview_data = preview.json()
    assert preview_data["usd_cents"] == 1
    assert preview_data["status"] == "awaiting_funding"


# ------------------------------------------------------------------
# 12. Redemption is blocked until escrow funding is confirmed
# ------------------------------------------------------------------
def test_micropayment_redeem_blocks_unfunded_claim():
    r = create_micropayment("RedeemSender1111111111111111111111111")
    data = r.json()
    secret = parse_qs(urlparse(data["claim_url"]).query)["secret"][0]

    redeem = client.post(
        f"/api/v1/claims/{data['claim_id']}/redeem",
        json={
            "secret": secret,
            "claimant_wallet": "RedeemClaimant11111111111111111111111",
        },
    )
    assert redeem.status_code == 200
    redeem_data = redeem.json()
    assert redeem_data["redeemed"] is False
    assert "not confirmed" in redeem_data["message"]


# ------------------------------------------------------------------
# 13. $0.00 micropayments are rejected
# ------------------------------------------------------------------
def test_micropayment_rejects_zero_cents():
    r = create_micropayment(
        "ZeroCentSender111111111111111111111111",
        usd_cents=0,
    )
    assert r.status_code == 422


# ------------------------------------------------------------------
# 14. BTC Lightning is unavailable unless explicitly configured
# ------------------------------------------------------------------
def test_btc_lightning_unavailable_without_configuration():
    r = create_micropayment(
        "LightningSender111111111111111111111111",
        asset="BTC_LIGHTNING",
    )
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]


# ------------------------------------------------------------------
# 15. Email/SMS providers report degraded mode instead of fake success
# ------------------------------------------------------------------
def test_email_delivery_reports_degraded_provider():
    r = create_micropayment(
        "EmailSender111111111111111111111111111",
        delivery_channel="email",
        recipient_hint="recipient@example.test",
    )
    data = r.json()
    assert data["backend_degraded"] is True

    delivery = client.post(
        f"/api/v1/claims/{data['claim_id']}/delivery",
        json={"channel": "email", "destination": "recipient@example.test"},
    )
    assert delivery.status_code == 200
    delivery_data = delivery.json()
    assert delivery_data["sent"] is False
    assert delivery_data["degraded"] is True
    assert "not configured" in delivery_data["message"]


# ------------------------------------------------------------------
# 16. Admin routes are not publicly usable with default secrets
# ------------------------------------------------------------------
def test_admin_reserve_attestation_requires_configured_admin_key():
    r = client.post(
        "/api/v1/admin/reserves/attest",
        json={"reserve_ratio_bps": 10_000, "statement": "devnet test attestation"},
    )
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]
