"""Embedding generation and vector store services."""

import logging
from typing import List, Tuple, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_surrealdb.vectorstores import SurrealDBVectorStore
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
    
    def __init__(self, db_manager: SurrealDBManager):
        """Initialize vector store service.
        
        Args:
            db_manager: SurrealDBManager instance for database access
        """
        self.db_manager = db_manager
        self._vector_store: Optional[SurrealDBVectorStore] = None
    
    async def _ensure_vector_store(self) -> SurrealDBVectorStore:
        """Ensure vector store is initialized.
        
        Returns:
            Initialized SurrealDBVectorStore instance
        """
        if self._vector_store is None:
            if not self.db_manager._connected or not self.db_manager.client:
                raise RuntimeError(
                    "SurrealDBManager must be connected before using VectorStoreService"
                )
            
            embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                openai_api_key=settings.openai_api_key,
            )
            
            # SurrealDBVectorStore requires a connection parameter
            # Create a sync Surreal connection following the SDK pattern
            from surrealdb import Surreal
            
            # Create sync connection - Surreal connects automatically on creation
            sync_conn = Surreal(self.db_manager.url)
            # Sign in and use namespace/database
            sync_conn.signin({"username": self.db_manager.user, "password": self.db_manager.password})
            sync_conn.use(self.db_manager.namespace, self.db_manager.database)
            
            self._vector_store = SurrealDBVectorStore(
                embedding=embeddings,
                connection=sync_conn,
                table="chunk",
            )
        
        return self._vector_store
    
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
                CREATE {chunk_id} SET
                    content = $content,
                    index = $index,
                    embedding = $embedding,
                    metadata = $metadata
                """,
                {
                    "content": chunk.content,
                    "index": chunk.index,
                    "embedding": chunk.embedding,
                    "metadata": metadata,
                }
            )
            
            try:
                await self.db_manager.execute(
                    f"RELATE {paper_id} ->has_chunk-> {chunk_id}",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create has_chunk edge from {paper_id} to {chunk_id}: {e}"
                )
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
    ) -> List[Document]:
        """Perform similarity search in the vector store.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            
        Returns:
            List of Document objects matching the query
        """
        vector_store = await self._ensure_vector_store()
        
        query_embedding = await vector_store.embeddings.aembed_query(query)
        
        results = await self.db_manager.execute(
            f"""
            SELECT 
                content,
                metadata,
                vector::similarity::cosine(embedding, $query_embedding) AS score
            FROM chunk
            WHERE embedding <|{k}|> $query_embedding
            """,
            {
                "query_embedding": query_embedding,
            }
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
    ) -> List[Tuple[Document, float]]:
        """Perform similarity search with relevance scores.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            
        Returns:
            List of tuples containing (Document, score) pairs
        """
        vector_store = await self._ensure_vector_store()
        
        query_embedding = await vector_store.embeddings.aembed_query(query)
        
        results = await self.db_manager.execute(
            f"""
            SELECT 
                content,
                metadata,
                vector::similarity::cosine(embedding, $query_embedding) AS score
            FROM chunk
            WHERE embedding <|{k}|> $query_embedding
            """,
            {
                "query_embedding": query_embedding,
            }
        )
        
        documents_with_scores = []
        for result in results:
            doc = Document(
                page_content=result.get("content", ""),
                metadata=result.get("metadata", {}),
            )
            score = result.get("score", 0.0)
            documents_with_scores.append((doc, float(score)))
        
        return documents_with_scores
