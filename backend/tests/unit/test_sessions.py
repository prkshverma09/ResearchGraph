"""Unit tests for session management module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any


@pytest.mark.asyncio
async def test_create_session_returns_id():
    """create_session should return a unique session ID."""
    from app.agent.sessions import create_session
    
    with patch("app.agent.sessions.SurrealDBManager") as mock_db_class:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=[{"id": "session:test123"}])
        mock_db_class.return_value = mock_db
        
        session_id = await create_session("user123")
        
        assert session_id == "session:test123"
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args[0][0]
        assert "CREATE session" in call_args
        assert "user_id" in call_args


@pytest.mark.asyncio
async def test_get_session_returns_data(mock_db):
    """get_session should return session data for a valid ID."""
    from app.agent.sessions import get_session
    
    mock_session_data = {
        "id": "session:test123",
        "user_id": "user123",
        "created_at": datetime.now(),
        "queries": ["query1", "query2"],
        "papers_explored": [],
        "notes": None,
    }
    
    mock_db.execute = AsyncMock(return_value=[mock_session_data])
    
    session_data = await get_session("session:test123", mock_db)
    
    assert session_data["id"] == "session:test123"
    assert session_data["user_id"] == "user123"
    assert session_data["queries"] == ["query1", "query2"]
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_session_raises_for_invalid_id(mock_db):
    """get_session should raise NotFoundError for invalid session."""
    from app.agent.sessions import get_session, NotFoundError
    
    mock_db.execute = AsyncMock(return_value=[])
    
    with pytest.raises(NotFoundError, match="Session.*not found"):
        await get_session("session:invalid", mock_db)


@pytest.mark.asyncio
async def test_list_sessions_returns_user_sessions(mock_db):
    """list_sessions should return all sessions for a user."""
    from app.agent.sessions import list_sessions
    
    mock_sessions = [
        {
            "id": "session:1",
            "user_id": "user123",
            "created_at": datetime.now(),
            "queries": ["query1"],
        },
        {
            "id": "session:2",
            "user_id": "user123",
            "created_at": datetime.now(),
            "queries": ["query2", "query3"],
        },
    ]
    
    mock_db.execute = AsyncMock(return_value=mock_sessions)
    
    sessions = await list_sessions("user123", mock_db)
    
    assert len(sessions) == 2
    assert sessions[0]["id"] == "session:1"
    assert sessions[1]["id"] == "session:2"
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0][0]
    assert "SELECT" in call_args
    assert "user_id" in call_args


@pytest.mark.asyncio
async def test_get_checkpointer_initializes_surreal_saver():
    """get_checkpointer should initialize and return SurrealSaver instance."""
    from app.agent.sessions import get_checkpointer
    from langgraph.checkpoint.surrealdb import SurrealSaver
    
    with patch("app.agent.sessions.SurrealSaver") as mock_surreal_saver_class:
        mock_checkpointer = Mock()
        mock_surreal_saver_class.return_value = mock_checkpointer
        
        checkpointer = get_checkpointer()
        
        assert checkpointer == mock_checkpointer
        mock_surreal_saver_class.assert_called_once()
        call_kwargs = mock_surreal_saver_class.call_args[1]
        assert "url" in call_kwargs
        assert "user" in call_kwargs
        assert "password" in call_kwargs
        assert "namespace" in call_kwargs
        assert "database" in call_kwargs


@pytest.mark.asyncio
async def test_create_session_stores_in_database(mock_db):
    """create_session should store session data in SurrealDB."""
    from app.agent.sessions import create_session
    
    mock_db.execute = AsyncMock(return_value=[{"id": "session:new123"}])
    
    session_id = await create_session("user456", db_manager=mock_db)
    
    assert session_id == "session:new123"
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args[0][0]
    assert "CREATE session" in call_args.upper()
    assert "user_id" in call_args.lower()


@pytest.mark.asyncio
async def test_get_session_handles_missing_fields(mock_db):
    """get_session should handle sessions with missing optional fields."""
    from app.agent.sessions import get_session
    
    mock_session_data = {
        "id": "session:minimal",
        "user_id": "user123",
        "created_at": datetime.now(),
    }
    
    mock_db.execute = AsyncMock(return_value=[mock_session_data])
    
    session_data = await get_session("session:minimal", mock_db)
    
    assert session_data["id"] == "session:minimal"
    assert "queries" not in session_data or session_data.get("queries") is None


@pytest.fixture
def mock_db():
    """Mock SurrealDBManager for unit tests."""
    mock = AsyncMock()
    mock.execute = AsyncMock()
    return mock
