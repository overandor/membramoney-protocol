"""ClaimNote Service — transferable reserve-backed digital claims."""
import uuid, hashlib, hmac, secrets, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class ClaimNoteService:
    """Full claim-note lifecycle: create, transfer, split, merge, expire, burn, revoke."""

    def __init__(self):
        self._claims: Dict[str, Any] = {}
        self._nullifiers: set = set()
        self._transfer_log: List[Dict] = []
        self._sequence = 0

    def _next_seq(self) -> int:
        self._sequence += 1
        return self._sequence

    def _hash_pin(self, pin: str, salt: str) -> str:
        return hashlib.sha256(f"{pin}:{salt}".encode()).hexdigest()

    def _generate_nullifier(self, claim_id: str) -> str:
        secret = secrets.token_hex(16)
        return hmac.new(secret.encode(), claim_id.encode(), hashlib.sha256).hexdigest()

    def create_claim(
        self,
        issuer_id: str,
        asset_type: str,
        denomination: int,
        owner: str,
        bearer_condition: str,
        expiry_minutes: Optional[int] = None,
        redemption_policy: str = "immediate",
    ) -> Dict[str, Any]:
        claim_id = str(uuid.uuid4())
        salt = secrets.token_hex(16)
        pin_hash = self._hash_pin(bearer_condition, salt)
        nullifier = self._generate_nullifier(claim_id)
        if nullifier in self._nullifiers:
            raise ValueError("Nullifier collision")
        self._nullifiers.add(nullifier)
        expires_at = None
        if expiry_minutes:
            expires_at = datetime.now(timezone.utc).timestamp() + expiry_minutes * 60
        claim = {
            "claim_id": claim_id,
            "issuer_id": issuer_id,
            "asset_type": asset_type,
            "denomination": denomination,
            "owner": owner,
            "pin_hash": pin_hash,
            "salt": salt,
            "nullifier": nullifier,
            "replay_nonce": 0,
            "expiry": expires_at,
            "redemption_policy": redemption_policy,
            "compliance_state": "pending",
            "state": "created",
            "created_at": datetime.now(timezone.utc).timestamp(),
            "version": 1,
        }
        self._claims[claim_id] = claim
        return dict(claim)

    def get_claim(self, claim_id: str) -> Optional[Dict[str, Any]]:
        return self._claims.get(claim_id)

    def transfer_claim(self, claim_id: str, from_user: str, to_user: str, transfer_type: str = "username") -> Dict[str, Any]:
        claim = self._claims.get(claim_id)
        if not claim:
            raise ValueError("Claim not found")
        if claim["state"] != "created":
            raise ValueError("Claim not transferable")
        if claim["owner"] != from_user:
            raise ValueError("Not owner")
        if claim.get("expiry") and datetime.now(timezone.utc).timestamp() > claim["expiry"]:
            raise ValueError("Claim expired")
        claim["owner"] = to_user
        claim["state"] = "transferred"
        claim["replay_nonce"] += 1
        claim["version"] += 1
        self._transfer_log.append({
            "claim_id": claim_id,
            "from_user": from_user,
            "to_user": to_user,
            "transfer_type": transfer_type,
            "occurred_at": datetime.now(timezone.utc).timestamp(),
        })
        return dict(claim)

    def split_claim(self, claim_id: str, amounts: List[int]) -> List[Dict[str, Any]]:
        claim = self._claims.get(claim_id)
        if not claim or claim["state"] != "created":
            raise ValueError("Invalid claim")
        if sum(amounts) != claim["denomination"]:
            raise ValueError("Split amounts must sum to denomination")
        del self._claims[claim_id]
        self._nullifiers.discard(claim["nullifier"])
        new_claims = []
        for amount in amounts:
            new = self.create_claim(
                claim["issuer_id"], claim["asset_type"], amount,
                claim["owner"], claim["pin_hash"][:8], claim.get("expiry"),
                claim["redemption_policy"]
            )
            new["compliance_state"] = claim["compliance_state"]
            new["state"] = "created"
            self._claims[new["claim_id"]] = new
            new_claims.append(dict(new))
        return new_claims

    def merge_claims(self, claim_ids: List[str], new_owner: str) -> Dict[str, Any]:
        total = 0
        asset_type = None
        for cid in claim_ids:
            c = self._claims.get(cid)
            if not c or c["state"] != "created":
                raise ValueError("Invalid claim")
            if asset_type and c["asset_type"] != asset_type:
                raise ValueError("Asset type mismatch")
            asset_type = c["asset_type"]
            total += c["denomination"]
            del self._claims[cid]
            self._nullifiers.discard(c["nullifier"])
        merged = self.create_claim("system", asset_type, total, new_owner, secrets.token_hex(4))
        merged["state"] = "created"
        return dict(merged)

    def burn_claim(self, claim_id: str) -> Dict[str, Any]:
        claim = self._claims.get(claim_id)
        if not claim:
            raise ValueError("Claim not found")
        claim["state"] = "burned"
        return dict(claim)

    def revoke_claim(self, claim_id: str, issuer_id: str) -> Dict[str, Any]:
        claim = self._claims.get(claim_id)
        if not claim:
            raise ValueError("Claim not found")
        if claim["issuer_id"] != issuer_id:
            raise ValueError("Only issuer can revoke")
        if claim["state"] in ("redeemed", "burned", "revoked"):
            raise ValueError("Claim already consumed")
        claim["state"] = "revoked"
        return dict(claim)
