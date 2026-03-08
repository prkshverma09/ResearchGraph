"""Unit tests for deterministic hybrid retriever."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.retrieval.hybrid import HybridRetriever, RetrievalCandidate


def test_keywords_are_normalized_and_deduplicated():
    retriever = HybridRetriever(db_manager=Mock())
    keywords = retriever._keywords("LLMs trained to censor politically sensitive topics topics")
    assert keywords[0] == "llms"
    assert "topics" in keywords
    assert keywords.count("topics") == 1


def test_query_variants_include_compact_keyword_form():
    retriever = HybridRetriever(db_manager=Mock())
    keywords = retriever._keywords("llms trained to censor politically sensitive topics")
    variants = retriever._query_variants("llms trained to censor politically sensitive topics", keywords)
    assert len(variants) >= 2
    assert variants[0] == "llms trained to censor politically sensitive topics"


@pytest.mark.asyncio
async def test_retrieve_fuses_vector_lexical_and_graph_candidates():
    retriever = HybridRetriever(db_manager=Mock())
    retriever._multi_query_vector_candidates = AsyncMock(
        return_value=[
            RetrievalCandidate(
                source="vector",
                score=0.9,
                content="Chunk A",
                metadata={"paper_id": "paper:1", "title": "Paper 1"},
            )
        ]
    )
    retriever._chunk_lexical_candidates = AsyncMock(
        return_value=[
            RetrievalCandidate(
                source="lexical_chunk",
                score=2.0,
                content="Chunk A",
                metadata={"paper_id": "paper:1", "title": "Paper 1"},
            )
        ]
    )
    retriever._paper_lexical_candidates = AsyncMock(
        return_value=[
            RetrievalCandidate(
                source="lexical_paper",
                score=1.0,
                content="Paper abstract",
                metadata={"paper_id": "paper:2", "title": "Paper 2"},
            )
        ]
    )
    retriever._topic_graph_expansion = AsyncMock(return_value=[])
    retriever._citation_graph_expansion = AsyncMock(return_value=[])

    result = await retriever.retrieve(
        query="politically sensitive topics",
        selected_paper_ids=["paper:1", "paper:2"],
        k=5,
    )

    assert "contexts" in result
    assert "debug" in result
    assert result["debug"]["vector_hits"] == 1
    assert result["debug"]["lexical_chunk_hits"] == 1
    assert result["debug"]["lexical_paper_hits"] == 1
    assert result["debug"]["graph_citation_hits"] == 0
    assert result["debug"]["selected_scope_applied"] is True
    assert len(result["contexts"]) >= 2
