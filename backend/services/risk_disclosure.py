"""
Membra Money Protocol — Risk Disclosure Service
"""

_RISK_TEXT = """
MEMBRA MONEY PROTOCOL — RISK DISCLOSURE
Version: v1.0.0-devnet

1. EXPERIMENTAL SOFTWARE
   This is unaudited, experimental software running on Solana devnet.
   It is not intended for real money, real BTC, or production use.

2. NO REAL CUSTODY
   The protocol does not hold, manage, or transfer real Bitcoin.
   All reserve figures are illustrative and unaudited.

3. SMART CONTRACT RISK
   The Anchor program has not been audited. Bugs, exploits, or design
   flaws may result in total loss of devnet test tokens.

4. DEVNET ONLY
   Devnet may be reset by Solana at any time. All state may be lost.

5. NO GUARANTEES
   There are no guarantees of value, redemption, or future development.

6. REGULATORY RISK
   Bearer-note designs may be regulated or prohibited in your jurisdiction.
   Consult legal counsel before any real-world use.

By accepting this disclosure, you acknowledge these risks and agree to
use the protocol solely for experimental purposes on devnet.
"""


class RiskDisclosureService:
    def get_text(self) -> str:
        return _RISK_TEXT.strip()
