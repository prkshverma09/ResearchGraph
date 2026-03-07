"""Integration tests for deletion endpoints."""
import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.fixture
async def my_async_client():
    from app.main import app
    from app.dependencies import get_db
    
    # We will let each test override the dependency
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_delete_paper_endpoint(my_async_client):
    """DELETE /api/graph/paper/{paper_id} should delete chunk edges, chunks, and the paper."""
    from app.main import app
    from app.dependencies import get_db
    
    mock_manager = MagicMock()
    mock_manager.execute = AsyncMock(side_effect=[
        [{"out": "chunk:1"}, {"out": "chunk:2"}],  # fetch chunks
        None,  # delete chunk 1
        None,  # delete chunk 2
        None,  # delete paper
    ])
    
    app.dependency_overrides[get_db] = lambda: mock_manager
    
    response = await my_async_client.delete("/api/graph/paper/paper:test1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["paper_id"] == "paper:test1"
    assert mock_manager.execute.call_count == 4

@pytest.mark.asyncio
async def test_clear_database_endpoint(my_async_client):
    """DELETE /api/graph/clear should wipe all tables."""
    from app.main import app
    from app.dependencies import get_db
    
    mock_manager = MagicMock()
    mock_manager.execute = AsyncMock(return_value=None)
    
    app.dependency_overrides[get_db] = lambda: mock_manager
    
    response = await my_async_client.delete("/api/graph/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Cleared" in data["message"]
    assert mock_manager.execute.call_count == 11  # number of tables
