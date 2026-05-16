import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(64), nullable=False, index=True)
    wallet_address = Column(String(44), index=True)
    details = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(String(512))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AuditLog(type={self.event_type}, wallet={self.wallet_address})>"
