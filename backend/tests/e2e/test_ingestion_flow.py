"""E2E ingestion flow tests. Requires backend, SurrealDB, and OPENAI_API_KEY."""

import pytest
import httpx


@pytest.mark.e2e
class TestPDFIngestion:
    """PDF ingestion E2E tests."""

    def test_pdf_ingestion_succeeds(
        self, api_client: httpx.Client, sample_pdf_path: str
    ):
        """POST /api/ingest/pdf should ingest a PDF and return paper_id."""
        with open(sample_pdf_path, "rb") as f:
            files = {"file": ("sample_paper.pdf", f, "application/pdf")}
            response = api_client.post("/api/ingest/pdf", files=files)

        assert response.status_code == 200, response.text
        data = response.json()
        assert "paper_id" in data
        assert data["status"] == "success"
        assert data["nodes_created"] >= 0
        assert data["edges_created"] >= 0


@pytest.mark.e2e
class TestArxivIngestion:
    """arXiv ingestion E2E tests."""

    def test_arxiv_ingestion_succeeds(self, api_client: httpx.Client):
        """POST /api/ingest/arxiv should ingest paper from arXiv."""
        response = api_client.post(
            "/api/ingest/arxiv",
            json={"arxiv_id": "1706.03762"},
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert "paper_id" in data
        assert data["status"] == "success"
