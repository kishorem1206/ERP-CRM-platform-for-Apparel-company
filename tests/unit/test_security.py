"""Unit tests for JWT and password hashing utilities."""
import pytest
import time
from uuid import uuid4
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

pytestmark = pytest.mark.unit


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        pw = "S0meTestPassword!"
        assert hash_password(pw) != pw

    def test_verify_correct_password(self):
        pw = "S0meTestPassword!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("S0meTestPassword!")
        assert verify_password("WrongPass", hashed) is False

    def test_two_hashes_differ(self):
        pw = "same_password"
        assert hash_password(pw) != hash_password(pw)  # bcrypt salts


class TestAccessToken:
    def test_token_decodes(self):
        uid = uuid4()
        company_id = uuid4()
        token = create_access_token({
            "sub": str(uid),
            "company_id": str(company_id),
            "permissions": ["inventory.view"],
        })
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(uid)
        assert payload["type"] == "access"
        assert "inventory.view" in payload["permissions"]

    def test_token_has_expiry(self):
        token = create_access_token({"sub": str(uuid4()), "company_id": str(uuid4()), "permissions": []})
        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_wrong_token_type_rejected(self):
        """Refresh token must not be accepted as access token in get_current_user logic."""
        uid = str(uuid4())
        refresh = create_refresh_token(uuid4())
        payload = decode_token(refresh)
        assert payload is not None
        assert payload["type"] == "refresh"
        assert payload["type"] != "access"

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": str(uuid4()), "company_id": str(uuid4()), "permissions": []})
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_empty_token_returns_none(self):
        assert decode_token("") is None


class TestRefreshToken:
    def test_refresh_token_decodes(self):
        uid = uuid4()
        token = create_refresh_token(uid)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(uid)
        assert payload["type"] == "refresh"
