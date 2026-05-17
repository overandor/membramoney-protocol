"""Security Service — fraud detection, anomaly monitoring, device fingerprinting."""
import hashlib, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class SecurityService:
    """Behavioral fraud detection and anomaly monitoring."""

    def __init__(self):
        self._velocity: Dict[str, List[float]] = {}
        self._alerts: List[Dict[str, Any]] = []

    def record_transaction(self, user_id: str, amount: int, ip_hash: str, device_fingerprint: str) -> None:
        key = f"{user_id}:{ip_hash}"
        now = datetime.now(timezone.utc).timestamp()
        self._velocity.setdefault(key, []).append(now)
        # Clean old entries (>24h)
        self._velocity[key] = [t for t in self._velocity[key] if now - t < 86400]

    def check_velocity(self, user_id: str, ip_hash: str) -> Dict[str, Any]:
        key = f"{user_id}:{ip_hash}"
        window = self._velocity.get(key, [])
        count_1h = sum(1 for t in window if datetime.now(timezone.utc).timestamp() - t < 3600)
        count_24h = len(window)
        total_24h = sum(0 for _ in window)  # placeholder for amount tracking
        blocked = count_1h > 50 or count_24h > 200
        return {
            "count_1h": count_1h,
            "count_24h": count_24h,
            "blocked": blocked,
            "reason": "Velocity limit exceeded" if blocked else None,
        }

    def check_anomaly(
        self, user_id: str, amount: int, geo_hash: str, device_fingerprint: str
    ) -> Dict[str, Any]:
        score = 0
        reasons = []
        if amount > 1_000_000_000:
            score += 25; reasons.append("Large amount")
        if not geo_hash or geo_hash == "unknown":
            score += 10; reasons.append("Unknown geo")
        if not device_fingerprint or device_fingerprint == "unknown":
            score += 15; reasons.append("Unknown device")
        if score >= 40:
            self._alerts.append({
                "user_id": user_id,
                "score": score,
                "reasons": reasons,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            })
        return {
            "score": score,
            "blocked": score >= 70,
            "reasons": reasons,
        }

    def get_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._alerts[-limit:]
