"""Integration tests for vector store service."""

import pytest
from langchain_core.documents import Document
from app.models.domain import Chunk
from app.ingestion.embeddings import VectorStoreService


class _MockEmbeddings:
    async def aembed_query(self, query: str):
        return [0.1] * 1536


@pytest.mark.asyncio
async def test_vector_store_adds_documents(db_manager):
    """VectorStoreService should add documents to SurrealDB."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    await db_manager.query(
        "CREATE paper:test1 SET title = 'Test Paper 1', abstract = 'Test abstract 1'"
    )
    
    service = VectorStoreService(db_manager=db_manager)
    
    chunks_with_embeddings = [
        Chunk(
            content="First chunk about machine learning",
            index=0,
            embedding=[0.1] * 1536,
            metadata={"paper_id": "paper:test1"}
        ),
        Chunk(
            content="Second chunk about neural networks",
            index=1,
            embedding=[0.2] * 1536,
            metadata={"paper_id": "paper:test1"}
        ),
    ]
    
    paper_id = "paper:test1"
    await service.add_paper_chunks(paper_id, chunks_with_embeddings)
    
    result = await db_manager.query(
        "SELECT * FROM chunk WHERE paper_id = $paper_id OR metadata.paper_id = $paper_id",
        {"paper_id": "paper:test1"}
    )
    
    assert len(result) == 2


@pytest.mark.asyncio
async def test_vector_store_similarity_search(db_manager):
    """Similarity search should return relevant documents."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    await db_manager.query(
        "CREATE paper:test2 SET title = 'Test Paper 2', abstract = 'Test abstract 2'"
    )
    
    service = VectorStoreService(db_manager=db_manager, embeddings=_MockEmbeddings())
    
    chunks_with_embeddings = [
        Chunk(
            content="Machine learning is a subset of artificial intelligence",
            index=0,
            embedding=[0.1] * 1536,
            metadata={"paper_id": "paper:test2", "title": "ML Paper"}
        ),
        Chunk(
            content="Neural networks are computational models inspired by the brain",
            index=1,
            embedding=[0.2] * 1536,
            metadata={"paper_id": "paper:test2", "title": "ML Paper"}
        ),
    ]
    
    paper_id = "paper:test2"
    await service.add_paper_chunks(paper_id, chunks_with_embeddings)
    
    results = await service.similarity_search("artificial intelligence", k=2)
    
    assert len(results) > 0
    assert isinstance(results[0], Document)
    assert results[0].page_content is not None


@pytest.mark.asyncio
async def test_vector_store_returns_scores(db_manager):
    """Similarity search with scores should return (doc, score) tuples."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    await db_manager.query(
        "CREATE paper:test3 SET title = 'Test Paper 3', abstract = 'Test abstract 3'"
    )
    
    service = VectorStoreService(db_manager=db_manager, embeddings=_MockEmbeddings())
    
    chunks_with_embeddings = [
        Chunk(
            content="Deep learning uses neural networks with multiple layers",
            index=0,
            embedding=[0.1] * 1536,
            metadata={"paper_id": "paper:test3"}
        ),
    ]
    
    paper_id = "paper:test3"
    await service.add_paper_chunks(paper_id, chunks_with_embeddings)
    
    results = await service.similarity_search_with_scores("neural networks", k=1)
    
    assert len(results) > 0
    assert isinstance(results[0], tuple)
    assert len(results[0]) == 2
    assert isinstance(results[0][0], Document)
    assert isinstance(results[0][1], float)


@pytest.mark.asyncio
async def test_vector_store_creates_has_chunk_edges(db_manager):
    """VectorStoreService should create has_chunk edges between paper and chunks."""
    from app.db.schema import apply_schema
    
    await apply_schema(db_manager)
    
    await db_manager.query(
        "CREATE paper:test4 SET title = 'Test Paper', abstract = 'Test abstract'"
    )
    
    service = VectorStoreService(db_manager=db_manager)
    
    chunks_with_embeddings = [
        Chunk(
            content="Test chunk content",
            index=0,
            embedding=[0.1] * 1536,
            metadata={}
        ),
    ]
    
    paper_id = "paper:test4"
    await service.add_paper_chunks(paper_id, chunks_with_embeddings)
    
    result = await db_manager.query("SELECT * FROM has_chunk WHERE in = paper:test4")

    assert len(result) > 0


@pytest.mark.asyncio
async def test_vector_store_creates_mentions_topic_edges(db_manager):
    """Chunk-topic mention edges should be persisted for topical chunks."""
    from app.db.schema import apply_schema

    await apply_schema(db_manager)

    await db_manager.query(
        "CREATE paper:test5 SET title = 'Censorship Study', abstract = 'Test abstract'"
    )
    await db_manager.query("CREATE topic:test5_topic SET name = 'politically sensitive topics'")

    service = VectorStoreService(db_manager=db_manager)
    chunks_with_embeddings = [
        Chunk(
            content="The paper studies politically sensitive topics in llms.",
            index=0,
            embedding=[0.1] * 1536,
            metadata={},
        ),
    ]
    await service.add_paper_chunks("paper:test5", chunks_with_embeddings)
    await service.link_chunks_to_topics(
        paper_id="paper:test5",
        chunks_with_embeddings=chunks_with_embeddings,
        topics=["politically sensitive topics"],
    )

    result = await db_manager.query("SELECT * FROM mentions_topic")
    assert len(result) > 0
