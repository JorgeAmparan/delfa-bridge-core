import os
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "fake-service-key")
os.environ.setdefault("GOOGLE_API_KEY", "fake-key")
os.environ.setdefault("BGE_M3_URL", "http://localhost:8080")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("FALKORDB_HOST", "localhost")
os.environ.setdefault("ORG_ID", "test-org")
os.environ.setdefault("API_KEY", "test-api-key-for-pytest")


@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from app.api.main import app
    return TestClient(app)
