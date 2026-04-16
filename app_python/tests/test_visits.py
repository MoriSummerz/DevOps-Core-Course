"""Tests for the /visits endpoint and counter persistence."""


class TestVisitsEndpoint:
    def test_initial_count_is_zero(self, client):
        response = client.get("/visits/")
        assert response.status_code == 200
        assert response.json() == {"visits": 0}

    def test_root_increments_counter(self, client):
        client.get("/")
        client.get("/")
        client.get("/")
        response = client.get("/visits/")
        assert response.json()["visits"] == 3

    def test_visits_endpoint_does_not_increment(self, client):
        client.get("/")
        client.get("/visits/")
        client.get("/visits/")
        response = client.get("/visits/")
        assert response.json()["visits"] == 1
