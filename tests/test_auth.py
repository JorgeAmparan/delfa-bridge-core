import os

import jwt
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-min-32-bytes-long-0000")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from app.api.auth import (
    JWT_ALGORITHM,
    JWT_SECRET,
    _create_access_token,
    _hash_token,
)


class TestJWT:
    def test_create_access_token_valid(self):
        user = {
            "id": "user-123",
            "org_id": "org-456",
            "role": "admin",
            "email": "test@test.com",
        }
        token = _create_access_token(user)
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert decoded["sub"] == "user-123"
        assert decoded["org_id"] == "org-456"
        assert decoded["role"] == "admin"

    def test_token_has_expiration(self):
        user = {"id": "u1", "org_id": "o1", "role": "viewer", "email": "a@b.com"}
        token = _create_access_token(user)
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "exp" in decoded

    def test_invalid_secret_rejects(self):
        user = {"id": "u1", "org_id": "o1", "role": "viewer", "email": "a@b.com"}
        token = _create_access_token(user)
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret-but-also-min-32-bytes-long-00", algorithms=[JWT_ALGORITHM])

    def test_expired_token_rejects(self):
        from datetime import datetime, timedelta, timezone

        payload = {
            "sub": "u1",
            "org_id": "o1",
            "role": "viewer",
            "email": "a@b.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


class TestHashToken:
    def test_deterministic(self):
        h1 = _hash_token("my-token")
        h2 = _hash_token("my-token")
        assert h1 == h2

    def test_different_inputs(self):
        h1 = _hash_token("token-a")
        h2 = _hash_token("token-b")
        assert h1 != h2


class TestJWTSecretRequired:
    def test_jwt_secret_is_set(self):
        assert JWT_SECRET is not None
        assert len(JWT_SECRET) > 0
