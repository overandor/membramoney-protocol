"""
Membra Money Protocol — FastAPI Backend

Devnet-first micropayment claim-link API. This service deliberately avoids
private-key delivery and real custody claims. Claim URLs carry one-time claim
secrets only; escrow funding and redemption must be reconciled with on-chain
state before any production release.
"""

import hashlib
import hmac
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.config import settings
from services.reserve_service import ReserveService
from services.risk_disclosure import RiskDisclosureService

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEVNET_WARNING = "EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY"
CUSTODY_DISCLAIMER = (
    "No private keys are sent, stored, sliced, or delivered. This API only creates "
    "one-time claim secrets and pending escrow records."
)
SUPPORTED_ASSETS = {"SOLANA_DEVNET_USDC", "SOLANA_DEVNET_SOL", "BTC_LIGHTNING"}
MICROPAYMENT_STATUSES = {
    "created",
    "awaiting_funding",
    "funding_submitted",
    "funding_unverified",
    "funded",
    "redeem_pending",
    "redeemed",
    "expired",
    "refunded",
}

# ------------------------------------------------------------------
# Safety Guards
# ------------------------------------------------------------------


def _unsafe(value: str) -> bool:
    return value.strip() in {"", "change-me", "change-me-256-bit-random-string-here", "change-me-256-bit-pepper-here", "change-me-claim-salt-here"}


def _production_safety_check() -> None:
    """Fail closed when production is requested with demo/devnet settings."""
    if settings.env.lower() != "production":
        return

    failures: list[str] = []
    if settings.debug:
        failures.append("DEBUG must be false")
    if "*" in settings.cors_origin_list:
        failures.append("CORS wildcard is forbidden")
    if _unsafe(settings.jwt_secret):
        failures.append("JWT_SECRET must be rotated")
    if _unsafe(settings.hmac_pepper):
        failures.append("HMAC_PEPPER must be rotated")
    if _unsafe(settings.claim_salt):
        failures.append("CLAIM_SALT must be rotated")
    if _unsafe(settings.admin_api_key):
        failures.append("ADMIN_API_KEY must be set")
    if settings.anchor_program_id == "11111111111111111111111111111111":
        failures.append("ANCHOR_PROGRAM_ID must not be the dummy program ID")
    if "localhost" in settings.database_url or "membra:membra" in settings.database_url:
        failures.append("DATABASE_URL must not use local/default credentials")
    if not settings.production_wallet_signature_required:
        failures.append("wallet signature verification must be required")

    if failures:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(failures))


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    _production_safety_check()
    yield


app = FastAPI(
    title="Membra Money Protocol API",
    version="0.2.0-devnet",
    description="EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.cors_origin_list,
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


class MicropaymentCreateRequest(BaseModel):
    sender_wallet: str = Field(..., min_length=32, max_length=44)
    usd_cents: int = Field(..., ge=1)
    asset: Literal["SOLANA_DEVNET_USDC", "SOLANA_DEVNET_SOL", "BTC_LIGHTNING"] = "SOLANA_DEVNET_USDC"
    delivery_channel: Literal["link", "qr", "email", "sms", "physical"] = "link"
    recipient_hint: Optional[str] = Field(default=None, max_length=160)
    expires_minutes: int = Field(default=60, ge=1, le=129600)
    risk_version: str
    sender_signature: Optional[str] = None
    escrow_tx_signature: Optional[str] = None


class MicropaymentCreateResponse(BaseModel):
    payment_id: str
    claim_id: str
    claim_url: str
    qr_payload: str
    asset: str
    usd_cents: int
    status: str
    funding_status: str
    delivery_channel: str
    expires_at: str
    backend_degraded: bool
    devnet_warning: str
    custody_disclaimer: str


class MicropaymentResponse(BaseModel):
    payment_id: str
    claim_id: str
    sender_wallet: str
    recipient_hint: Optional[str]
    usd_cents: int
    asset: str
    status: str
    funding_status: str
    delivery_channel: str
    expires_at: str
    devnet_warning: str
    custody_disclaimer: str


class ClaimPreviewResponse(BaseModel):
    claim_id: str
    payment_id: Optional[str]
    usd_cents: Optional[int]
    asset: Optional[str]
    status: str
    expired: bool
    message: str
    devnet_warning: str


class ClaimRedeemRequest(BaseModel):
    secret: str = Field(..., min_length=32, max_length=160)
    claimant_wallet: str = Field(..., min_length=32, max_length=44)
    claimant_signature: Optional[str] = None


class ClaimRedeemResponse(BaseModel):
    redeemed: bool
    claim_id: str
    payment_id: Optional[str]
    status: str
    message: str
    devnet_warning: str


class DeliveryRequest(BaseModel):
    channel: Literal["link", "qr", "email", "sms", "physical"]
    destination: Optional[str] = Field(default=None, max_length=160)


class DeliveryResponse(BaseModel):
    claim_id: str
    channel: str
    sent: bool
    degraded: bool
    message: str
    devnet_warning: str


class RailsResponse(BaseModel):
    primary: str
    minimum_usd_cents: int
    rails: Dict[str, Dict[str, Any]]
    custody_disclaimer: str


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
    total_micropayments: int
    active_micropayments: int
    reserve_ratio_bps: int
    devnet: bool
    generated_at: str


class ReserveAttestationRequest(BaseModel):
    reserve_ratio_bps: int = Field(..., ge=0, le=100_000)
    statement: str = Field(..., min_length=8, max_length=500)


class AdminActionResponse(BaseModel):
    ok: bool
    message: str
    devnet_warning: str


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
_micropayments: Dict[str, Dict[str, Any]] = {}
_claim_index: Dict[str, str] = {}
_reserve_attestations: list[Dict[str, Any]] = []

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

MAX_BRUTE_FORCE_ATTEMPTS = 5
BRUTE_FORCE_WINDOW_SECONDS = 3600


def _hash_pin(pin: str, salt: str) -> str:
    pepper = settings.hmac_pepper
    return hashlib.sha256(f"{pin}:{salt}:{pepper}".encode()).hexdigest()


def _claim_secret_hash(secret: str) -> str:
    return hmac.new(settings.claim_salt.encode(), secret.encode(), hashlib.sha256).hexdigest()


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


def _ensure_risk_accepted(wallet: str) -> None:
    if not _risk_acceptances.get(wallet):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Risk disclosure not accepted for this wallet.",
        )


def _assert_current_risk_version(risk_version: str) -> None:
    if risk_version != settings.risk_disclosure_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Risk disclosure version mismatch. Expected {settings.risk_disclosure_version}, got {risk_version}",
        )


def _assert_asset_available(asset: str) -> None:
    if asset not in SUPPORTED_ASSETS:
        raise HTTPException(status_code=400, detail="Unsupported asset.")
    if asset == "BTC_LIGHTNING" and not settings.btc_lightning_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BTC Lightning rail is not configured. BTC L1 micropayments are disabled.",
        )


def _expires_at_iso(expires_at: float) -> str:
    return datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()


def _get_micropayment_by_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    payment_id = _claim_index.get(claim_id)
    if not payment_id:
        return None
    return _micropayments.get(payment_id)


def _require_admin(admin_api_key: Optional[str]) -> None:
    if _unsafe(settings.admin_api_key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured.",
        )
    if not admin_api_key or not hmac.compare_digest(admin_api_key, settings.admin_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required.")


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


@app.get("/api/v1/rails", response_model=RailsResponse)
async def get_payment_rails():
    return RailsResponse(
        primary="SOLANA_DEVNET_USDC",
        minimum_usd_cents=settings.min_micropayment_usd_cents,
        rails={
            "SOLANA_DEVNET_USDC": {
                "available": True,
                "network": "solana-devnet",
                "custody": "escrow-required",
                "minimum_usd_cents": settings.min_micropayment_usd_cents,
            },
            "SOLANA_DEVNET_SOL": {
                "available": True,
                "network": "solana-devnet",
                "custody": "escrow-required",
                "minimum_usd_cents": settings.min_micropayment_usd_cents,
            },
            "BTC_LIGHTNING": {
                "available": settings.btc_lightning_enabled,
                "network": "lightning-testnet-or-signet",
                "custody": "not-configured" if not settings.btc_lightning_enabled else "invoice-settlement-required",
                "minimum_usd_cents": settings.min_micropayment_usd_cents,
            },
            "BTC_L1": {
                "available": False,
                "reason": "BTC L1 is disabled for $0.01 micropayments.",
            },
        },
        custody_disclaimer=CUSTODY_DISCLAIMER,
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
    _assert_current_risk_version(req.accepted_version)

    accepted_at = datetime.now(timezone.utc).isoformat()
    _risk_acceptances[req.wallet_address] = {
        "wallet_address": req.wallet_address,
        "accepted_version": req.accepted_version,
        "accepted_at": accepted_at,
        "signature_present": bool(req.signature),
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
    """Legacy devnet claim route retained for compatibility with existing tests/UI."""
    _ensure_risk_accepted(req.wallet_address)

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

    _add_audit("legacy_claim_created", {
        "claim_id": claim_id,
        "issuer": req.wallet_address,
        "denomination_sats": req.denomination_sats,
    })

    claim_url = f"{settings.backend_url}/claim/{claim_id}"

    return ClaimCreateResponse(
        claim_id=claim_id,
        claim_url=claim_url,
        pin_hash=pin_hash,
        expires_at=_expires_at_iso(expires_at),
        denomination_sats=req.denomination_sats,
        devnet_warning=DEVNET_WARNING,
    )


@app.post("/api/v1/micropayments", response_model=MicropaymentCreateResponse)
async def create_micropayment(req: MicropaymentCreateRequest):
    _assert_current_risk_version(req.risk_version)
    _ensure_risk_accepted(req.sender_wallet)
    _assert_asset_available(req.asset)

    if req.usd_cents < settings.min_micropayment_usd_cents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Minimum micropayment is ${settings.min_micropayment_usd_cents / 100:.2f}.",
        )
    if req.usd_cents > settings.max_micropayment_usd_cents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Micropayment exceeds configured devnet maximum.",
        )
    if settings.env == "production" and settings.production_wallet_signature_required and not req.sender_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sender wallet signature required.")

    payment_id = str(uuid.uuid4())
    claim_id = str(uuid.uuid4())
    claim_secret = f"mm_{uuid.uuid4().hex}{uuid.uuid4().hex}"
    secret_hash = _claim_secret_hash(claim_secret)
    expires_at = datetime.now(timezone.utc).timestamp() + (req.expires_minutes * 60)
    funding_status = "submitted_unverified" if req.escrow_tx_signature else "awaiting_escrow_funding"
    payment_status = "funding_submitted" if req.escrow_tx_signature else "awaiting_funding"
    claim_url = f"{settings.frontend_url}/claim/{claim_id}?secret={claim_secret}"

    record = {
        "payment_id": payment_id,
        "claim_id": claim_id,
        "secret_hash": secret_hash,
        "sender_wallet": req.sender_wallet,
        "recipient_hint": req.recipient_hint,
        "usd_cents": req.usd_cents,
        "asset": req.asset,
        "status": payment_status,
        "funding_status": funding_status,
        "delivery_channel": req.delivery_channel,
        "escrow_tx_signature": req.escrow_tx_signature,
        "claimant_wallet": None,
        "expires_at": expires_at,
        "created_at": datetime.now(timezone.utc).timestamp(),
        "redeemed_at": None,
    }
    _micropayments[payment_id] = record
    _claim_index[claim_id] = payment_id

    _add_audit("micropayment_created", {
        "payment_id": payment_id,
        "claim_id": claim_id,
        "sender": req.sender_wallet,
        "asset": req.asset,
        "usd_cents": req.usd_cents,
        "funding_status": funding_status,
        "delivery_channel": req.delivery_channel,
    })

    return MicropaymentCreateResponse(
        payment_id=payment_id,
        claim_id=claim_id,
        claim_url=claim_url,
        qr_payload=claim_url,
        asset=req.asset,
        usd_cents=req.usd_cents,
        status=payment_status,
        funding_status=funding_status,
        delivery_channel=req.delivery_channel,
        expires_at=_expires_at_iso(expires_at),
        backend_degraded=req.delivery_channel in {"email", "sms"},
        devnet_warning=DEVNET_WARNING,
        custody_disclaimer=CUSTODY_DISCLAIMER,
    )


@app.get("/api/v1/micropayments/{payment_id}", response_model=MicropaymentResponse)
async def get_micropayment(payment_id: str):
    record = _micropayments.get(payment_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Micropayment not found.")
    return MicropaymentResponse(
        payment_id=record["payment_id"],
        claim_id=record["claim_id"],
        sender_wallet=record["sender_wallet"],
        recipient_hint=record["recipient_hint"],
        usd_cents=record["usd_cents"],
        asset=record["asset"],
        status=record["status"],
        funding_status=record["funding_status"],
        delivery_channel=record["delivery_channel"],
        expires_at=_expires_at_iso(record["expires_at"]),
        devnet_warning=DEVNET_WARNING,
        custody_disclaimer=CUSTODY_DISCLAIMER,
    )


@app.get("/api/v1/claims/{claim_id}", response_model=ClaimPreviewResponse)
async def preview_claim(claim_id: str):
    record = _get_micropayment_by_claim(claim_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    now = datetime.now(timezone.utc).timestamp()
    expired = now > record["expires_at"]
    if expired and record["status"] not in {"redeemed", "refunded"}:
        record["status"] = "expired"
    return ClaimPreviewResponse(
        claim_id=claim_id,
        payment_id=record["payment_id"],
        usd_cents=record["usd_cents"],
        asset=record["asset"],
        status=record["status"],
        expired=expired,
        message="Claim preview only. Connect wallet and provide the one-time secret to redeem.",
        devnet_warning=DEVNET_WARNING,
    )


@app.post("/api/v1/claims/{claim_id}/redeem", response_model=ClaimRedeemResponse)
async def redeem_claim(claim_id: str, req: ClaimRedeemRequest):
    record = _get_micropayment_by_claim(claim_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    if datetime.now(timezone.utc).timestamp() > record["expires_at"]:
        record["status"] = "expired"
        return ClaimRedeemResponse(
            redeemed=False,
            claim_id=claim_id,
            payment_id=record["payment_id"],
            status="expired",
            message="Claim expired. Sender refund path should be used after escrow reconciliation.",
            devnet_warning=DEVNET_WARNING,
        )
    bf_key = f"micropayment:{claim_id}:{req.claimant_wallet}"
    if _check_brute_force(bf_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many claim attempts.")
    if not hmac.compare_digest(_claim_secret_hash(req.secret), record["secret_hash"]):
        _record_brute_force(bf_key)
        return ClaimRedeemResponse(
            redeemed=False,
            claim_id=claim_id,
            payment_id=record["payment_id"],
            status=record["status"],
            message="Invalid claim secret.",
            devnet_warning=DEVNET_WARNING,
        )
    if record["status"] != "funded":
        _add_audit("micropayment_redeem_blocked_unfunded", {
            "payment_id": record["payment_id"],
            "claim_id": claim_id,
            "claimant_wallet": req.claimant_wallet,
            "status": record["status"],
        })
        return ClaimRedeemResponse(
            redeemed=False,
            claim_id=claim_id,
            payment_id=record["payment_id"],
            status=record["status"],
            message="Escrow funding is not confirmed. Redemption is intentionally blocked instead of pretending success.",
            devnet_warning=DEVNET_WARNING,
        )

    record["status"] = "redeemed"
    record["claimant_wallet"] = req.claimant_wallet
    record["redeemed_at"] = datetime.now(timezone.utc).timestamp()
    _add_audit("micropayment_redeemed", {"payment_id": record["payment_id"], "claim_id": claim_id})
    return ClaimRedeemResponse(
        redeemed=True,
        claim_id=claim_id,
        payment_id=record["payment_id"],
        status="redeemed",
        message="Claim redeemed after confirmed escrow funding.",
        devnet_warning=DEVNET_WARNING,
    )


@app.post("/api/v1/claims/{claim_id}/delivery", response_model=DeliveryResponse)
async def deliver_claim(claim_id: str, req: DeliveryRequest):
    record = _get_micropayment_by_claim(claim_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    if req.channel == "email" and not settings.email_provider_enabled:
        message = "Email provider is not configured; return the claim link/QR to the sender instead."
        sent = False
        degraded = True
    elif req.channel == "sms" and not settings.sms_provider_enabled:
        message = "SMS provider is not configured; return the claim link/QR to the sender instead."
        sent = False
        degraded = True
    else:
        message = "Claim payload is available for sender-controlled delivery."
        sent = req.channel in {"link", "qr", "physical"}
        degraded = False

    _add_audit("micropayment_delivery_requested", {
        "claim_id": claim_id,
        "payment_id": record["payment_id"],
        "channel": req.channel,
        "sent": sent,
        "degraded": degraded,
    })
    return DeliveryResponse(
        claim_id=claim_id,
        channel=req.channel,
        sent=sent,
        degraded=degraded,
        message=message,
        devnet_warning=DEVNET_WARNING,
    )


@app.get("/api/v1/claims/{claim_id}/audit", response_model=AuditEventsResponse)
async def get_claim_audit(claim_id: str):
    events = [event for event in _audit_events if event.details.get("claim_id") == claim_id]
    return AuditEventsResponse(events=events, count=len(events))


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

    _add_audit("legacy_claim_validated", {
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
    latest = _reserve_attestations[-1] if _reserve_attestations else None
    return ReserveResponse(
        status=svc.status(),
        reserve_ratio_bps=latest["reserve_ratio_bps"] if latest else svc.reserve_ratio_bps(),
        attested_at=latest["attested_at"] if latest else svc.attested_at(),
        disclaimer="Reserve data is illustrative only. No real BTC custody exists.",
        devnet_only=True,
    )


@app.post("/api/v1/admin/reserves/attest", response_model=AdminActionResponse)
async def admin_reserve_attest(req: ReserveAttestationRequest, x_admin_api_key: Optional[str] = Header(default=None)):
    _require_admin(x_admin_api_key)
    attestation = {
        "reserve_ratio_bps": req.reserve_ratio_bps,
        "statement": req.statement,
        "attested_at": datetime.now(timezone.utc).isoformat(),
    }
    _reserve_attestations.append(attestation)
    _add_audit("admin_reserve_attestation", attestation)
    return AdminActionResponse(ok=True, message="Reserve attestation recorded.", devnet_warning=DEVNET_WARNING)


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    total = len(_claims)
    redeemed = sum(1 for c in _claims.values() if c["claimed"])
    active = total - redeemed
    active_micropayments = sum(1 for p in _micropayments.values() if p["status"] not in {"redeemed", "refunded", "expired"})
    svc = ReserveService()
    return StatsResponse(
        total_notes=total,
        redeemed_notes=redeemed,
        active_claims=active,
        total_micropayments=len(_micropayments),
        active_micropayments=active_micropayments,
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
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error.",
            "devnet_warning": "EXPERIMENTAL DEVNET ONLY",
        },
    )
