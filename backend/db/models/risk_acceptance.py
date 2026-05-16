import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, INET
from .base import Base


class RiskAcceptance(Base):
    __tablename__ = "risk_acceptances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_address = Column(String(44), nullable=False, index=True)
    accepted_version = Column(String(32), nullable=False)
    accepted_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    ip_address = Column(INET)
    user_agent = Column(String(512))

    def __repr__(self):
        return f"<RiskAcceptance(wallet={self.wallet_address}, version={self.accepted_version})>"
