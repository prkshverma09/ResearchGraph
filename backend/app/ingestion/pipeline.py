"""Ingestion pipeline orchestrator."""

import logging
from typing import List, Dict, Any, Optional
from app.db.connection import SurrealDBManager
from app.ingestion.loaders import PDFLoader, ArxivLoader, SemanticScholarLoader, TextChunker
from app.ingestion.extractors import EntityExtractor
from app.ingestion.embeddings import EmbeddingService, VectorStoreService
from app.ingestion.graph_builder import persist_graph
from app.models.domain import (
    RawDocument,
    Chunk,
    ExtractedEntities,
    PaperIngestionResult,
)

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the complete paper ingestion pipeline."""
    
    def __init__(
        self,
        db_manager: SurrealDBManager,
        loader: Optional[Any] = None,
        chunker: Optional[TextChunker] = None,
        extractor: Optional[EntityExtractor] = None,
        embedder: Optional[EmbeddingService] = None,
        graph_builder: Optional[Any] = None,
        vector_store: Optional[VectorStoreService] = None,
    ):
        """Initialize ingestion pipeline.
        
        Args:
            db_manager: SurrealDB manager instance
            loader: Optional custom loader (defaults to PDFLoader)
            chunker: Optional custom chunker (defaults to TextChunker)
            extractor: Optional custom extractor (defaults to EntityExtractor)
            embedder: Optional custom embedder (defaults to EmbeddingService)
            graph_builder: Optional custom graph builder (uses persist_graph function)
            vector_store: Optional custom vector store (defaults to VectorStoreService)
        """
        self.db_manager = db_manager
        self.loader = loader or PDFLoader()
        self.chunker = chunker or TextChunker()
        self.extractor = extractor or EntityExtractor()
        self.embedder = embedder or EmbeddingService()
        self.vector_store = vector_store or VectorStoreService(db_manager)
    
    async def ingest_pdf(self, file_path: str) -> PaperIngestionResult:
        """Ingest a paper from a PDF file.
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            PaperIngestionResult with paper_id and status
        """
        try:
            # Step 1: Load document
            logger.info(f"Loading PDF: {file_path}")
            raw_doc = self.loader.load(file_path)
            
            # Step 2: Chunk text
            logger.info("Chunking document text")
            chunks = self.chunker.chunk(raw_doc)
            
            # Step 3: Extract entities
            logger.info("Extracting entities from document")
            entities = await self.extractor.extract(raw_doc.text, existing_metadata=raw_doc.metadata)
            
            # Step 4: Generate embeddings
            logger.info("Generating embeddings for chunks")
            chunks_with_embeddings = self.embedder.embed_chunks(chunks)
            
            # Step 5: Persist graph nodes and edges
            logger.info("Persisting graph nodes and edges")
            paper_id = await persist_graph(self.db_manager, entities)
            
            # Step 6: Store chunks with embeddings
            logger.info("Storing chunks with embeddings")
            await self.vector_store.add_paper_chunks(paper_id, chunks_with_embeddings)
            
            semantic_counts, full_counts = await self._compute_persisted_counts(paper_id)
            
            logger.info(f"Ingestion complete: {paper_id}")
            return PaperIngestionResult(
                paper_id=paper_id,
                status="success",
                nodes_created=semantic_counts["nodes"],
                edges_created=semantic_counts["edges"],
                semantic_counts=semantic_counts,
                full_counts=full_counts,
            )
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            return PaperIngestionResult(
                paper_id="",
                status="error",
                error=str(e),
            )
    
    async def ingest_arxiv(self, arxiv_id: str) -> PaperIngestionResult:
        """Ingest a paper from arXiv.
        
        Args:
            arxiv_id: arXiv paper ID (e.g., "2401.00001")
        
        Returns:
            PaperIngestionResult with paper_id and status
        """
        try:
            # Step 1: Load document
            logger.info(f"Loading arXiv paper: {arxiv_id}")
            loader = ArxivLoader()
            raw_doc = loader.load(arxiv_id)
            
            # Step 2-6: Same as PDF ingestion
            chunks = self.chunker.chunk(raw_doc)
            entities = await self.extractor.extract(raw_doc.text, existing_metadata=raw_doc.metadata)
            chunks_with_embeddings = self.embedder.embed_chunks(chunks)
            paper_id = await persist_graph(self.db_manager, entities)
            await self.vector_store.add_paper_chunks(paper_id, chunks_with_embeddings)
            
            semantic_counts, full_counts = await self._compute_persisted_counts(paper_id)
            
            logger.info(f"arXiv ingestion complete: {paper_id}")
            return PaperIngestionResult(
                paper_id=paper_id,
                status="success",
                nodes_created=semantic_counts["nodes"],
                edges_created=semantic_counts["edges"],
                semantic_counts=semantic_counts,
                full_counts=full_counts,
            )
        except Exception as e:
            logger.error(f"arXiv ingestion failed: {e}", exc_info=True)
            return PaperIngestionResult(
                paper_id="",
                status="error",
                error=str(e),
            )
    
    async def ingest_semantic_scholar(self, paper_id: str) -> PaperIngestionResult:
        """Ingest a paper from Semantic Scholar.
        
        Args:
            paper_id: Semantic Scholar paper ID
        
        Returns:
            PaperIngestionResult with paper_id and status
        """
        try:
            # Step 1: Load document
            logger.info(f"Loading Semantic Scholar paper: {paper_id}")
            loader = SemanticScholarLoader()
            raw_doc = loader.load(paper_id)
            
            # Step 2-6: Same as PDF ingestion
            chunks = self.chunker.chunk(raw_doc)
            entities = await self.extractor.extract(raw_doc.text, existing_metadata=raw_doc.metadata)
            chunks_with_embeddings = self.embedder.embed_chunks(chunks)
            paper_id_result = await persist_graph(self.db_manager, entities)
            await self.vector_store.add_paper_chunks(paper_id_result, chunks_with_embeddings)
            
            semantic_counts, full_counts = await self._compute_persisted_counts(paper_id_result)
            
            logger.info(f"Semantic Scholar ingestion complete: {paper_id_result}")
            return PaperIngestionResult(
                paper_id=paper_id_result,
                status="success",
                nodes_created=semantic_counts["nodes"],
                edges_created=semantic_counts["edges"],
                semantic_counts=semantic_counts,
                full_counts=full_counts,
            )
        except Exception as e:
            logger.error(f"Semantic Scholar ingestion failed: {e}", exc_info=True)
            return PaperIngestionResult(
                paper_id="",
                status="error",
                error=str(e),
            )
    
    async def ingest_batch(
        self,
        sources: List[Dict[str, Any]],
    ) -> List[PaperIngestionResult]:
        """Ingest multiple papers in batch.
        
        Args:
            sources: List of source dictionaries with 'type' and 'source' keys
                    Example: [{"type": "pdf", "source": "file.pdf"}, ...]
        
        Returns:
            List of PaperIngestionResult objects
        """
        results = []
        
        for source in sources:
            source_type = source.get("type")
            source_value = source.get("source")
            
            try:
                if source_type == "pdf":
                    result = await self.ingest_pdf(source_value)
                elif source_type == "arxiv":
                    result = await self.ingest_arxiv(source_value)
                elif source_type == "semantic_scholar":
                    result = await self.ingest_semantic_scholar(source_value)
                else:
                    result = PaperIngestionResult(
                        paper_id="",
                        status="error",
                        error=f"Unknown source type: {source_type}",
                    )
                
                results.append(result)
            except Exception as e:
                logger.error(f"Batch ingestion failed for {source}: {e}")
                results.append(PaperIngestionResult(
                    paper_id="",
                    status="error",
                    error=str(e),
                ))
        
        return results

    async def _compute_persisted_counts(self, paper_id: str) -> tuple[Dict[str, int], Dict[str, int]]:
        """Compute exact persisted node/edge counts for semantic and full graph modes."""
        authored_edges = await self.db_manager.execute(
            f"SELECT out FROM authored_by WHERE in = {paper_id}"
        )
        topic_edges = await self.db_manager.execute(
            f"SELECT out FROM belongs_to WHERE in = {paper_id}"
        )
        citation_edges = await self.db_manager.execute(
            f"SELECT out FROM cites WHERE in = {paper_id}"
        )
        chunk_edges = await self.db_manager.execute(
            f"SELECT out FROM has_chunk WHERE in = {paper_id}"
        )

        author_ids = {str(row.get("out")) for row in authored_edges if row.get("out")}
        topic_ids = {str(row.get("out")) for row in topic_edges if row.get("out")}
        citation_ids = {str(row.get("out")) for row in citation_edges if row.get("out")}
        chunk_ids = {str(row.get("out")) for row in chunk_edges if row.get("out")}

        affiliation_count = 0
        institution_ids: set[str] = set()
        for author_id in author_ids:
            aff_edges = await self.db_manager.execute(
                f"SELECT out FROM affiliated_with WHERE in = {author_id}"
            )
            affiliation_count += len(aff_edges)
            for row in aff_edges:
                if row.get("out"):
                    institution_ids.add(str(row.get("out")))

        semantic_nodes = 1 + len(author_ids) + len(topic_ids) + len(citation_ids) + len(institution_ids)
        semantic_edges = len(authored_edges) + len(topic_edges) + len(citation_edges) + affiliation_count
        full_nodes = semantic_nodes + len(chunk_ids)
        full_edges = semantic_edges + len(chunk_edges)

        return (
            {"nodes": semantic_nodes, "edges": semantic_edges},
            {"nodes": full_nodes, "edges": full_edges},
        )
