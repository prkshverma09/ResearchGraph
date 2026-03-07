"""API routes for paper ingestion."""

import logging
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.ingestion.pipeline import IngestionPipeline
from app.models.schemas import (
    IngestArxivRequest,
    IngestSemanticScholarRequest,
    IngestionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])


@router.post("/pdf", response_model=IngestionResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    db: SurrealDBManager = Depends(get_db),
):
    """Upload and ingest a PDF file.
    
    Args:
        file: PDF file to upload
        db: SurrealDB manager dependency
        
    Returns:
        IngestionResponse with paper_id and status
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        pipeline = IngestionPipeline(db_manager=db)
        result = await pipeline.ingest_pdf(temp_file_path)
        
        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error or "Ingestion failed")
        
        return IngestionResponse(
            paper_id=result.paper_id,
            status=result.status,
            nodes_created=result.nodes_created,
            edges_created=result.edges_created,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post("/arxiv", response_model=IngestionResponse)
async def ingest_arxiv(
    request: IngestArxivRequest,
    db: SurrealDBManager = Depends(get_db),
):
    """Ingest a paper from arXiv by ID.
    
    Args:
        request: IngestArxivRequest with arxiv_id
        db: SurrealDB manager dependency
        
    Returns:
        IngestionResponse with paper_id and status
    """
    try:
        pipeline = IngestionPipeline(db_manager=db)
        result = await pipeline.ingest_arxiv(request.arxiv_id)
        
        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error or "Ingestion failed")
        
        return IngestionResponse(
            paper_id=result.paper_id,
            status=result.status,
            nodes_created=result.nodes_created,
            edges_created=result.edges_created,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"arXiv ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/semantic-scholar", response_model=IngestionResponse)
async def ingest_semantic_scholar(
    request: IngestSemanticScholarRequest,
    db: SurrealDBManager = Depends(get_db),
):
    """Ingest a paper from Semantic Scholar by ID.
    
    Args:
        request: IngestSemanticScholarRequest with paper_id
        db: SurrealDB manager dependency
        
    Returns:
        IngestionResponse with paper_id and status
    """
    try:
        pipeline = IngestionPipeline(db_manager=db)
        result = await pipeline.ingest_semantic_scholar(request.paper_id)
        
        if result.status == "error":
            raise HTTPException(status_code=500, detail=result.error or "Ingestion failed")
        
        return IngestionResponse(
            paper_id=result.paper_id,
            status=result.status,
            nodes_created=result.nodes_created,
            edges_created=result.edges_created,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic Scholar ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
