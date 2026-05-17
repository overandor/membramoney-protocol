"""Compliance Service — KYC/AML, sanctions screening, quarantine."""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class ComplianceService:
    """Simplified compliance layer — production integrates SumSub/Onfido/Jumio."""

    def __init__(self):
        self._screenings: Dict[str, Any] = {}
        self._risk_scores: Dict[str, Any] = {}
        self._quarantine: Dict[str, Any] = {}
        self._ofac: set = {
            "0x1234abcd",  # Example sanctioned address
        }

    def screen_user(
        self, user_id: str, screening_type: str, provider: str = "internal"
    ) -> Dict[str, Any]:
        result = "clear"
        if user_id in self._ofac:
            result = "hit"
        screening = {
            "screening_id": str(uuid.uuid4()),
            "user_id": user_id,
            "screening_type": screening_type,
            "provider": provider,
            "result": result,
            "screened_at": datetime.now(timezone.utc).timestamp(),
        }
        self._screenings[user_id] = screening
        return dict(screening)

    def calculate_risk_score(self, user_id: str, factors: Optional[Dict] = None) -> Dict[str, Any]:
        score = 0
        reasons = []
        if factors:
            if factors.get("high_velocity"):
                score += 30; reasons.append("High velocity")
            if factors.get("large_amount"):
                score += 20; reasons.append("Large amount")
            if factors.get("new_account"):
                score += 15; reasons.append("New account")
        score = min(score, 100)
        self._risk_scores[user_id] = {
            "score": score,
            "reasons": reasons,
            "calculated_at": datetime.now(timezone.utc).timestamp(),
        }
        return dict(self._risk_scores[user_id])

    def quarantine_entry(
        self, entry_id: str, reason: str, risk_score: int
    ) -> Dict[str, Any]:
        q = {
            "quarantine_id": str(uuid.uuid4()),
            "entry_id": entry_id,
            "reason": reason,
            "risk_score": risk_score,
            "resolution": "pending",
            "created_at": datetime.now(timezone.utc).timestamp(),
        }
        self._quarantine[entry_id] = q
        return dict(q)

    def resolve_quarantine(self, entry_id: str, resolution: str) -> Dict[str, Any]:
        q = self._quarantine.get(entry_id)
        if not q:
            raise ValueError("Quarantine not found")
        q["resolution"] = resolution
        q["resolved_at"] = datetime.now(timezone.utc).timestamp()
        return dict(q)

    def get_quarantine(self) -> List[Dict[str, Any]]:
        return [dict(q) for q in self._quarantine.values() if q["resolution"] == "pending"]
