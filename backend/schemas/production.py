from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class IdentityRegisterResponse(BaseModel):
    user_id: str
    username: str
    wallet_address: str
    receive_tag: str
    is_active: bool = True
    created_at: str

class IdentityResolveResponse(BaseModel):
    username: str
    tag: str

class ClaimCreateResponse(BaseModel):
    claim_id: str
    issuer_id: str
    asset_type: str
    denomination: int
    state: str = "created"
    created_at: float

class LedgerBalanceResponse(BaseModel):
    account_id: str
    balance: int

class TreasuryReserveResponse(BaseModel):
    btc: int
    sol: int
    eth: int
    usdc: int
