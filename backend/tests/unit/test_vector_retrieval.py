"""Unit tests for vector retrieval behavior in VectorStoreService."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.ingestion.embeddings import VectorStoreService
from app.models.domain import Chunk


@pytest.mark.asyncio
async def test_similarity_search_with_scores_uses_bruteforce_for_scoped_queries():
    """Scoped retrieval should skip ANN and run brute-force cosine directly."""
    mock_db = Mock()
    mock_db.execute = AsyncMock(
        return_value=[
            {
                "content": "Matched chunk",
                "metadata": {"paper_id": "paper:1", "title": "Paper One"},
                "score": 0.91,
            }
        ]
    )
    mock_embeddings = Mock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.1] * 1536)

    service = VectorStoreService(db_manager=mock_db, embeddings=mock_embeddings)
    results = await service.similarity_search_with_scores(
        "test query",
        k=5,
        paper_ids=["paper:1"],
    )

    assert len(results) == 1
    assert results[0][0].metadata["paper_id"] == "paper:1"
    assert results[0][1] == 0.91
    assert mock_db.execute.call_count == 1

    fallback_query, fallback_params = mock_db.execute.call_args.args

    assert "embedding != NONE" in fallback_query
    assert "ORDER BY score DESC" in fallback_query
    assert fallback_params["paper_ids"] == ["paper:1"]


@pytest.mark.asyncio
async def test_similarity_search_with_scores_skips_fallback_when_ann_hits():
    """Service should not run fallback query when ANN already returns results."""
    mock_db = Mock()
    mock_db.execute = AsyncMock(
        return_value=[
            {
                "content": "ANN chunk",
                "metadata": {"paper_id": "paper:2", "title": "Paper Two"},
                "score": 0.99,
            }
        ]
    )
    mock_embeddings = Mock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.2] * 1536)

    service = VectorStoreService(db_manager=mock_db, embeddings=mock_embeddings)
    results = await service.similarity_search_with_scores("test query", k=3)

    assert len(results) == 1
    assert results[0][0].metadata["paper_id"] == "paper:2"
    assert mock_db.execute.call_count == 1
    query, _ = mock_db.execute.call_args.args
    assert "embedding <|3|> $query_embedding" in query


@pytest.mark.asyncio
async def test_similarity_search_with_scores_uses_keyword_fallback_when_vectors_empty():
    """Service should run lexical fallback when vector retrieval returns no rows."""
    mock_db = Mock()
    mock_db.execute = AsyncMock(
        side_effect=[
            [],
            [
                {
                    "content": "Politically sensitive topics in LLM censorship",
                    "metadata": {"paper_id": "paper:2", "title": "Paper Two"},
                    "search_score": 3,
                }
            ],
        ]
    )
    mock_embeddings = Mock()
    mock_embeddings.aembed_query = AsyncMock(return_value=[0.2] * 1536)

    service = VectorStoreService(db_manager=mock_db, embeddings=mock_embeddings)
    results = await service.similarity_search_with_scores(
        "llms trained to censor politically sensitive topics",
        k=3,
        paper_ids=["paper:2"],
    )

    assert len(results) == 1
    assert results[0][0].metadata["paper_id"] == "paper:2"
    assert mock_db.execute.call_count == 2
    keyword_query, keyword_params = mock_db.execute.call_args_list[1].args
    assert "search_score" in keyword_query
    assert keyword_params["paper_ids"] == ["paper:2"]


@pytest.mark.asyncio
async def test_link_chunks_to_topics_creates_mentions_edges():
    mock_db = Mock()
    mock_db.execute = AsyncMock(side_effect=[[], [], []])
    service = VectorStoreService(db_manager=mock_db, embeddings=Mock())

    linked = await service.link_chunks_to_topics(
        paper_id="paper:test",
        chunks_with_embeddings=[
            Chunk(
                content="This section studies politically sensitive topics in censored llms.",
                index=0,
                metadata={},
                embedding=[0.1] * 4,
            )
        ],
        topics=["politically sensitive topics"],
    )

    assert linked == 1
    assert mock_db.execute.call_count == 3
    relate_query = mock_db.execute.call_args_list[2].args[0]
    assert "mentions_topic" in relate_query
