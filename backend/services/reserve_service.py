"""
Membra Money Protocol — Reserve Service

Illustrative reserve metadata. No real BTC custody is implemented.
"""

from datetime import datetime, timezone
from typing import Optional


class ReserveService:
    def status(self) -> str:
        return "devnet_demo"

    def reserve_ratio_bps(self) -> int:
        # 100% as a default illustration
        return 10_000

    def attested_at(self) -> Optional[str]:
        return datetime.now(timezone.utc).isoformat()
