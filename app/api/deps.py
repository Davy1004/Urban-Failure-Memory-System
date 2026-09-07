"""Shared route dependencies: DB session, current user, role gates."""
from typing import Optional

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, PermissionError_
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repo import UserRepository


def _bearer_token(request: Request) -> str:
    header: Optional[str] = request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise AuthError("Missing bearer token.")
    return header.split(" ", 1)[1].strip()


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    token = _bearer_token(request)
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthError("Session expired. Sign in again.")
    except jwt.PyJWTError:
        raise AuthError("Invalid token.")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthError("Malformed token.")

    user = UserRepository(db).get(int(user_id))
    if user is None or not user.is_active:
        raise AuthError("Account no longer active.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionError_("This action requires an admin account.")
    return user
