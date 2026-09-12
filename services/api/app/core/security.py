from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password for secure storage."""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored password hash."""
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False
