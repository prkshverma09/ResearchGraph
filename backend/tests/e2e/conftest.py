"""E2E test fixtures and configuration."""

import pytest
import httpx
from pathlib import Path

BASE_URL = "http://localhost:18001"
FRONTEND_URL = "http://localhost:13000"


@pytest.fixture
def api_client():
    """HTTP client for backend API."""
    return httpx.Client(base_url=BASE_URL, timeout=60.0)


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF for E2E testing."""
    path = Path(__file__).parent.parent / "fixtures" / "sample_paper.pdf"
    if not path.exists():
        pytest.skip("Sample PDF not found. Run: curl -sL -o backend/tests/fixtures/sample_paper.pdf https://arxiv.org/pdf/1706.03762.pdf")
    return str(path)
