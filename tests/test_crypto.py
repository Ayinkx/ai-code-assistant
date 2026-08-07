"""Tests for the crypto service (GitHub token encryption at rest)."""

import pytest

from app.services.crypto import decrypt_secret, encrypt_secret


class TestCrypto:
    def test_roundtrip(self, app):
        with app.app_context():
            ciphertext = encrypt_secret("gho_supersecrettoken123")
            assert ciphertext != "gho_supersecrettoken123"
            assert decrypt_secret(ciphertext) == "gho_supersecrettoken123"

    def test_ciphertext_is_deterministic_salt(self, app):
        # Fernet is not deterministic across calls, so two encryptions of the
        # same value must differ (random IV) but both must decrypt back.
        with app.app_context():
            first = encrypt_secret("same")
            second = encrypt_secret("same")
            assert first != second
            assert decrypt_secret(first) == decrypt_secret(second) == "same"

    def test_decrypt_fails_with_other_key(self, app):
        with app.app_context():
            ciphertext = encrypt_secret("token")
        app.config["SECRET_KEY"] = "a-different-secret-key"
        with app.app_context(), pytest.raises(ValueError):
            decrypt_secret(ciphertext)

    def test_decrypt_rejects_garbage(self, app):
        with app.app_context(), pytest.raises(ValueError):
            decrypt_secret("this is not a valid fernet token at all")
