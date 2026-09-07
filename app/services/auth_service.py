"""Registration and login. Transactions are committed here, not in routes."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import Token, UserCreate, UserLogin, UserOut


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, payload: UserCreate) -> User:
        email = payload.email.lower().strip()
        if self.users.email_exists(email):
            raise ConflictError("An account with that email already exists.")

        user = User(
            name=payload.name.strip(),
            email=email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            department=payload.department,
            city_id=payload.city_id,
            is_active=True,
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def login(self, payload: UserLogin) -> Token:
        user = self.users.get_by_email(payload.email)
        # Same message either way — never reveal which half was wrong.
        if not user or not verify_password(payload.password, user.password_hash):
            raise AuthError("Incorrect email or password.")
        if not user.is_active:
            raise AuthError("This account has been deactivated.")

        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)

        token = create_access_token(subject=str(user.user_id), role=user.role.value)
        return Token(
            access_token=token,
            expires_in_minutes=settings.access_token_expire_minutes,
            user=UserOut.model_validate(user),
        )
