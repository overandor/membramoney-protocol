"""Tests for Proof-of-Volatility, GasVault, Proof-of-Development, Token Routing."""
import pytest
from services.proof_of_volatility import ProofOfVolatilityService, VolatilityWindow, TWAPSnapshot
from services.gasvault_service import GasVaultService
from services.proof_of_development import ProofOfDevelopmentService, Phase
from services.token_routing import TokenRoutingService, Chain


class TestVolatilityWindow:
    def test_empty_window(self):
        w = VolatilityWindow(asset="TEST/USD")
        assert w.twap is None
        assert w.stddev is None
        assert w.volatility_ratio is None

    def test_single_sample(self):
        w = VolatilityWindow(asset="TEST/USD")
        w.push(TWAPSnapshot(asset="TEST/USD", price=100.0, timestamp=1000, source="test"))
        assert w.twap == 100.0
        assert w.stddev is None

    def test_twap_calculation(self):
        w = VolatilityWindow(asset="TEST/USD")
        for p in [100, 110, 90]:
            w.push(TWAPSnapshot(asset="TEST/USD", price=p, timestamp=1000, source="test"))
        assert w.twap == 100.0

    def test_volatility_detection(self):
        w = VolatilityWindow(asset="TEST/USD")
        for p in [100, 105, 95, 110, 90]:
            w.push(TWAPSnapshot(asset="TEST/USD", price=p, timestamp=1000, source="test"))
        assert w.twap == 100.0
        assert w.stddev is not None
        assert w.stddev > 0


class TestProofOfVolatility:
    def test_initial_state(self):
        pov = ProofOfVolatilityService()
        state = pov.get_state()
        assert state["volatility_state"] == "unknown"
        assert state["membra"]["twap"] is None

    def test_feed_updates_state(self):
        pov = ProofOfVolatilityService()
        pov.feed_membra_twap(1.0)
        pov.feed_sol_twap(100.0)
        pov.feed_gas_fee(5000)
        pov.update_liquidity_depth(50000)
        pov.update_treasury_coverage(10000)
        state = pov.get_state()
        assert state["membra"]["twap"] == 1.0
        assert state["sol"]["twap"] == 100.0

    def test_gate_unlocks_with_fresh_data(self):
        pov = ProofOfVolatilityService()
        for p in [1.0, 1.02, 0.98, 1.03, 0.97]:
            pov.feed_membra_twap(p)
            pov.feed_sol_twap(100.0)
            pov.feed_gas_fee(5000)
        pov.update_liquidity_depth(50000)
        pov.update_treasury_coverage(10000)
        assert pov.is_unlocked("rebase_execution")

    def test_gate_blocked_stale_oracles(self):
        pov = ProofOfVolatilityService(max_oracle_age_seconds=0)
        pov.feed_membra_twap(1.0)
        assert not pov.is_unlocked("rebase_execution")

    def test_rebase_pause_always_unlocked(self):
        pov = ProofOfVolatilityService()
        pov._evaluate_gates()
        assert pov.is_unlocked("rebase_pause")

    def test_proof_logging(self):
        pov = ProofOfVolatilityService()
        pov.feed_membra_twap(1.0)
        pov.feed_sol_twap(100.0)
        pov.feed_gas_fee(5000)
        pov.update_liquidity_depth(50000)
        pov.update_treasury_coverage(10000)
        proof = pov.log_proof("rebase_execution", True)
        assert proof["approved"] is True
        assert proof["proof_hash"]
        assert len(pov.get_proofs()) == 1


class TestGasVault:
    def test_initial_vault_empty(self):
        gv = GasVaultService()
        assert gv.vault_sol == 0.0
        assert gv.coverage_ratio == float("inf")

    def test_deposit_sol(self):
        gv = GasVaultService()
        gv.deposit_sol(10.0)
        assert gv.vault_sol == 10.0

    def test_issue_credits(self):
        gv = GasVaultService()
        result = gv.issue_credits("user1", 5000, "test")
        assert result["credits_issued"] == 5000
        bal = gv.get_credit_balance("user1")
        assert bal["balance_lamports"] == 5000

    def test_spend_credits(self):
        gv = GasVaultService()
        gv.issue_credits("user1", 10000)
        result = gv.spend_credits("user1", 5000, "tx_sig")
        assert result["remaining_balance"] == 5000

    def test_insufficient_credits_raises(self):
        gv = GasVaultService()
        gv.issue_credits("user1", 1000)
        with pytest.raises(ValueError, match="Insufficient"):
            gv.spend_credits("user1", 5000)

    def test_relayer_lifecycle(self):
        gv = GasVaultService()
        gv.deposit_sol(1.0)
        r = gv.register_relayer("pubkey123")
        rid = r["relayer_id"]
        req = gv.request_reimbursement(rid, 5000, "tx_sig")
        gv.approve_reimbursement(req["request_id"])
        relayer = gv.get_relayer(rid)
        assert relayer["total_reimbursed_lamports"] == 5000

    def test_coverage_ratio(self):
        gv = GasVaultService()
        gv.deposit_sol(1.0)
        gv.issue_credits("user1", 500_000_000)
        assert gv.coverage_ratio == 2.0

    def test_proof_of_need(self):
        gv = GasVaultService()
        gv.deposit_sol(0.1)
        gv.issue_credits("user1", 500_000_000)
        need = gv.evaluate_need(gas_fee_twap=15000, membra_twap=2.0, liquidity_depth_usd=50000)
        assert need["requires_governance"]
        assert len(need["needs"]) > 0


class TestProofOfDevelopment:
    def test_record_push(self):
        pod = ProofOfDevelopmentService()
        result = pod.record_push("abc123", "main", "dev", "feat: test")
        assert result["phase"] == Phase.PUSH.value

    def test_tests_pass_advances_phase(self):
        pod = ProofOfDevelopmentService()
        r = pod.record_push("abc123", "main", "dev", "feat: test")
        result = pod.record_tests(r["proof_id"], total=10, passed=10, failed=0)
        assert result["phase"] == Phase.TESTS.value

    def test_tests_fail_rejects(self):
        pod = ProofOfDevelopmentService()
        r = pod.record_push("abc123", "main", "dev", "feat: test")
        result = pod.record_tests(r["proof_id"], total=10, passed=5, failed=5)
        assert result["phase"] == Phase.REJECTED.value

    def test_full_lifecycle(self):
        pod = ProofOfDevelopmentService()
        r = pod.record_push("abc123", "main", "dev", "feat: test")
        pid = r["proof_id"]
        pod.record_tests(pid, 10, 10, 0)
        pod.record_security(pid, criticals=0)
        pod.cast_vote(pid, "voter1")
        pod.cast_vote(pid, "voter2")
        pod.cast_vote(pid, "voter3")
        result = pod.approve_governance(pid, emission_amount=1000)
        assert result["phase"] == Phase.EXECUTED.value
        assert result["emission_amount"] == 1000
        assert result["proof_hash"]

    def test_emission_exceeds_cap_raises(self):
        pod = ProofOfDevelopmentService(emission_cap=100)
        r = pod.record_push("abc123", "main", "dev", "feat: test")
        pid = r["proof_id"]
        pod.record_tests(pid, 10, 10, 0)
        pod.record_security(pid, criticals=0)
        for v in ["v1", "v2", "v3"]:
            pod.cast_vote(pid, v)
        with pytest.raises(ValueError, match="exceeds cap"):
            pod.approve_governance(pid, emission_amount=500)

    def test_security_criticals_reject(self):
        pod = ProofOfDevelopmentService()
        r = pod.record_push("abc123", "main", "dev", "feat: test")
        pid = r["proof_id"]
        pod.record_tests(pid, 10, 10, 0)
        result = pod.record_security(pid, criticals=3)
        assert result["phase"] == Phase.REJECTED.value

    def test_stats(self):
        pod = ProofOfDevelopmentService()
        pod.record_push("abc1", "main", "dev", "feat: a")
        pod.record_push("abc2", "main", "dev", "feat: b")
        stats = pod.get_stats()
        assert stats["total_proofs"] == 2
        assert stats["pending"] == 2


class TestTokenRouting:
    def test_list_chains(self):
        tr = TokenRoutingService()
        chains = tr.list_chains()
        assert len(chains) >= 1
        assert any(c["chain"] == "solana" for c in chains)

    def test_register_and_verify_token(self):
        tr = TokenRoutingService()
        t = tr.register_token("MEMBRA", "Membra Token", Chain.SOLANA, "addr123")
        assert t["is_verified"] is False
        v = tr.verify_token(t["token_id"])
        assert v["is_verified"] is True

    def test_adapter_lifecycle(self):
        tr = TokenRoutingService()
        a = tr.register_adapter("Wormhole", Chain.SOLANA, Chain.ETHEREUM, fee_bps=10)
        assert a["is_verified"] is False
        v = tr.verify_adapter(a["adapter_id"])
        assert v["is_verified"] is True
        assert v["is_enabled"] is True

    def test_create_route(self):
        tr = TokenRoutingService()
        src = tr.register_token("MEMBRA", "Membra", Chain.SOLANA, "addr1", verified=True)
        dst = tr.register_token("USDC", "USD Coin", Chain.ETHEREUM, "addr2", verified=True)
        adapter = tr.register_adapter("Wormhole", Chain.SOLANA, Chain.ETHEREUM)
        tr.verify_adapter(adapter["adapter_id"])
        route = tr.create_route(src["token_id"], dst["token_id"], adapter["adapter_id"])
        assert route["status"] == "pending_verification"
        active = tr.verify_route(route["route_id"])
        assert active["status"] == "active"

    def test_liquidity_check(self):
        tr = TokenRoutingService()
        src = tr.register_token("MEMBRA", "Membra", Chain.SOLANA, "addr1", verified=True)
        dst = tr.register_token("USDC", "USD Coin", Chain.ETHEREUM, "addr2", verified=True)
        adapter = tr.register_adapter("Wormhole", Chain.SOLANA, Chain.ETHEREUM)
        tr.verify_adapter(adapter["adapter_id"])
        route = tr.create_route(src["token_id"], dst["token_id"], adapter["adapter_id"])
        tr.verify_route(route["route_id"])
        check = tr.check_liquidity(route["route_id"], 100.0)
        assert check["sufficient"] is True

    def test_route_proof_logging(self):
        tr = TokenRoutingService()
        src = tr.register_token("MEMBRA", "Membra", Chain.SOLANA, "addr1", verified=True)
        dst = tr.register_token("USDC", "USD Coin", Chain.ETHEREUM, "addr2", verified=True)
        adapter = tr.register_adapter("Wormhole", Chain.SOLANA, Chain.ETHEREUM)
        tr.verify_adapter(adapter["adapter_id"])
        route = tr.create_route(src["token_id"], dst["token_id"], adapter["adapter_id"])
        tr.verify_route(route["route_id"])
        proof = tr.log_route_proof(route["route_id"], "tx_hash_123", 100.0, 99.0, 1.0)
        assert proof["proof_hash"]
        assert len(tr.get_proofs()) == 1

    def test_stats(self):
        tr = TokenRoutingService()
        tr.register_token("MEMBRA", "Membra", Chain.SOLANA, "addr1")
        stats = tr.get_stats()
        assert stats["tokens"] == 1
        assert stats["chains"] >= 1
