"""Unit tests for SurrealDB connection module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.asyncio
async def test_surreal_manager_connects():
    """Manager should establish connection to SurrealDB."""
    from app.db.connection import SurrealDBManager
    
    with patch("app.db.connection.Surreal") as mock_surreal:
        mock_instance = Mock()
        mock_instance.connect = AsyncMock()
        mock_surreal.return_value = mock_instance
        
        manager = SurrealDBManager(
            url="ws://localhost:8000/rpc",
            user="root",
            password="root",
            namespace="test",
            database="test",
        )
        
        await manager.connect()
        
        mock_instance.connect.assert_called_once()


@pytest.mark.asyncio
async def test_surreal_manager_health_check():
    """Health check should return True when connected."""
    from app.db.connection import SurrealDBManager
    
    with patch("app.db.connection.Surreal") as mock_surreal:
        mock_instance = Mock()
        mock_instance.connect = AsyncMock()
        mock_instance.query = AsyncMock(return_value=[{"result": [{"status": "ok"}]}])
        mock_surreal.return_value = mock_instance
        
        manager = SurrealDBManager(
            url="ws://localhost:8000/rpc",
            user="root",
            password="root",
            namespace="test",
            database="test",
        )
        
        await manager.connect()
        is_healthy = await manager.health_check()
        
        assert is_healthy is True


@pytest.mark.asyncio
async def test_surreal_manager_reconnects_on_failure():
    """Manager should retry connection on transient failures."""
    from app.db.connection import SurrealDBManager
    
    with patch("app.db.connection.Surreal") as mock_surreal:
        mock_instance = Mock()
        # First call fails, second succeeds
        mock_instance.connect = AsyncMock(side_effect=[Exception("Connection failed"), None])
        mock_surreal.return_value = mock_instance
        
        manager = SurrealDBManager(
            url="ws://localhost:8000/rpc",
            user="root",
            password="root",
            namespace="test",
            database="test",
        )
        
        # Should handle retry logic
        try:
            await manager.connect()
        except Exception:
            pass  # Expected on first attempt
        
        # Retry should succeed
        await manager.connect()


@pytest.mark.asyncio
async def test_surreal_manager_executes_query():
    """Manager should execute SurrealQL queries and return results."""
    from app.db.connection import SurrealDBManager
    
    with patch("app.db.connection.Surreal") as mock_surreal:
        mock_instance = Mock()
        mock_instance.connect = AsyncMock()
        mock_instance.query = AsyncMock(return_value=[{"result": [{"id": "paper:1", "title": "Test"}]}])
        mock_surreal.return_value = mock_instance
        
        manager = SurrealDBManager(
            url="ws://localhost:8000/rpc",
            user="root",
            password="root",
            namespace="test",
            database="test",
        )
        
        await manager.connect()
        result = await manager.execute("SELECT * FROM paper LIMIT 1")
        
        assert result == [{"id": "paper:1", "title": "Test"}]
        mock_instance.query.assert_called_once()


@pytest.mark.asyncio
async def test_surreal_manager_disconnect():
    """Manager should disconnect cleanly."""
    from app.db.connection import SurrealDBManager
    
    with patch("app.db.connection.Surreal") as mock_surreal:
        mock_instance = Mock()
        mock_instance.connect = AsyncMock()
        mock_instance.close = AsyncMock()
        mock_surreal.return_value = mock_instance
        
        manager = SurrealDBManager(
            url="ws://localhost:8000/rpc",
            user="root",
            password="root",
            namespace="test",
            database="test",
        )
        
        await manager.connect()
        await manager.disconnect()
        
        mock_instance.close.assert_called_once()
