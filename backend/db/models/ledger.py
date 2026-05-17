import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, Integer, ForeignKey, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
import enum


class AccountType(str, enum.Enum):
    USER = "user"
    RESERVE = "reserve"
    SETTLEMENT = "settlement"
    FEE = "fee"
    LIQUIDITY = "liquidity"


class AssetType(str, enum.Enum):
    BTC = "btc"
    SOL = "sol"
    ETH = "eth"
    USDC = "usdc"
    USD = "usd"


class EntryType(str, enum.Enum):
    CLAIM_CREATE = "claim_create"
    CLAIM_TRANSFER = "claim_transfer"
    CLAIM_REDEEM = "claim_redeem"
    CLAIM_EXPIRE = "claim_expire"
    CLAIM_SPLIT = "claim_split"
    CLAIM_MERGE = "claim_merge"
    SETTLEMENT_OUT = "settlement_out"
    SETTLEMENT_IN = "settlement_in"
    FEE_COLLECT = "fee_collect"
    RESERVE_DEPOSIT = "reserve_deposit"
    RESERVE_WITHDRAW = "reserve_withdraw"


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(Enum(AccountType), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    balance = Column(BigInteger, default=0, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_type = Column(Enum(EntryType), nullable=False)
    debit_account_id = Column(UUID(as_uuid=True), ForeignKey("ledger_accounts.id"), nullable=False)
    credit_account_id = Column(UUID(as_uuid=True), ForeignKey("ledger_accounts.id"), nullable=False)
    amount = Column(BigInteger, nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    claim_id = Column(UUID(as_uuid=True), nullable=True)
    settlement_tx_hash = Column(String(128), nullable=True)
    metadata = Column(JSON, default=dict)
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    sequence_number = Column(BigInteger, nullable=False, index=True)
