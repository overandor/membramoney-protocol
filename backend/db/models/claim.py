import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(String(64), unique=True, nullable=False, index=True)
    issuer_wallet = Column(String(44), nullable=False, index=True)
    denomination_sats = Column(BigInteger, nullable=False)
    pin_hash = Column(String(64), nullable=False)
    salt = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    claimed = Column(Boolean, default=False)
    claimant_wallet = Column(String(44), index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    claimed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Claim(id={self.claim_id}, issuer={self.issuer_wallet})>"
