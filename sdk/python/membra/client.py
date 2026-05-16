"""Python SDK for Membra Money Protocol API."""

import requests
from typing import Optional, Dict, Any


class MembraClient:
    def __init__(self, base_url: str = "https://api.membramoney.dev", api_key: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def ready(self) -> Dict[str, Any]:
        return self._request("GET", "/ready")

    def create_claim(self, wallet_address: str, denomination_sats: int, expires_minutes: int,
                     risk_version: str, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        body = {
            "wallet_address": wallet_address,
            "denomination_sats": denomination_sats,
            "expires_minutes": expires_minutes,
            "risk_version": risk_version,
        }
        if idempotency_key:
            body["idempotency_key"] = idempotency_key
        return self._request("POST", "/api/v1/claims/create", json=body)

    def validate_claim(self, claim_id: str, pin: str, claimant_wallet: str) -> Dict[str, Any]:
        return self._request("POST", "/api/v1/claims/validate", json={
            "claim_id": claim_id,
            "pin": pin,
            "claimant_wallet": claimant_wallet,
        })

    def get_reserves(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/reserves")

    def get_stats(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v1/stats")

    def get_audit_events(self, limit: int = 100) -> Dict[str, Any]:
        return self._request("GET", f"/api/v1/audit/events?limit={limit}")
