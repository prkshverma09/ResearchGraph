"""API routes for session management."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.agent.sessions import (
    create_session,
    get_session,
    list_sessions,
    NotFoundError,
)
from app.models.schemas import (
    CreateSessionRequest,
    SessionResponse,
    ListSessionsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_new_session(
    request: CreateSessionRequest,
    db: SurrealDBManager = Depends(get_db),
):
    """Create a new session.
    
    Args:
        request: CreateSessionRequest with user_id
        db: SurrealDB manager dependency
        
    Returns:
        SessionResponse with session data
    """
    try:
        session_id = await create_session(user_id=request.user_id, db_manager=db)
        session_data = await get_session(session_id, db_manager=db)
        
        return SessionResponse(**session_data)
    except Exception as e:
        logger.error(f"Create session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_by_id(
    session_id: str,
    db: SurrealDBManager = Depends(get_db),
):
    """Get a session by ID.
    
    Args:
        session_id: Session identifier
        db: SurrealDB manager dependency
        
    Returns:
        SessionResponse with session data
    """
    try:
        session_data = await get_session(session_id, db_manager=db)
        return SessionResponse(**session_data)
    except NotFoundError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        logger.error(f"Get session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.get("", response_model=ListSessionsResponse)
async def list_user_sessions(
    user_id: str = Query(..., description="User identifier"),
    db: SurrealDBManager = Depends(get_db),
):
    """List all sessions for a user.
    
    Args:
        user_id: User identifier
        db: SurrealDB manager dependency
        
    Returns:
        ListSessionsResponse with list of sessions
    """
    try:
        sessions = await list_sessions(user_id=user_id, db_manager=db)
        session_responses = [SessionResponse(**session) for session in sessions]
        return ListSessionsResponse(sessions=session_responses)
    except Exception as e:
        logger.error(f"List sessions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")
