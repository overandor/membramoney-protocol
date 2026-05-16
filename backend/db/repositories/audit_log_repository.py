from typing import List
from sqlalchemy.orm import Session
from db.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event_type: str, wallet_address: str = None, details: dict = None,
               ip_address: str = None, user_agent: str = None) -> AuditLog:
        log = AuditLog(
            event_type=event_type,
            wallet_address=wallet_address,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_by_wallet(self, wallet_address: str, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(
            AuditLog.wallet_address == wallet_address
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()

    def get_by_type(self, event_type: str, limit: int = 100) -> List[AuditLog]:
        return self.db.query(AuditLog).filter(
            AuditLog.event_type == event_type
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
