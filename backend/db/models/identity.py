import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base


class IdentityUser(Base):
    __tablename__ = "identity_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(32), unique=True, nullable=False, index=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    wallet_address = Column(String(44), unique=True, nullable=False, index=True)
    receive_tag = Column(String(16), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    transfer_limit_daily = Column(BigInteger, default=10_000_000)
    risk_level = Column(String(8), default="low")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    devices = relationship("DeviceSession", back_populates="user")


class DeviceSession(Base):
    __tablename__ = "device_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("identity_users.id"), nullable=False)
    device_fingerprint = Column(String(64), nullable=False)
    user_agent_hash = Column(String(64), nullable=False)
    ip_address_hash = Column(String(64), nullable=False)
    last_active_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)

    user = relationship("IdentityUser", back_populates="devices")
