"""
SQLAlchemy models for MEMBRA FileLife Collateral Registry.
"""
import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./filelife.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), unique=True, index=True, nullable=False)
    sku_hash = Column(String(128), nullable=False)
    raw_file_hash = Column(String(128), nullable=False)
    base64_hash = Column(String(128), nullable=False)
    manifest_hash = Column(String(128), nullable=False)
    category = Column(String(32), default="FIN")
    subcategory = Column(String(32), default="ACC")
    kind = Column(String(32), default="INV")
    lifecycle_stage = Column(Integer, default=1)
    version = Column(Integer, default=1)
    jurisdiction = Column(String(16), default="US")
    subject_pid = Column(String(128), nullable=True)
    content_exposed = Column(Boolean, default=False)
    identity_exposed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class LifecycleEvent(Base):
    __tablename__ = "lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    stage = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    event_hash = Column(String(128), nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utcnow)


class AppraisalRecord(Base):
    __tablename__ = "appraisals"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    version = Column(Integer, default=1)
    appraisal_value_usd = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    rationale = Column(Text, default="")
    llm_model = Column(String(64), default="")
    created_at = Column(DateTime, default=utcnow)


class CollateralRecord(Base):
    __tablename__ = "collateral_records"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    eligible = Column(Boolean, default=False)
    collateral_class = Column(String(64), default="")
    face_value_usd = Column(Float, default=0.0)
    appraised_value_usd = Column(Float, default=0.0)
    advance_rate_percent = Column(Float, default=0.0)
    lendable_value_usd = Column(Float, default=0.0)
    haircut_percent = Column(Float, default=0.0)
    liquidity_score = Column(Integer, default=0)
    default_risk_score = Column(Integer, default=0)
    fraud_risk_score = Column(Integer, default=0)
    verification_score = Column(Float, default=0.0)
    audit_score = Column(Float, default=0.0)
    payment_probability = Column(Integer, default=0)
    days_to_maturity = Column(Integer, default=0)
    lien_status = Column(String(32), default="none")
    collateral_cert_id = Column(String(128), nullable=True)
    loan_id_hash = Column(String(128), nullable=True)
    chain_anchor_tx = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class LienRecord(Base):
    __tablename__ = "liens"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    lien_holder_pid = Column(String(128), nullable=False)
    lien_status = Column(String(32), default="pledged")
    collateral_cert_id = Column(String(128), nullable=True)
    loan_id_hash = Column(String(128), nullable=True)
    chain_tx = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    released_at = Column(DateTime, nullable=True)


class VerificationRecord(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    version = Column(Integer, default=1)
    raw_file_hash = Column(String(128), nullable=False)
    base64_hash = Column(String(128), nullable=False)
    manifest_hash = Column(String(128), nullable=False)
    sku_hash = Column(String(128), nullable=False)
    verified = Column(Boolean, default=False)
    failures_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=utcnow)


class GitHubCommit(Base):
    __tablename__ = "github_commits"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    repo_alias = Column(String(64), default="")
    repo = Column(String(256), default="")
    branch = Column(String(64), default="main")
    commit_sha = Column(String(64), default="")
    commit_short = Column(String(16), default="")
    commit_url = Column(String(512), default="")
    created_at = Column(DateTime, default=utcnow)


class ChainAnchor(Base):
    __tablename__ = "chain_anchors"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    network_code = Column(String(16), default="SDV")
    network = Column(String(64), default="solana-devnet")
    anchor_tx = Column(String(256), default="")
    anchor_tx_short = Column(String(16), default="")
    explorer_url = Column(String(512), default="")
    payload_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utcnow)


class LLMQuery(Base):
    __tablename__ = "llm_queries"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(512), index=True, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, default="")
    sources_json = Column(Text, default="[]")
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)


class PIDRecord(Base):
    __tablename__ = "pids"

    id = Column(Integer, primary_key=True, index=True)
    pid = Column(String(128), unique=True, index=True, nullable=False)
    namespace = Column(String(32), default="MBR")
    role = Column(String(32), default="OWNER")
    region = Column(String(16), default="US")
    year = Column(Integer, nullable=True)
    hash_frag = Column(String(16), nullable=False)
    created_at = Column(DateTime, default=utcnow)


# Create all tables
Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
