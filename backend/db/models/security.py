import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    reasons = Column(JSON, default=list)
    amount = Column(Integer, nullable=True)
    geo_hash = Column(String(64), nullable=True)
    device_fingerprint = Column(String(64), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
