-- Membra Money Protocol — Initial Database Schema
-- For PostgreSQL 15+
-- Run: psql -U membra -d membramoney -f 001_initial_schema.sql

-- ------------------------------------------------------------------
-- Extensions
-- ------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------
-- Risk Disclosures
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_disclosures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version VARCHAR(32) NOT NULL UNIQUE,
    text TEXT NOT NULL,
    hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------
-- Risk Acceptances
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_acceptances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_address VARCHAR(44) NOT NULL,
    accepted_version VARCHAR(32) NOT NULL,
    accepted_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    UNIQUE(wallet_address, accepted_version)
);

CREATE INDEX IF NOT EXISTS idx_risk_acceptances_wallet ON risk_acceptances(wallet_address);

-- ------------------------------------------------------------------
-- Claims
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    claim_id VARCHAR(64) NOT NULL UNIQUE,
    issuer_wallet VARCHAR(44) NOT NULL,
    denomination_sats BIGINT NOT NULL CHECK (denomination_sats >= 1),
    pin_hash VARCHAR(64) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    claimed BOOLEAN DEFAULT FALSE,
    claimant_wallet VARCHAR(44),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    claimed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_claims_issuer ON claims(issuer_wallet);
CREATE INDEX IF NOT EXISTS idx_claims_claimant ON claims(claimant_wallet);
CREATE INDEX IF NOT EXISTS idx_claims_expires ON claims(expires_at);

-- ------------------------------------------------------------------
-- Audit Events
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(64) NOT NULL,
    wallet_address VARCHAR(44),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_wallet ON audit_events(wallet_address);
CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at);

-- ------------------------------------------------------------------
-- Idempotency Keys
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idempotency_keys (
    key VARCHAR(64) PRIMARY KEY,
    response JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires ON idempotency_keys(expires_at);

-- ------------------------------------------------------------------
-- Reserve Attestations
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reserve_attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    authority_wallet VARCHAR(44) NOT NULL,
    reserve_ratio_bps SMALLINT NOT NULL CHECK (reserve_ratio_bps <= 10000),
    attested_at TIMESTAMPTZ DEFAULT NOW(),
    attestation_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------------
-- Update timestamps trigger
-- ------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_risk_disclosures_updated_at ON risk_disclosures;
CREATE TRIGGER update_risk_disclosures_updated_at
    BEFORE UPDATE ON risk_disclosures
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
