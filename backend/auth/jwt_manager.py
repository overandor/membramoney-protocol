import uuid
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from core.config import settings


class JWTManager:
    """JWT token manager with wallet-based authentication."""

    def __init__(self, secret: str = None, algorithm: str = "HS256"):
        self.secret = secret or settings.jwt_secret
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=30)
        self.refresh_token_expire = timedelta(days=30)

    def create_access_token(self, wallet_address: str, role: str = "viewer") -> str:
        """Create a short-lived access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": wallet_address,
            "role": role,
            "type": "access",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + self.access_token_expire,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, wallet_address: str) -> str:
        """Create a long-lived refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": wallet_address,
            "type": "refresh",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + self.refresh_token_expire,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a token."""
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_wallet_from_token(self, token: str) -> Optional[str]:
        """Extract wallet address from token."""
        payload = self.decode_token(token)
        if payload and "sub" in payload:
            return payload["sub"]
        return None
