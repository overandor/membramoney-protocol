from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class ClaimCreateRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=44)
    denomination_sats: int = Field(..., ge=1000)
    expires_minutes: int = Field(..., ge=1, le=1440)
    risk_version: str = Field(..., pattern=r"^v\d+\.\d+\.\d+.*")
    idempotency_key: Optional[str] = Field(None, max_length=64)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]+$", v):
            raise ValueError("Invalid wallet address format")
        return v


class ClaimCreateResponse(BaseModel):
    claim_id: str
    claim_url: str
    pin_hash: str
    expires_at: str
    denomination_sats: int


class ClaimValidateRequest(BaseModel):
    claim_id: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=4, max_length=16)
    claimant_wallet: str = Field(..., min_length=32, max_length=44)


class ClaimValidateResponse(BaseModel):
    valid: bool
    claim_id: str
    message: str
    denomination_sats: Optional[int] = None
