"""Persistent session management for LangGraph agent using SurrealDB."""

import logging
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from langgraph_checkpoint_surrealdb import SurrealSaver

from app.config import settings
from app.db.connection import SurrealDBManager

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a session is not found."""
    pass


_checkpointer_instance: Optional[SurrealSaver] = None


def get_checkpointer() -> Union[SurrealSaver, None]:
    """Get or create the SurrealSaver checkpointer instance.
    
    Returns:
        SurrealSaver instance configured with settings, or None if checkpointing is disabled
    """
    if not settings.enable_checkpointing:
        logger.info("Checkpointing is disabled (enable_checkpointing=False)")
        return None
    
    global _checkpointer_instance
    
    if _checkpointer_instance is None:
        _checkpointer_instance = SurrealSaver(
            url=settings.surrealdb_url,
            user=settings.surrealdb_user,
            password=settings.surrealdb_password,
            namespace=settings.surrealdb_namespace,
            database=settings.surrealdb_database,
        )
        logger.info("Initialized SurrealSaver checkpointer")
    
    return _checkpointer_instance


async def create_session(
    user_id: str,
    db_manager: Optional[SurrealDBManager] = None,
) -> str:
    """Create a new session for a user.
    
    Args:
        user_id: User identifier
        db_manager: Optional SurrealDBManager instance (creates new if not provided)
        
    Returns:
        Session ID (e.g., "session:123")
    """
    if db_manager is None:
        db_manager = SurrealDBManager()
        await db_manager.connect()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        query = """
            CREATE session SET
                user_id = $user_id,
                created_at = time::now(),
                updated_at = time::now(),
                queries = [],
                papers_explored = [],
                notes = NONE
            RETURN id
        """
        
        result = await db_manager.execute(query, {"user_id": user_id})
        
        if not result or len(result) == 0:
            raise RuntimeError("Failed to create session")
        
        session_id = result[0].get("id")
        # Convert RecordID to string if needed
        if hasattr(session_id, '__str__'):
            session_id = str(session_id)
        if not session_id:
            raise RuntimeError("Session created but no ID returned")
        
        logger.info(f"Created session {session_id} for user {user_id}")
        return session_id
    finally:
        if should_disconnect:
            await db_manager.disconnect()


async def get_session(
    session_id: str,
    db_manager: Optional[SurrealDBManager] = None,
) -> Dict[str, Any]:
    """Get session data by session ID.
    
    Args:
        session_id: Session identifier (e.g., "session:123")
        db_manager: Optional SurrealDBManager instance (creates new if not provided)
        
    Returns:
        Session data dictionary
        
    Raises:
        NotFoundError: If session does not exist
    """
    if db_manager is None:
        db_manager = SurrealDBManager()
        await db_manager.connect()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        query = f"SELECT * FROM {session_id}"
        
        result = await db_manager.execute(query)
        
        if not result or len(result) == 0:
            raise NotFoundError(f"Session {session_id} not found")
        
        session_data = result[0]
        # Convert RecordID to string if needed
        if 'id' in session_data and hasattr(session_data['id'], '__str__'):
            session_data['id'] = str(session_data['id'])
        
        return session_data
    finally:
        if should_disconnect:
            await db_manager.disconnect()


async def list_sessions(
    user_id: str,
    db_manager: Optional[SurrealDBManager] = None,
) -> List[Dict[str, Any]]:
    """List all sessions for a user.
    
    Args:
        user_id: User identifier
        db_manager: Optional SurrealDBManager instance (creates new if not provided)
        
    Returns:
        List of session dictionaries
    """
    if db_manager is None:
        db_manager = SurrealDBManager()
        await db_manager.connect()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        query = """
            SELECT id, user_id, created_at, updated_at, queries, papers_explored, notes
            FROM session
            WHERE user_id = $user_id
            ORDER BY created_at DESC
        """
        
        result = await db_manager.execute(query, {"user_id": user_id})
        
        # Convert RecordID to string for all sessions
        sessions = []
        for session in (result if result else []):
            session_data = dict(session)
            if 'id' in session_data and hasattr(session_data['id'], '__str__'):
                session_data['id'] = str(session_data['id'])
            sessions.append(session_data)
        
        return sessions
    finally:
        if should_disconnect:
            await db_manager.disconnect()


async def update_session_papers(
    session_id: str,
    paper_ids: List[str],
    db_manager: Optional[SurrealDBManager] = None,
) -> None:
    """Update the papers_explored field for a session.
    
    Args:
        session_id: Session identifier
        paper_ids: List of paper IDs to add to explored papers
        db_manager: Optional SurrealDBManager instance (creates new if not provided)
    """
    if db_manager is None:
        db_manager = SurrealDBManager()
        await db_manager.connect()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        current_session = await get_session(session_id, db_manager=db_manager)
        existing_papers = current_session.get("papers_explored", []) or []
        
        existing_paper_ids = set()
        for p in existing_papers:
            if isinstance(p, dict):
                existing_paper_ids.add(p.get("id", str(p)))
            elif isinstance(p, str):
                existing_paper_ids.add(p)
            else:
                existing_paper_ids.add(str(p))
        
        new_paper_ids = [pid for pid in paper_ids if pid not in existing_paper_ids]
        
        if new_paper_ids:
            all_paper_ids = list(existing_paper_ids) + new_paper_ids
            
            query = f"""
                UPDATE {session_id} SET
                    papers_explored = $all_papers,
                    updated_at = time::now()
            """
            
            await db_manager.execute(query, {
                "all_papers": all_paper_ids,
            })
            
            logger.info(f"Updated session {session_id} with {len(new_paper_ids)} new papers")
    finally:
        if should_disconnect:
            await db_manager.disconnect()


async def add_query_to_session(
    session_id: str,
    query: str,
    db_manager: Optional[SurrealDBManager] = None,
) -> None:
    """Add a query to the session's query history.
    
    Args:
        session_id: Session identifier
        query: Query string to add
        db_manager: Optional SurrealDBManager instance (creates new if not provided)
    """
    if db_manager is None:
        db_manager = SurrealDBManager()
        await db_manager.connect()
        should_disconnect = True
    else:
        should_disconnect = False
    
    try:
        current_session = await get_session(session_id, db_manager=db_manager)
        existing_queries = current_session.get("queries", []) or []
        
        query_sql = f"""
            UPDATE {session_id} SET
                queries = $all_queries,
                updated_at = time::now()
        """
        
        all_queries = existing_queries + [query]
        
        await db_manager.execute(query_sql, {
            "all_queries": all_queries,
        })
    finally:
        if should_disconnect:
            await db_manager.disconnect()


def get_langgraph_config(session_id: str) -> Dict[str, Any]:
    """Get LangGraph configuration with session_id as thread_id.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Configuration dictionary for LangGraph invocations
    """
    return {"configurable": {"thread_id": session_id}}
