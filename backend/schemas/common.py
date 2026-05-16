from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class HealthResponse(BaseModel):
    status: str
    env: str
    devnet: bool
    timestamp: str
    version: str
    stores: Dict[str, int]
    memory_mb: Optional[float]
    python_version: str


class StatsResponse(BaseModel):
    total_claims_created: int
    total_claims_claimed: int
    total_claims_expired: int
    total_denomination_issued_sats: int
    total_denomination_claimed_sats: int
    total_risk_acceptances: int
    total_audit_events: int
    total_reserve_attestations: int
    reserve_ratio_bps: Optional[int]
    timestamp: str


class ErrorResponse(BaseModel):
    detail: str
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
