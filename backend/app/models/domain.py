"""Domain models for ResearchGraph Assistant."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Paper(BaseModel):
    """Paper domain model."""
    title: str
    abstract: str
    year: Optional[int] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Author(BaseModel):
    """Author domain model."""
    name: str
    institution: Optional[str] = None


class Topic(BaseModel):
    """Topic domain model."""
    name: str


class Institution(BaseModel):
    """Institution domain model."""
    name: str
    country: Optional[str] = None


class ExtractedAuthor(BaseModel):
    """Extracted author with metadata."""
    name: str
    institution: Optional[str] = None


class ExtractedEntities(BaseModel):
    """Entities extracted from a paper."""
    title: str
    authors: List[ExtractedAuthor]
    topics: List[str]
    institutions: List[str]
    citations: List[str]  # Titles or IDs of cited papers
    year: Optional[int] = None
    venue: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)


class Chunk(BaseModel):
    """Text chunk with metadata."""
    content: str
    index: int
    metadata: dict = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class RawDocument(BaseModel):
    """Raw document from a loader."""
    text: str
    metadata: dict = Field(default_factory=dict)


class PaperIngestionResult(BaseModel):
    """Result of paper ingestion."""
    paper_id: str
    status: str  # "success" or "error"
    nodes_created: int = 0
    edges_created: int = 0
    semantic_counts: Optional[dict] = None
    full_counts: Optional[dict] = None
    error: Optional[str] = None
