from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, stored_password_hash: str) -> bool:
    return password_hash.verify(plain_password, stored_password_hash)
