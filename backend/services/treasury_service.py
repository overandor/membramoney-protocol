"""Treasury Service — reserve custody, attestations, multi-sig key management."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Dual-approval thresholds
_MULTISIG_REQUIRED_DEFAULT = 2   # M-of-N: 2 operator signatures required
_BATCH_EXPIRY_SECONDS = 3600     # Unsigned batches expire after 1 hour


class TreasuryService:
    """Hot/warm/cold wallet tracking, reserve attestations, proof-of-reserves."""

    def __init__(self):
        self._wallets: Dict[str, Any] = {}
        self._attestations: List[Dict[str, Any]] = []
        self._settlements: Dict[str, Any] = {}
        self._operators: Dict[str, Any] = {}       # operator_id → metadata
        self._audit_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Wallet management
    # ------------------------------------------------------------------

    def add_wallet(
        self, wallet_type: str, asset_type: str, address: str, public_key: str
    ) -> Dict[str, Any]:
        wid = str(uuid.uuid4())
        w = {
            "wallet_id": wid,
            "wallet_type": wallet_type,   # hot | warm | cold | squads_multisig
            "asset_type": asset_type,
            "address": address,
            "public_key": public_key,
            "balance": 0,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        self._wallets[wid] = w
        self._audit("wallet_added", wallet_id=wid, wallet_type=wallet_type,
                    asset_type=asset_type)
        return dict(w)

    def update_balance(self, wallet_id: str, balance: int) -> Dict[str, Any]:
        w = self._wallets.get(wallet_id)
        if not w:
            raise ValueError("Wallet not found")
        w["balance"] = balance
        w["last_synced_at"] = datetime.now(timezone.utc).timestamp()
        return dict(w)

    def get_reserve_total(self, asset_type: str) -> int:
        return sum(
            w["balance"] for w in self._wallets.values()
            if w["asset_type"] == asset_type and w["is_active"]
        )

    def get_liabilities(self, ledger_service, asset_type: str) -> int:
        total = 0
        for acc in ledger_service._accounts.values():
            if acc["account_type"] == "user" and acc["asset_type"] == asset_type:
                total += acc["balance"]
        return total

    def get_solvency_ratio(self, ledger_service, asset_type: str) -> Dict[str, Any]:
        reserves = self.get_reserve_total(asset_type)
        liabilities = self.get_liabilities(ledger_service, asset_type)
        ratio_bps = (reserves * 10_000 // liabilities) if liabilities > 0 else 10_000
        return {
            "asset_type": asset_type,
            "reserves": reserves,
            "liabilities": liabilities,
            "ratio_bps": ratio_bps,
            "solvent": ratio_bps >= 10_000,
        }

    # ------------------------------------------------------------------
    # Reserve attestations
    # ------------------------------------------------------------------

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
        self._audit("reserve_attested", asset_type=asset_type, attested_by=attested_by,
                    total=total)
        return dict(att)

    def get_latest_attestation(self, asset_type: str) -> Optional[Dict[str, Any]]:
        for a in reversed(self._attestations):
            if a["asset_type"] == asset_type:
                return dict(a)
        return None

    # ------------------------------------------------------------------
    # Settlement batch management (with multi-sig approval)
    # ------------------------------------------------------------------

    def create_settlement_batch(
        self, asset_type: str, requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        batch_id = str(uuid.uuid4())
        total = sum(r["amount"] for r in requests)
        now = datetime.now(timezone.utc).timestamp()
        batch = {
            "batch_id": batch_id,
            "batch_status": "pending_signatures",  # requires M-of-N before broadcast
            "asset_type": asset_type,
            "total_amount": total,
            "fee_estimate": 0,
            "tx_hash": None,
            "confirmations": 0,
            "requests": requests,
            "created_at": now,
            "expires_at": now + _BATCH_EXPIRY_SECONDS,
            "broadcast_at": None,
            "completed_at": None,
            # Multi-sig tracking
            "required_signatures": _MULTISIG_REQUIRED_DEFAULT,
            "signatures": [],   # list of {operator_id, signed_at}
            "rejections": [],   # list of {operator_id, reason, rejected_at}
        }
        self._settlements[batch_id] = batch
        self._audit("batch_created", batch_id=batch_id, asset_type=asset_type, total=total)
        return dict(batch)

    # ------------------------------------------------------------------
    # Multi-sig approval workflow (P8)
    # ------------------------------------------------------------------

    def register_operator(self, operator_id: str, name: str, public_key: str) -> Dict[str, Any]:
        op = {
            "operator_id": operator_id,
            "name": name,
            "public_key": public_key,
            "is_active": True,
            "added_at": datetime.now(timezone.utc).timestamp(),
        }
        self._operators[operator_id] = op
        self._audit("operator_registered", operator_id=operator_id)
        return dict(op)

    def sign_batch(
        self, batch_id: str, operator_id: str, signature_hex: str
    ) -> Dict[str, Any]:
        batch = self._settlements.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        if batch["batch_status"] not in ("pending_signatures",):
            raise ValueError(f"Batch not accepting signatures (status={batch['batch_status']})")
        now = datetime.now(timezone.utc).timestamp()
        if now > batch["expires_at"]:
            batch["batch_status"] = "expired"
            raise ValueError("Batch signing window expired")
        if any(s["operator_id"] == operator_id for s in batch["signatures"]):
            raise ValueError("Operator already signed this batch")
        if any(r["operator_id"] == operator_id for r in batch["rejections"]):
            raise ValueError("Operator already rejected this batch")

        batch["signatures"].append({
            "operator_id": operator_id,
            "signature_hex": signature_hex,
            "signed_at": now,
        })
        self._audit("batch_signed", batch_id=batch_id, operator_id=operator_id,
                    sigs_count=len(batch["signatures"]))

        if len(batch["signatures"]) >= batch["required_signatures"]:
            batch["batch_status"] = "approved"
            self._audit("batch_approved", batch_id=batch_id,
                        operators=[s["operator_id"] for s in batch["signatures"]])

        return dict(batch)

    def reject_batch(
        self, batch_id: str, operator_id: str, reason: str
    ) -> Dict[str, Any]:
        batch = self._settlements.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        if batch["batch_status"] not in ("pending_signatures",):
            raise ValueError(f"Batch cannot be rejected (status={batch['batch_status']})")

        batch["rejections"].append({
            "operator_id": operator_id,
            "reason": reason,
            "rejected_at": datetime.now(timezone.utc).timestamp(),
        })
        batch["batch_status"] = "rejected"
        self._audit("batch_rejected", batch_id=batch_id, operator_id=operator_id, reason=reason)
        return dict(batch)

    def broadcast_batch(self, batch_id: str, tx_hash: str) -> Dict[str, Any]:
        batch = self._settlements.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        if batch["batch_status"] != "approved":
            raise ValueError("Batch must be approved before broadcasting")
        batch["batch_status"] = "broadcasting"
        batch["tx_hash"] = tx_hash
        batch["broadcast_at"] = datetime.now(timezone.utc).timestamp()
        self._audit("batch_broadcast", batch_id=batch_id, tx_hash=tx_hash)
        return dict(batch)

    def confirm_batch(self, batch_id: str, confirmations: int) -> Dict[str, Any]:
        batch = self._settlements.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        batch["confirmations"] = confirmations
        required = {"btc": 6, "sol": 32, "eth": 12, "usdc": 12}.get(
            batch["asset_type"], 6
        )
        if confirmations >= required:
            batch["batch_status"] = "completed"
            batch["completed_at"] = datetime.now(timezone.utc).timestamp()
            self._audit("batch_completed", batch_id=batch_id, confirmations=confirmations)
        return dict(batch)

    def get_pending_batches(self) -> List[Dict[str, Any]]:
        return [
            dict(b) for b in self._settlements.values()
            if b["batch_status"] in ("pending_signatures", "approved")
        ]

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    def _audit(self, event: str, **kwargs: Any) -> None:
        self._audit_log.append({
            "event": event,
            "ts": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        })

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit_log[-limit:]
