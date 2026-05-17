"""Identity Service — username routing, MFA, device management."""
import secrets, hashlib, re, uuid, time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class IdentityService:
    USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{2,30}$")
    RESERVED = {"admin", "root", "support", "help", "api", "www"}

    def __init__(self):
        self._users: Dict = {}
        self._tags: Dict = {}
        self._devices: Dict = {}
        self._nonces: Dict = {}

    def _generate_tag(self) -> str:
        return secrets.token_urlsafe(8)[:8].lower()

    def generate_nonce(self, wallet: str) -> str:
        nonce = secrets.token_hex(16)
        self._nonces[wallet] = nonce
        return nonce

    def verify_nonce(self, wallet: str, nonce: str) -> bool:
        stored = self._nonces.get(wallet)
        if stored and stored == nonce:
            del self._nonces[wallet]
            return True
        return False

    def register(self, username: str, wallet_address: str) -> Dict:
        un = username.lower().strip("@")
        if un in self.RESERVED:
            raise ValueError("Reserved username")
        if not self.USERNAME_RE.match(un):
            raise ValueError("Invalid username format")
        if un in self._users:
            raise ValueError("Username taken")
        user_id = hashlib.sha256(f"{un}:{wallet_address}".encode()).hexdigest()[:32]
        tag = self._generate_tag()
        self._users[un] = {"user_id": user_id, "username": un, "wallet_address": wallet_address, "receive_tag": tag, "is_active": True, "created_at": datetime.now(timezone.utc).isoformat()}
        self._tags[tag] = un
        return dict(self._users[un])

    def resolve(self, username_or_tag: str) -> Dict:
        key = username_or_tag.lower().strip("@")
        if key in self._users:
            return {"username": key, "tag": self._users[key]["receive_tag"]}
        if key in self._tags:
            user = self._users[self._tags[key]]
            return {"username": user["username"], "tag": key}
        raise ValueError("Not found")

    def rotate_tag(self, username: str) -> str:
        un = username.lower().strip("@")
        if un not in self._users:
            raise ValueError("User not found")
        old = self._users[un]["receive_tag"]
        if old in self._tags:
            del self._tags[old]
        new_tag = self._generate_tag()
        self._users[un]["receive_tag"] = new_tag
        self._tags[new_tag] = un
        return new_tag

    def register_device(self, username: str, fingerprint: str, user_agent: str) -> Dict:
        un = username.lower().strip("@")
        device = {"device_id": secrets.token_hex(8), "fingerprint": fingerprint, "user_agent_hash": hashlib.sha256(user_agent.encode()).hexdigest()[:16], "registered_at": datetime.now(timezone.utc).isoformat(), "last_active": datetime.now(timezone.utc).isoformat(), "is_revoked": False}
        self._devices.setdefault(un, []).append(device)
        return dict(device)

    def list_devices(self, username: str) -> List[Dict]:
        un = username.lower().strip("@")
        return [dict(d) for d in self._devices.get(un, [])]

    def revoke_device(self, username: str, device_id: str) -> bool:
        un = username.lower().strip("@")
        for d in self._devices.get(un, []):
            if d["device_id"] == device_id:
                d["is_revoked"] = True
                return True
        return False

    def get_user(self, username: str) -> Optional[Dict]:
        return self._users.get(username.lower().strip("@"))
