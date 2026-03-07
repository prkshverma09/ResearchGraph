"""E2E performance tests. Requires backend, SurrealDB, and OPENAI_API_KEY."""

import pytest
import httpx
import concurrent.futures
import time
from pathlib import Path


@pytest.mark.e2e
class TestPerformance:
    """Performance E2E tests."""

    @pytest.fixture
    def large_pdf_path(self):
        """Path to a large PDF (10+ pages) for testing."""
        path = Path(__file__).parent.parent / "fixtures" / "large_paper.pdf"
        if not path.exists():
            pytest.skip(
                "Large PDF not found. Create a 10+ page PDF for performance testing."
            )
        return str(path)

    def test_large_pdf_ingestion(self, api_client: httpx.Client, large_pdf_path: str):
        """Test ingestion of large PDF (10+ pages)."""
        start_time = time.time()

        with open(large_pdf_path, "rb") as f:
            files = {"file": ("large_paper.pdf", f, "application/pdf")}
            response = api_client.post(
                "/api/ingest/pdf",
                files=files,
                timeout=300.0,
            )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "success"
        assert "paper_id" in data

        assert elapsed_time < 300, f"Large PDF ingestion took {elapsed_time}s, expected < 300s"

    def test_concurrent_requests(self, api_client: httpx.Client):
        """Test handling of concurrent requests."""
        session_ids = []
        for i in range(5):
            create_resp = api_client.post(
                "/api/sessions",
                json={"user_id": f"e2e-concurrent-{i}"},
            )
            assert create_resp.status_code == 200
            session_ids.append(create_resp.json()["id"])

        def make_request(session_id: str):
            return api_client.post(
                "/api/ask",
                json={
                    "question": "What papers are in the database?",
                    "session_id": session_id,
                },
                timeout=60.0,
            )

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_request, session_id) for session_id in session_ids
            ]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        elapsed_time = time.time() - start_time

        assert len(responses) == 5
        for response in responses:
            assert response.status_code == 200, response.text
            data = response.json()
            assert "answer" in data

        assert elapsed_time < 120, f"Concurrent requests took {elapsed_time}s, expected < 120s"

    def test_concurrent_search_requests(self, api_client: httpx.Client):
        """Test concurrent search requests."""
        queries = [
            "transformer",
            "attention",
            "neural network",
            "machine learning",
            "deep learning",
        ]

        def make_search(query: str):
            return api_client.get(
                "/api/search",
                params={"query": query, "limit": 5},
                timeout=30.0,
            )

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_search, query) for query in queries]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        elapsed_time = time.time() - start_time

        assert len(responses) == 5
        for response in responses:
            assert response.status_code == 200, response.text
            data = response.json()
            assert "results" in data

        assert elapsed_time < 60, f"Concurrent searches took {elapsed_time}s, expected < 60s"

    def test_network_interruption_simulation(self, api_client: httpx.Client):
        """Test behavior when request is interrupted."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-interruption-test"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        try:
            response = api_client.post(
                "/api/ask",
                json={
                    "question": "What papers are in the database?",
                    "session_id": session_id,
                },
                timeout=0.1,
            )
        except httpx.TimeoutException:
            pass

        time.sleep(1)

        response = api_client.post(
            "/api/ask",
            json={
                "question": "What papers are in the database?",
                "session_id": session_id,
            },
            timeout=60.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    def test_large_query_response(self, api_client: httpx.Client):
        """Test handling of large query responses."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-large-response"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        response = api_client.post(
            "/api/ask",
            json={
                "question": "Summarize all papers in the database in detail, including methodology, results, and conclusions.",
                "session_id": session_id,
            },
            timeout=180.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 100

    def test_rapid_sequential_queries(self, api_client: httpx.Client):
        """Test rapid sequential queries to same session."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-rapid-queries"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        queries = [
            "What papers are in the database?",
            "Tell me about the first one",
            "What about the second?",
            "Compare them",
            "What are the key differences?",
        ]

        start_time = time.time()

        for query in queries:
            response = api_client.post(
                "/api/ask",
                json={"question": query, "session_id": session_id},
                timeout=60.0,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id

        elapsed_time = time.time() - start_time

        assert elapsed_time < 300, f"Rapid sequential queries took {elapsed_time}s, expected < 300s"
