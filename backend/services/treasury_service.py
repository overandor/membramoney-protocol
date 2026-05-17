"""Treasury Service — reserve custody, attestations, key management."""
import uuid, hashlib, secrets
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class TreasuryService:
    """Hot/warm/cold wallet tracking, reserve attestations, proof-of-reserves."""

    def __init__(self):
        self._wallets: Dict[str, Any] = {}
        self._attestations: List[Dict[str, Any]] = []
        self._settlements: Dict[str, Any] = {}

    def add_wallet(
        self, wallet_type: str, asset_type: str, address: str, public_key: str
    ) -> Dict[str, Any]:
        wid = str(uuid.uuid4())
        w = {
            "wallet_id": wid,
            "wallet_type": wallet_type,
            "asset_type": asset_type,
            "address": address,
            "public_key": public_key,
            "balance": 0,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        self._wallets[wid] = w
        return dict(w)

    def update_balance(self, wallet_id: str, balance: int) -> Dict[str, Any]:
        w = self._wallets.get(wallet_id)
        if not w:
            raise ValueError("Wallet not found")
        w["balance"] = balance
        w["last_synced_at"] = datetime.now(timezone.utc).timestamp()
        return dict(w)

    def get_reserve_total(self, asset_type: str) -> int:
        return sum(w["balance"] for w in self._wallets.values()
                   if w["asset_type"] == asset_type and w["is_active"])

    def get_liabilities(self, ledger_service, asset_type: str) -> int:
        total = 0
        for acc in ledger_service._accounts.values():
            if acc["account_type"] == "user" and acc["asset_type"] == asset_type:
                total += acc["balance"]
        return total

    def attest_reserve(
        self, asset_type: str, attested_by: str, signature: str
    ) -> Dict[str, Any]:
        total = self.get_reserve_total(asset_type)
        liabilities = 0
        ratio_bps = 10_000 if total > 0 else 0
        att = {
            "attestation_id": str(uuid.uuid4()),
            "asset_type": asset_type,
            "total_reserve": total,
            "total_liabilities": liabilities,
            "reserve_ratio_bps": ratio_bps,
            "attested_by": attested_by,
            "attestation_signature": signature,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        self._attestations.append(att)
        return dict(att)

    def get_latest_attestation(self, asset_type: str) -> Optional[Dict[str, Any]]:
        for a in reversed(self._attestations):
            if a["asset_type"] == asset_type:
                return dict(a)
        return None

    def create_settlement_batch(
        self, asset_type: str, requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        batch_id = str(uuid.uuid4())
        total = sum(r["amount"] for r in requests)
        batch = {
            "batch_id": batch_id,
            "batch_status": "collecting",
            "asset_type": asset_type,
            "total_amount": total,
            "fee_estimate": 0,
            "tx_hash": None,
            "confirmations": 0,
            "requests": requests,
            "created_at": datetime.now(timezone.utc).timestamp(),
            "broadcast_at": None,
            "completed_at": None,
        }
        self._settlements[batch_id] = batch
        return dict(batch)
