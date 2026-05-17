"""Tests for P6 (redemption controls) and P8 (multi-sig treasury)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.claimnote_service import ClaimNoteService
from services.ledger_service import LedgerService
from services.treasury_service import TreasuryService
from services.settlement_engine import SettlementEngine
from services.redemption_service import RedemptionService, _LARGE_TX_SATS, _RATE_LIMIT_PER_HOUR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_redemption_svc():
    c = ClaimNoteService()
    l = LedgerService()
    s = SettlementEngine()
    t = TreasuryService()
    r = RedemptionService(c, l, s, t)
    return c, l, s, t, r


# ---------------------------------------------------------------------------
# P6 — Idempotency
# ---------------------------------------------------------------------------

def test_idempotency_returns_same_receipt():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", 1000, "alice", "1234")
    key = "idem-abc-123"
    receipt1 = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", key)
    # Second call with same key must return the same receipt
    receipt2 = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", key)
    assert receipt1["receipt_id"] == receipt2["receipt_id"]


# ---------------------------------------------------------------------------
# P6 — Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_blocks_after_threshold():
    c, l, s, t, r = _make_redemption_svc()
    for i in range(_RATE_LIMIT_PER_HOUR):
        claim = c.create_claim("issuer", "btc", 100, "alice", "1234")
        r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", f"key-{i}")
    # Next redemption should be rate-limited
    claim_over = c.create_claim("issuer", "btc", 100, "alice", "1234")
    with pytest.raises(ValueError, match="Rate limit"):
        r.redeem(claim_over["claim_id"], "alice", "1234", "dest", "btc", "key-over")


# ---------------------------------------------------------------------------
# P6 — Large transaction routing to approval queue
# ---------------------------------------------------------------------------

def test_large_tx_routes_to_approval_queue():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", _LARGE_TX_SATS, "alice", "1234")
    receipt = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", "key-large")
    assert receipt["status"] == "pending_approval"
    queue = r.get_approval_queue()
    assert any(q["receipt_id"] == receipt["receipt_id"] for q in queue)


# ---------------------------------------------------------------------------
# P6 — Dual-operator approval workflow
# ---------------------------------------------------------------------------

def test_dual_approval_releases_settlement():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", _LARGE_TX_SATS, "alice", "1234")
    receipt = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", "key-dual")
    assert receipt["status"] == "pending_approval"

    # First operator approves — still pending
    after_first = r.approve_redemption(receipt["receipt_id"], "ops-1", required_approvals=2)
    assert after_first["status"] == "pending_approval"

    # Second operator approves — threshold met, auto-settles
    after_second = r.approve_redemption(receipt["receipt_id"], "ops-2", required_approvals=2)
    assert after_second["status"] == "processing"


def test_operator_cannot_double_approve():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", _LARGE_TX_SATS, "alice", "1234")
    receipt = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", "key-dup")
    r.approve_redemption(receipt["receipt_id"], "ops-1", required_approvals=2)
    with pytest.raises(ValueError, match="already approved"):
        r.approve_redemption(receipt["receipt_id"], "ops-1", required_approvals=2)


def test_reject_redemption():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", _LARGE_TX_SATS, "alice", "1234")
    receipt = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", "key-rej")
    rejected = r.reject_redemption(receipt["receipt_id"], "ops-1", "Sanctions match")
    assert rejected["status"] == "rejected"
    assert "Sanctions match" in rejected["rejection_reason"]


# ---------------------------------------------------------------------------
# P6 — Audit log
# ---------------------------------------------------------------------------

def test_audit_log_records_events():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", 500, "alice", "1234")
    receipt = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", "key-audit")
    log = r.get_audit_log()
    events = [e["event"] for e in log]
    assert "auto_settled" in events


def test_audit_log_filter_by_receipt():
    c, l, s, t, r = _make_redemption_svc()
    claim = c.create_claim("issuer", "btc", 500, "alice", "1234")
    receipt = r.redeem(claim["claim_id"], "alice", "1234", "dest", "btc", "key-filter")
    log = r.get_audit_log(receipt_id=receipt["receipt_id"])
    assert len(log) >= 1
    assert all(e["receipt_id"] == receipt["receipt_id"] for e in log)


# ---------------------------------------------------------------------------
# P8 — Treasury multi-sig batch signing
# ---------------------------------------------------------------------------

def test_treasury_batch_requires_multisig():
    t = TreasuryService()
    batch = t.create_settlement_batch("btc", [{"amount": 1000}])
    assert batch["batch_status"] == "pending_signatures"
    assert batch["required_signatures"] == 2


def test_treasury_batch_approved_after_threshold():
    t = TreasuryService()
    batch = t.create_settlement_batch("btc", [{"amount": 1000}])
    b1 = t.sign_batch(batch["batch_id"], "ops-1", "0xdeadbeef01")
    assert b1["batch_status"] == "pending_signatures"  # still needs one more
    b2 = t.sign_batch(batch["batch_id"], "ops-2", "0xdeadbeef02")
    assert b2["batch_status"] == "approved"


def test_treasury_broadcast_requires_approval():
    t = TreasuryService()
    batch = t.create_settlement_batch("btc", [{"amount": 1000}])
    with pytest.raises(ValueError, match="approved"):
        t.broadcast_batch(batch["batch_id"], "0xabc")


def test_treasury_operator_cannot_double_sign():
    t = TreasuryService()
    batch = t.create_settlement_batch("btc", [{"amount": 1000}])
    t.sign_batch(batch["batch_id"], "ops-1", "0xaaa")
    with pytest.raises(ValueError, match="already signed"):
        t.sign_batch(batch["batch_id"], "ops-1", "0xbbb")


def test_treasury_batch_rejection():
    t = TreasuryService()
    batch = t.create_settlement_batch("btc", [{"amount": 1000}])
    rejected = t.reject_batch(batch["batch_id"], "ops-1", "Suspicious destination")
    assert rejected["batch_status"] == "rejected"


def test_treasury_audit_log():
    t = TreasuryService()
    t.add_wallet("hot", "btc", "addr1", "pk1")
    t.create_settlement_batch("btc", [{"amount": 100}])
    log = t.get_audit_log()
    events = [e["event"] for e in log]
    assert "wallet_added" in events
    assert "batch_created" in events


def test_treasury_solvency_ratio():
    t = TreasuryService()
    l = LedgerService()
    w = t.add_wallet("hot", "btc", "addr1", "pk1")
    t.update_balance(w["wallet_id"], 10_000)
    l.create_account("acc1", "user", "btc")
    l._accounts["acc1"]["balance"] = 5_000
    ratio = t.get_solvency_ratio(l, "btc")
    assert ratio["solvent"] is True
    assert ratio["ratio_bps"] == 20_000  # 200% collateralized


def test_treasury_register_operator():
    t = TreasuryService()
    op = t.register_operator("ops-1", "Alice", "0xpubkey")
    assert op["operator_id"] == "ops-1"
    assert op["is_active"] is True
