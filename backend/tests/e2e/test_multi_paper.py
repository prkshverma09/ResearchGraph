"""E2E multi-paper scenario tests. Requires backend, SurrealDB, OPENAI_API_KEY, and multiple ingested papers."""

import pytest
import httpx


@pytest.mark.e2e
class TestMultiPaperScenarios:
    """Multi-paper scenario E2E tests."""

    @pytest.fixture(autouse=True)
    def ensure_papers_ingested(self, api_client: httpx.Client):
        """Ensure at least 5 papers are ingested before running tests."""
        arxiv_ids = [
            "1706.03762",
            "1706.03763",
            "2005.14165",
            "1810.04805",
            "2010.11929",
        ]

        for arxiv_id in arxiv_ids:
            try:
                response = api_client.post(
                    "/api/ingest/arxiv",
                    json={"arxiv_id": arxiv_id},
                    timeout=180.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        continue
            except Exception:
                pass

    def test_topic_exploration_across_papers(self, api_client: httpx.Client):
        """Test exploring topics across multiple papers."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-multi-paper-topic"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        response = api_client.post(
            "/api/ask",
            json={
                "question": "What are the main topics covered across all papers in the database?",
                "session_id": session_id,
            },
            timeout=120.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "sources" in data
        assert len(data["sources"]) > 0

    def test_author_network_analysis(self, api_client: httpx.Client):
        """Test author network analysis across papers."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-author-network"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        response = api_client.post(
            "/api/ask",
            json={
                "question": "What authors appear in multiple papers? Show me the author network.",
                "session_id": session_id,
            },
            timeout=120.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_citation_network_traversal(self, api_client: httpx.Client):
        """Test citation network traversal."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-citation-network"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        response = api_client.post(
            "/api/ask",
            json={
                "question": "Show me papers that cite each other. Traverse the citation network.",
                "session_id": session_id,
            },
            timeout=120.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_cross_paper_comparison(self, api_client: httpx.Client):
        """Test comparing concepts across multiple papers."""
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-cross-paper"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        response = api_client.post(
            "/api/ask",
            json={
                "question": "Compare the approaches to attention mechanisms across different papers.",
                "session_id": session_id,
            },
            timeout=120.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "sources" in data
        assert len(data["sources"]) >= 2

    def test_multi_paper_search(self, api_client: httpx.Client):
        """Test search across multiple papers."""
        response = api_client.get(
            "/api/search",
            params={"query": "transformer attention", "limit": 10},
            timeout=60.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0

        paper_ids = set()
        for result in data["results"]:
            assert "paper_id" in result
            paper_ids.add(result["paper_id"])

        assert len(paper_ids) > 1
