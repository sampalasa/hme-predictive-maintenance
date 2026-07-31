"""Repository for the User model."""

from app.models import User, db
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data-access operations specific to User."""

    def __init__(self) -> None:
        super().__init__(User)

    def get_by_username(self, username: str) -> User | None:
        return db.session.query(User).filter_by(username=username).first()

    def get_by_email(self, email: str) -> User | None:
        return db.session.query(User).filter_by(email=email).first()
