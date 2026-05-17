"""Identity Service."""
import secrets, hashlib, re
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
        return secrets.token_urlsafe(8)[:8].upper()

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
            u = self._users[self._tags[key]]
            return {"username": u["username"], "tag": key}
        raise ValueError("Not found")

    def get_user(self, username: str) -> Optional[Dict]:
        return self._users.get(username.lower().strip("@"))
