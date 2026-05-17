"""
Fee Sponsor Service — gasless Solana transaction sponsoring for note transfers.

When enabled, the protocol pays Solana transaction fees (~0.000005 SOL / ~$0.00025)
on behalf of users, making bearer-note transfers effectively free.

In a full production deployment this service would:
  1. Hold a funded fee-payer Solana wallet (hot wallet, limited balance).
  2. Partially sign transactions submitted by users, adding the fee-payer signature.
  3. Rate-limit sponsoring per IP / wallet to prevent abuse.
  4. Top up the hot wallet automatically from a warm wallet via a treasury sweep.
"""

from typing import Optional, Dict, Any


class FeeSponsorService:
    SOLANA_FEE_LAMPORTS = 5_000
    LAMPORTS_PER_SOL = 1_000_000_000

    def __init__(self, enabled: bool = False, sponsor_wallet: Optional[str] = None):
        self._enabled = enabled
        self._sponsor_wallet = sponsor_wallet or ""
        self._sponsored_count = 0
        self._total_lamports_sponsored = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def estimate_user_fee(self, transaction_count: int = 1) -> Dict[str, Any]:
        lamports = 0 if self._enabled else self.SOLANA_FEE_LAMPORTS * transaction_count
        return {
            "lamports": lamports,
            "sol": lamports / self.LAMPORTS_PER_SOL,
            "sponsored": self._enabled,
        }

    def record_sponsorship(self, user_wallet: str, lamports: Optional[int] = None) -> Dict[str, Any]:
        if not self._enabled:
            raise ValueError("Fee sponsoring is not enabled")
        amount = lamports or self.SOLANA_FEE_LAMPORTS
        self._sponsored_count += 1
        self._total_lamports_sponsored += amount
        return {
            "user_wallet": user_wallet,
            "lamports_sponsored": amount,
            "total_sponsored_count": self._sponsored_count,
            "total_lamports_sponsored": self._total_lamports_sponsored,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "sponsor_wallet": self._sponsor_wallet or None,
            "sponsored_transaction_count": self._sponsored_count,
            "total_lamports_sponsored": self._total_lamports_sponsored,
            "total_sol_sponsored": self._total_lamports_sponsored / self.LAMPORTS_PER_SOL,
        }
