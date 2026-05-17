import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, Integer, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
import enum


class WalletType(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class AssetType(str, enum.Enum):
    BTC = "btc"
    SOL = "sol"
    ETH = "eth"
    USDC = "usdc"
    USD = "usd"


class BatchStatus(str, enum.Enum):
    COLLECTING = "collecting"
    REVIEWING = "reviewing"
    SIGNING = "signing"
    BROADCASTING = "broadcasting"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    FAILED = "failed"


class TreasuryWallet(Base):
    __tablename__ = "treasury_wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_type = Column(Enum(WalletType), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    address = Column(String(128), nullable=False)
    public_key = Column(String(128), nullable=False)
    balance = Column(BigInteger, default=0, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ReserveAttestation(Base):
    __tablename__ = "reserve_attestations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_type = Column(Enum(AssetType), nullable=False)
    total_reserve = Column(BigInteger, nullable=False)
    total_liabilities = Column(BigInteger, nullable=False)
    reserve_ratio_bps = Column(Integer, nullable=False)
    attested_by = Column(String(64), nullable=False)
    attestation_signature = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class SettlementBatch(Base):
    __tablename__ = "settlement_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_status = Column(Enum(BatchStatus), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    total_amount = Column(BigInteger, nullable=False)
    fee_estimate = Column(BigInteger, nullable=False)
    tx_hash = Column(String(128), nullable=True)
    confirmations = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    broadcast_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
