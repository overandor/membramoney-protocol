import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Enum, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
import enum


class ScreeningType(str, enum.Enum):
    ONBOARDING = "onboarding"
    TRANSACTION = "transaction"
    PERIODIC = "periodic"


class ScreeningResult(str, enum.Enum):
    CLEAR = "clear"
    HIT = "hit"
    REVIEW = "review"


class Resolution(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class SanctionsScreening(Base):
    __tablename__ = "sanctions_screenings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    screening_type = Column(Enum(ScreeningType), nullable=False)
    provider = Column(String(32), default="internal")
    result = Column(Enum(ScreeningResult), nullable=False)
    hit_details = Column(JSON, nullable=True)
    screened_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AmlRiskScore(Base):
    __tablename__ = "aml_risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    factors = Column(JSON, default=dict)
    calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class FraudQuarantine(Base):
    __tablename__ = "fraud_quarantine"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), nullable=False)
    quarantine_reason = Column(String(256), nullable=False)
    risk_score = Column(Integer, nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution = Column(Enum(Resolution), default=Resolution.PENDING)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
