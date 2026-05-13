"""Tests for the health endpoint (GET /health)."""


class TestHealthEndpoint:
    """Test suite for the health endpoint."""

    def test_health_returns_200(self, client):
        """Test that GET /health returns 200 status code."""
        response = client.get("/health/")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Test that GET /health returns JSON content type."""
        response = client.get("/health/")
        assert response.headers["content-type"] == "application/json"

    def test_health_response_has_required_fields(self, client):
        """Test that health response contains all required fields."""
        response = client.get("/health/")
        data = response.json()

        required_fields = ["status", "timestamp", "uptime_seconds"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_health_status_is_healthy(self, client):
        """Test that health status returns 'healthy'."""
        response = client.get("/health/")
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_uptime_is_non_negative(self, client):
        """Test that uptime_seconds is a non-negative integer."""
        response = client.get("/health/")
        data = response.json()

        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

    def test_health_timestamp_is_valid(self, client):
        """Test that timestamp is a valid ISO format string."""
        response = client.get("/health/")
        data = response.json()

        assert isinstance(data["timestamp"], str)
        # Basic ISO format check (contains date separator)
        assert "T" in data["timestamp"] or "-" in data["timestamp"]

    def test_health_without_trailing_slash(self, client):
        """Test that /health (without trailing slash) redirects or works."""
        response = client.get("/health", follow_redirects=True)
        # Should either work directly or redirect to /health/
        assert response.status_code == 200


class TestHealthEndpointEdgeCases:
    """Edge case tests for the health endpoint."""

    def test_health_method_not_allowed_post(self, client):
        """Test that POST to /health returns 405 Method Not Allowed."""
        response = client.post("/health/")
        assert response.status_code == 405

    def test_health_method_not_allowed_put(self, client):
        """Test that PUT to /health returns 405 Method Not Allowed."""
        response = client.put("/health/")
        assert response.status_code == 405

    def test_health_method_not_allowed_delete(self, client):
        """Test that DELETE to /health returns 405 Method Not Allowed."""
        response = client.delete("/health/")
        assert response.status_code == 405

    def test_multiple_health_calls_consistent(self, client):
        """Test that multiple health calls return consistent structure."""
        responses = [client.get("/health/") for _ in range(3)]

        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "uptime_seconds" in data
