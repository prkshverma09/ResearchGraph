"""E2E error handling tests."""

import pytest
import httpx


@pytest.mark.e2e
class TestErrorHandling:
    """Error handling E2E tests."""

    def test_ingest_rejects_non_pdf(self, api_client: httpx.Client):
        """POST /api/ingest/pdf should reject non-PDF files."""
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        response = api_client.post("/api/ingest/pdf", files=files)
        assert response.status_code == 400

    def test_ask_requires_question(self, api_client: httpx.Client):
        """POST /api/ask should require question field."""
        response = api_client.post(
            "/api/ask",
            json={},
        )
        assert response.status_code == 422

    def test_search_requires_query(self, api_client: httpx.Client):
        """POST /api/search should require query."""
        response = api_client.post(
            "/api/search",
            json={"top_k": 5},
        )
        assert response.status_code == 422
