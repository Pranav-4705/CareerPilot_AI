from typing import Optional, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

# OAuth2 scheme for Swagger UI integration and header extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticate_token(db: Session, token: Optional[str]) -> User:
    """
    Resolves a raw JWT access token to a `User`.

    Raises HTTP 401 Unauthorized for missing, invalid or expired tokens.
    """
    if not token:
        raise _unauthorized("Authentication credentials were not provided")

    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise _unauthorized("Invalid token payload")
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token has expired")
    except (jwt.PyJWTError, ValueError):
        raise _unauthorized("Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise _unauthorized("User not found")

    return user


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """
    Dependency to extract and validate the authenticated user from the Bearer JWT token.
    Raises standard HTTP 401 Unauthorized for missing, invalid, or expired tokens.
    """
    return authenticate_token(db, token)