from pydantic import BaseModel, Field
from typing import Optional


class RiskAcceptanceRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=44)
    accepted_version: str = Field(..., pattern=r"^v\d+\.\d+\.\d+.*")


class RiskAcceptanceResponse(BaseModel):
    accepted: bool
    wallet_address: str
    version: str
    accepted_at: Optional[str] = None
    message: str
