#!/usr/bin/env python3
"""Seed test data for Membra Money Protocol."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db.connection import db_manager
from db.repositories import UserRepository, ClaimRepository, RiskAcceptanceRepository, AuditLogRepository
from db.models.user import UserRole
from datetime import datetime, timedelta, timezone
import random
import string


def generate_wallet() -> str:
    chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return "".join(random.choices(chars, k=44))


def seed_users():
    db = db_manager.get_session()
    repo = UserRepository(db)
    for i in range(5):
        wallet = generate_wallet()
        role = random.choice(list(UserRole))
        repo.create(wallet, role)
        print(f"Created user: {wallet[:8]}... role={role.value}")
    db.close()


def seed_risk_acceptances():
    db = db_manager.get_session()
    repo = RiskAcceptanceRepository(db)
    from db.models.user import User
    users = db.query(User).all()
    for user in users:
        repo.create(user.wallet_address, "v1.0.0-devnet")
        print(f"Created risk acceptance for: {user.wallet_address[:8]}...")
    db.close()


def seed_claims():
    db = db_manager.get_session()
    claim_repo = ClaimRepository(db)
    from db.models.user import User
    users = db.query(User).all()
    for i in range(20):
        user = random.choice(users)
        claim_id = "".join(random.choices(string.hexdigits, k=32))
        claim_repo.create(
            claim_id=claim_id,
            issuer_wallet=user.wallet_address,
            denomination_sats=random.randint(1000, 10000000),
            pin_hash="a" * 64,
            salt="b" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=random.randint(10, 1440)),
        )
        print(f"Created claim: {claim_id[:8]}...")
    db.close()


def seed_audit_logs():
    db = db_manager.get_session()
    repo = AuditLogRepository(db)
    events = ["claim_created", "claim_validated", "risk_accepted", "reserve_attested"]
    for i in range(50):
        repo.create(
            event_type=random.choice(events),
            wallet_address=generate_wallet(),
            details={"test": True, "index": i},
        )
    print("Created 50 audit events")
    db.close()


if __name__ == "__main__":
    print("Seeding Membra Money Protocol test data...")
    seed_users()
    seed_risk_acceptances()
    seed_claims()
    seed_audit_logs()
    print("Done.")
