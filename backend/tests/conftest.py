"""Shared pytest fixtures and configuration."""

import pytest
import os
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator


@pytest.fixture
def mock_llm():
    """Mock ChatOpenAI that returns predetermined responses."""
    mock = Mock()
    mock.ainvoke = AsyncMock(return_value=Mock(content="Mocked LLM response"))
    mock.invoke = Mock(return_value=Mock(content="Mocked LLM response"))
    return mock


@pytest.fixture
def mock_embeddings():
    """Mock OpenAIEmbeddings that returns random 1536-dim vectors."""
    mock = Mock()
    
    def embed_documents(texts):
        # Return deterministic embeddings for testing
        import random
        random.seed(42)
        return [[random.random() for _ in range(1536)] for _ in texts]
    
    async def aembed_documents(texts):
        return embed_documents(texts)
    
    mock.embed_documents = Mock(side_effect=embed_documents)
    mock.aembed_documents = AsyncMock(side_effect=aembed_documents)
    return mock


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Path to a sample PDF file for testing."""
    # Create a minimal PDF file for testing
    pdf_path = tmp_path / "sample_paper.pdf"
    # For now, return path - actual PDF creation can be added if needed
    return str(pdf_path)


@pytest.fixture
def sample_entities():
    """Pre-built ExtractedEntities for testing graph construction."""
    from app.models.domain import ExtractedEntities, ExtractedAuthor
    
    return ExtractedEntities(
        title="Test Paper: Machine Learning Advances",
        authors=[
            ExtractedAuthor(name="Alice Researcher", institution="MIT"),
            ExtractedAuthor(name="Bob Scientist", institution="Stanford"),
        ],
        topics=["Machine Learning", "Neural Networks"],
        institutions=["MIT", "Stanford"],
        citations=["Paper A", "Paper B"],
        year=2024,
        venue="ICLR",
        key_findings=["Finding 1", "Finding 2"],
    )


@pytest.fixture
def mock_arxiv_api():
    """Mock arXiv API responses."""
    mock = Mock()
    mock.search = Mock(return_value=[
        Mock(
            title="Test Paper",
            authors=["Alice Researcher", "Bob Scientist"],
            summary="Test abstract",
            published="2024-01-01",
            arxiv_id="2401.00001",
        )
    ])
    return mock


@pytest.fixture
def mock_ss_api():
    """Mock Semantic Scholar API responses."""
    mock = Mock()
    mock.get_paper = Mock(return_value={
        "title": "Test Paper",
        "authors": [{"name": "Alice Researcher"}],
        "abstract": "Test abstract",
        "year": 2024,
        "citations": [{"title": "Cited Paper"}],
    })
    return mock


# Integration test fixtures (require real SurrealDB)
@pytest.fixture
async def db_manager():
    """Real SurrealDB connection for integration tests.
    Creates a fresh namespace per test, tears down after."""
    from app.db.connection import SurrealDBManager
    
    # Use test namespace/database
    manager = SurrealDBManager(
        url=os.getenv("SURREALDB_URL", "ws://localhost:8000/rpc"),
        user=os.getenv("SURREALDB_USER", "root"),
        password=os.getenv("SURREALDB_PASSWORD", "root"),
        namespace="test",
        database=f"test_{os.getpid()}",  # Unique per test run
    )
    
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.fixture
async def seeded_db(db_manager):
    """DB pre-populated with 5 test papers, authors, topics, citations."""
    # This will be implemented when we have the schema and ingestion pipeline
    # For now, return the db_manager
    yield db_manager


@pytest.fixture
async def async_client(db_manager):
    """httpx.AsyncClient bound to FastAPI test app."""
    import httpx
    from app.main import app, db_manager as global_db_manager
    import app.main
    
    app.main.db_manager = db_manager
    
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client
