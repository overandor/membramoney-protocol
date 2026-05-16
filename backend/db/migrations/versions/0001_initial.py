"""Initial migration

Revision ID: 0001
Revises:
Create Date: 2026-05-16 12:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("wallet_address", sa.String(44), unique=True, nullable=False, index=True),
        sa.Column("role", sa.Enum("admin", "issuer", "claimant", "viewer", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("claim_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("issuer_wallet", sa.String(44), nullable=False, index=True),
        sa.Column("denomination_sats", sa.BigInteger, nullable=False),
        sa.Column("pin_hash", sa.String(64), nullable=False),
        sa.Column("salt", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed", sa.Boolean, default=False),
        sa.Column("claimant_wallet", sa.String(44), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "risk_acceptances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("wallet_address", sa.String(44), nullable=False, index=True),
        sa.Column("accepted_version", sa.String(32), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ip_address", postgresql.INET),
        sa.Column("user_agent", sa.String(512)),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("wallet_address", sa.String(44), index=True),
        sa.Column("details", postgresql.JSONB),
        sa.Column("ip_address", postgresql.INET),
        sa.Column("user_agent", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_table(
        "reserve_attestations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("authority_wallet", sa.String(44), nullable=False),
        sa.Column("reserve_ratio_bps", sa.SmallInteger, nullable=False),
        sa.Column("attested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("attestation_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("reserve_attestations")
    op.drop_table("audit_logs")
    op.drop_table("risk_acceptances")
    op.drop_table("claims")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
