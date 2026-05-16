"""
Membra Money Protocol — FastAPI Backend
"""

import hashlib
import hmac
import json
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
from services.claim_service import ClaimService
from services.reserve_service import ReserveService
from services.risk_disclosure import RiskDisclosureService

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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

_claims: Dict[str, Dict[str, Any]] = {}
_risk_acceptances: Dict[str, Dict[str, Any]] = {}
_brute_force_tracker: Dict[str, List[float]] = {}
_audit_events: List[AuditEvent] = []

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

def _record_brute_force(key: str):
    now = time.time()
    attempts = _brute_force_tracker.get(key, [])
    attempts.append(now)
    _brute_force_tracker[key] = attempts

def _add_audit(event_type: str, details: Dict[str, Any]):
    event = AuditEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details=details,
    )
    _audit_events.append(event)

# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        env=settings.env,
        devnet=settings.env == "devnet",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@app.get("/ready", response_model=HealthResponse)
async def ready():
    return HealthResponse(
        status="ready",
        env=settings.env,
        devnet=settings.env == "devnet",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

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
    _risk_acceptances[req.wallet_address] = {
        "wallet_address": req.wallet_address,
        "accepted_version": req.accepted_version,
        "accepted_at": accepted_at,
    }
    _add_audit("risk_disclosure_accepted", {"wallet": req.wallet_address, "version": req.accepted_version})

    return RiskAcceptResponse(
        accepted=True,
        wallet_address=req.wallet_address,
        accepted_at=accepted_at,
        version=req.accepted_version,
    )

@app.post("/api/v1/claims/create", response_model=ClaimCreateResponse)
async def create_claim(req: ClaimCreateRequest):
    if not _risk_acceptances.get(req.wallet_address):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Risk disclosure not accepted for this wallet.",
        )

    claim_id = str(uuid.uuid4())
    raw_pin = str(uuid.uuid4())[:8].upper()
    salt = str(uuid.uuid4())
    pin_hash = _hash_pin(raw_pin, salt)
    expires_at = datetime.now(timezone.utc).timestamp() + (req.expires_minutes * 60)

    _claims[claim_id] = {
        "claim_id": claim_id,
        "issuer_wallet": req.wallet_address,
        "denomination_sats": req.denomination_sats,
        "pin_hash": pin_hash,
        "salt": salt,
        "expires_at": expires_at,
        "claimed": False,
        "claimant_wallet": None,
        "created_at": datetime.now(timezone.utc).timestamp(),
    }

    _add_audit("claim_created", {
        "claim_id": claim_id,
        "issuer": req.wallet_address,
        "denomination_sats": req.denomination_sats,
    })

    claim_url = f"{settings.backend_url}/claim/{claim_id}"

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
    claim = _claims.get(req.claim_id)
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    if claim["claimed"]:
        return ClaimValidateResponse(
            valid=False,
            claim_id=req.claim_id,
            message="Claim already consumed.",
        )

    now = datetime.now(timezone.utc).timestamp()
    if now > claim["expires_at"]:
        return ClaimValidateResponse(
            valid=False,
            claim_id=req.claim_id,
            message="Claim expired.",
        )

    bf_key = f"{req.claim_id}:{req.claimant_wallet}"
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

    claim["claimed"] = True
    claim["claimant_wallet"] = req.claimant_wallet

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
    total = len(_claims)
    redeemed = sum(1 for c in _claims.values() if c["claimed"])
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
    events = _audit_events[-limit:]
    return AuditEventsResponse(
        events=events,
        count=len(events),
    )

# ------------------------------------------------------------------
# Exception Handlers
# ------------------------------------------------------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error.",
            "devnet_warning": "EXPERIMENTAL DEVNET ONLY",
        },
    )
