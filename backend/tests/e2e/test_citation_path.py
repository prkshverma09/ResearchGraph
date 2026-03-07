"""E2E citation path tests. Requires backend, SurrealDB, and ingested papers with citations."""

import pytest
import httpx


@pytest.mark.e2e
class TestCitationPath:
    """Citation path API tests."""

    def test_citation_path_endpoint(self, api_client: httpx.Client):
        """GET /api/citation-path should accept paper titles and return path."""
        response = api_client.get(
            "/api/citation-path",
            params={
                "paper_a": "Attention Is All You Need",
                "paper_b": "Some Other Paper",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
