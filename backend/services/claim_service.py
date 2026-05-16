"""
Membra Money Protocol — Claim Service

Business logic for creating, validating, and managing claims.
For devnet, this wraps the in-memory store in main.py.
"""

from typing import Any, Dict, Optional


class ClaimService:
    def __init__(self, store: Optional[Dict[str, Any]] = None):
        self.store = store or {}

    def get(self, claim_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get(claim_id)

    def exists(self, claim_id: str) -> bool:
        return claim_id in self.store
