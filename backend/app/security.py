import os
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, stored_password_hash: str) -> bool:
    return password_hash.verify(plain_password, stored_password_hash)


def get_secret_key() -> str:
    secret_key = os.getenv("DEPOSITA_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("DEPOSITA_SECRET_KEY must be configured")
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
