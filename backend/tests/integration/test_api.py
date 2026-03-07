"""Integration tests for FastAPI endpoints."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def async_client(db_manager):
    """httpx.AsyncClient bound to FastAPI test app."""
    from app.main import db_manager as global_db_manager
    import app.main
    
    app.main.db_manager = db_manager
    
    with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """GET /api/health should return 200 with db status."""
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "db_connected" in data
    assert isinstance(data["db_connected"], bool)


@pytest.mark.asyncio
async def test_search_endpoint(async_client, seeded_db):
    """POST /api/search should return relevant papers."""
    with patch("app.api.routes_search.VectorStoreService") as mock_vector_store:
        mock_service = MagicMock()
        mock_doc = MagicMock()
        mock_doc.metadata = {"title": "Test Paper", "paper_id": "paper:1"}
        mock_doc.page_content = "This is a test abstract about machine learning."
        mock_service.similarity_search_with_scores = AsyncMock(
            return_value=[(mock_doc, 0.95)]
        )
        mock_vector_store.return_value = mock_service
        
        response = await async_client.post(
            "/api/search",
            json={"query": "machine learning", "top_k": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert isinstance(data["papers"], list)


@pytest.mark.asyncio
async def test_ask_endpoint(async_client, seeded_db):
    """POST /api/ask should return answer with sources."""
    with patch("app.api.routes_ask.create_agent_graph") as mock_graph, \
         patch("app.api.routes_ask.get_checkpointer") as mock_checkpointer, \
         patch("app.api.routes_ask.create_session") as mock_create_session:
        
        mock_create_session.return_value = "session:123"
        
        mock_state = {
            "messages": [],
            "final_answer": "Machine learning is a subset of AI...",
            "search_results": [{"title": "Paper 1", "paper_id": "paper:1"}],
            "graph_results": [],
            "citation_path": []
        }
        
        mock_graph_instance = AsyncMock()
        mock_graph_instance.ainvoke = AsyncMock(return_value=mock_state)
        mock_graph.return_value = mock_graph_instance
        
        response = await async_client.post(
            "/api/ask",
            json={"question": "What is machine learning?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["answer"] == "Machine learning is a subset of AI..."


@pytest.mark.asyncio
async def test_ask_endpoint_creates_session(async_client, seeded_db):
    """POST /api/ask without session_id should create a new session."""
    with patch("app.api.routes_ask.create_agent_graph") as mock_graph, \
         patch("app.api.routes_ask.get_checkpointer") as mock_checkpointer, \
         patch("app.api.routes_ask.create_session") as mock_create_session:
        
        mock_create_session.return_value = "session:new123"
        
        mock_state = {
            "messages": [],
            "final_answer": "Answer",
            "search_results": [],
            "graph_results": [],
            "citation_path": []
        }
        
        mock_graph_instance = AsyncMock()
        mock_graph_instance.ainvoke = AsyncMock(return_value=mock_state)
        mock_graph.return_value = mock_graph_instance
        
        response = await async_client.post(
            "/api/ask",
            json={"question": "Test question"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session:new123"
        mock_create_session.assert_called_once()


@pytest.mark.asyncio
async def test_ask_endpoint_resumes_session(async_client, seeded_db):
    """POST /api/ask with session_id should load previous context."""
    with patch("app.api.routes_ask.create_agent_graph") as mock_graph, \
         patch("app.api.routes_ask.get_checkpointer") as mock_checkpointer, \
         patch("app.api.routes_ask.get_session") as mock_get_session:
        
        mock_get_session.return_value = {"id": "session:existing", "user_id": "user:1"}
        
        mock_state = {
            "messages": [],
            "final_answer": "Answer",
            "search_results": [],
            "graph_results": [],
            "citation_path": []
        }
        
        mock_graph_instance = AsyncMock()
        mock_graph_instance.ainvoke = AsyncMock(return_value=mock_state)
        mock_graph.return_value = mock_graph_instance
        
        response = await async_client.post(
            "/api/ask",
            json={"question": "Follow-up question", "session_id": "session:existing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session:existing"


@pytest.mark.asyncio
async def test_ingest_pdf_endpoint(async_client):
    """POST /api/ingest/pdf should ingest paper and return paper_id."""
    with patch("app.api.routes_ingest.IngestionPipeline") as mock_pipeline:
        mock_instance = AsyncMock()
        mock_instance.ingest_pdf = AsyncMock(return_value=MagicMock(
            paper_id="paper:123",
            status="success",
            nodes_created=10,
            edges_created=15,
            error=None
        ))
        mock_pipeline.return_value = mock_instance
        
        files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        response = await async_client.post("/api/ingest/pdf", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == "paper:123"
        assert data["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_arxiv_endpoint(async_client):
    """POST /api/ingest/arxiv should ingest paper and return paper_id."""
    with patch("app.api.routes_ingest.IngestionPipeline") as mock_pipeline:
        mock_instance = AsyncMock()
        mock_instance.ingest_arxiv = AsyncMock(return_value=MagicMock(
            paper_id="paper:456",
            status="success",
            nodes_created=8,
            edges_created=12,
            error=None
        ))
        mock_pipeline.return_value = mock_instance
        
        response = await async_client.post(
            "/api/ingest/arxiv",
            json={"arxiv_id": "2401.00001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == "paper:456"
        assert data["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_semantic_scholar_endpoint(async_client):
    """POST /api/ingest/semantic-scholar should ingest paper and return paper_id."""
    with patch("app.api.routes_ingest.IngestionPipeline") as mock_pipeline:
        mock_instance = AsyncMock()
        mock_instance.ingest_semantic_scholar = AsyncMock(return_value=MagicMock(
            paper_id="paper:789",
            status="success",
            nodes_created=6,
            edges_created=10,
            error=None
        ))
        mock_pipeline.return_value = mock_instance
        
        response = await async_client.post(
            "/api/ingest/semantic-scholar",
            json={"paper_id": "12345678"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == "paper:789"
        assert data["status"] == "success"


@pytest.mark.asyncio
async def test_graph_stats_endpoint(async_client, seeded_db):
    """GET /api/graph/stats should return counts."""
    with patch("app.api.routes_graph.SurrealDBManager") as mock_db:
        mock_manager = MagicMock()
        mock_manager.execute = AsyncMock(return_value=[
            {"count": 10}, {"count": 20}, {"count": 5}, {"count": 30}
        ])
        mock_db.return_value = mock_manager
        
        response = await async_client.get("/api/graph/stats")
        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert "authors" in data
        assert "topics" in data
        assert "edges" in data


@pytest.mark.asyncio
async def test_citation_path_endpoint(async_client, seeded_db):
    """GET /api/citation-path should return path between papers."""
    with patch("app.api.routes_citation.CitationPathTool") as mock_tool:
        mock_instance = AsyncMock()
        mock_instance._arun = AsyncMock(return_value={
            "path": [
                {"id": "paper:1", "title": "Paper A"},
                {"id": "paper:2", "title": "Paper B"}
            ]
        })
        mock_tool.return_value = mock_instance
        
        response = await async_client.get(
            "/api/citation-path?paper_a=Paper+A&paper_b=Paper+B"
        )
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert len(data["path"]) == 2


@pytest.mark.asyncio
async def test_get_paper_with_relations_endpoint(async_client, seeded_db):
    """GET /api/graph/paper/{id} should return paper with relations."""
    with patch("app.api.routes_graph.SurrealDBManager") as mock_db:
        mock_manager = MagicMock()
        mock_manager.execute = AsyncMock(side_effect=[
            [{"id": "paper:1", "title": "Test Paper"}],
            [{"id": "author:1", "name": "Alice"}],
            [{"id": "topic:1", "name": "ML"}],
            [{"id": "paper:2", "title": "Cited Paper"}]
        ])
        mock_db.return_value = mock_manager
        
        response = await async_client.get("/api/graph/paper/paper:1")
        assert response.status_code == 200
        data = response.json()
        assert "paper" in data
        assert "authors" in data
        assert "topics" in data
        assert "citations" in data


@pytest.mark.asyncio
async def test_session_crud(async_client):
    """Session create → get → list should work."""
    with patch("app.api.routes_sessions.create_session") as mock_create, \
         patch("app.api.routes_sessions.get_session") as mock_get, \
         patch("app.api.routes_sessions.list_sessions") as mock_list:
        
        from datetime import datetime
        
        mock_create.return_value = "session:123"
        mock_get.return_value = {
            "id": "session:123",
            "user_id": "user:1",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "queries": [],
            "papers_explored": []
        }
        mock_list.return_value = [mock_get.return_value]
        
        create_response = await async_client.post(
            "/api/sessions",
            json={"user_id": "user:1"}
        )
        assert create_response.status_code == 200
        create_data = create_response.json()
        assert "id" in create_data
        session_id = create_data["id"]
        
        get_response = await async_client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == session_id
        
        list_response = await async_client.get("/api/sessions?user_id=user:1")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert "sessions" in list_data
        assert len(list_data["sessions"]) == 1
