"""API routes for citation path queries."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.agent.tools import CitationPathTool
from app.models.schemas import CitationPathResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/citation-path", response_model=CitationPathResponse)
async def get_citation_path(
    paper_a: str = Query(..., description="Title or ID of first paper"),
    paper_b: str = Query(..., description="Title or ID of second paper"),
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Find citation path between two papers.
    
    Args:
        paper_a: Title or ID of first paper
        paper_b: Title or ID of second paper
        db_manager: SurrealDB manager dependency
        
    Returns:
        CitationPathResponse with path list
    """
    try:
        citation_tool = CitationPathTool(db_manager=db_manager)
        result = await citation_tool._arun(paper_a_title=paper_a, paper_b_title=paper_b)
        
        path = result.get("path", [])
        message = result.get("message")
        
        return CitationPathResponse(path=path, message=message)
    except Exception as e:
        logger.error(f"Citation path error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find citation path: {str(e)}")
