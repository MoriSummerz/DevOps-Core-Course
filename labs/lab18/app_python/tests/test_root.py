"""Tests for the root endpoint (GET /)."""


class TestRootEndpoint:
    """Test suite for the root endpoint."""

    def test_root_returns_200(self, client):
        """Test that GET / returns 200 status code."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_json(self, client):
        """Test that GET / returns JSON content type."""
        response = client.get("/")
        assert response.headers["content-type"] == "application/json"

    def test_root_response_has_required_fields(self, client):
        """Test that response contains all required top-level fields."""
        response = client.get("/")
        data = response.json()

        required_fields = ["service", "system", "runtime", "request", "endpoints"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_service_info_structure(self, client):
        """Test that service info has correct structure and values."""
        response = client.get("/")
        service = response.json()["service"]

        assert "name" in service
        assert "version" in service
        assert "description" in service
        assert "framework" in service

        assert service["name"] == "devops-info-service"
        assert service["version"] == "1.0.0"
        assert service["framework"] == "FastAPI"

    def test_system_info_structure(self, client):
        """Test that system info has correct structure."""
        response = client.get("/")
        system = response.json()["system"]

        required_fields = [
            "hostname",
            "platform",
            "platform_version",
            "architecture",
            "cpu_count",
            "python_version",
        ]
        for field in required_fields:
            assert field in system, f"Missing system field: {field}"

        # Validate types
        assert isinstance(system["hostname"], str)
        assert isinstance(system["platform"], str)
        assert isinstance(system["cpu_count"], int)
        assert system["cpu_count"] > 0

    def test_runtime_info_structure(self, client):
        """Test that runtime info has correct structure."""
        response = client.get("/")
        runtime = response.json()["runtime"]

        required_fields = [
            "uptime_seconds",
            "uptime_human",
            "current_time",
            "timezone",
        ]
        for field in required_fields:
            assert field in runtime, f"Missing runtime field: {field}"

        assert isinstance(runtime["uptime_seconds"], int)
        assert runtime["uptime_seconds"] >= 0

    def test_request_info_structure(self, client):
        """Test that request info has correct structure."""
        response = client.get("/")
        request_info = response.json()["request"]

        required_fields = ["client_ip", "user_agent", "method", "path"]
        for field in required_fields:
            assert field in request_info, f"Missing request field: {field}"

        assert request_info["method"] == "GET"
        assert request_info["path"] == "/"

    def test_endpoints_is_list(self, client):
        """Test that endpoints is a non-empty list."""
        response = client.get("/")
        endpoints = response.json()["endpoints"]

        assert isinstance(endpoints, list)
        assert len(endpoints) > 0

    def test_endpoints_structure(self, client):
        """Test that each endpoint has correct structure."""
        response = client.get("/")
        endpoints = response.json()["endpoints"]

        for endpoint in endpoints:
            assert "path" in endpoint
            assert "method" in endpoint
            assert "description" in endpoint
            assert endpoint["method"] in [
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "PATCH",
                "OPTIONS",
                "HEAD",
            ]

    def test_custom_user_agent_reflected(self, client):
        """Test that custom user agent is captured in request info."""
        custom_ua = "TestBot/1.0"
        response = client.get("/", headers={"User-Agent": custom_ua})
        request_info = response.json()["request"]

        assert request_info["user_agent"] == custom_ua
