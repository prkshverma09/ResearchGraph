"""API smoke tests - run against live backend. Requires backend and SurrealDB running."""

import pytest
import httpx


@pytest.mark.e2e
class TestHealthSmoke:
    """Health check smoke tests."""

    def test_health_endpoint_returns_ok(self, api_client: httpx.Client):
        """GET /api/health should return 200 with status."""
        response = api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "db_connected" in data

    def test_health_returns_db_status(self, api_client: httpx.Client):
        """Health should indicate database connection status."""
        response = api_client.get("/api/health")
        data = response.json()
        assert data["db_connected"] is True


@pytest.mark.e2e
class TestGraphStatsSmoke:
    """Graph stats smoke tests."""

    def test_graph_stats_endpoint(self, api_client: httpx.Client):
        """GET /api/graph/stats should return counts."""
        response = api_client.get("/api/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert "authors" in data
        assert "topics" in data
        assert isinstance(data["papers"], int)


@pytest.mark.e2e
class TestSearchSmoke:
    """Search smoke tests."""

    def test_search_endpoint_accepts_query(self, api_client: httpx.Client):
        """POST /api/search should accept query and return papers."""
        response = api_client.post(
            "/api/search",
            json={"query": "transformers", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert isinstance(data["papers"], list)


@pytest.mark.e2e
class TestSessionSmoke:
    """Session smoke tests."""

    def test_create_session(self, api_client: httpx.Client):
        """POST /api/sessions should create session."""
        response = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-test-user"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

    def test_list_sessions(self, api_client: httpx.Client):
        """GET /api/sessions should return sessions."""
        response = api_client.get("/api/sessions?user_id=e2e-test-user")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
