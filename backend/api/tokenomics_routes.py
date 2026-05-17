"""MEMBRA Tokenomics API routes — PoV, GasVault, PoD, Token Routing."""
from fastapi import APIRouter, HTTPException, Query
from services.proof_of_volatility import ProofOfVolatilityService
from services.gasvault_service import GasVaultService
from services.proof_of_development import ProofOfDevelopmentService
from services.token_routing import TokenRoutingService, Chain

router = APIRouter(prefix="/api/v1", tags=["tokenomics"])

_pov = ProofOfVolatilityService()
_gasvault = GasVaultService()
_pod = ProofOfDevelopmentService()
_routing = TokenRoutingService()

# -- Proof-of-Volatility -----------------------------------------------

@router.get("/pov/state")
async def pov_state():
    return _pov.get_state()

@router.get("/pov/gates")
async def pov_gates():
    return {"gates": _pov.get_all_gates()}

@router.post("/pov/feed/membra")
async def pov_feed_membra(price: float, source: str = "oracle"):
    _pov.feed_membra_twap(price, source)
    return {"status": "ok", "membra_twap": _pov._membra_window.twap}

@router.post("/pov/feed/sol")
async def pov_feed_sol(price: float, source: str = "oracle"):
    _pov.feed_sol_twap(price, source)
    return {"status": "ok", "sol_twap": _pov._sol_window.twap}

@router.post("/pov/feed/gas")
async def pov_feed_gas(lamports: float, source: str = "rpc"):
    _pov.feed_gas_fee(lamports, source)
    return {"status": "ok", "gas_twap": _pov._gas_window.twap}

@router.post("/pov/liquidity")
async def pov_liquidity(usd_value: float):
    _pov.update_liquidity_depth(usd_value)
    return {"status": "ok", "liquidity_depth_usd": usd_value}

@router.post("/pov/treasury-coverage")
async def pov_treasury_coverage(coverage_bps: int):
    _pov.update_treasury_coverage(coverage_bps)
    return {"status": "ok", "coverage_bps": coverage_bps}

@router.get("/pov/proofs")
async def pov_proofs(limit: int = 50):
    return {"proofs": _pov.get_proofs(limit)}

# -- GasVault ----------------------------------------------------------

@router.get("/gasvault/health")
async def gasvault_health():
    return _gasvault.get_health()

@router.post("/gasvault/deposit")
async def gasvault_deposit(amount_sol: float):
    return _gasvault.deposit_sol(amount_sol)

@router.post("/gasvault/credits/issue")
async def gasvault_issue_credits(user_id: str, amount_lamports: int, reason: str = ""):
    return _gasvault.issue_credits(user_id, amount_lamports, reason)

@router.post("/gasvault/credits/spend")
async def gasvault_spend_credits(user_id: str, amount_lamports: int, tx_signature: str = ""):
    return _gasvault.spend_credits(user_id, amount_lamports, tx_signature)

@router.get("/gasvault/credits/{user_id}")
async def gasvault_credit_balance(user_id: str):
    return _gasvault.get_credit_balance(user_id)

@router.post("/gasvault/relayers/register")
async def gasvault_register_relayer(public_key: str):
    return _gasvault.register_relayer(public_key)

@router.get("/gasvault/relayers")
async def gasvault_list_relayers():
    return {"relayers": _gasvault.list_relayers()}

@router.post("/gasvault/reimburse/request")
async def gasvault_request_reimbursement(relayer_id: str, amount_lamports: int, tx_signature: str, user_id: str = None):
    return _gasvault.request_reimbursement(relayer_id, amount_lamports, tx_signature, user_id)

@router.post("/gasvault/reimburse/approve")
async def gasvault_approve_reimbursement(request_id: str):
    return _gasvault.approve_reimbursement(request_id)

@router.get("/gasvault/need")
async def gasvault_proof_of_need(gas_fee_twap: float, membra_twap: float, liquidity_depth_usd: float):
    return _gasvault.evaluate_need(gas_fee_twap, membra_twap, liquidity_depth_usd)

# -- Proof-of-Development ----------------------------------------------

@router.post("/pod/push")
async def pod_record_push(commit_sha: str, branch: str, author: str, message: str):
    return _pod.record_push(commit_sha, branch, author, message)

@router.post("/pod/tests")
async def pod_record_tests(proof_id: str, total: int, passed: int, failed: int, logs_url: str = ""):
    return _pod.record_tests(proof_id, total, passed, failed, logs_url)

@router.post("/pod/security")
async def pod_record_security(proof_id: str, criticals: int = 0, highs: int = 0, report_url: str = ""):
    return _pod.record_security(proof_id, criticals, highs, report_url)

@router.post("/pod/vote")
async def pod_cast_vote(proof_id: str, voter: str, approve: bool = True):
    return _pod.cast_vote(proof_id, voter, approve)

@router.post("/pod/governance/approve")
async def pod_governance_approve(proof_id: str, emission_amount: int, governance_tx: str = ""):
    return _pod.approve_governance(proof_id, emission_amount, governance_tx)

@router.post("/pod/governance/reject")
async def pod_governance_reject(proof_id: str, reason: str = ""):
    return _pod.reject_governance(proof_id, reason)

@router.get("/pod/proofs")
async def pod_list_proofs(phase: str = None):
    return {"proofs": _pod.list_proofs(phase)}

@router.get("/pod/proofs/{proof_id}")
async def pod_get_proof(proof_id: str):
    p = _pod.get_proof(proof_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proof not found")
    return p

@router.get("/pod/stats")
async def pod_stats():
    return _pod.get_stats()

# -- Token Routing -----------------------------------------------------

@router.get("/routing/chains")
async def routing_chains():
    return {"chains": _routing.list_chains()}

@router.post("/routing/tokens")
async def routing_register_token(symbol: str, name: str, chain: str, address: str, decimals: int = 9):
    return _routing.register_token(symbol, name, Chain(chain), address, decimals)

@router.get("/routing/tokens")
async def routing_list_tokens(chain: str = None, verified_only: bool = False):
    c = Chain(chain) if chain else None
    return {"tokens": _routing.list_tokens(c, verified_only)}

@router.post("/routing/tokens/verify")
async def routing_verify_token(token_id: str):
    return _routing.verify_token(token_id)

@router.post("/routing/adapters")
async def routing_register_adapter(name: str, source_chain: str, dest_chain: str, fee_bps: int = 0):
    return _routing.register_adapter(name, Chain(source_chain), Chain(dest_chain), fee_bps)

@router.get("/routing/adapters")
async def routing_list_adapters(verified_only: bool = False):
    return {"adapters": _routing.list_adapters(verified_only)}

@router.post("/routing/adapters/verify")
async def routing_verify_adapter(adapter_id: str):
    return _routing.verify_adapter(adapter_id)

@router.post("/routing/routes")
async def routing_create_route(source_token: str, dest_token: str, adapter_id: str):
    return _routing.create_route(source_token, dest_token, adapter_id)

@router.get("/routing/routes")
async def routing_find_routes(source_chain: str = None, dest_chain: str = None):
    sc = Chain(source_chain) if source_chain else None
    dc = Chain(dest_chain) if dest_chain else None
    return {"routes": _routing.find_routes(sc, dc)}

@router.post("/routing/routes/verify")
async def routing_verify_route(route_id: str):
    return _routing.verify_route(route_id)

@router.get("/routing/liquidity/{route_id}")
async def routing_check_liquidity(route_id: str, amount: float):
    return _routing.check_liquidity(route_id, amount)

@router.post("/routing/proofs")
async def routing_log_proof(route_id: str, tx_hash: str, source_amount: float, dest_amount: float, fee_paid: float):
    return _routing.log_route_proof(route_id, tx_hash, source_amount, dest_amount, fee_paid)

@router.get("/routing/proofs")
async def routing_get_proofs(route_id: str = None, limit: int = 50):
    return {"proofs": _routing.get_proofs(route_id, limit)}

@router.get("/routing/stats")
async def routing_stats():
    return _routing.get_stats()
