"""Unit tests for embedding generation module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.models.domain import Chunk
from app.ingestion.embeddings import EmbeddingService


def test_embedding_service_returns_vectors(mock_embeddings):
    """EmbeddingService should return float vectors for text chunks."""
    service = EmbeddingService(embeddings=mock_embeddings)
    
    chunks = [
        Chunk(content="First chunk", index=0),
        Chunk(content="Second chunk", index=1),
    ]
    
    result = service.embed_chunks(chunks)
    
    assert len(result) == 2
    assert result[0].embedding is not None
    assert result[1].embedding is not None
    assert len(result[0].embedding) == 1536
    assert len(result[1].embedding) == 1536
    assert all(isinstance(x, float) for x in result[0].embedding)
    assert result[0].content == "First chunk"
    assert result[1].content == "Second chunk"


def test_embedding_service_batches_requests(mock_embeddings):
    """Large chunk lists should be processed in batches."""
    service = EmbeddingService(embeddings=mock_embeddings, batch_size=2)
    
    chunks = [
        Chunk(content=f"Chunk {i}", index=i)
        for i in range(5)
    ]
    
    result = service.embed_chunks(chunks)
    
    assert len(result) == 5
    assert mock_embeddings.embed_documents.call_count == 3
    assert len(mock_embeddings.embed_documents.call_args_list[0][0][0]) == 2
    assert len(mock_embeddings.embed_documents.call_args_list[1][0][0]) == 2
    assert len(mock_embeddings.embed_documents.call_args_list[2][0][0]) == 1


def test_embedding_vector_dimensions(mock_embeddings):
    """Embeddings should be 1536-dimensional for text-embedding-3-small."""
    service = EmbeddingService(embeddings=mock_embeddings)
    
    chunks = [Chunk(content="Test chunk", index=0)]
    
    result = service.embed_chunks(chunks)
    
    assert len(result) == 1
    assert result[0].embedding is not None
    assert len(result[0].embedding) == 1536


def test_embedding_service_preserves_metadata(mock_embeddings):
    """EmbeddingService should preserve chunk metadata."""
    service = EmbeddingService(embeddings=mock_embeddings)
    
    chunks = [
        Chunk(
            content="Test chunk",
            index=0,
            metadata={"paper_id": "paper:123", "page": 1}
        )
    ]
    
    result = service.embed_chunks(chunks)
    
    assert result[0].metadata == {"paper_id": "paper:123", "page": 1}
    assert result[0].index == 0


def test_embedding_service_handles_empty_chunks(mock_embeddings):
    """EmbeddingService should handle empty chunk list."""
    service = EmbeddingService(embeddings=mock_embeddings)
    
    result = service.embed_chunks([])
    
    assert result == []
    mock_embeddings.embed_documents.assert_not_called()
