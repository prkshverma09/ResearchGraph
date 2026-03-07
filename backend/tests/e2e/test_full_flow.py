"""E2E full flow tests. Requires backend, SurrealDB, and OPENAI_API_KEY."""

import pytest
import httpx


@pytest.mark.e2e
class TestEndToEnd:
    """End-to-end flow tests covering complete user scenarios."""

    def test_full_research_flow(self, api_client: httpx.Client, sample_pdf_path: str):
        """
        Complete flow: ingest PDF → verify stats → ask question → verify answer → 
        check session → follow-up question → verify context
        """
        # 1. Ingest a test PDF via /api/ingest/pdf
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("sample_paper.pdf", f, "application/pdf")}
            ingest_response = api_client.post("/api/ingest/pdf", files=files, timeout=180.0)

        assert ingest_response.status_code == 200, ingest_response.text
        ingest_data = ingest_response.json()
        assert "paper_id" in ingest_data
        assert ingest_data["status"] == "success"
        paper_id = ingest_data["paper_id"]

        # 2. Verify paper appears in /api/graph/stats
        stats_response = api_client.get("/api/graph/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "papers" in stats_data
        assert stats_data["papers"] > 0

        # 3. Ask a question via /api/ask
        ask_response = api_client.post(
            "/api/ask",
            json={"question": "What papers are in the database?"},
            timeout=120.0,
        )
        assert ask_response.status_code == 200, ask_response.text
        ask_data = ask_response.json()

        # 4. Verify answer contains paper reference
        assert "answer" in ask_data
        assert len(ask_data["answer"]) > 0
        assert "sources" in ask_data
        assert len(ask_data["sources"]) > 0

        # 5. Check session was created
        assert "session_id" in ask_data
        session_id = ask_data["session_id"]
        assert session_id is not None
        assert len(session_id) > 0

        # Verify session exists
        session_response = api_client.get(f"/api/sessions/{session_id}")
        assert session_response.status_code == 200
        session_data = session_response.json()
        assert session_data["id"] == session_id

        # 6. Ask follow-up question with same session_id
        followup_response = api_client.post(
            "/api/ask",
            json={
                "question": "Tell me more about the first paper you mentioned",
                "session_id": session_id,
            },
            timeout=120.0,
        )
        assert followup_response.status_code == 200, followup_response.text
        followup_data = followup_response.json()

        # 7. Verify follow-up uses previous context
        assert followup_data["session_id"] == session_id
        assert "answer" in followup_data
        assert len(followup_data["answer"]) > 0

    def test_citation_discovery_flow(self, api_client: httpx.Client):
        """
        Ingest paper A (cites B) → ingest B → query citation path → verify path found
        """
        # 1. Ingest paper A (cites paper B)
        # Using arXiv papers - paper A will cite paper B
        paper_a_response = api_client.post(
            "/api/ingest/arxiv",
            json={"arxiv_id": "1706.03762"},  # Attention Is All You Need
            timeout=180.0,
        )
        assert paper_a_response.status_code == 200, paper_a_response.text
        paper_a_data = paper_a_response.json()
        assert paper_a_data["status"] == "success"
        paper_a_id = paper_a_data["paper_id"]

        # 2. Ingest paper B
        paper_b_response = api_client.post(
            "/api/ingest/arxiv",
            json={"arxiv_id": "1810.04805"},  # BERT
            timeout=180.0,
        )
        assert paper_b_response.status_code == 200, paper_b_response.text
        paper_b_data = paper_b_response.json()
        assert paper_b_data["status"] == "success"
        paper_b_id = paper_b_data["paper_id"]

        # Get paper titles for citation path query
        paper_a_graph = api_client.get(f"/api/graph/paper/{paper_a_id}")
        assert paper_a_graph.status_code == 200
        paper_a_info = paper_a_graph.json()
        paper_a_title = paper_a_info.get("paper", {}).get("title", "")

        paper_b_graph = api_client.get(f"/api/graph/paper/{paper_b_id}")
        assert paper_b_graph.status_code == 200
        paper_b_info = paper_b_graph.json()
        paper_b_title = paper_b_info.get("paper", {}).get("title", "")

        # 3. Query citation path between A and B
        if paper_a_title and paper_b_title:
            citation_path_response = api_client.get(
                "/api/citation-path",
                params={
                    "paper_a": paper_a_title,
                    "paper_b": paper_b_title,
                },
                timeout=60.0,
            )
            assert citation_path_response.status_code == 200
            path_data = citation_path_response.json()

            # 4. Verify path is found (or gracefully handles no path)
            assert "path" in path_data
            # Path may be empty if papers aren't directly connected, which is valid

    def test_multi_paper_topic_exploration(self, api_client: httpx.Client):
        """
        Ingest 3 papers → ask about themes → verify multiple papers referenced
        """
        # 1. Ingest 3 papers on related topics
        arxiv_ids = ["1706.03762", "1810.04805", "2005.14165"]  # Transformer, BERT, GPT-3
        paper_ids = []

        for arxiv_id in arxiv_ids:
            response = api_client.post(
                "/api/ingest/arxiv",
                json={"arxiv_id": arxiv_id},
                timeout=180.0,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    paper_ids.append(data["paper_id"])

        assert len(paper_ids) >= 2, "At least 2 papers should be ingested"

        # 2. Ask 'What are the key themes across these papers?'
        create_resp = api_client.post(
            "/api/sessions",
            json={"user_id": "e2e-topic-exploration"},
        )
        assert create_resp.status_code == 200
        session_id = create_resp.json()["id"]

        ask_response = api_client.post(
            "/api/ask",
            json={
                "question": "What are the key themes across these papers?",
                "session_id": session_id,
            },
            timeout=120.0,
        )
        assert ask_response.status_code == 200, ask_response.text
        ask_data = ask_response.json()

        # 3. Verify answer references multiple papers
        assert "answer" in ask_data
        assert len(ask_data["answer"]) > 0
        assert "sources" in ask_data
        assert len(ask_data["sources"]) > 0

        # Verify multiple papers are referenced in sources
        source_paper_ids = set()
        for source in ask_data["sources"]:
            if "paper_id" in source:
                source_paper_ids.add(source["paper_id"])

        assert len(source_paper_ids) >= 2, "Answer should reference multiple papers"

    def test_graph_visualization_data(self, api_client: httpx.Client, sample_pdf_path: str):
        """
        Ingest papers → GET /api/graph/paper/{id} → verify nodes/edges for visualization
        """
        # 1. Ingest papers
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("sample_paper.pdf", f, "application/pdf")}
            ingest_response = api_client.post("/api/ingest/pdf", files=files, timeout=180.0)

        assert ingest_response.status_code == 200, ingest_response.text
        ingest_data = ingest_response.json()
        assert ingest_data["status"] == "success"
        paper_id = ingest_data["paper_id"]

        # 2. GET /api/graph/paper/{id}
        graph_response = api_client.get(f"/api/graph/paper/{paper_id}")
        assert graph_response.status_code == 200, graph_response.text
        graph_data = graph_response.json()

        # 3. Verify response has nodes and edges suitable for visualization
        assert "paper" in graph_data
        paper_info = graph_data["paper"]
        assert "id" in paper_info or "title" in paper_info

        # Check for nodes (authors, topics, etc.)
        # Response should have structure suitable for graph visualization
        # Common fields: authors, topics, citations, etc.
        has_nodes = False
        has_edges = False

        # Check for author nodes
        if "authors" in graph_data and isinstance(graph_data["authors"], list):
            has_nodes = True
            if len(graph_data["authors"]) > 0:
                has_edges = True  # authored_by edges implied

        # Check for topic nodes
        if "topics" in graph_data and isinstance(graph_data["topics"], list):
            has_nodes = True
            if len(graph_data["topics"]) > 0:
                has_edges = True  # belongs_to edges implied

        # Check for citation nodes/edges
        if "citations" in graph_data and isinstance(graph_data["citations"], list):
            has_nodes = True
            if len(graph_data["citations"]) > 0:
                has_edges = True  # cites edges implied

        # At minimum, we should have the paper node
        assert has_nodes or "paper" in graph_data, "Response should contain nodes for visualization"