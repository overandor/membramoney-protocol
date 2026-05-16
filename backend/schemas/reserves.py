from pydantic import BaseModel, Field


class ReserveAttestationRequest(BaseModel):
    reserve_ratio_bps: int = Field(..., ge=0, le=10_000)
    authority_wallet: str = Field(..., min_length=32, max_length=44)
    attestation_hash: str = Field(..., min_length=64, max_length=64)


class ReserveResponse(BaseModel):
    reserve_ratio_bps: int
    latest_attestation: str
    disclaimer: str
    devnet_only: bool
