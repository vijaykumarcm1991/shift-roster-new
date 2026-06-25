"""Authentication utilities — JWT creation/verification and password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of a plaintext password."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plaintext matches the stored hash."""
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
ALGORITHM = settings.jwt_algorithm


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    subject:
        The value stored in the ``sub`` claim (typically the username).
    expires_delta:
        Override the default expiration window.
    extra:
        Additional claims merged into the payload.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": now,
    }
    if extra:
        payload.update(extra)

    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT.  Returns the payload dict or None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
