"""API routes for vector similarity search."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.ingestion.embeddings import VectorStoreService
from app.models.schemas import SearchRequest, SearchResponse, PaperSearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: SurrealDBManager = Depends(get_db),
):
    """Perform vector similarity search on paper chunks.
    
    Args:
        request: SearchRequest with query and top_k
        db: SurrealDB manager dependency
        
    Returns:
        SearchResponse with list of relevant papers
    """
    try:
        vector_store = VectorStoreService(db_manager=db)
        results = await vector_store.similarity_search_with_scores(
            request.query,
            k=request.top_k
        )
        
        papers = []
        for doc, score in results:
            papers.append(PaperSearchResult(
                title=doc.metadata.get("title", "Unknown"),
                abstract=doc.page_content[:500] if len(doc.page_content) > 500 else doc.page_content,
                paper_id=doc.metadata.get("paper_id", "unknown"),
                relevance_score=float(score),
            ))
        
        return SearchResponse(papers=papers)
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
