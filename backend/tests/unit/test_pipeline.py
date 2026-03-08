"""Unit tests for ingestion pipeline."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.asyncio
async def test_pipeline_orchestrates_all_steps():
    """Pipeline should call loader → chunker → extractor → embedder → graph_builder."""
    from app.ingestion.pipeline import IngestionPipeline
    from app.models.domain import RawDocument, Chunk, ExtractedEntities, ExtractedAuthor
    
    # Mock all dependencies
    mock_loader = Mock()
    mock_loader.load = Mock(return_value=RawDocument(
        text="Test paper abstract",
        metadata={"title": "Test Paper"}
    ))
    
    mock_chunker = Mock()
    mock_chunker.chunk = Mock(return_value=[
        Chunk(content="Test paper abstract", index=0, metadata={})
    ])
    
    mock_extractor = Mock()
    mock_extractor.extract = AsyncMock(return_value=ExtractedEntities(
        title="Test Paper",
        authors=[ExtractedAuthor(name="Alice", institution="MIT")],
        topics=["ML"],
        institutions=["MIT"],
        citations=[],
        year=2024,
    ))
    
    mock_embedder = Mock()
    mock_embedder.embed_chunks = Mock(return_value=[
        Chunk(content="Test", index=0, metadata={}, embedding=[0.1] * 1536)
    ])
    
    mock_graph_builder = Mock()
    mock_graph_builder.persist_graph = AsyncMock(return_value="paper:123")
    
    mock_vector_store = Mock()
    mock_vector_store.add_paper_chunks = AsyncMock()
    mock_vector_store.link_chunks_to_topics = AsyncMock(return_value=1)

    mock_db_manager = Mock()
    mock_db_manager.execute = AsyncMock(return_value=[])
    
    pipeline = IngestionPipeline(
        db_manager=mock_db_manager,
        loader=mock_loader,
        chunker=mock_chunker,
        extractor=mock_extractor,
        embedder=mock_embedder,
        graph_builder=mock_graph_builder,
        vector_store=mock_vector_store,
    )
    
    result = await pipeline.ingest_pdf("test.pdf")
    
    # Verify all steps were called
    mock_loader.load.assert_called_once()
    mock_chunker.chunk.assert_called_once()
    mock_extractor.extract.assert_called_once()
    mock_embedder.embed_chunks.assert_called_once()
    mock_graph_builder.persist_graph.assert_called_once()
    mock_vector_store.add_paper_chunks.assert_called_once()
    mock_vector_store.link_chunks_to_topics.assert_called_once()
    
    assert result.status == "success"
    assert result.paper_id == "paper:123"


@pytest.mark.asyncio
async def test_pipeline_returns_result():
    """Pipeline should return PaperIngestionResult with paper_id."""
    from app.ingestion.pipeline import IngestionPipeline
    from app.models.domain import RawDocument, Chunk, ExtractedEntities, ExtractedAuthor
    
    # Setup mocks
    with patch("app.ingestion.pipeline.PDFLoader") as mock_loader_class, \
         patch("app.ingestion.pipeline.TextChunker") as mock_chunker_class, \
         patch("app.ingestion.pipeline.EntityExtractor") as mock_extractor_class, \
         patch("app.ingestion.pipeline.EmbeddingService") as mock_embedder_class, \
         patch("app.ingestion.pipeline.persist_graph", new_callable=AsyncMock) as mock_persist, \
         patch("app.ingestion.pipeline.VectorStoreService") as mock_vector_class:
        
        mock_persist.return_value = "paper:456"

        mock_loader = Mock()
        mock_loader.load = Mock(return_value=RawDocument(text="Test", metadata={}))
        mock_loader_class.return_value = mock_loader
        
        mock_chunker = Mock()
        mock_chunker.chunk = Mock(return_value=[Chunk(content="Test", index=0)])
        mock_chunker_class.return_value = mock_chunker
        
        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(return_value=ExtractedEntities(
            title="Test",
            authors=[],
            topics=[],
            institutions=[],
            citations=[],
        ))
        mock_extractor_class.return_value = mock_extractor
        
        mock_embedder = Mock()
        mock_embedder.embed_chunks = Mock(return_value=[
            Chunk(content="Test", index=0, embedding=[0.1] * 1536)
        ])
        mock_embedder_class.return_value = mock_embedder
        
        mock_vector = Mock()
        mock_vector.add_paper_chunks = AsyncMock()
        mock_vector.link_chunks_to_topics = AsyncMock(return_value=0)
        mock_vector_class.return_value = mock_vector
        
        mock_db = Mock()
        mock_db.execute = AsyncMock(return_value=[])
        
        pipeline = IngestionPipeline(mock_db)
        result = await pipeline.ingest_pdf("test.pdf")
        
        assert result.status == "success"
        assert result.paper_id == "paper:456"


@pytest.mark.asyncio
async def test_pipeline_handles_extraction_failure():
    """Pipeline should report error when entity extraction fails."""
    from app.ingestion.pipeline import IngestionPipeline
    from app.models.domain import RawDocument, Chunk
    
    with patch("app.ingestion.pipeline.PDFLoader") as mock_loader_class, \
         patch("app.ingestion.pipeline.TextChunker") as mock_chunker_class, \
         patch("app.ingestion.pipeline.EntityExtractor") as mock_extractor_class:
        
        mock_loader = Mock()
        mock_loader.load = Mock(return_value=RawDocument(text="Test", metadata={}))
        mock_loader_class.return_value = mock_loader
        
        mock_chunker = Mock()
        mock_chunker.chunk = Mock(return_value=[Chunk(content="Test", index=0)])
        mock_chunker_class.return_value = mock_chunker
        
        mock_extractor = Mock()
        mock_extractor.extract = AsyncMock(side_effect=Exception("Extraction failed"))
        mock_extractor_class.return_value = mock_extractor
        
        mock_db = Mock()
        
        pipeline = IngestionPipeline(mock_db)
        result = await pipeline.ingest_pdf("test.pdf")
        
        assert result.status == "error"
        assert result.error is not None
        assert "Extraction failed" in result.error


@pytest.mark.asyncio
async def test_pipeline_batch_continues_on_failure():
    """Batch ingestion should continue processing after one paper fails."""
    from app.ingestion.pipeline import IngestionPipeline
    
    mock_db = Mock()
    
    with patch("app.ingestion.pipeline.PDFLoader") as mock_loader_class:
        mock_loader = Mock()
        # First call succeeds, second fails, third succeeds
        mock_loader.load = AsyncMock(side_effect=[
            Exception("Failed"),
            None,  # Will be mocked properly
            None,
        ])
        mock_loader_class.return_value = mock_loader
        
        pipeline = IngestionPipeline(mock_db)
        
        # Mock the rest of the pipeline for successful cases
        with patch.object(pipeline, 'ingest_pdf') as mock_ingest:
            mock_ingest.side_effect = [
                type('Result', (), {'status': 'error', 'error': 'Failed'})(),
                type('Result', (), {'status': 'success', 'paper_id': 'paper:2'})(),
            ]
            
            results = await pipeline.ingest_batch([
                {"type": "pdf", "source": "file1.pdf"},
                {"type": "pdf", "source": "file2.pdf"},
            ])
            
            assert len(results) == 2
            assert results[0].status == "error"
            assert results[1].status == "success"


def test_enrich_chunk_metadata_adds_paper_context():
    """Chunk metadata should include normalized paper-level fields."""
    from app.ingestion.pipeline import IngestionPipeline
    from app.models.domain import Chunk, ExtractedEntities, ExtractedAuthor

    pipeline = IngestionPipeline(db_manager=Mock())
    chunks = [Chunk(content="test", index=0, metadata={"source": "pdf"})]
    entities = ExtractedEntities(
        title="Test Paper",
        authors=[ExtractedAuthor(name="Alice", institution="MIT")],
        topics=["LLMs", "Censorship"],
        institutions=["MIT"],
        citations=[],
        year=2026,
        venue="arXiv",
    )

    enriched = pipeline._enrich_chunk_metadata(chunks, entities)

    assert len(enriched) == 1
    metadata = enriched[0].metadata
    assert metadata["paper_title"] == "Test Paper"
    assert metadata["title"] == "Test Paper"
    assert metadata["authors"] == ["Alice"]
    assert metadata["topics"] == ["LLMs", "Censorship"]
    assert metadata["year"] == 2026
