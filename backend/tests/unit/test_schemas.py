"""Unit tests for Pydantic request/response schemas."""

import pytest
from pydantic import ValidationError
from app.models.schemas import (
    IngestArxivRequest,
    IngestSemanticScholarRequest,
    IngestionResponse,
    SearchRequest,
    SearchResponse,
    PaperSearchResult,
    AskRequest,
    AskResponse,
    CitationPathRequest,
    CitationPathResponse,
    GraphStatsResponse,
    CreateSessionRequest,
    SessionResponse,
    HealthResponse,
)


def test_ask_request_validates():
    """AskRequest should require 'question' field."""
    request = AskRequest(question="What is machine learning?")
    assert request.question == "What is machine learning?"
    assert request.session_id is None
    
    request_with_session = AskRequest(question="Follow-up question", session_id="session:123")
    assert request_with_session.session_id == "session:123"
    
    with pytest.raises(ValidationError):
        AskRequest()


def test_ask_response_includes_sources():
    """AskResponse should include sources list."""
    response = AskResponse(
        answer="Machine learning is...",
        sources=[{"title": "Paper 1", "paper_id": "paper:1"}],
        session_id="session:123"
    )
    assert response.answer == "Machine learning is..."
    assert len(response.sources) == 1
    assert response.session_id == "session:123"
    assert response.graph_paths == []


def test_ingest_arxiv_request_validates():
    """IngestArxivRequest should require arxiv_id field."""
    request = IngestArxivRequest(arxiv_id="2401.00001")
    assert request.arxiv_id == "2401.00001"
    
    with pytest.raises(ValidationError):
        IngestArxivRequest()


def test_ingest_semantic_scholar_request_validates():
    """IngestSemanticScholarRequest should require paper_id field."""
    request = IngestSemanticScholarRequest(paper_id="12345678")
    assert request.paper_id == "12345678"
    
    with pytest.raises(ValidationError):
        IngestSemanticScholarRequest()


def test_ingestion_response_includes_all_fields():
    """IngestionResponse should include all required fields."""
    response = IngestionResponse(
        paper_id="paper:123",
        status="success",
        nodes_created=10,
        edges_created=15
    )
    assert response.paper_id == "paper:123"
    assert response.status == "success"
    assert response.nodes_created == 10
    assert response.edges_created == 15
    assert response.error is None
    
    error_response = IngestionResponse(
        paper_id="",
        status="error",
        error="Failed to parse PDF"
    )
    assert error_response.error == "Failed to parse PDF"


def test_search_request_validates():
    """SearchRequest should validate query and top_k."""
    request = SearchRequest(query="machine learning")
    assert request.query == "machine learning"
    assert request.top_k == 5
    
    request_custom_k = SearchRequest(query="neural networks", top_k=10)
    assert request_custom_k.top_k == 10
    
    with pytest.raises(ValidationError):
        SearchRequest()
    
    with pytest.raises(ValidationError):
        SearchRequest(query="test", top_k=0)
    
    with pytest.raises(ValidationError):
        SearchRequest(query="test", top_k=100)


def test_search_response_includes_papers():
    """SearchResponse should include papers list."""
    papers = [
        PaperSearchResult(
            title="Paper 1",
            abstract="Abstract 1",
            paper_id="paper:1",
            relevance_score=0.95
        ),
        PaperSearchResult(
            title="Paper 2",
            abstract="Abstract 2",
            paper_id="paper:2",
            relevance_score=0.87
        )
    ]
    response = SearchResponse(papers=papers)
    assert len(response.papers) == 2
    assert response.papers[0].title == "Paper 1"
    assert response.papers[0].relevance_score == 0.95


def test_citation_path_request_validates():
    """CitationPathRequest should require both paper_a and paper_b."""
    request = CitationPathRequest(paper_a="Paper A", paper_b="Paper B")
    assert request.paper_a == "Paper A"
    assert request.paper_b == "Paper B"
    
    with pytest.raises(ValidationError):
        CitationPathRequest(paper_a="Paper A")


def test_citation_path_response():
    """CitationPathResponse should include path and optional message."""
    response = CitationPathResponse(path=[{"id": "paper:1", "title": "Paper 1"}])
    assert len(response.path) == 1
    assert response.message is None
    
    response_with_message = CitationPathResponse(
        path=[],
        message="No path found"
    )
    assert response_with_message.message == "No path found"


def test_graph_stats_response():
    """GraphStatsResponse should include all counts."""
    response = GraphStatsResponse(papers=10, authors=20, topics=5, edges=30)
    assert response.papers == 10
    assert response.authors == 20
    assert response.topics == 5
    assert response.edges == 30


def test_create_session_request_validates():
    """CreateSessionRequest should require user_id."""
    request = CreateSessionRequest(user_id="user:123")
    assert request.user_id == "user:123"
    
    with pytest.raises(ValidationError):
        CreateSessionRequest()


def test_session_response():
    """SessionResponse should include all session fields."""
    from datetime import datetime
    
    now = datetime.now()
    response = SessionResponse(
        id="session:123",
        user_id="user:456",
        created_at=now,
        updated_at=now,
        queries=["query1", "query2"],
        papers_explored=["paper:1", "paper:2"]
    )
    assert response.id == "session:123"
    assert response.user_id == "user:456"
    assert len(response.queries) == 2
    assert len(response.papers_explored) == 2


def test_health_response():
    """HealthResponse should include status and db_connected."""
    response = HealthResponse(status="ok", db_connected=True)
    assert response.status == "ok"
    assert response.db_connected is True
    
    response_error = HealthResponse(status="error", db_connected=False)
    assert response_error.db_connected is False
