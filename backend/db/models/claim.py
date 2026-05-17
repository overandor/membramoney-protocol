import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, BigInteger, ForeignKey, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
import enum


class ClaimState(str, enum.Enum):
    CREATED = "created"
    TRANSFERRED = "transferred"
    REDEEMED = "redeemed"
    EXPIRED = "expired"
    BURNED = "burned"
    REVOKED = "revoked"


class ComplianceState(str, enum.Enum):
    PENDING = "pending"
    CLEARED = "cleared"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"


class AssetType(str, enum.Enum):
    BTC = "btc"
    SOL = "sol"
    ETH = "eth"
    USDC = "usdc"
    USD = "usd"


class RedemptionPolicy(str, enum.Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    BATCHED = "batched"


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(String(64), unique=True, nullable=False, index=True)
    issuer_wallet = Column(String(44), nullable=False, index=True)
    denomination_sats = Column(BigInteger, nullable=False)
    pin_hash = Column(String(64), nullable=True)
    salt = Column(String(64), nullable=True)
    nullifier = Column(String(64), unique=True, nullable=False, index=True)
    replay_nonce = Column(BigInteger, default=0, nullable=False)
    state = Column(Enum(ClaimState), default=ClaimState.CREATED, nullable=False)
    compliance_state = Column(Enum(ComplianceState), default=ComplianceState.PENDING, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    redemption_policy = Column(Enum(RedemptionPolicy), default=RedemptionPolicy.IMMEDIATE, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    claimed = Column(Boolean, default=False)
    claimant_wallet = Column(String(44), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    claimed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Claim(id={self.claim_id}, issuer={self.issuer_wallet}, state={self.state})>"
