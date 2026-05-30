

class TestCORS:
    def test_allowed_origin_gets_cors_header(self, test_client):
        response = test_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin_no_cors_header(self, test_client):
        response = test_client.get(
            "/health",
            headers={"Origin": "http://evil.com"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_health_returns_ok(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_returns_product_info(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["product"] == "DOCYAN LDE™"
        assert data["status"] == "operational"
