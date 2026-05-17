"""Settlement Engine — batched, delayed, fee-aware blockchain settlement."""
import uuid, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class SettlementEngine:
    """Collect, net, fee-estimate, sign, broadcast, confirm, receipt."""

    def __init__(self):
        self._pending: List[Dict[str, Any]] = []
        self._batches: Dict[str, Any] = {}

    def submit_request(
        self, user_id: str, destination: str, amount: int, asset_type: str, chain: str
    ) -> Dict[str, Any]:
        req = {
            "request_id": str(uuid.uuid4()),
            "user_id": user_id,
            "destination": destination,
            "amount": amount,
            "asset_type": asset_type,
            "chain": chain,
            "status": "pending",
            "fee_quote": self._estimate_fee(amount, chain),
            "submitted_at": datetime.now(timezone.utc).timestamp(),
        }
        self._pending.append(req)
        return dict(req)

    def _estimate_fee(self, amount: int, chain: str) -> int:
        # Simplified fee estimation
        base = {"btc": 1000, "sol": 5000, "eth": 20000, "usdc": 5000}
        return base.get(chain, 1000)

    def build_batch(self, asset_type: str, chain: str) -> Dict[str, Any]:
        batch_reqs = [r for r in self._pending
                      if r["asset_type"] == asset_type and r["chain"] == chain and r["status"] == "pending"]
        if not batch_reqs:
            raise ValueError("No pending requests")
        total = sum(r["amount"] for r in batch_reqs)
        fees = sum(r["fee_quote"] for r in batch_reqs)
        batch_id = str(uuid.uuid4())
        batch = {
            "batch_id": batch_id,
            "status": "collecting",
            "asset_type": asset_type,
            "chain": chain,
            "total_amount": total,
            "total_fees": fees,
            "requests": [r["request_id"] for r in batch_reqs],
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        for r in batch_reqs:
            r["status"] = "batched"
        self._batches[batch_id] = batch
        return dict(batch)

    def approve_batch(self, batch_id: str) -> Dict[str, Any]:
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        if batch["status"] != "collecting":
            raise ValueError("Batch not in collecting state")
        batch["status"] = "approved"
        return dict(batch)

    def broadcast_batch(self, batch_id: str, tx_hash: str) -> Dict[str, Any]:
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        batch["status"] = "broadcasting"
        batch["tx_hash"] = tx_hash
        batch["broadcast_at"] = datetime.now(timezone.utc).timestamp()
        return dict(batch)

    def confirm_batch(self, batch_id: str, confirmations: int) -> Dict[str, Any]:
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError("Batch not found")
        batch["confirmations"] = confirmations
        if confirmations >= self._required_confs(batch["chain"]):
            batch["status"] = "completed"
            batch["completed_at"] = datetime.now(timezone.utc).timestamp()
        return dict(batch)

    def _required_confs(self, chain: str) -> int:
        return {"btc": 6, "sol": 32, "eth": 12, "usdc": 12}.get(chain, 6)
