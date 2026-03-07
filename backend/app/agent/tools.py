"""LangChain-compatible tools for the ResearchGraph agent."""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
try:
    import langsmith as ls
except ImportError:
    ls = None

from app.ingestion.embeddings import VectorStoreService
from app.db.connection import SurrealDBManager
from app.config import settings

logger = logging.getLogger(__name__)


class VectorSearchInput(BaseModel):
    """Input schema for VectorSearchTool."""
    query: str = Field(description="Search query text")
    top_k: int = Field(default=5, description="Number of results to return")


class GraphQueryInput(BaseModel):
    """Input schema for GraphQueryTool."""
    query_type: str = Field(
        description="Type of graph query: 'author_papers', 'paper_citations', 'topic_papers', or 'coauthors'"
    )
    author_name: Optional[str] = Field(default=None, description="Author name (for author_papers or coauthors)")
    paper_title: Optional[str] = Field(default=None, description="Paper title (for paper_citations)")
    topic: Optional[str] = Field(default=None, description="Topic name (for topic_papers)")


class CitationPathInput(BaseModel):
    """Input schema for CitationPathTool."""
    paper_a_title: str = Field(description="Title of the first paper")
    paper_b_title: str = Field(description="Title of the second paper")


class PaperSummarizerInput(BaseModel):
    """Input schema for PaperSummarizerTool."""
    paper_id: str = Field(description="SurrealDB paper ID (e.g., 'paper:123')")


class TopicExplorerInput(BaseModel):
    """Input schema for TopicExplorerTool."""
    topic: str = Field(description="Topic to explore")


def create_vector_search_tool(vector_store_service: VectorStoreService) -> StructuredTool:
    """Create VectorSearchTool as a LangChain StructuredTool."""
    
    async def _arun(query: str, top_k: int = 5) -> Dict[str, Any]:
        """Execute vector search."""
        try:
            results = await vector_store_service.similarity_search_with_scores(query, k=top_k)
            
            papers = []
            paper_ids = []
            for doc, score in results:
                paper_id = doc.metadata.get("paper_id", "unknown")
                paper_info = {
                    "title": doc.metadata.get("title", "Unknown"),
                    "abstract": doc.page_content[:500] if len(doc.page_content) > 500 else doc.page_content,
                    "paper_id": paper_id,
                    "relevance_score": float(score),
                }
                papers.append(paper_info)
                if paper_id != "unknown":
                    paper_ids.append(paper_id)
            
            if ls:
                metadata = {
                    "tool": "vector_search",
                    "query": query,
                    "top_k": top_k,
                }
                if paper_ids:
                    metadata["paper_ids"] = list(set(paper_ids))
                
                with ls.tracing_context(metadata=metadata):
                    pass
            
            return {"papers": papers}
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {"papers": [], "error": str(e)}
    
    return StructuredTool.from_function(
        func=_arun,
        name="vector_search",
        description="Search for papers using semantic similarity. Use this when the user asks to find papers about a topic, concept, or research area.",
        args_schema=VectorSearchInput,
    )


class VectorSearchTool:
    """Tool for performing semantic similarity search on paper chunks."""
    
    def __init__(self, vector_store_service: VectorStoreService):
        """Initialize vector search tool.
        
        Args:
            vector_store_service: VectorStoreService instance
        """
        self.vector_store_service = vector_store_service
        self.name = "vector_search"
        self.description = "Search for papers using semantic similarity. Use this when the user asks to find papers about a topic, concept, or research area."
        self.args_schema = VectorSearchInput
    
    async def _arun(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Execute vector search.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            Dictionary with 'papers' list containing title, abstract, and relevance_score
        """
        try:
            results = await self.vector_store_service.similarity_search_with_scores(query, k=top_k)
            
            papers = []
            paper_ids = []
            for doc, score in results:
                paper_id = doc.metadata.get("paper_id", "unknown")
                paper_info = {
                    "title": doc.metadata.get("title", "Unknown"),
                    "abstract": doc.page_content[:500] if len(doc.page_content) > 500 else doc.page_content,
                    "paper_id": paper_id,
                    "relevance_score": float(score),
                }
                papers.append(paper_info)
                if paper_id != "unknown":
                    paper_ids.append(paper_id)
            
            if ls:
                metadata = {
                    "tool": "vector_search",
                    "query": query,
                    "top_k": top_k,
                }
                if paper_ids:
                    metadata["paper_ids"] = list(set(paper_ids))
                
                with ls.tracing_context(metadata=metadata):
                    pass
            
            return {"papers": papers}
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {"papers": [], "error": str(e)}
    
    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async invoke method for LangChain compatibility."""
        return await self._arun(**input_data)


class GraphQueryTool:
    """Tool for executing graph traversal queries on the research graph."""
    
    def __init__(self, db_manager: SurrealDBManager):
        """Initialize graph query tool.
        
        Args:
            db_manager: SurrealDBManager instance
        """
        self.db_manager = db_manager
        self.name = "graph_query"
        self.description = "Query the research graph to find papers by author, citations, topics, or coauthors. Use this when the user asks about relationships between papers, authors, or topics."
        self.args_schema = GraphQueryInput
    
    async def _arun(
        self,
        query_type: str,
        author_name: Optional[str] = None,
        paper_title: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute graph query.
        
        Args:
            query_type: Type of query ('author_papers', 'paper_citations', 'topic_papers', 'coauthors')
            author_name: Author name (for author_papers or coauthors)
            paper_title: Paper title (for paper_citations)
            topic: Topic name (for topic_papers)
            
        Returns:
            Dictionary with query results
        """
        try:
            paper_ids = []
            
            if query_type == "author_papers":
                if not author_name:
                    return {"error": "author_name is required for author_papers query"}
                
                query = """
                    SELECT paper.*
                    FROM paper
                    WHERE id IN (
                        SELECT ->wrote->paper.id
                        FROM author
                        WHERE name = $author_name
                    )
                    ORDER BY year DESC
                """
                results = await self.db_manager.execute(query, {"author_name": author_name})
                for paper in results:
                    if isinstance(paper, dict) and "id" in paper:
                        paper_ids.append(paper["id"])
                
                if ls:
                    metadata = {
                        "tool": "graph_query",
                        "query_type": query_type,
                        "author_name": author_name,
                    }
                    if paper_ids:
                        metadata["paper_ids"] = list(set(paper_ids))
                    
                    with ls.tracing_context(metadata=metadata):
                        pass
                
                return {"papers": results}
            
            elif query_type == "paper_citations":
                if not paper_title:
                    return {"error": "paper_title is required for paper_citations query"}
                
                query = """
                    SELECT paper.*
                    FROM paper
                    WHERE id IN (
                        SELECT ->cites->paper.id
                        FROM paper
                        WHERE title = $paper_title
                    )
                """
                results = await self.db_manager.execute(query, {"paper_title": paper_title})
                for citation in results:
                    if isinstance(citation, dict) and "id" in citation:
                        paper_ids.append(citation["id"])
                
                if ls:
                    metadata = {
                        "tool": "graph_query",
                        "query_type": query_type,
                        "paper_title": paper_title,
                    }
                    if paper_ids:
                        metadata["paper_ids"] = list(set(paper_ids))
                    
                    with ls.tracing_context(metadata=metadata):
                        pass
                
                return {"citations": results}
            
            elif query_type == "topic_papers":
                if not topic:
                    return {"error": "topic is required for topic_papers query"}
                
                query = """
                    SELECT paper.*
                    FROM paper
                    WHERE id IN (
                        SELECT ->has_topic->paper.id
                        FROM topic
                        WHERE name = $topic
                    )
                    ORDER BY year DESC
                """
                results = await self.db_manager.execute(query, {"topic": topic})
                for paper in results:
                    if isinstance(paper, dict) and "id" in paper:
                        paper_ids.append(paper["id"])
                
                if ls:
                    metadata = {
                        "tool": "graph_query",
                        "query_type": query_type,
                        "topic": topic,
                    }
                    if paper_ids:
                        metadata["paper_ids"] = list(set(paper_ids))
                    
                    with ls.tracing_context(metadata=metadata):
                        pass
                
                return {"papers": results}
            
            elif query_type == "coauthors":
                if not author_name:
                    return {"error": "author_name is required for coauthors query"}
                
                query = """
                    SELECT DISTINCT author.*
                    FROM author
                    WHERE id IN (
                        SELECT ->wrote->author.id
                        FROM paper
                        WHERE id IN (
                            SELECT ->wrote->paper.id
                            FROM author
                            WHERE name = $author_name
                        )
                    )
                    AND name != $author_name
                """
                results = await self.db_manager.execute(query, {"author_name": author_name})
                
                if ls:
                    metadata = {
                        "tool": "graph_query",
                        "query_type": query_type,
                        "author_name": author_name,
                    }
                    if paper_ids:
                        metadata["paper_ids"] = list(set(paper_ids))
                    
                    with ls.tracing_context(metadata=metadata):
                        pass
                
                return {"coauthors": results}
            
            else:
                return {"error": f"Unknown query_type: {query_type}"}
        
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"error": str(e)}
    
    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async invoke method for LangChain compatibility."""
        return await self._arun(**input_data)


class CitationPathTool:
    """Tool for finding shortest citation paths between papers."""
    
    def __init__(self, db_manager: SurrealDBManager):
        """Initialize citation path tool.
        
        Args:
            db_manager: SurrealDBManager instance
        """
        self.db_manager = db_manager
        self.name = "citation_path"
        self.description = "Find the shortest citation path between two papers. Use this when the user asks how two papers are connected or related through citations."
        self.args_schema = CitationPathInput
    
    async def _arun(self, paper_a_title: str, paper_b_title: str) -> Dict[str, Any]:
        """Find citation path between two papers.
        
        Args:
            paper_a_title: Title of the first paper
            paper_b_title: Title of the second paper
            
        Returns:
            Dictionary with 'path' list of papers in the citation chain
        """
        try:
            paper_a_query = "SELECT * FROM paper WHERE title = $paper_a_title LIMIT 1"
            paper_b_query = "SELECT * FROM paper WHERE title = $paper_b_title LIMIT 1"
            
            paper_a_results = await self.db_manager.execute(paper_a_query, {"paper_a_title": paper_a_title})
            paper_b_results = await self.db_manager.execute(paper_b_query, {"paper_b_title": paper_b_title})
            
            if not paper_a_results or not paper_b_results:
                return {"path": [], "message": "One or both papers not found"}
            
            paper_a_id = paper_a_results[0]["id"]
            paper_b_id = paper_b_results[0]["id"]
            paper_ids = [paper_a_id, paper_b_id]
            
            direct_query = f"""
                SELECT VALUE ->cites->paper
                FROM {paper_a_id}
                WHERE id = {paper_b_id}
            """
            
            direct_results = await self.db_manager.execute(direct_query)
            
            if direct_results:
                if ls:
                    metadata = {
                        "tool": "citation_path",
                        "paper_a_title": paper_a_title,
                        "paper_b_title": paper_b_title,
                        "paper_ids": paper_ids,
                    }
                    with ls.tracing_context(metadata=metadata):
                        pass
                return {"path": [paper_a_results[0], paper_b_results[0]]}
            
            two_hop_query = f"""
                SELECT ->cites->paper->cites->paper.*
                FROM {paper_a_id}
                WHERE id = {paper_b_id}
            """
            
            two_hop_results = await self.db_manager.execute(two_hop_query)
            
            if two_hop_results:
                intermediate_paper = two_hop_results[0] if isinstance(two_hop_results[0], dict) else None
                if intermediate_paper:
                    if isinstance(intermediate_paper, dict) and "id" in intermediate_paper:
                        paper_ids.append(intermediate_paper["id"])
                    if ls:
                        metadata = {
                            "tool": "citation_path",
                            "paper_a_title": paper_a_title,
                            "paper_b_title": paper_b_title,
                            "paper_ids": list(set(paper_ids)),
                        }
                        with ls.tracing_context(metadata=metadata):
                            pass
                    return {"path": [paper_a_results[0], intermediate_paper, paper_b_results[0]]}
            
            if ls:
                metadata = {
                    "tool": "citation_path",
                    "paper_a_title": paper_a_title,
                    "paper_b_title": paper_b_title,
                    "paper_ids": paper_ids,
                }
                with ls.tracing_context(metadata=metadata):
                    pass
            
            return {"path": [], "message": "No citation path found between the papers"}
        
        except Exception as e:
            logger.error(f"Citation path search failed: {e}")
            return {"path": [], "error": str(e)}
    
    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async invoke method for LangChain compatibility."""
        return await self._arun(**input_data)


class PaperSummarizerTool:
    """Tool for summarizing papers using LLM."""
    
    def __init__(self, db_manager: SurrealDBManager, llm: Optional[ChatOpenAI] = None):
        """Initialize paper summarizer tool.
        
        Args:
            db_manager: SurrealDBManager instance
            llm: ChatOpenAI instance (defaults to GPT-4o-mini)
        """
        self.db_manager = db_manager
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.openai_api_key,
        )
        self.name = "paper_summarizer"
        self.description = "Generate a concise summary of a paper by retrieving its chunks and summarizing them. Use this when the user asks for a summary or overview of a specific paper."
        self.args_schema = PaperSummarizerInput
    
    async def _arun(self, paper_id: str) -> Dict[str, Any]:
        """Summarize a paper.
        
        Args:
            paper_id: SurrealDB paper ID (e.g., 'paper:123')
            
        Returns:
            Dictionary with 'summary' string
        """
        try:
            query = """
                SELECT content, index
                FROM chunk
                WHERE id IN (
                    SELECT ->has_chunk->chunk.id
                    FROM paper
                    WHERE id = $paper_id
                )
                ORDER BY index ASC
            """
            
            chunks = await self.db_manager.execute(query, {"paper_id": paper_id})
            
            if not chunks:
                return {"summary": "No chunks found for this paper.", "error": "Paper not found"}
            
            chunk_texts = [chunk["content"] for chunk in chunks]
            full_text = "\n\n".join(chunk_texts)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a research assistant. Summarize the following paper content in 2-3 concise paragraphs, highlighting key contributions, methods, and findings."),
                ("user", "{text}"),
            ])
            
            chain = prompt | self.llm
            
            if ls:
                metadata = {
                    "tool": "paper_summarizer",
                    "paper_id": paper_id,
                }
                
                with ls.tracing_context(metadata=metadata):
                    response = await chain.ainvoke({"text": full_text})
            else:
                response = await chain.ainvoke({"text": full_text})
            
            summary = response.content if hasattr(response, "content") else str(response)
            
            return {"summary": summary, "paper_id": paper_id}
        
        except Exception as e:
            logger.error(f"Paper summarization failed: {e}")
            return {"summary": "", "error": str(e)}
    
    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async invoke method for LangChain compatibility."""
        return await self._arun(**input_data)


class TopicExplorerTool:
    """Tool for exploring topics by combining vector search and graph traversal."""
    
    def __init__(
        self,
        vector_store_service: VectorStoreService,
        db_manager: SurrealDBManager,
    ):
        """Initialize topic explorer tool.
        
        Args:
            vector_store_service: VectorStoreService instance
            db_manager: SurrealDBManager instance
        """
        self.vector_store_service = vector_store_service
        self.db_manager = db_manager
        self.name = "topic_explorer"
        self.description = "Explore a research topic by finding relevant papers (semantic search) and associated authors (graph traversal). Use this when the user wants a comprehensive overview of a research topic."
        self.args_schema = TopicExplorerInput
    
    async def _arun(self, topic: str) -> Dict[str, Any]:
        """Explore a topic.
        
        Args:
            topic: Topic name to explore
            
        Returns:
            Dictionary with 'papers' and 'authors' lists
        """
        try:
            vector_results = await self.vector_store_service.similarity_search_with_scores(topic, k=5)
            
            papers = []
            paper_ids = []
            
            for doc, score in vector_results:
                paper_id = doc.metadata.get("paper_id")
                if paper_id:
                    paper_ids.append(paper_id)
                    papers.append({
                        "title": doc.metadata.get("title", "Unknown"),
                        "paper_id": paper_id,
                        "relevance_score": float(score),
                        "abstract": doc.page_content[:300] if len(doc.page_content) > 300 else doc.page_content,
                    })
            
            authors = []
            if paper_ids:
                query = """
                    SELECT DISTINCT author.*
                    FROM author
                    WHERE id IN (
                        SELECT ->wrote->author.id
                        FROM paper
                        WHERE id IN $paper_ids
                    )
                """
                authors = await self.db_manager.execute(query, {"paper_ids": paper_ids})
            
            if ls:
                metadata = {
                    "tool": "topic_explorer",
                    "topic": topic,
                }
                if paper_ids:
                    metadata["paper_ids"] = list(set(paper_ids))
                
                with ls.tracing_context(metadata=metadata):
                    pass
            
            return {
                "topic": topic,
                "papers": papers,
                "authors": authors,
            }
        
        except Exception as e:
            logger.error(f"Topic exploration failed: {e}")
            return {"topic": topic, "papers": [], "authors": [], "error": str(e)}
    
    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async invoke method for LangChain compatibility."""
        return await self._arun(**input_data)
