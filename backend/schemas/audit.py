from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class AuditEventCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=64)
    wallet_address: Optional[str] = Field(None, max_length=44)
    details: Optional[Dict[str, Any]] = None


class AuditEventResponse(BaseModel):
    event_id: str
    event_type: str
    wallet_address: Optional[str]
    timestamp: str
    details: Optional[Dict[str, Any]]
