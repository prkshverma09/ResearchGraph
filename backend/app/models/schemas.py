"""Pydantic request/response schemas for FastAPI endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class IngestPDFRequest(BaseModel):
    """Request schema for PDF ingestion (file upload handled separately)."""
    pass


class IngestArxivRequest(BaseModel):
    """Request schema for arXiv ingestion."""
    arxiv_id: str = Field(..., description="arXiv paper ID (e.g., '2401.00001')")


class IngestSemanticScholarRequest(BaseModel):
    """Request schema for Semantic Scholar ingestion."""
    paper_id: str = Field(..., description="Semantic Scholar paper ID")


class IngestionResponse(BaseModel):
    """Response schema for ingestion endpoints."""
    paper_id: str
    status: str
    nodes_created: int = 0
    edges_created: int = 0
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """Request schema for vector similarity search."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return")


class PaperSearchResult(BaseModel):
    """Single paper result from search."""
    title: str
    abstract: str
    paper_id: str
    relevance_score: float


class SearchResponse(BaseModel):
    """Response schema for search endpoint."""
    papers: List[PaperSearchResult]


class AskRequest(BaseModel):
    """Request schema for asking the research agent."""
    question: str = Field(..., description="User's research question")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation continuity")


class AskResponse(BaseModel):
    """Response schema for ask endpoint."""
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="List of source papers/references")
    graph_paths: List[List[Dict[str, Any]]] = Field(default_factory=list, description="Citation paths found")
    session_id: str


class CitationPathRequest(BaseModel):
    """Request schema for citation path endpoint (query params)."""
    paper_a: str = Field(..., description="Title or ID of first paper")
    paper_b: str = Field(..., description="Title or ID of second paper")


class CitationPathResponse(BaseModel):
    """Response schema for citation path endpoint."""
    path: List[Dict[str, Any]] = Field(default_factory=list, description="List of papers in the citation path")
    message: Optional[str] = None


class PaperWithRelations(BaseModel):
    """Paper with its relations."""
    paper: Dict[str, Any]
    authors: List[Dict[str, Any]] = Field(default_factory=list)
    topics: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)


class GraphStatsResponse(BaseModel):
    """Response schema for graph statistics."""
    papers: int = 0
    authors: int = 0
    topics: int = 0
    edges: int = 0


class CreateSessionRequest(BaseModel):
    """Request schema for creating a session."""
    user_id: str = Field(..., description="User identifier")


class SessionResponse(BaseModel):
    """Response schema for session endpoints."""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    queries: List[str] = Field(default_factory=list)
    papers_explored: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ListSessionsResponse(BaseModel):
    """Response schema for listing sessions."""
    sessions: List[SessionResponse]


class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    db_connected: bool
