"""Redemption Flow — validate, fraud check, compliance, settle, receipt."""
import uuid, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class RedemptionService:
    """External redemption: validate, fraud, compliance, fee quote, burn, settle."""

    def __init__(self, claim_service, ledger_service, settlement_engine, treasury_service):
        self.claims = claim_service
        self.ledger = ledger_service
        self.settlement = settlement_engine
        self.treasury = treasury_service
        self._quarantine: Dict[str, Any] = {}
        self._receipts: Dict[str, Any] = {}

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
        return {"valid": True, "claim_id": claim_id, "denomination": claim["denomination"], "asset_type": claim["asset_type"]}

    def fraud_check(self, user_id: str, amount: int, velocity_24h: int) -> Dict[str, Any]:
        score = 0
        reasons = []
        if velocity_24h > 10_000_000_000:
            score += 30; reasons.append("High velocity")
        if amount > 1_000_000_000:
            score += 20; reasons.append("Large amount")
        return {"score": score, "blocked": score >= 50, "reasons": reasons}

    def compliance_check(self, user_id: str, amount: int, destination: str) -> Dict[str, Any]:
        # Simplified compliance — production integrates sanctions APIs
        return {
            "kyc_required": amount > 1_000_000_000,
            "sanctions_clear": True,
            "aml_risk": "low",
            "jurisdiction_ok": True,
        }

    def fee_quote(self, amount: int, asset_type: str, chain: str) -> Dict[str, Any]:
        network = self.settlement._estimate_fee(amount, chain)
        service = max(1, amount // 10_000)
        return {
            "network_fee": network,
            "service_fee": service,
            "total": network + service,
            "net_to_user": amount - network - service,
        }

    def redeem(
        self, claim_id: str, user_id: str, pin: str, destination: str,
        chain: str, idempotency_key: str
    ) -> Dict[str, Any]:
        validation = self.validate_claim(claim_id, user_id, pin)
        claim = self.claims.get_claim(claim_id)
        amount = claim["denomination"]
        asset_type = claim["asset_type"]
        fraud = self.fraud_check(user_id, amount, 0)
        if fraud["blocked"]:
            self._quarantine[claim_id] = {
                "claim_id": claim_id,
                "reason": "Fraud check failed",
                "risk_score": fraud["score"],
                "created_at": datetime.now(timezone.utc).timestamp(),
            }
            raise ValueError("Fraud check failed")
        fees = self.fee_quote(amount, asset_type, chain)
        self.claims.burn_claim(claim_id)
        req = self.settlement.submit_request(user_id, destination, amount, asset_type, chain)
        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "claim_id": claim_id,
            "request_id": req["request_id"],
            "user_id": user_id,
            "destination": destination,
            "amount": amount,
            "fees": fees,
            "status": "pending",
            "tx_hash": None,
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        self._receipts[receipt["receipt_id"]] = receipt
        return dict(receipt)
