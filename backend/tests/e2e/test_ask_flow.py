"""E2E ask flow tests. Requires backend, SurrealDB, OPENAI_API_KEY, and ingested papers."""

import pytest
import httpx


@pytest.mark.e2e
class TestAskFlow:
    """Ask agent E2E tests."""

    def test_ask_creates_session_and_returns_answer(self, api_client: httpx.Client):
        """POST /api/ask should return answer and session_id."""
        response = api_client.post(
            "/api/ask",
            json={"question": "Find papers about transformers"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "answer" in data
        assert "session_id" in data
        assert "sources" in data

    def test_ask_with_session_id(self, api_client: httpx.Client):
        """POST /api/ask with session_id should use existing session."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-ask-test"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        response = api_client.post(
            "/api/ask",
            json={"question": "What papers are in the database?", "session_id": session_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_selected_paper_query_returns_context(self, api_client: httpx.Client, sample_pdf_path: str):
        """Selected-paper scope should still return contextual answer for matching query."""
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("sample_paper.pdf", f, "application/pdf")}
            ingest_response = api_client.post("/api/ingest/pdf", files=files)
        assert ingest_response.status_code == 200, ingest_response.text
        paper_id = ingest_response.json()["paper_id"]

        response = api_client.post(
            "/api/ask",
            json={
                "question": "llms trained to censor politically sensitive topics",
                "filter_selected_only": True,
                "selected_paper_ids": [paper_id],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "insufficient context" not in data.get("answer", "").lower()
        assert len(data.get("sources", [])) >= 1
