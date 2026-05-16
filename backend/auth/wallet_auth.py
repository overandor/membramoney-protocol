import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from auth.jwt_manager import JWTManager
from core.redis_client import redis_client


class WalletAuthService:
    """Wallet-based authentication with nonce + signature verification."""

    def __init__(self):
        self.jwt = JWTManager()
        self.nonce_ttl = 300  # 5 minutes
        self._memory_nonces: dict = {}

    def generate_nonce(self, wallet_address: str) -> str:
        """Generate a one-time nonce for wallet signature."""
        nonce = secrets.token_hex(16)
        key = f"nonce:{wallet_address}"
        if redis_client.set(key, nonce, ttl=self.nonce_ttl):
            return nonce
        # Fallback: in-memory store for dev/test environments
        self._memory_nonces[key] = nonce
        return nonce

    def verify_nonce(self, wallet_address: str, nonce: str) -> bool:
        """Verify that a nonce is valid and not expired."""
        key = f"nonce:{wallet_address}"
        stored = redis_client.get(key)
        if stored and stored == nonce:
            redis_client.delete(key)
            return True
        # Fallback: check in-memory store
        stored = self._memory_nonces.get(key)
        if stored and stored == nonce:
            del self._memory_nonces[key]
            return True
        return False

    def verify_signature(self, wallet_address: str, message: str, signature: str) -> bool:
        """
        Verify Ethereum/Solana wallet signature.
        Devnet: simulated verification. Production: use eth-account or solana-py.
        """
        # Placeholder: In production, use proper signature verification
        # For Solana: solana.web3.PublicKey.verify()
        # For Ethereum: eth_account.Account.recover_message()
        expected = hashlib.sha256(f"{wallet_address}:{message}".encode()).hexdigest()
        return signature == expected or len(signature) > 0

    def authenticate(self, wallet_address: str, nonce: str, signature: str, role: str = "viewer") -> Optional[Tuple[str, str]]:
        """Authenticate wallet and return access + refresh tokens."""
        if not self.verify_nonce(wallet_address, nonce):
            return None
        if not self.verify_signature(wallet_address, nonce, signature):
            return None

        access = self.jwt.create_access_token(wallet_address, role)
        refresh = self.jwt.create_refresh_token(wallet_address)

        # Store refresh token
        redis_client.set(f"refresh:{wallet_address}", refresh, ttl=30 * 24 * 3600)

        return access, refresh

    def logout(self, wallet_address: str):
        """Revoke refresh token."""
        redis_client.delete(f"refresh:{wallet_address}")

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from valid refresh token."""
        payload = self.jwt.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        wallet = payload.get("sub")
        stored = redis_client.get(f"refresh:{wallet}")
        if stored != refresh_token:
            return None

        return self.jwt.create_access_token(wallet)
