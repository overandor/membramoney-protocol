from typing import Optional, List
from sqlalchemy.orm import Session
from db.models.claim import Claim


class ClaimRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, claim_id: str) -> Optional[Claim]:
        return self.db.query(Claim).filter(Claim.claim_id == claim_id).first()

    def create(self, claim_id: str, issuer_wallet: str, denomination_sats: int,
               pin_hash: str, salt: str, expires_at) -> Claim:
        claim = Claim(
            claim_id=claim_id,
            issuer_wallet=issuer_wallet,
            denomination_sats=denomination_sats,
            pin_hash=pin_hash,
            salt=salt,
            expires_at=expires_at,
        )
        self.db.add(claim)
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def get_by_issuer(self, issuer_wallet: str) -> List[Claim]:
        return self.db.query(Claim).filter(Claim.issuer_wallet == issuer_wallet).all()

    def mark_claimed(self, claim_id: str, claimant_wallet: str):
        from datetime import datetime
        claim = self.get_by_id(claim_id)
        if claim:
            claim.claimed = True
            claim.claimant_wallet = claimant_wallet
            claim.claimed_at = datetime.utcnow()
            self.db.commit()
        return claim
