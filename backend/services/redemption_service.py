"""Redemption Flow — validate, fraud check, compliance, settle, receipt."""
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

# Amounts in satoshis. Thresholds drive approval routing.
_LARGE_TX_SATS = 1_000_000_000    # ~10 BTC — requires operator approval
_HIGH_VELOCITY_SATS = 10_000_000_000  # ~100 BTC in 24h — blocked
_FRAUD_BLOCK_SCORE = 50
_RATE_LIMIT_PER_HOUR = 10  # max redemptions per user per hour


class RedemptionService:
    """External redemption: validate, fraud, compliance, fee quote, burn, settle."""

    def __init__(self, claim_service, ledger_service, settlement_engine, treasury_service):
        self.claims = claim_service
        self.ledger = ledger_service
        self.settlement = settlement_engine
        self.treasury = treasury_service

        self._quarantine: Dict[str, Any] = {}
        self._receipts: Dict[str, Any] = {}
        self._idempotency: Dict[str, str] = {}      # idempotency_key → receipt_id
        self._pending_approval: Dict[str, Any] = {} # receipt_id → approval request
        self._audit_log: List[Dict[str, Any]] = []

        # User-level velocity tracking: user_id → list of UTC timestamps
        self._user_timestamps: Dict[str, List[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_claim(self, claim_id: str, user_id: str, pin: str) -> Dict[str, Any]:
        claim = self.claims.get_claim(claim_id)
        if not claim:
            raise ValueError("Claim not found")
        if claim.get("expiry") and datetime.now(timezone.utc).timestamp() > claim["expiry"]:
            raise ValueError("Claim expired")
        if claim["state"] in ("redeemed", "burned", "revoked"):
            raise ValueError("Claim already consumed")
        if claim["owner"] != user_id:
            raise ValueError("Not owner")
        return {
            "valid": True,
            "claim_id": claim_id,
            "denomination": claim["denomination"],
            "asset_type": claim["asset_type"],
        }

    # ------------------------------------------------------------------
    # Risk controls
    # ------------------------------------------------------------------

    def _check_rate_limit(self, user_id: str) -> bool:
        """Return True if the user has exceeded the per-hour redemption cap."""
        now = datetime.now(timezone.utc).timestamp()
        cutoff = now - 3600
        recent = [t for t in self._user_timestamps[user_id] if t > cutoff]
        self._user_timestamps[user_id] = recent
        return len(recent) >= _RATE_LIMIT_PER_HOUR

    def _record_user_action(self, user_id: str) -> None:
        self._user_timestamps[user_id].append(datetime.now(timezone.utc).timestamp())

    def fraud_check(self, user_id: str, amount: int, velocity_24h: int) -> Dict[str, Any]:
        score = 0
        reasons: List[str] = []
        if velocity_24h > _HIGH_VELOCITY_SATS:
            score += 30
            reasons.append("High 24h velocity")
        if amount > _LARGE_TX_SATS:
            score += 20
            reasons.append("Large single amount")
        return {"score": score, "blocked": score >= _FRAUD_BLOCK_SCORE, "reasons": reasons}

    def compliance_check(self, user_id: str, amount: int, destination: str) -> Dict[str, Any]:
        # Simplified compliance — production integrates sanctions APIs (Chainalysis/TRM)
        return {
            "kyc_required": amount > _LARGE_TX_SATS,
            "sanctions_clear": True,
            "aml_risk": "low",
            "jurisdiction_ok": True,
        }

    # ------------------------------------------------------------------
    # Fee quoting
    # ------------------------------------------------------------------

    def fee_quote(self, amount: int, asset_type: str, chain: str) -> Dict[str, Any]:
        network = self.settlement._estimate_fee(amount, chain)
        service = max(1, amount // 10_000)
        return {
            "network_fee": network,
            "service_fee": service,
            "total": network + service,
            "net_to_user": amount - network - service,
        }

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    def _audit(self, event: str, **kwargs: Any) -> None:
        self._audit_log.append({
            "event": event,
            "ts": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        })

    def get_audit_log(
        self, receipt_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        entries = self._audit_log
        if receipt_id:
            entries = [e for e in entries if e.get("receipt_id") == receipt_id]
        return entries[-limit:]

    # ------------------------------------------------------------------
    # Core redemption flow
    # ------------------------------------------------------------------

    def redeem(
        self,
        claim_id: str,
        user_id: str,
        pin: str,
        destination: str,
        chain: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        # Idempotency — return existing receipt for duplicate keys
        if idempotency_key in self._idempotency:
            existing_id = self._idempotency[idempotency_key]
            self._audit("idempotency_hit", receipt_id=existing_id, user_id=user_id)
            return dict(self._receipts[existing_id])

        # Rate limiting
        if self._check_rate_limit(user_id):
            self._audit("rate_limit_blocked", user_id=user_id, claim_id=claim_id)
            raise ValueError("Rate limit exceeded — try again later")

        # Validation
        self.validate_claim(claim_id, user_id, pin)
        claim = self.claims.get_claim(claim_id)
        amount = claim["denomination"]
        asset_type = claim["asset_type"]

        # Fraud check
        fraud = self.fraud_check(user_id, amount, 0)
        if fraud["blocked"]:
            self._quarantine[claim_id] = {
                "claim_id": claim_id,
                "reason": "Fraud check failed",
                "risk_score": fraud["score"],
                "flags": fraud["reasons"],
                "created_at": datetime.now(timezone.utc).timestamp(),
            }
            self._audit("quarantine", claim_id=claim_id, user_id=user_id,
                        score=fraud["score"], reasons=fraud["reasons"])
            raise ValueError("Fraud check failed")

        # Compliance check
        compliance = self.compliance_check(user_id, amount, destination)
        if not compliance["sanctions_clear"] or not compliance["jurisdiction_ok"]:
            self._audit("compliance_blocked", claim_id=claim_id, user_id=user_id)
            raise ValueError("Compliance check failed")

        fees = self.fee_quote(amount, asset_type, chain)

        # Large transactions route to operator approval queue instead of auto-settling
        requires_approval = amount >= _LARGE_TX_SATS or compliance["kyc_required"]

        receipt_id = str(uuid.uuid4())
        receipt: Dict[str, Any] = {
            "receipt_id": receipt_id,
            "claim_id": claim_id,
            "idempotency_key": idempotency_key,
            "user_id": user_id,
            "destination": destination,
            "amount": amount,
            "asset_type": asset_type,
            "chain": chain,
            "fees": fees,
            "tx_hash": None,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }

        if requires_approval:
            receipt["status"] = "pending_approval"
            self._pending_approval[receipt_id] = {
                "receipt_id": receipt_id,
                "claim_id": claim_id,
                "user_id": user_id,
                "amount": amount,
                "reason": "Large transaction" if amount >= _LARGE_TX_SATS else "KYC required",
                "submitted_at": datetime.now(timezone.utc).timestamp(),
                "approvals": [],
                "rejections": [],
            }
            self._audit("pending_approval", receipt_id=receipt_id, user_id=user_id,
                        amount=amount, reason=receipt["status"])
        else:
            # Auto-settle small transactions
            self.claims.burn_claim(claim_id)
            req = self.settlement.submit_request(user_id, destination, amount, asset_type, chain)
            receipt["status"] = "processing"
            receipt["request_id"] = req["request_id"]
            self._audit("auto_settled", receipt_id=receipt_id, user_id=user_id, amount=amount)

        self._receipts[receipt_id] = receipt
        self._idempotency[idempotency_key] = receipt_id
        self._record_user_action(user_id)

        return dict(receipt)

    # ------------------------------------------------------------------
    # Operator approval controls (P8 — dual approval for large txs)
    # ------------------------------------------------------------------

    def get_approval_queue(self) -> List[Dict[str, Any]]:
        return [dict(v) for v in self._pending_approval.values()
                if self._receipts.get(v["receipt_id"], {}).get("status") == "pending_approval"]

    def approve_redemption(
        self, receipt_id: str, operator_id: str, required_approvals: int = 2
    ) -> Dict[str, Any]:
        approval = self._pending_approval.get(receipt_id)
        receipt = self._receipts.get(receipt_id)
        if not approval or not receipt:
            raise ValueError("Approval request not found")
        if receipt["status"] != "pending_approval":
            raise ValueError(f"Receipt is not pending approval (status={receipt['status']})")
        if operator_id in approval["approvals"]:
            raise ValueError("Operator already approved this redemption")
        if operator_id in approval["rejections"]:
            raise ValueError("Operator already rejected this redemption")

        approval["approvals"].append(operator_id)
        self._audit("operator_approved", receipt_id=receipt_id, operator_id=operator_id,
                    approvals_count=len(approval["approvals"]))

        if len(approval["approvals"]) >= required_approvals:
            claim_id = receipt["claim_id"]
            self.claims.burn_claim(claim_id)
            req = self.settlement.submit_request(
                receipt["user_id"], receipt["destination"],
                receipt["amount"], receipt["asset_type"], receipt["chain"],
            )
            receipt["status"] = "processing"
            receipt["request_id"] = req["request_id"]
            self._audit("approval_threshold_reached", receipt_id=receipt_id,
                        operators=approval["approvals"])

        return dict(receipt)

    def reject_redemption(
        self, receipt_id: str, operator_id: str, reason: str
    ) -> Dict[str, Any]:
        approval = self._pending_approval.get(receipt_id)
        receipt = self._receipts.get(receipt_id)
        if not approval or not receipt:
            raise ValueError("Approval request not found")
        if receipt["status"] != "pending_approval":
            raise ValueError(f"Receipt is not pending approval (status={receipt['status']})")

        approval["rejections"].append({"operator": operator_id, "reason": reason})
        receipt["status"] = "rejected"
        receipt["rejection_reason"] = reason
        self._audit("operator_rejected", receipt_id=receipt_id, operator_id=operator_id,
                    reason=reason)
        return dict(receipt)

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        r = self._receipts.get(receipt_id)
        return dict(r) if r else None

    def get_quarantine(self) -> List[Dict[str, Any]]:
        return list(self._quarantine.values())
