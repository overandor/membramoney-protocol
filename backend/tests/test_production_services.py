"""Tests for production services."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.identity_service import IdentityService
from services.claimnote_service import ClaimNoteService
from services.ledger_service import LedgerService
from services.treasury_service import TreasuryService
from services.settlement_engine import SettlementEngine
from services.redemption_service import RedemptionService

def test_identity_register_and_resolve():
    svc = IdentityService()
    user = svc.register("alice", "wallet123")
    assert user["username"] == "alice"
    assert "receive_tag" in user
    resolved = svc.resolve("alice")
    assert resolved["username"] == "alice"
    tag = user["receive_tag"]
    resolved2 = svc.resolve(tag)
    assert resolved2["username"] == "alice"

def test_claimnote_lifecycle():
    svc = ClaimNoteService()
    claim = svc.create_claim("issuer1", "btc", 1000000, "alice", "1234")
    assert claim["state"] == "created"
    transferred = svc.transfer_claim(claim["claim_id"], "alice", "bob")
    assert transferred["state"] == "transferred"
    assert transferred["owner"] == "bob"
    burned = svc.burn_claim(claim["claim_id"])
    assert burned["state"] == "burned"

def test_claimnote_split():
    svc = ClaimNoteService()
    claim = svc.create_claim("issuer1", "btc", 1000000, "alice", "1234")
    parts = svc.split_claim(claim["claim_id"], [400000, 600000])
    assert len(parts) == 2
    assert parts[0]["denomination"] + parts[1]["denomination"] == 1000000

def test_ledger_post_entry():
    ledger = LedgerService()
    ledger.create_account("acc_a", "user", "btc")
    ledger.create_account("acc_b", "user", "btc")
    ledger._accounts["acc_a"]["balance"] = 5000
    ledger.post_entry("test", "acc_a", "acc_b", 500, "btc", "idem_1")
    assert ledger.get_balance("acc_a") == 4500
    assert ledger.get_balance("acc_b") == 500
    same = ledger.post_entry("test", "acc_a", "acc_b", 500, "btc", "idem_1")
    assert ledger.get_balance("acc_a") == 4500

def test_treasury_reserve():
    t = TreasuryService()
    w = t.add_wallet("hot", "btc", "addr1", "pk1")
    t.update_balance(w["wallet_id"], 5000000)
    assert t.get_reserve_total("btc") == 5000000
    att = t.attest_reserve("btc", "admin", "sig")
    assert att["total_reserve"] == 5000000

def test_settlement_batch():
    s = SettlementEngine()
    req = s.submit_request("u1", "dest1", 1000, "btc", "btc")
    assert req["status"] == "pending"
    batch = s.build_batch("btc", "btc")
    assert batch["status"] == "collecting"
    approved = s.approve_batch(batch["batch_id"])
    assert approved["status"] == "approved"

def test_redemption_fraud():
    c = ClaimNoteService()
    l = LedgerService()
    s = SettlementEngine()
    t = TreasuryService()
    r = RedemptionService(c, l, s, t)
    claim = c.create_claim("issuer1", "btc", 1000000, "alice", "1234")
    fraud = r.fraud_check("alice", 1000000, 0)
    assert fraud["score"] < 50
    assert not fraud["blocked"]
