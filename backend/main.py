"""
Membra Money Protocol — FastAPI Backend
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import settings
from core.logging import log_info, log_warn, log_error
from core.metrics import metrics
from middleware import RequestIDMiddleware, AuditLoggingMiddleware, RateLimitMiddleware
from services.claim_service import ClaimService
from services.reserve_service import ReserveService
from services.risk_disclosure import RiskDisclosureService
from db.adapter import db

# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Membra Money Protocol API",
    version="0.1.0-devnet",
    description="EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health and readiness probes"},
        {"name": "risk", "description": "Risk disclosure management"},
        {"name": "claims", "description": "Claim creation and validation"},
        {"name": "reserves", "description": "Reserve status (illustrative only)"},
        {"name": "audit", "description": "Audit event logging"},
        {"name": "metrics", "description": "Prometheus-style metrics"},
    ],
)

# ------------------------------------------------------------------
# Security: CORS Configuration
# ------------------------------------------------------------------

# Parse allowed origins from environment (comma-separated)
# Default: localhost for dev, empty for production
_DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:3000,http://localhost:8000"
_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", _DEFAULT_ORIGINS if settings.debug else "").split(",")
_ALLOWED_ORIGINS = [o.strip() for o in _ALLOWED_ORIGINS if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-Idempotency-Key"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, rate=2.0, capacity=20, window=60)

# ------------------------------------------------------------------
# Request / Response Models
# ------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    env: str
    devnet: bool
    timestamp: str

class RiskDisclosureResponse(BaseModel):
    version: str
    text: str
    hash: str

class RiskAcceptRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=44)
    accepted_version: str
    signature: Optional[str] = None

class RiskAcceptResponse(BaseModel):
    accepted: bool
    wallet_address: str
    accepted_at: str
    version: str

class ClaimCreateRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=44)
    denomination_sats: int = Field(..., ge=1)
    expires_minutes: int = Field(..., ge=1, le=129600)
    risk_version: str
    idempotency_key: Optional[str] = Field(default=None, max_length=64)

class ClaimCreateResponse(BaseModel):
    claim_id: str
    claim_url: str
    pin_hash: str
    expires_at: str
    denomination_sats: int
    devnet_warning: str

class ClaimValidateRequest(BaseModel):
    claim_id: str
    pin: str = Field(..., min_length=4, max_length=32)
    claimant_wallet: str = Field(..., min_length=32, max_length=44)

class ClaimValidateResponse(BaseModel):
    valid: bool
    claim_id: str
    message: str
    denomination_sats: Optional[int] = None

class ReserveResponse(BaseModel):
    status: str
    reserve_ratio_bps: int
    attested_at: Optional[str]
    disclaimer: str
    devnet_only: bool

class StatsResponse(BaseModel):
    total_notes: int
    redeemed_notes: int
    active_claims: int
    reserve_ratio_bps: int
    devnet: bool
    generated_at: str

class AuditEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: str
    details: Dict[str, Any]

class AuditEventsResponse(BaseModel):
    events: List[AuditEvent]
    count: int

# ------------------------------------------------------------------
# In-Memory Stores (devnet/demo only)
# ------------------------------------------------------------------
# Claims, risk acceptances, audit events, and idempotency keys are
# managed by db.adapter (PostgreSQL when DATABASE_URL is set, otherwise
# in-memory fallback). Only brute-force tracker remains local.
# ------------------------------------------------------------------

_brute_force_tracker: Dict[str, List[float]] = {}

# ------------------------------------------------------------------
# Store Limits (devnet/demo only — production should use PostgreSQL)
# ------------------------------------------------------------------

MAX_CLAIMS = 10_000
MAX_RISK_ACCEPTANCES = 10_000
MAX_AUDIT_EVENTS = 50_000
MAX_IDEMPOTENCY_KEYS = 10_000
MAX_BRUTE_FORCE_TRACKER = 10_000

def _enforce_store_limits():
    """Trim in-memory stores to prevent unbounded growth."""
    global _brute_force_tracker

    if len(_brute_force_tracker) > MAX_BRUTE_FORCE_TRACKER:
        _brute_force_tracker = {}
        log_warn("Cleared brute force tracker")

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

MAX_BRUTE_FORCE_ATTEMPTS = 5
BRUTE_FORCE_WINDOW_SECONDS = 3600

def _hash_pin(pin: str, salt: str) -> str:
    pepper = settings.hmac_pepper
    return hashlib.sha256(f"{pin}:{salt}:{pepper}".encode()).hexdigest()

def _check_brute_force(key: str) -> bool:
    now = time.time()
    attempts = _brute_force_tracker.get(key, [])
    attempts = [t for t in attempts if now - t < BRUTE_FORCE_WINDOW_SECONDS]
    _brute_force_tracker[key] = attempts
    return len(attempts) >= MAX_BRUTE_FORCE_ATTEMPTS

def _sanitize_wallet_address(addr: str) -> str:
    """Sanitize wallet address: strip whitespace, lowercase base58 chars only."""
    addr = addr.strip()
    # Base58 alphabet: 1-9, A-H, J-N, P-Z, a-k, m-z
    valid_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    if not all(c in valid_chars for c in addr):
        raise ValueError("Invalid characters in wallet address")
    return addr

def _sanitize_claim_id(claim_id: str) -> str:
    """Sanitize claim ID: strip whitespace, validate UUID format roughly."""
    claim_id = claim_id.strip()
    # UUID format: 8-4-4-4-12 hex chars
    if len(claim_id) < 8:
        raise ValueError("Claim ID too short")
    # Allow only hex chars and dashes
    valid_chars = set("0123456789abcdefABCDEF-")
    if not all(c in valid_chars for c in claim_id):
        raise ValueError("Invalid characters in claim ID")
    return claim_id

def _sanitize_pin(pin: str) -> str:
    """Sanitize PIN: strip whitespace, alphanumeric only."""
    pin = pin.strip()
    if not pin.isalnum():
        raise ValueError("PIN must be alphanumeric")
    return pin

def _record_brute_force(key: str):
    now = time.time()
    attempts = _brute_force_tracker.get(key, [])
    attempts.append(now)
    _brute_force_tracker[key] = attempts

def _add_audit(event_type: str, details: Dict[str, Any]):
    db.create_audit(event_type, details=details)
    log_info(f"Audit: {event_type}", extra=details)

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
async def health():
    import sys
    memory_mb = None
    try:
        import psutil
        process = psutil.Process()
        memory_mb = round(process.memory_info().rss / 1024 / 1024, 2)
    except ImportError:
        pass

    return {
        "status": "healthy",
        "env": settings.env,
        "devnet": settings.env == "devnet",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0-devnet",
        "stores": {
            "claims": db.claim_count(),
            "risk_acceptances": db.risk_acceptance_count(),
            "audit_events": db.audit_count(),
            "idempotency_keys": db.idempotency_count(),
        },
        "memory_mb": memory_mb,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

@app.get("/ready")
async def ready():
    checks = {
        "claims_store": db.claim_count() >= 0,
        "risk_store": db.risk_acceptance_count() >= 0,
        "audit_store": db.audit_count() >= 0,
        "settings_loaded": settings is not None,
    }
    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "env": settings.env,
        "devnet": settings.env == "devnet",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }

@app.get("/api/v1/risk-disclosure", response_model=RiskDisclosureResponse)
async def get_risk_disclosure():
    svc = RiskDisclosureService()
    text = svc.get_text()
    version = settings.risk_disclosure_version
    return RiskDisclosureResponse(
        version=version,
        text=text,
        hash=hashlib.sha256(f"{version}:{text}".encode()).hexdigest(),
    )

@app.post("/api/v1/risk-disclosure/accept", response_model=RiskAcceptResponse)
async def accept_risk_disclosure(req: RiskAcceptRequest):
    svc = RiskDisclosureService()
    current_version = settings.risk_disclosure_version
    if req.accepted_version != current_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Risk disclosure version mismatch. Expected {current_version}, got {req.accepted_version}",
        )

    accepted_at = datetime.now(timezone.utc).isoformat()
    db.create_risk_acceptance(req.wallet_address, req.accepted_version)
    _add_audit("risk_disclosure_accepted", {"wallet": req.wallet_address, "version": req.accepted_version})

    return RiskAcceptResponse(
        accepted=True,
        wallet_address=req.wallet_address,
        accepted_at=accepted_at,
        version=req.accepted_version,
    )

@app.post("/api/v1/claims/create", response_model=ClaimCreateResponse)
async def create_claim(req: ClaimCreateRequest):
    # Sanitize inputs
    try:
        wallet_address = _sanitize_wallet_address(req.wallet_address)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not db.has_risk_acceptance(wallet_address, settings.risk_disclosure_version):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Risk disclosure not accepted for this wallet.",
        )

    # Idempotency: return existing claim if key already used
    if req.idempotency_key:
        existing = db.get_idempotency(req.idempotency_key)
        if existing:
            return ClaimCreateResponse(
                claim_id=existing["claim_id"],
                claim_url=existing["claim_url"],
                pin_hash=existing["pin_hash"],
                expires_at=existing["expires_at"],
                denomination_sats=existing["denomination_sats"],
                devnet_warning="EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY (idempotent replay)",
            )

    claim_id = str(uuid.uuid4())
    raw_pin = str(uuid.uuid4())[:8].upper()
    salt = str(uuid.uuid4())
    pin_hash = _hash_pin(raw_pin, salt)
    expires_at = datetime.now(timezone.utc).timestamp() + (req.expires_minutes * 60)

    db.create_claim(
        claim_id=claim_id,
        issuer_wallet=req.wallet_address,
        denomination_sats=req.denomination_sats,
        pin_hash=pin_hash,
        salt=salt,
        expires_at=expires_at,
    )

    _add_audit("claim_created", {
        "claim_id": claim_id,
        "issuer": req.wallet_address,
        "denomination_sats": req.denomination_sats,
    })

    claim_url = f"{settings.backend_url}/claim/{claim_id}"

    # Store idempotency mapping
    if req.idempotency_key:
        db.set_idempotency(req.idempotency_key, {
            "claim_id": claim_id,
            "claim_url": claim_url,
            "pin_hash": pin_hash,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            "denomination_sats": req.denomination_sats,
        })

    return ClaimCreateResponse(
        claim_id=claim_id,
        claim_url=claim_url,
        pin_hash=pin_hash,
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        denomination_sats=req.denomination_sats,
        devnet_warning="EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY",
    )

@app.post("/api/v1/claims/validate", response_model=ClaimValidateResponse)
async def validate_claim(req: ClaimValidateRequest):
    # Sanitize inputs
    try:
        claim_id = _sanitize_claim_id(req.claim_id)
        claimant_wallet = _sanitize_wallet_address(req.claimant_wallet)
        pin = _sanitize_pin(req.pin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    if claim["claimed"]:
        return ClaimValidateResponse(
            valid=False,
            claim_id=claim_id,
            message="Claim already consumed.",
        )

    now = datetime.now(timezone.utc).timestamp()
    if now > claim["expires_at"]:
        return ClaimValidateResponse(
            valid=False,
            claim_id=claim_id,
            message="Claim expired.",
        )

    bf_key = f"{claim_id}:{claimant_wallet}"
    if _check_brute_force(bf_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
        )

    provided_hash = _hash_pin(req.pin, claim["salt"])
    if not hmac.compare_digest(provided_hash, claim["pin_hash"]):
        _record_brute_force(bf_key)
        return ClaimValidateResponse(
            valid=False,
            claim_id=req.claim_id,
            message="Invalid PIN.",
        )

    db.mark_claim_claimed(claim_id, req.claimant_wallet)

    _add_audit("claim_validated", {
        "claim_id": req.claim_id,
        "claimant": req.claimant_wallet,
    })

    return ClaimValidateResponse(
        valid=True,
        claim_id=req.claim_id,
        message="Claim validated successfully.",
        denomination_sats=claim["denomination_sats"],
    )

@app.get("/api/v1/reserves", response_model=ReserveResponse)
async def get_reserves():
    svc = ReserveService()
    return ReserveResponse(
        status=svc.status(),
        reserve_ratio_bps=svc.reserve_ratio_bps(),
        attested_at=svc.attested_at(),
        disclaimer="Reserve data is illustrative only. No real BTC custody exists.",
        devnet_only=True,
    )

@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    total = db.claim_count()
    redeemed = db.redeemed_claim_count()
    active = total - redeemed
    svc = ReserveService()
    return StatsResponse(
        total_notes=total,
        redeemed_notes=redeemed,
        active_claims=active,
        reserve_ratio_bps=svc.reserve_ratio_bps(),
        devnet=True,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/api/v1/audit/events", response_model=AuditEventsResponse)
async def get_audit_events(limit: int = 100):
    raw_events = db.get_audits(limit)
    events = [
        AuditEvent(
            event_id=e.get("event_id", ""),
            event_type=e.get("event_type", ""),
            timestamp=e.get("timestamp", ""),
            details=e.get("details", {}),
        )
        for e in raw_events
    ]
    return AuditEventsResponse(
        events=events,
        count=len(events),
    )

@app.get("/metrics", tags=["metrics"])
async def get_metrics():
    """Prometheus-style metrics endpoint."""
    metrics.gauge("membra_claims_total", db.claim_count())
    metrics.gauge("membra_risk_acceptances_total", db.risk_acceptance_count())
    metrics.gauge("membra_audit_events_total", db.audit_count())
    metrics.gauge("membra_idempotency_keys_total", db.idempotency_count())
    return JSONResponse(
        content=metrics.to_dict(),
        media_type="application/json",
    )

# ------------------------------------------------------------------
# Exception Handlers
# ------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "devnet": True,
                "production_ready": False,
            },
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "status_code": 500,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "devnet": True,
                "production_ready": False,
            },
        },
    )

# Production services
from services.identity_service import IdentityService
from services.claimnote_service import ClaimNoteService
from services.ledger_service import LedgerService
from services.treasury_service import TreasuryService
from services.settlement_engine import SettlementEngine
from services.redemption_service import RedemptionService

_identity = IdentityService()
_claimnotes = ClaimNoteService()
_ledger = LedgerService()
_treasury = TreasuryService()
_settlement = SettlementEngine()
_redemption = RedemptionService(_claimnotes, _ledger, _settlement, _treasury)

_ledger.create_account("reserve_btc", "reserve", "btc")
_ledger.create_account("settlement_btc", "settlement", "btc")
_ledger.create_account("fee_pool_btc", "fee", "btc")

# Identity endpoints
@app.post("/api/v1/identity/register")
async def identity_register(username: str, wallet_address: str):
    user = _identity.register(username, wallet_address)
    _ledger.create_account(f"user_{user['user_id']}", "user", "btc", user["user_id"])
    return user

@app.get("/api/v1/identity/resolve/{identifier}")
async def identity_resolve(identifier: str):
    return _identity.resolve(identifier)

@app.post("/api/v1/identity/rotate-tag")
async def identity_rotate_tag(username: str):
    return {"new_tag": _identity.rotate_tag(username)}

# Claim-note endpoints
@app.post("/api/v1/claims")
async def claim_create(issuer_id: str, asset_type: str, denomination: int, owner: str, bearer_condition: str, expiry_minutes: int = 60):
    return _claimnotes.create_claim(issuer_id, asset_type, denomination, owner, bearer_condition, expiry_minutes)

@app.get("/api/v1/claims/{claim_id}")
async def claim_get(claim_id: str):
    claim = _claimnotes.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim

@app.post("/api/v1/claims/{claim_id}/transfer")
async def claim_transfer(claim_id: str, from_user: str, to_user: str):
    return _claimnotes.transfer_claim(claim_id, from_user, to_user)

@app.post("/api/v1/claims/{claim_id}/split")
async def claim_split(claim_id: str, amounts: list):
    return _claimnotes.split_claim(claim_id, amounts)

@app.post("/api/v1/claims/{claim_id}/redeem")
async def claim_redeem(claim_id: str, user_id: str, pin: str, destination: str, chain: str):
    return _redemption.redeem(claim_id, user_id, pin, destination, chain, str(uuid.uuid4()))

# Ledger endpoints
@app.get("/api/v1/ledger/balance/{account_id}")
async def ledger_balance(account_id: str):
    return {"account_id": account_id, "balance": _ledger.get_balance(account_id)}

@app.get("/api/v1/ledger/history/{account_id}")
async def ledger_history(account_id: str, limit: int = 100):
    return {"entries": _ledger.get_history(account_id, limit)}

# Settlement endpoints
@app.get("/api/v1/settlement/quote")
async def settlement_quote(amount: int, chain: str):
    return {"fee": _settlement._estimate_fee(amount, chain)}

@app.get("/api/v1/settlement/status/{batch_id}")
async def settlement_status(batch_id: str):
    batch = _settlement._batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch

# Treasury endpoints
@app.get("/api/v1/treasury/reserves")
async def treasury_reserves():
    return {
        "btc": _treasury.get_reserve_total("btc"),
        "sol": _treasury.get_reserve_total("sol"),
        "eth": _treasury.get_reserve_total("eth"),
        "usdc": _treasury.get_reserve_total("usdc"),
    }

@app.get("/api/v1/treasury/batches/pending")
async def treasury_pending_batches():
    """Return settlement batches awaiting multi-sig approval."""
    return {"batches": _treasury.get_pending_batches()}

@app.post("/api/v1/treasury/batches/{batch_id}/sign")
async def treasury_sign_batch(batch_id: str, operator_id: str, signature_hex: str):
    """Submit one operator signature toward the M-of-N threshold."""
    try:
        return _treasury.sign_batch(batch_id, operator_id, signature_hex)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/treasury/batches/{batch_id}/reject")
async def treasury_reject_batch(batch_id: str, operator_id: str, reason: str):
    try:
        return _treasury.reject_batch(batch_id, operator_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/treasury/operators")
async def register_operator(operator_id: str, name: str, public_key: str):
    return _treasury.register_operator(operator_id, name, public_key)

@app.get("/api/v1/treasury/audit")
async def treasury_audit_log(limit: int = 100):
    return {"events": _treasury.get_audit_log(limit)}

# Redemption approval queue endpoints (P6 — operational controls)
@app.get("/api/v1/redemption/queue")
async def redemption_approval_queue():
    """Return redemptions pending dual-operator approval."""
    return {"queue": _redemption.get_approval_queue()}

@app.post("/api/v1/redemption/{receipt_id}/approve")
async def approve_redemption(receipt_id: str, operator_id: str, required_approvals: int = 2):
    try:
        return _redemption.approve_redemption(receipt_id, operator_id, required_approvals)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/redemption/{receipt_id}/reject")
async def reject_redemption(receipt_id: str, operator_id: str, reason: str):
    try:
        return _redemption.reject_redemption(receipt_id, operator_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/redemption/{receipt_id}")
async def get_receipt(receipt_id: str):
    r = _redemption.get_receipt(receipt_id)
    if not r:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return r

@app.get("/api/v1/redemption/audit/log")
async def redemption_audit_log(receipt_id: Optional[str] = None, limit: int = 100):
    return {"events": _redemption.get_audit_log(receipt_id, limit)}

@app.get("/api/v1/redemption/quarantine/list")
async def redemption_quarantine():
    return {"quarantine": _redemption.get_quarantine()}

# Compliance + Security endpoints
from services.compliance_service import ComplianceService
from services.security_service import SecurityService

_compliance = ComplianceService()
_security = SecurityService()

@app.post("/api/v1/compliance/screen")
async def compliance_screen(user_id: str, screening_type: str):
    return _compliance.screen_user(user_id, screening_type)

@app.get("/api/v1/compliance/quarantine")
async def compliance_quarantine():
    return {"quarantine": _compliance.get_quarantine()}

@app.post("/api/v1/security/check")
async def security_check(user_id: str, amount: int, ip_hash: str, device_fingerprint: str):
    _security.record_transaction(user_id, amount, ip_hash, device_fingerprint)
    velocity = _security.check_velocity(user_id, ip_hash)
    anomaly = _security.check_anomaly(user_id, amount, ip_hash, device_fingerprint)
    return {"velocity": velocity, "anomaly": anomaly}

# Fee savings + sponsor endpoints
from services.fee_sponsor_service import FeeSponsorService as _FeeSponsorSvc

_fee_sponsor = _FeeSponsorSvc(
    enabled=os.getenv("FEE_SPONSORING_ENABLED", "false").lower() == "true",
    sponsor_wallet=os.getenv("FEE_SPONSOR_WALLET", ""),
)

@app.get("/api/v1/fees/savings")
async def fee_savings(amount_sats: int = 100_000):
    """Show BTC network fee savings when using Membra bearer notes on Solana."""
    btc_low = 15_000
    btc_med = 50_000
    btc_high = 200_000
    sol_fee_sats = 25  # ~5000 lamports at typical SOL price
    user_pays = 0 if _fee_sponsor.enabled else sol_fee_sats
    return {
        "amount_transferred_sats": amount_sats,
        "btc_network_fees": {
            "low_congestion_sats": btc_low,
            "medium_congestion_sats": btc_med,
            "high_congestion_sats": btc_high,
        },
        "membra_fee_sats": sol_fee_sats,
        "fee_sponsored": _fee_sponsor.enabled,
        "user_pays_sats": user_pays,
        "savings_vs_btc": {
            "low_congestion_pct": round((1 - user_pays / btc_low) * 100, 1),
            "medium_congestion_pct": round((1 - user_pays / btc_med) * 100, 1),
            "high_congestion_pct": round((1 - user_pays / btc_high) * 100, 1),
        },
        "settlement_time": {
            "btc_confirmations": "10–60 minutes",
            "membra_solana": "~400ms",
        },
        "btc_tps": 7,
        "solana_tps": 65_000,
        "innovation": {
            "cross_chain_value": "BTC-denominated value transferred on Solana without a bridge",
            "no_wallet_needed": "Recipients claim via PIN/link — no wallet required to receive",
            "programmable_expiry": "Notes expire automatically; no stuck funds",
            "split_merge": "Split one note into change or merge many into one",
        },
        "disclaimer": "Fee estimates are illustrative. SOL and BTC prices fluctuate.",
        "devnet": settings.env == "devnet",
    }

@app.get("/api/v1/sponsor/status")
async def sponsor_status():
    """Check whether fee sponsoring (gasless transfers) is active."""
    stats = _fee_sponsor.get_stats()
    return {
        "fee_sponsoring_enabled": _fee_sponsor.enabled,
        "user_pays_fees": not _fee_sponsor.enabled,
        "solana_fee_per_tx_lamports": 5_000,
        "explanation": (
            "Fee sponsoring means the protocol pays the Solana transaction fee (~$0.00025) "
            "on behalf of the user, making bearer-note transfers completely free."
        ),
        "stats": stats,
        "devnet": settings.env == "devnet",
    }

# Production metrics endpoint
from metrics_service import MetricsService

_prod_metrics = MetricsService()

@app.get("/api/v1/metrics")
async def production_metrics():
    _prod_metrics.gauge("membra_users_total", len(_identity._users))
    _prod_metrics.gauge("membra_claims_active", len([c for c in _claimnotes._claims.values() if c["state"] == "created"]))
    _prod_metrics.gauge("membra_ledger_entries_total", len(_ledger._entries))
    _prod_metrics.gauge("membra_settlement_batches_total", len(_settlement._batches))
    _prod_metrics.gauge("membra_quarantine_total", len(_compliance.get_quarantine()))
    return _prod_metrics.to_dict()

@app.get("/health/services")
async def health_services():
    return {
        "services": {
            "identity": {"status": "ok", "users": len(_identity._users)},
            "claimnotes": {"status": "ok", "claims": len(_claimnotes._claims)},
            "ledger": {"status": "ok", "entries": len(_ledger._entries)},
            "treasury": {"status": "ok", "wallets": len(_treasury._wallets)},
            "settlement": {"status": "ok", "batches": len(_settlement._batches)},
            "redemption": {"status": "ok"},
            "compliance": {"status": "ok", "quarantine_count": len(_compliance.get_quarantine())},
            "security": {"status": "ok", "alert_count": len(_security.get_alerts())},
        },
        "overall": "healthy",
    }
