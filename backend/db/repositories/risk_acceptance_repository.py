from typing import Optional
from sqlalchemy.orm import Session
from db.models.risk_acceptance import RiskAcceptance


class RiskAcceptanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_wallet(self, wallet_address: str, version: str) -> Optional[RiskAcceptance]:
        return self.db.query(RiskAcceptance).filter(
            RiskAcceptance.wallet_address == wallet_address,
            RiskAcceptance.accepted_version == version
        ).first()

    def create(self, wallet_address: str, version: str, ip_address: str = None, user_agent: str = None) -> RiskAcceptance:
        ra = RiskAcceptance(
            wallet_address=wallet_address,
            accepted_version=version,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(ra)
        self.db.commit()
        self.db.refresh(ra)
        return ra

    def has_accepted(self, wallet_address: str, version: str) -> bool:
        return self.get_by_wallet(wallet_address, version) is not None
