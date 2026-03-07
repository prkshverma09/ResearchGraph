"""API routes for graph queries and statistics."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.agent.tools import CitationPathTool
from app.models.schemas import (
    PaperWithRelations,
    GraphStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/paper/{paper_id}", response_model=PaperWithRelations)
async def get_paper_with_relations(
    paper_id: str,
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Get a paper with its relations (authors, topics, citations).
    
    Args:
        paper_id: SurrealDB paper ID (e.g., "paper:123")
        db_manager: SurrealDB manager dependency
        
    Returns:
        PaperWithRelations with paper, authors, topics, and citations
    """
    try:
        # Optimized: Use a single query with graph traversal to fetch paper and relations
        combined_query = f"""
            SELECT 
                *,
                (SELECT ->authored_by->author.* FROM {paper_id}) AS authors,
                (SELECT ->belongs_to->topic.* FROM {paper_id}) AS topics,
                (SELECT ->cites->paper.* FROM {paper_id}) AS citations
            FROM {paper_id}
        """
        results = await db_manager.execute(combined_query)
        
        if not results or len(results) == 0:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        
        result = results[0]
        paper = {k: v for k, v in result.items() if k not in ['authors', 'topics', 'citations']}
        authors = result.get('authors', []) or []
        topics = result.get('topics', []) or []
        citations = result.get('citations', []) or []
        
        return PaperWithRelations(
            paper=paper,
            authors=authors if authors else [],
            topics=topics if topics else [],
            citations=citations if citations else [],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get paper: {str(e)}")


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Get graph statistics (counts of nodes and edges).
    
    Args:
        db_manager: SurrealDB manager dependency
        
    Returns:
        GraphStatsResponse with counts
    """
    try:
        papers_query = "SELECT COUNT() AS count FROM paper GROUP ALL"
        authors_query = "SELECT COUNT() AS count FROM author GROUP ALL"
        topics_query = "SELECT COUNT() AS count FROM topic GROUP ALL"
        
        papers_result = await db_manager.execute(papers_query)
        authors_result = await db_manager.execute(authors_query)
        topics_result = await db_manager.execute(topics_query)
        
        papers_count = papers_result[0].get("count", 0) if papers_result else 0
        authors_count = authors_result[0].get("count", 0) if authors_result else 0
        topics_count = topics_result[0].get("count", 0) if topics_result else 0
        
        # Count edges separately and sum them
        wrote_query = "SELECT COUNT() AS count FROM (SELECT ->wrote FROM paper GROUP ALL)"
        cites_query = "SELECT COUNT() AS count FROM (SELECT ->cites FROM paper GROUP ALL)"
        topics_query = "SELECT COUNT() AS count FROM (SELECT ->has_topic FROM paper GROUP ALL)"
        
        wrote_result = await db_manager.execute(wrote_query)
        cites_result = await db_manager.execute(cites_query)
        topics_result = await db_manager.execute(topics_query)
        
        wrote_count = wrote_result[0].get("count", 0) if wrote_result else 0
        cites_count = cites_result[0].get("count", 0) if cites_result else 0
        topics_count = topics_result[0].get("count", 0) if topics_result else 0
        edges_count = wrote_count + cites_count + topics_count
        
        return GraphStatsResponse(
            papers=papers_count,
            authors=authors_count,
            topics=topics_count,
            edges=edges_count,
        )
    except Exception as e:
        logger.error(f"Graph stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get graph stats: {str(e)}")
