import os
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
INSECURE_SECRET_KEYS = frozenset(
    {
        "secret",
        "password",
        "changeme",
        "change-me",
        "deposita",
        "your-secret-key",
        "your-secret-key-here",
    }
)


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, stored_password_hash: str) -> bool:
    return password_hash.verify(plain_password, stored_password_hash)


def get_secret_key() -> str:
    secret_key = os.getenv("DEPOSITA_SECRET_KEY")
    if secret_key is None:
        raise RuntimeError("DEPOSITA_SECRET_KEY must be configured")

    normalized_secret_key = secret_key.strip()
    if not normalized_secret_key:
        raise RuntimeError("DEPOSITA_SECRET_KEY must not be empty")
    if normalized_secret_key.lower() in INSECURE_SECRET_KEYS:
        raise RuntimeError("DEPOSITA_SECRET_KEY must not use a common insecure value")
    if len(normalized_secret_key) < 32:
        raise RuntimeError("DEPOSITA_SECRET_KEY must be at least 32 characters long")

    return secret_key


def validate_auth_settings() -> None:
    get_secret_key()


def create_access_token(
    subject: str, expires_delta: timedelta | None = None
) -> str:
    now = datetime.now(timezone.utc)
    expiration = now + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"sub": subject, "iat": now, "exp": expiration},
        get_secret_key(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    payload = jwt.decode(
        token,
        get_secret_key(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp"]},
    )
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError("Invalid token subject")
    return subject
