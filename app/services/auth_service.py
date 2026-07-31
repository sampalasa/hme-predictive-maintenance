"""Password hashing and JWT issuance/verification.

Two authentication paths are supported: session-based login for the web UI
(Flask-Login, using the password hash from this service) and stateless JWT
bearer tokens for the REST API, both signed with the app's SECRET_KEY.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config.settings import Config
from app.models import User

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8


class AuthService:
    """Handles password hashing/verification and JWT token lifecycle."""

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def generate_token(user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.name,
            "iat": now,
            "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        """Raises jwt.PyJWTError (or a subclass) if the token is invalid/expired."""

        return jwt.decode(token, Config.SECRET_KEY, algorithms=[JWT_ALGORITHM])
