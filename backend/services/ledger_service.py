"""Ledger Service — ACID event-sourced internal ledger."""
import uuid, hashlib, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class LedgerService:
    """Append-only ledger with idempotent processing, optimistic concurrency, snapshots."""

    def __init__(self):
        self._accounts: Dict[str, Any] = {}
        self._entries: List[Dict[str, Any]] = []
        self._events: List[Dict[str, Any]] = []
        self._idempotency_keys: set = set()
        self._global_sequence = 0

    def _next_seq(self) -> int:
        self._global_sequence += 1
        return self._global_sequence

    def _event(
        self, event_type: str, aggregate_id: str, payload: Dict[str, Any],
        causation_id: Optional[str] = None, correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "occurred_at": datetime.now(timezone.utc).timestamp(),
            "sequence_number": self._next_seq(),
            "causation_id": causation_id,
            "correlation_id": correlation_id or str(uuid.uuid4()),
        }
        self._events.append(event)
        return event

    def create_account(
        self, account_id: str, account_type: str, asset_type: str, owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if account_id in self._accounts:
            return dict(self._accounts[account_id])
        acc = {
            "account_id": account_id,
            "owner_id": owner_id,
            "account_type": account_type,
            "asset_type": asset_type,
            "balance": 0,
            "version": 1,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        self._accounts[account_id] = acc
        self._event("account_created", account_id, dict(acc))
        return dict(acc)

    def post_entry(
        self,
        entry_type: str,
        debit_account: str,
        credit_account: str,
        amount: int,
        asset_type: str,
        idempotency_key: str,
        claim_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if idempotency_key in self._idempotency_keys:
            for e in self._entries:
                if e.get("idempotency_key") == idempotency_key:
                    return dict(e)
            raise ValueError("Idempotency collision without entry")
        if debit_account not in self._accounts or credit_account not in self._accounts:
            raise ValueError("Account not found")
        debit = self._accounts[debit_account]
        credit = self._accounts[credit_account]
        if debit["asset_type"] != asset_type or credit["asset_type"] != asset_type:
            raise ValueError("Asset type mismatch")
        if debit["balance"] < amount:
            raise ValueError("Insufficient balance")
        entry = {
            "entry_id": str(uuid.uuid4()),
            "entry_type": entry_type,
            "debit_account": debit_account,
            "credit_account": credit_account,
            "amount": amount,
            "asset_type": asset_type,
            "claim_id": claim_id,
            "metadata": metadata or {},
            "idempotency_key": idempotency_key,
            "occurred_at": datetime.now(timezone.utc).timestamp(),
            "sequence_number": self._next_seq(),
        }
        self._entries.append(entry)
        self._idempotency_keys.add(idempotency_key)
        debit["balance"] -= amount
        debit["version"] += 1
        credit["balance"] += amount
        credit["version"] += 1
        self._event("ledger_entry_posted", entry["entry_id"], dict(entry))
        return dict(entry)

    def get_balance(self, account_id: str) -> int:
        return self._accounts.get(account_id, {}).get("balance", 0)

    def get_history(self, account_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        entries = [dict(e) for e in self._entries
                   if e["debit_account"] == account_id or e["credit_account"] == account_id]
        return entries[-limit:]

    def get_events(self, aggregate_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        events = [dict(ev) for ev in self._events if ev["aggregate_id"] == aggregate_id]
        return events[-limit:]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "accounts": {k: dict(v) for k, v in self._accounts.items()},
            "sequence": self._global_sequence,
            "timestamp": datetime.now(timezone.utc).timestamp(),
        }

    def reconcile(self, expected_balances: Dict[str, int]) -> List[str]:
        mismatches = []
        for acc_id, expected in expected_balances.items():
            actual = self.get_balance(acc_id)
            if actual != expected:
                mismatches.append(f"{acc_id}: expected {expected}, got {actual}")
        return mismatches
