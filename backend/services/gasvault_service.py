"""
GasVault Service — fee-credit accounting and relayer reimbursement.

Users do not receive free SOL. Users receive fee credits.
Relayers pay real fees. GasVault reimburses relayers from real SOL reserves.

Hard rule: Computation does not create lamports. GasVault must already contain real SOL.
"""

import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FeeCreditAccount:
    """Per-user fee-credit balance."""
    user_id: str
    balance_lamports: int = 0
    total_earned: int = 0
    total_spent: int = 0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    last_updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class RelayerRecord:
    """Registered relayer that pays real Solana gas."""
    relayer_id: str
    public_key: str
    total_paid_lamports: int = 0
    total_reimbursed_lamports: int = 0
    pending_reimbursement: int = 0
    is_active: bool = True
    registered_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class ReimbursementRequest:
    """A single reimbursement claim from a relayer."""
    request_id: str
    relayer_id: str
    amount_lamports: int
    tx_signature: str
    user_id: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected, paid
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    resolved_at: Optional[float] = None


# ---------------------------------------------------------------------------
# GasVault Service
# ---------------------------------------------------------------------------


class GasVaultService:
    """
    Manages fee credits, relayers, and reimbursements.

    Lifecycle:
      1. User earns fee credits (via ZK compute, PoV, PoD, etc.)
      2. User spends fee credits → relayer pays real gas
      3. Relayer submits reimbursement request
      4. GasVault verifies and reimburses from real SOL reserves
    """

    # Solana fee constants
    DEFAULT_FEE_LAMPORTS_PER_SIG = 5_000
    LAMPORTS_PER_SOL = 1_000_000_000

    # Safety caps
    MAX_CREDITS_PER_USER = 1_000_000_000  # 1 SOL equivalent
    MAX_REIMBURSEMENT_PER_BATCH = 100_000_000  # 0.1 SOL per batch

    def __init__(
        self,
        vault_sol_balance: float = 0.0,
        fee_lamports_per_sig: int = DEFAULT_FEE_LAMPORTS_PER_SIG,
    ):
        self._vault_sol_balance = vault_sol_balance
        self.fee_lamports_per_sig = fee_lamports_per_sig

        # Fee-credit accounts by user_id
        self._credits: Dict[str, FeeCreditAccount] = {}

        # Relayers
        self._relayers: Dict[str, RelayerRecord] = {}

        # Reimbursement requests
        self._reimbursements: Dict[str, ReimbursementRequest] = {}

        # Audit log
        self._events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Vault balance
    # ------------------------------------------------------------------

    @property
    def vault_lamports(self) -> int:
        return int(self._vault_sol_balance * self.LAMPORTS_PER_SOL)

    @property
    def vault_sol(self) -> float:
        return self._vault_sol_balance

    def deposit_sol(self, amount_sol: float) -> Dict[str, Any]:
        """Deposit real SOL into the GasVault."""
        if amount_sol <= 0:
            raise ValueError("Deposit amount must be positive")
        self._vault_sol_balance += amount_sol
        event = self._log_event("vault_deposit", {"amount_sol": amount_sol})
        return {"vault_sol": self._vault_sol_balance, "event": event}

    def withdraw_sol(self, amount_sol: float) -> Dict[str, Any]:
        """Withdraw SOL from GasVault (governance-gated)."""
        if amount_sol <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount_sol > self._vault_sol_balance:
            raise ValueError("Insufficient vault balance")
        self._vault_sol_balance -= amount_sol
        event = self._log_event("vault_withdraw", {"amount_sol": amount_sol})
        return {"vault_sol": self._vault_sol_balance, "event": event}

    # ------------------------------------------------------------------
    # Fee-credit accounting
    # ------------------------------------------------------------------

    def _get_or_create_credit_account(self, user_id: str) -> FeeCreditAccount:
        if user_id not in self._credits:
            self._credits[user_id] = FeeCreditAccount(user_id=user_id)
        return self._credits[user_id]

    def issue_credits(
        self, user_id: str, amount_lamports: int, reason: str = ""
    ) -> Dict[str, Any]:
        """Issue fee credits to a user. Does NOT create SOL."""
        if amount_lamports <= 0:
            raise ValueError("Credit amount must be positive")

        acct = self._get_or_create_credit_account(user_id)
        if acct.balance_lamports + amount_lamports > self.MAX_CREDITS_PER_USER:
            raise ValueError(f"Would exceed max credits per user ({self.MAX_CREDITS_PER_USER})")

        acct.balance_lamports += amount_lamports
        acct.total_earned += amount_lamports
        acct.last_updated_at = datetime.now(timezone.utc).timestamp()

        event = self._log_event("credits_issued", {
            "user_id": user_id,
            "amount_lamports": amount_lamports,
            "reason": reason,
        })
        return {
            "user_id": user_id,
            "credits_issued": amount_lamports,
            "new_balance": acct.balance_lamports,
            "event": event,
        }

    def spend_credits(
        self, user_id: str, amount_lamports: int, tx_signature: str = ""
    ) -> Dict[str, Any]:
        """Spend fee credits on a transaction. Relayer pays real gas."""
        acct = self._credits.get(user_id)
        if not acct:
            raise ValueError("No fee-credit account found")
        if acct.balance_lamports < amount_lamports:
            raise ValueError(
                f"Insufficient credits: have {acct.balance_lamports}, need {amount_lamports}"
            )

        acct.balance_lamports -= amount_lamports
        acct.total_spent += amount_lamports
        acct.last_updated_at = datetime.now(timezone.utc).timestamp()

        event = self._log_event("credits_spent", {
            "user_id": user_id,
            "amount_lamports": amount_lamports,
            "tx_signature": tx_signature,
        })
        return {
            "user_id": user_id,
            "credits_spent": amount_lamports,
            "remaining_balance": acct.balance_lamports,
            "event": event,
        }

    def get_credit_balance(self, user_id: str) -> Dict[str, Any]:
        acct = self._credits.get(user_id)
        if not acct:
            return {"user_id": user_id, "balance_lamports": 0, "exists": False}
        return {
            "user_id": user_id,
            "balance_lamports": acct.balance_lamports,
            "total_earned": acct.total_earned,
            "total_spent": acct.total_spent,
            "exists": True,
        }

    # ------------------------------------------------------------------
    # Relayer management
    # ------------------------------------------------------------------

    def register_relayer(self, public_key: str) -> Dict[str, Any]:
        relayer_id = str(uuid.uuid4())
        relayer = RelayerRecord(relayer_id=relayer_id, public_key=public_key)
        self._relayers[relayer_id] = relayer
        self._log_event("relayer_registered", {
            "relayer_id": relayer_id,
            "public_key": public_key,
        })
        return {
            "relayer_id": relayer_id,
            "public_key": public_key,
            "is_active": True,
        }

    def deactivate_relayer(self, relayer_id: str) -> Dict[str, Any]:
        relayer = self._relayers.get(relayer_id)
        if not relayer:
            raise ValueError("Relayer not found")
        relayer.is_active = False
        self._log_event("relayer_deactivated", {"relayer_id": relayer_id})
        return {"relayer_id": relayer_id, "is_active": False}

    def get_relayer(self, relayer_id: str) -> Optional[Dict[str, Any]]:
        r = self._relayers.get(relayer_id)
        if not r:
            return None
        return {
            "relayer_id": r.relayer_id,
            "public_key": r.public_key,
            "total_paid_lamports": r.total_paid_lamports,
            "total_reimbursed_lamports": r.total_reimbursed_lamports,
            "pending_reimbursement": r.pending_reimbursement,
            "is_active": r.is_active,
        }

    def list_relayers(self) -> List[Dict[str, Any]]:
        return [self.get_relayer(rid) for rid in self._relayers]

    # ------------------------------------------------------------------
    # Reimbursement
    # ------------------------------------------------------------------

    def request_reimbursement(
        self, relayer_id: str, amount_lamports: int, tx_signature: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Relayer requests reimbursement for gas paid."""
        relayer = self._relayers.get(relayer_id)
        if not relayer:
            raise ValueError("Relayer not found")
        if not relayer.is_active:
            raise ValueError("Relayer is deactivated")
        if amount_lamports <= 0:
            raise ValueError("Amount must be positive")
        if amount_lamports > self.MAX_REIMBURSEMENT_PER_BATCH:
            raise ValueError(f"Amount exceeds max per batch ({self.MAX_REIMBURSEMENT_PER_BATCH})")

        request_id = str(uuid.uuid4())
        req = ReimbursementRequest(
            request_id=request_id,
            relayer_id=relayer_id,
            amount_lamports=amount_lamports,
            tx_signature=tx_signature,
            user_id=user_id,
        )
        self._reimbursements[request_id] = req
        relayer.pending_reimbursement += amount_lamports

        self._log_event("reimbursement_requested", {
            "request_id": request_id,
            "relayer_id": relayer_id,
            "amount_lamports": amount_lamports,
            "tx_signature": tx_signature,
        })
        return {
            "request_id": request_id,
            "status": "pending",
            "amount_lamports": amount_lamports,
        }

    def approve_reimbursement(self, request_id: str) -> Dict[str, Any]:
        """Approve and pay a reimbursement request."""
        req = self._reimbursements.get(request_id)
        if not req:
            raise ValueError("Reimbursement request not found")
        if req.status != "pending":
            raise ValueError(f"Request already {req.status}")

        total_lamports = req.amount_lamports
        if total_lamports > self.vault_lamports:
            raise ValueError("Insufficient vault balance for reimbursement")

        # Deduct from vault
        self._vault_sol_balance -= total_lamports / self.LAMPORTS_PER_SOL

        # Update relayer
        relayer = self._relayers[req.relayer_id]
        relayer.total_paid_lamports += total_lamports
        relayer.total_reimbursed_lamports += total_lamports
        relayer.pending_reimbursement -= total_lamports

        # Mark request
        req.status = "paid"
        req.resolved_at = datetime.now(timezone.utc).timestamp()

        self._log_event("reimbursement_paid", {
            "request_id": request_id,
            "relayer_id": req.relayer_id,
            "amount_lamports": total_lamports,
        })
        return {
            "request_id": request_id,
            "status": "paid",
            "amount_lamports": total_lamports,
            "vault_remaining_sol": self._vault_sol_balance,
        }

    def reject_reimbursement(self, request_id: str, reason: str = "") -> Dict[str, Any]:
        """Reject a reimbursement request."""
        req = self._reimbursements.get(request_id)
        if not req:
            raise ValueError("Reimbursement request not found")
        if req.status != "pending":
            raise ValueError(f"Request already {req.status}")

        req.status = "rejected"
        req.resolved_at = datetime.now(timezone.utc).timestamp()

        relayer = self._relayers[req.relayer_id]
        relayer.pending_reimbursement -= req.amount_lamports

        self._log_event("reimbursement_rejected", {
            "request_id": request_id,
            "reason": reason,
        })
        return {"request_id": request_id, "status": "rejected", "reason": reason}

    def get_reimbursement(self, request_id: str) -> Optional[Dict[str, Any]]:
        req = self._reimbursements.get(request_id)
        if not req:
            return None
        return {
            "request_id": req.request_id,
            "relayer_id": req.relayer_id,
            "amount_lamports": req.amount_lamports,
            "tx_signature": req.tx_signature,
            "user_id": req.user_id,
            "status": req.status,
            "created_at": req.created_at,
            "resolved_at": req.resolved_at,
        }

    # ------------------------------------------------------------------
    # Coverage & health
    # ------------------------------------------------------------------

    @property
    def total_outstanding_credits(self) -> int:
        return sum(acct.balance_lamports for acct in self._credits.values())

    @property
    def total_pending_reimbursements(self) -> int:
        return sum(r.pending_reimbursement for r in self._relayers.values())

    @property
    def coverage_ratio(self) -> float:
        """Vault SOL / total outstanding liabilities."""
        liabilities = self.total_outstanding_credits + self.total_pending_reimbursements
        if liabilities == 0:
            return float("inf")
        return self.vault_lamports / liabilities

    @property
    def is_solvent(self) -> bool:
        return self.coverage_ratio >= 1.0

    def get_health(self) -> Dict[str, Any]:
        return {
            "vault_sol": self._vault_sol_balance,
            "vault_lamports": self.vault_lamports,
            "total_outstanding_credits": self.total_outstanding_credits,
            "total_pending_reimbursements": self.total_pending_reimbursements,
            "coverage_ratio": self.coverage_ratio,
            "is_solvent": self.is_solvent,
            "active_relayers": sum(1 for r in self._relayers.values() if r.is_active),
            "total_relayers": len(self._relayers),
            "total_credit_accounts": len(self._credits),
        }

    # ------------------------------------------------------------------
    # Proof-of-Need controller integration
    # ------------------------------------------------------------------

    def evaluate_need(
        self,
        gas_fee_twap: float,
        membra_twap: float,
        liquidity_depth_usd: float,
    ) -> Dict[str, Any]:
        """
        Proof-of-Need evaluation for GasVault actions.

        Returns proposed actions that require governance approval before execution.
        """
        needs = []
        coverage = self.coverage_ratio

        # High gas fees + low coverage → need SOL accumulation
        if gas_fee_twap > 10_000 and coverage < 0.5:
            needs.append({
                "action": "accumulate_sol",
                "urgency": "high",
                "reason": f"gas_fee_twap={gas_fee_twap}, coverage={coverage:.2f}",
            })

        # Low coverage → need refill
        if coverage < 0.8:
            needs.append({
                "action": "refill_gasvault",
                "urgency": "medium",
                "reason": f"coverage_ratio={coverage:.2f} below 0.8 threshold",
            })

        # High MEMBRA price + sufficient liquidity → could emit
        if membra_twap > 0 and coverage < 1.0 and liquidity_depth_usd > 10_000:
            needs.append({
                "action": "capped_membra_emission_for_gasvault",
                "urgency": "low",
                "reason": f"membra_twap={membra_twap}, coverage={coverage:.2f}",
            })

        return {
            "needs": needs,
            "requires_governance": len(needs) > 0,
            "coverage_ratio": coverage,
            "gas_fee_twap": gas_fee_twap,
            "membra_twap": membra_twap,
        }

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "data": data,
        }
        self._events.append(event)
        return event

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._events[-limit:]
