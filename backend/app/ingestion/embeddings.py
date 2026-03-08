"""Embedding generation and vector store services."""

import logging
import re
import hashlib
from typing import List, Tuple, Optional, Any
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from app.models.domain import Chunk
from app.db.connection import SurrealDBManager
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings for text chunks."""
    
    def __init__(
        self,
        embeddings: Optional[OpenAIEmbeddings] = None,
        batch_size: int = 100,
    ):
        """Initialize embedding service.
        
        Args:
            embeddings: OpenAIEmbeddings instance (defaults to text-embedding-3-small)
            batch_size: Number of chunks to process in each batch
        """
        if embeddings is None:
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.openai_api_key,
            )
        else:
            self.embeddings = embeddings
        
        self.batch_size = batch_size
    
    def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for a list of chunks.
        
        Args:
            chunks: List of Chunk objects to embed
            
        Returns:
            List of Chunk objects with embeddings populated
        """
        if not chunks:
            return []
        
        texts = [chunk.content for chunk in chunks]
        embeddings_list = []
        
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = self.embeddings.embed_documents(batch_texts)
            embeddings_list.extend(batch_embeddings)
        
        result = []
        for chunk, embedding in zip(chunks, embeddings_list):
            chunk_with_embedding = Chunk(
                content=chunk.content,
                index=chunk.index,
                metadata=chunk.metadata.copy(),
                embedding=embedding,
            )
            result.append(chunk_with_embedding)
        
        return result


class VectorStoreService:
    """Service for storing and querying vector embeddings in SurrealDB."""
    
    def __init__(
        self,
        db_manager: SurrealDBManager,
        embeddings: Optional[Any] = None,
    ):
        """Initialize vector store service.
        
        Args:
            db_manager: SurrealDBManager instance for database access
            embeddings: Optional embeddings model override (for tests)
        """
        self.db_manager = db_manager
        self.embeddings = embeddings or OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key,
        )
    
    async def _ann_similarity_query(
        self,
        query_embedding: List[float],
        k: int,
        paper_ids: Optional[List[str]],
    ) -> List[dict]:
        """Primary ANN retrieval query using embedding vector index."""
        if paper_ids is None:
            query_sql = f"""
                SELECT
                    content,
                    metadata,
                    vector::similarity::cosine(embedding, $query_embedding) AS score
                FROM chunk
                WHERE embedding <|{k}|> $query_embedding
            """
            params = {"query_embedding": query_embedding}
        else:
            query_sql = f"""
                SELECT
                    content,
                    metadata,
                    vector::similarity::cosine(embedding, $query_embedding) AS score
                FROM chunk
                WHERE embedding <|{k}|> $query_embedding
                  AND (paper_id IN $paper_ids OR metadata.paper_id IN $paper_ids)
            """
            params = {"query_embedding": query_embedding, "paper_ids": paper_ids}
        return await self.db_manager.execute(query_sql, params)

    async def _bruteforce_similarity_query(
        self,
        query_embedding: List[float],
        k: int,
        paper_ids: Optional[List[str]],
    ) -> List[dict]:
        """Fallback retrieval via cosine ranking when ANN path returns empty rows."""
        if paper_ids is None:
            query_sql = f"""
                SELECT
                    content,
                    metadata,
                    vector::similarity::cosine(embedding, $query_embedding) AS score
                FROM chunk
                WHERE embedding != NONE
                ORDER BY score DESC
                LIMIT {k}
            """
            params = {"query_embedding": query_embedding}
        else:
            query_sql = f"""
                SELECT
                    content,
                    metadata,
                    vector::similarity::cosine(embedding, $query_embedding) AS score
                FROM chunk
                WHERE embedding != NONE
                  AND (paper_id IN $paper_ids OR metadata.paper_id IN $paper_ids)
                ORDER BY score DESC
                LIMIT {k}
            """
            params = {"query_embedding": query_embedding, "paper_ids": paper_ids}
        return await self.db_manager.execute(query_sql, params)

    async def _keyword_fallback_query(
        self,
        query: str,
        k: int,
        paper_ids: Optional[List[str]],
    ) -> List[dict]:
        """Lexical fallback query for cases where vector similarity returns no rows."""
        terms = [token for token in re.findall(r"[a-zA-Z0-9]{3,}", query.lower()) if token]
        if not terms:
            return []

        # Keep parameter count bounded for predictable query cost.
        terms = terms[:8]
        query_sql = """
            SELECT
                content,
                metadata,
                array::len(array::filter($terms, |$term| string::lowercase(content) CONTAINS $term)) AS search_score
            FROM chunk
            WHERE embedding != NONE
        """

        if paper_ids is not None:
            query_sql += "\n  AND (paper_id IN $paper_ids OR metadata.paper_id IN $paper_ids)"

        query_sql += """
            ORDER BY search_score DESC
            LIMIT $limit
        """

        params = {"terms": terms, "limit": k}
        if paper_ids is not None:
            params["paper_ids"] = paper_ids

        results = await self.db_manager.execute(query_sql, params)
        return [row for row in results if float(row.get("search_score", 0.0)) > 0.0]
    
    async def add_paper_chunks(
        self,
        paper_id: str,
        chunks_with_embeddings: List[Chunk],
    ) -> None:
        """Add paper chunks with embeddings to vector store and create has_chunk edges.
        
        Args:
            paper_id: SurrealDB paper record ID (e.g., "paper:123")
            chunks_with_embeddings: List of Chunk objects with embeddings populated
        """
        if not chunks_with_embeddings:
            return
        
        chunk_ids = []
        
        for chunk in chunks_with_embeddings:
            if chunk.embedding is None:
                raise ValueError(f"Chunk at index {chunk.index} has no embedding")
            
            # SurrealDB doesn't allow colons in record IDs, use underscore separator
            paper_id_clean = paper_id.replace(":", "_")
            chunk_id = f"chunk:{paper_id_clean}_{chunk.index}"
            chunk_ids.append(chunk_id)
            
            metadata = chunk.metadata.copy()
            metadata["paper_id"] = paper_id
            metadata["index"] = chunk.index
            
            await self.db_manager.execute(
                f"""
                UPSERT {chunk_id} SET
                    content = $content,
                    index = $index,
                    paper_id = <string>$paper_id,
                    embedding = $embedding,
                    metadata = $metadata
                """,
                {
                    "content": chunk.content,
                    "index": chunk.index,
                    "paper_id": paper_id,
                    "embedding": chunk.embedding,
                    "metadata": metadata,
                }
            )
            
            try:
                existing_edge = await self.db_manager.execute(
                    f"SELECT * FROM has_chunk WHERE in = {paper_id} AND out = {chunk_id} LIMIT 1"
                )
                if existing_edge:
                    continue
                await self.db_manager.execute(
                    f"RELATE {paper_id} ->has_chunk-> {chunk_id}",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create has_chunk edge from {paper_id} to {chunk_id}: {e}"
                )

    async def link_chunks_to_topics(
        self,
        paper_id: str,
        chunks_with_embeddings: List[Chunk],
        topics: List[str],
    ) -> int:
        """Create chunk->mentions_topic edges when topic terms appear in chunk text."""
        if not chunks_with_embeddings or not topics:
            return 0

        linked = 0
        paper_id_clean = paper_id.replace(":", "_")
        normalized_topics = [topic.strip() for topic in topics if isinstance(topic, str) and topic.strip()]
        topic_id_map = {}
        for topic in normalized_topics:
            rows = await self.db_manager.execute(
                """
                SELECT id
                FROM topic
                WHERE string::lowercase(name) = $name
                LIMIT 1
                """,
                {"name": topic.lower()},
            )
            topic_id: Optional[str] = None
            if rows:
                value = rows[0].get("id")
                if isinstance(value, dict) and "tb" in value and "id" in value:
                    topic_id = f"{value['tb']}:{value['id']}"
                elif value:
                    topic_id = str(value)
            if not topic_id:
                topic_hash = hashlib.md5(topic.lower().encode("utf-8")).hexdigest()[:16]
                topic_id = f"topic:{topic_hash}"
            topic_id_map[topic] = topic_id

        for chunk in chunks_with_embeddings:
            chunk_id = f"chunk:{paper_id_clean}_{chunk.index}"
            content = chunk.content.lower()
            for topic in normalized_topics:
                topic_tokens = [token for token in re.findall(r"[a-zA-Z0-9]{3,}", topic.lower())]
                if not topic_tokens:
                    continue
                if not all(token in content for token in topic_tokens):
                    continue

                topic_id = topic_id_map[topic]
                try:
                    existing_edge = await self.db_manager.execute(
                        f"SELECT * FROM mentions_topic WHERE in = {chunk_id} AND out = {topic_id} LIMIT 1"
                    )
                    if existing_edge:
                        continue
                    await self.db_manager.execute(f"RELATE {chunk_id} ->mentions_topic-> {topic_id}")
                    linked += 1
                except Exception as e:
                    logger.warning(
                        "Failed to create mentions_topic edge from %s to %s: %s",
                        chunk_id,
                        topic_id,
                        e,
                    )
        return linked
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Document]:
        """Perform similarity search in the vector store.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            paper_ids: Optional paper ID filter
            
        Returns:
            List of Document objects matching the query
        """
        if paper_ids is not None and not paper_ids:
            return []

        query_embedding = await self.embeddings.aembed_query(query)
        fallback_used = False
        lexical_used = False

        if paper_ids is None:
            results = await self._ann_similarity_query(query_embedding, k, paper_ids)
            if not results:
                results = await self._bruteforce_similarity_query(query_embedding, k, paper_ids)
                fallback_used = True
        else:
            # Scoped retrieval is more reliable with deterministic cosine ranking.
            results = await self._bruteforce_similarity_query(query_embedding, k, paper_ids)
            fallback_used = True

        if not results:
            results = await self._keyword_fallback_query(query, k, paper_ids)
            lexical_used = True

        logger.info(
            "vector_retrieval",
            extra={
                "query": query,
                "k": k,
                "selected_paper_ids": paper_ids or [],
                "ann_hits": 0 if paper_ids is not None or fallback_used else len(results),
                "fallback_used": fallback_used,
                "lexical_fallback_used": lexical_used,
                "final_hits": len(results),
            },
        )
        
        documents = []
        for result in results:
            doc = Document(
                page_content=result.get("content", ""),
                metadata=result.get("metadata", {}),
            )
            documents.append(doc)
        
        return documents
    
    async def similarity_search_with_scores(
        self,
        query: str,
        k: int = 5,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Tuple[Document, float]]:
        """Perform similarity search with relevance scores.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            paper_ids: Optional paper ID filter
            
        Returns:
            List of tuples containing (Document, score) pairs
        """
        if paper_ids is not None and not paper_ids:
            return []

        query_embedding = await self.embeddings.aembed_query(query)
        fallback_used = False
        lexical_used = False
        ann_results: List[dict] = []

        if paper_ids is None:
            ann_results = await self._ann_similarity_query(query_embedding, k, paper_ids)
            results = ann_results
            if not results:
                results = await self._bruteforce_similarity_query(query_embedding, k, paper_ids)
                fallback_used = True
        else:
            # Scoped retrieval is more reliable with deterministic cosine ranking.
            results = await self._bruteforce_similarity_query(query_embedding, k, paper_ids)
            fallback_used = True

        if not results:
            results = await self._keyword_fallback_query(query, k, paper_ids)
            lexical_used = True

        logger.info(
            "vector_retrieval",
            extra={
                "query": query,
                "k": k,
                "selected_paper_ids": paper_ids or [],
                "ann_hits": len(ann_results),
                "fallback_used": fallback_used,
                "lexical_fallback_used": lexical_used,
                "final_hits": len(results),
            },
        )
        
        documents_with_scores = []
        for result in results:
            doc = Document(
                page_content=result.get("content", ""),
                metadata=result.get("metadata", {}),
            )
            score = result.get("score", result.get("search_score", 0.0))
            documents_with_scores.append((doc, float(score)))
        
        return documents_with_scores
