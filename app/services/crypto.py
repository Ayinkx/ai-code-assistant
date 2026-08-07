"""Symmetric encryption for sensitive values (e.g. GitHub access tokens).

Tokens are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256). The
encryption key is deterministically derived from the application ``SECRET_KEY``
so no extra key material needs to be provisioned, while still ensuring the
stored ciphertext is useless without the secret key.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def _fernet():
    """Return a Fernet instance derived from the application secret key."""
    secret = current_app.config.get("SECRET_KEY", "")
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt ``plaintext`` and return a base64 ciphertext string."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt ``ciphertext`` produced by :func:`encrypt_secret`.

    Raises :class:`ValueError` if the ciphertext is invalid or the secret key
    changed (which invalidates all previously encrypted values).
    """
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt stored secret (invalid key or corrupt data).") from exc
