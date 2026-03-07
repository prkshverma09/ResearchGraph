"""E2E session persistence tests. Requires backend, SurrealDB, and OPENAI_API_KEY."""

import pytest
import httpx
import time


@pytest.mark.e2e
class TestSessionPersistence:
    """Session persistence E2E tests."""

    def test_context_maintained_across_queries(self, api_client: httpx.Client):
        """Session should maintain context across multiple queries."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-persistence-test"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        first_response = api_client.post(
            "/api/ask",
            json={
                "question": "What papers are in the database?",
                "session_id": session_id,
            },
        )
        assert first_response.status_code == 200
        first_data = first_response.json()
        assert first_data["session_id"] == session_id

        second_response = api_client.post(
            "/api/ask",
            json={
                "question": "Tell me more about the first paper you mentioned",
                "session_id": session_id,
            },
        )
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert second_data["session_id"] == session_id
        assert "answer" in second_data
        assert len(second_data["answer"]) > 0

    def test_session_persists_across_requests(self, api_client: httpx.Client):
        """Session should persist across separate HTTP requests."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-persistence-test-2"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        first_response = api_client.post(
            "/api/ask",
            json={
                "question": "List all papers",
                "session_id": session_id,
            },
        )
        assert first_response.status_code == 200

        time.sleep(1)

        second_response = api_client.post(
            "/api/ask",
            json={
                "question": "What was the first paper?",
                "session_id": session_id,
            },
        )
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert second_data["session_id"] == session_id

    def test_multiple_concurrent_sessions(self, api_client: httpx.Client):
        """Multiple concurrent sessions should work independently."""
        session_ids = []
        for i in range(3):
            create_resp = api_client.post(
                "/api/sessions",
                json={"user_id": f"e2e-concurrent-test-{i}"},
            )
            assert create_resp.status_code == 200
            session_ids.append(create_resp.json()["id"])

        responses = []
        for session_id in session_ids:
            response = api_client.post(
                "/api/ask",
                json={
                    "question": f"What papers are in the database? Session {session_id[:8]}",
                    "session_id": session_id,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            responses.append(data)

        assert len(responses) == 3
        assert len(set(r["session_id"] for r in responses)) == 3

    def test_session_retrieval(self, api_client: httpx.Client):
        """GET /api/sessions/:id should retrieve existing session."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-retrieval-test"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        get_resp = api_client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        session_data = get_resp.json()
        assert session_data["id"] == session_id
        assert "created_at" in session_data
