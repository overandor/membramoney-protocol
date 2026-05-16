from typing import Optional
from sqlalchemy.orm import Session
from db.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_wallet(self, wallet_address: str) -> Optional[User]:
        return self.db.query(User).filter(User.wallet_address == wallet_address).first()

    def create(self, wallet_address: str, role: UserRole = UserRole.VIEWER) -> User:
        user = User(wallet_address=wallet_address, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_or_create(self, wallet_address: str) -> User:
        user = self.get_by_wallet(wallet_address)
        if user:
            return user
        return self.create(wallet_address)

    def set_role(self, wallet_address: str, role: UserRole) -> Optional[User]:
        user = self.get_by_wallet(wallet_address)
        if user:
            user.role = role
            self.db.commit()
            self.db.refresh(user)
        return user
