"""
Database adapter — uses PostgreSQL via SQLAlchemy when DATABASE_URL is set,
falls back to in-memory stores for dev/demo.
"""

import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# Try SQLAlchemy; if not available, use in-memory fallback
try:
    from sqlalchemy.orm import Session
    from db.connection import db_manager
    from db.repositories import (
        UserRepository, ClaimRepository,
        RiskAcceptanceRepository, AuditLogRepository,
    )
    from db.models.user import UserRole
    _HAS_DB = True
except Exception:
    _HAS_DB = False


class InMemoryStore:
    """Drop-in replacement for DB repositories using in-memory dicts."""

    def __init__(self):
        self._claims: Dict[str, Dict[str, Any]] = {}
        self._risk_acceptances: Dict[str, Dict[str, Any]] = {}
        self._audit_events: List[Dict[str, Any]] = []
        self._idempotency_keys: Dict[str, Any] = {}
        self._users: Dict[str, Dict[str, Any]] = {}

    # Claims
    def create_claim(self, claim_id: str, issuer_wallet: str, denomination_sats: int,
                     pin_hash: str, salt: str, expires_at) -> Dict[str, Any]:
        self._claims[claim_id] = {
            "claim_id": claim_id,
            "issuer_wallet": issuer_wallet,
            "denomination_sats": denomination_sats,
            "pin_hash": pin_hash,
            "salt": salt,
            "expires_at": expires_at,
            "claimed": False,
            "claimant_wallet": None,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        return self._claims[claim_id]

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        return self._claims.get(claim_id)

    def mark_claim_claimed(self, claim_id: str, claimant_wallet: str):
        c = self._claims.get(claim_id)
        if c:
            c["claimed"] = True
            c["claimant_wallet"] = claimant_wallet
        return c

    # Risk acceptances
    def get_risk_acceptance(self, wallet: str, version: str) -> Optional[Dict[str, Any]]:
        key = f"{wallet}:{version}"
        return self._risk_acceptances.get(key)

    def create_risk_acceptance(self, wallet: str, version: str):
        key = f"{wallet}:{version}"
        self._risk_acceptances[key] = {
            "wallet_address": wallet,
            "accepted_version": version,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        }

    # Audit
    def create_audit(self, event_type: str, wallet: str = None, details: dict = None):
        self._audit_events.append({
            "event_id": str(__import__("uuid").uuid4()),
            "event_type": event_type,
            "wallet_address": wallet,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        })

    def get_audits(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit_events[-limit:]

    # Idempotency
    def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        return self._idempotency_keys.get(key)

    def set_idempotency(self, key: str, value: Dict[str, Any]):
        self._idempotency_keys[key] = value

    # Users
    def get_or_create_user(self, wallet: str, role: str = "viewer"):
        if wallet not in self._users:
            self._users[wallet] = {
                "wallet_address": wallet,
                "role": role,
                "is_active": True,
            }
        return self._users[wallet]

    def reset(self):
        """Clear all in-memory stores. Used for test isolation."""
        self._claims.clear()
        self._risk_acceptances.clear()
        self._audit_events.clear()
        self._idempotency_keys.clear()
        self._users.clear()


class DBAdapter:
    """Unified adapter that routes to SQLAlchemy or in-memory."""

    def __init__(self):
        self._use_db = _HAS_DB and bool(os.getenv("DATABASE_URL"))
        self._memory = InMemoryStore()

    def _session(self):
        if self._use_db:
            return db_manager.get_session()
        return None

    # Claims
    def create_claim(self, **kwargs):
        if self._use_db:
            with self._session() as db:
                repo = ClaimRepository(db)
                kwargs = dict(kwargs)
                import datetime as _dt
                if isinstance(kwargs.get("expires_at"), (int, float)):
                    kwargs["expires_at"] = _dt.datetime.fromtimestamp(kwargs["expires_at"], tz=_dt.timezone.utc)
                claim = repo.create(**kwargs)
                return self._claim_to_dict(claim)
        return self._memory.create_claim(**kwargs)

    def get_claim(self, claim_id: str):
        if self._use_db:
            with self._session() as db:
                repo = ClaimRepository(db)
                claim = repo.get_by_id(claim_id)
                return self._claim_to_dict(claim) if claim else None
        return self._memory.get_claim(claim_id)

    def mark_claim_claimed(self, claim_id: str, claimant_wallet: str):
        if self._use_db:
            with self._session() as db:
                repo = ClaimRepository(db)
                claim = repo.mark_claimed(claim_id, claimant_wallet)
                return self._claim_to_dict(claim) if claim else None
        return self._memory.mark_claim_claimed(claim_id, claimant_wallet)

    def _claim_to_dict(self, claim) -> Dict[str, Any]:
        return {
            "claim_id": claim.claim_id,
            "issuer_wallet": claim.issuer_wallet,
            "denomination_sats": claim.denomination_sats,
            "pin_hash": claim.pin_hash,
            "salt": claim.salt,
            "expires_at": claim.expires_at.timestamp() if claim.expires_at else None,
            "claimed": claim.claimed,
            "claimant_wallet": claim.claimant_wallet,
            "created_at": claim.created_at.timestamp() if claim.created_at else None,
        }

    # Risk
    def has_risk_acceptance(self, wallet: str, version: str) -> bool:
        if self._use_db:
            with self._session() as db:
                repo = RiskAcceptanceRepository(db)
                return repo.has_accepted(wallet, version)
        return self._memory.get_risk_acceptance(wallet, version) is not None

    def create_risk_acceptance(self, wallet: str, version: str):
        if self._use_db:
            with self._session() as db:
                repo = RiskAcceptanceRepository(db)
                return repo.create(wallet, version)
        return self._memory.create_risk_acceptance(wallet, version)

    # Audit
    def create_audit(self, event_type: str, wallet: str = None, details: dict = None):
        if self._use_db:
            with self._session() as db:
                repo = AuditLogRepository(db)
                return repo.create(event_type, wallet, details)
        return self._memory.create_audit(event_type, wallet, details)

    def get_audits(self, limit: int = 100):
        if self._use_db:
            with self._session() as db:
                repo = AuditLogRepository(db)
                return [{"event_id": str(e.id), "event_type": e.event_type,
                         "wallet_address": e.wallet_address,
                         "timestamp": e.created_at.isoformat(),
                         "details": e.details} for e in repo.get_by_type("", limit)]
        return self._memory.get_audits(limit)

    # Idempotency
    def get_idempotency(self, key: str):
        return self._memory.get_idempotency(key)

    def set_idempotency(self, key: str, value: Dict[str, Any]):
        self._memory.set_idempotency(key, value)

    # Stats
    def claim_count(self) -> int:
        if self._use_db:
            with self._session() as db:
                return db.query(__import__("db.models.claim", fromlist=["Claim"]).Claim).count()
        return len(self._memory._claims)

    def risk_acceptance_count(self) -> int:
        if self._use_db:
            with self._session() as db:
                return db.query(__import__("db.models.risk_acceptance", fromlist=["RiskAcceptance"]).RiskAcceptance).count()
        return len(self._memory._risk_acceptances)

    def audit_count(self) -> int:
        if self._use_db:
            with self._session() as db:
                return db.query(__import__("db.models.audit_log", fromlist=["AuditLog"]).AuditLog).count()
        return len(self._memory._audit_events)

    def idempotency_count(self) -> int:
        return len(self._memory._idempotency_keys)

    def redeemed_claim_count(self) -> int:
        if self._use_db:
            with self._session() as db:
                return db.query(__import__("db.models.claim", fromlist=["Claim"]).Claim).filter_by(claimed=True).count()
        return sum(1 for c in self._memory._claims.values() if c.get("claimed"))

    def active_claim_count(self) -> int:
        return self.claim_count() - self.redeemed_claim_count()

    def reset(self):
        """Reset in-memory stores. Used for test isolation."""
        self._memory.reset()


# Global singleton
db = DBAdapter()
