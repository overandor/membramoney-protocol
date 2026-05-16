import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class ReserveAttestation(Base):
    __tablename__ = "reserve_attestations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    authority_wallet = Column(String(44), nullable=False)
    reserve_ratio_bps = Column(SmallInteger, nullable=False)
    attested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    attestation_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<ReserveAttestation(ratio={self.reserve_ratio_bps}bps, auth={self.authority_wallet})>"
