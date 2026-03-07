"""API routes for graph queries and statistics."""

import logging
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.models.schemas import (
    PaperWithRelations,
    GraphStatsResponse,
    PaperSearchResult,
    SearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _serialize_record_ids(obj: Any) -> Any:
    """Recursively convert SurrealDB RecordID objects to strings for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _serialize_record_ids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_record_ids(v) for v in obj]
    if type(obj).__name__ == "RecordID":
        return str(obj)
    return obj


def _record_id_to_str(value: Any) -> str:
    """Normalize a SurrealDB record ID into table:id string form."""
    if type(value).__name__ == "RecordID":
        return str(value)
    if isinstance(value, dict) and "tb" in value and "id" in value:
        return f"{value['tb']}:{value['id']}"
    if isinstance(value, str):
        return value
    return ""


def _normalize_records(records: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalize records and recursively serialize IDs."""
    normalized: list[dict[str, Any]] = []
    for record in records or []:
        item = _serialize_record_ids(record)
        if isinstance(item, dict):
            item["id"] = _record_id_to_str(item.get("id"))
            normalized.append(item)
    return normalized


def _build_node(record: dict[str, Any], node_type: str) -> dict[str, Any]:
    """Create a graph node payload from a normalized record."""
    node_id = _record_id_to_str(record.get("id"))
    if node_type == "paper":
        label = record.get("title") or node_id or "Unknown paper"
    elif node_type == "author":
        label = record.get("name") or "Unknown author"
    elif node_type == "topic":
        label = record.get("name") or "Unknown topic"
    elif node_type == "institution":
        label = record.get("name") or "Unknown institution"
    elif node_type == "chunk":
        content = (record.get("content") or "").strip()
        label = content if content else "Chunk"
    else:
        label = node_id or "Unknown"
    return {"id": node_id, "label": label, "type": node_type}


@router.get("/papers", response_model=SearchResponse)
async def list_papers(
    db_manager: SurrealDBManager = Depends(get_db),
):
    """List all papers from the paper table (direct query, no vector search).

    Use this when the Papers tab loads with no search query.

    Returns:
        SearchResponse with papers in PaperSearchResult format (relevance_score: 1.0)
    """
    try:
        results = await db_manager.execute("SELECT * FROM paper")
        papers = []
        for row in results or []:
            paper_id = row.get("id")
            if isinstance(paper_id, dict) and "tb" in paper_id and "id" in paper_id:
                paper_id = f"{paper_id['tb']}:{paper_id['id']}"
            else:
                paper_id = str(paper_id) if paper_id else ""
            papers.append(
                PaperSearchResult(
                    paper_id=paper_id,
                    title=row.get("title", "Unknown"),
                    abstract=row.get("abstract", "") or "",
                    relevance_score=1.0,
                )
            )
        return SearchResponse(papers=papers)
    except Exception as e:
        logger.error(f"List papers error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list papers: {str(e)}")


@router.get("/paper/{paper_id}", response_model=PaperWithRelations)
async def get_paper_with_relations(
    paper_id: str,
    mode: Literal["semantic", "full"] = Query(default="semantic"),
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Get a paper with its relations (authors, topics, citations).
    
    Args:
        paper_id: SurrealDB paper ID (e.g., "paper:123")
        db_manager: SurrealDB manager dependency
        
    Returns:
        PaperWithRelations with paper, authors, topics, and citations
    """
    try:
        paper_result = await db_manager.execute(f"SELECT * FROM {paper_id}")
        if not paper_result:
            raise HTTPException(status_code=404, detail=f"Paper {paper_id} not found")
        paper = _normalize_records(paper_result)[0]

        authors_result = await db_manager.execute(
            f"SELECT ->authored_by->author.* AS authors FROM {paper_id}"
        )
        topics_result = await db_manager.execute(
            f"SELECT ->belongs_to->topic.* AS topics FROM {paper_id}"
        )
        citations_result = await db_manager.execute(
            f"SELECT ->cites->paper.* AS citations FROM {paper_id}"
        )
        institutions_result = await db_manager.execute(
            f"SELECT ->authored_by->author->affiliated_with->institution.* AS institutions FROM {paper_id}"
        )
        chunks_result = await db_manager.execute(
            f"SELECT ->has_chunk->chunk.* AS chunks FROM {paper_id}"
        )

        authors = _normalize_records((authors_result[0] if authors_result else {}).get("authors", []))
        topics = _normalize_records((topics_result[0] if topics_result else {}).get("topics", []))
        citations = _normalize_records((citations_result[0] if citations_result else {}).get("citations", []))
        institutions = _normalize_records((institutions_result[0] if institutions_result else {}).get("institutions", []))
        chunks = _normalize_records((chunks_result[0] if chunks_result else {}).get("chunks", []))

        authored_edges = await db_manager.execute(f"SELECT in, out FROM authored_by WHERE in = {paper_id}")
        topic_edges = await db_manager.execute(f"SELECT in, out FROM belongs_to WHERE in = {paper_id}")
        citation_edges = await db_manager.execute(f"SELECT in, out FROM cites WHERE in = {paper_id}")
        chunk_edges = await db_manager.execute(f"SELECT in, out FROM has_chunk WHERE in = {paper_id}")

        affiliation_edges: list[dict[str, Any]] = []
        author_ids = [author["id"] for author in authors if author.get("id")]
        if author_ids:
            author_ids_surreal = ", ".join(author_ids)
            affiliation_edges = await db_manager.execute(
                f"SELECT in, out FROM affiliated_with WHERE in INSIDE [{author_ids_surreal}]"
            )

        nodes_map: dict[str, dict[str, Any]] = {}
        paper_node = _build_node(paper, "paper")
        if paper_node["id"]:
            nodes_map[paper_node["id"]] = paper_node

        for author in authors:
            node = _build_node(author, "author")
            if node["id"]:
                nodes_map[node["id"]] = node
        for topic in topics:
            node = _build_node(topic, "topic")
            if node["id"]:
                nodes_map[node["id"]] = node
        for citation in citations:
            node = _build_node(citation, "paper")
            if node["id"]:
                nodes_map[node["id"]] = node
        for institution in institutions:
            node = _build_node(institution, "institution")
            if node["id"]:
                nodes_map[node["id"]] = node
        if mode == "full":
            for chunk in chunks:
                node = _build_node(chunk, "chunk")
                if node["id"]:
                    nodes_map[node["id"]] = node

        edge_map: dict[tuple[str, str, str], dict[str, Any]] = {}

        def add_edges(rows: list[dict[str, Any]], edge_type: str) -> None:
            for row in rows or []:
                source = _record_id_to_str(row.get("in"))
                target = _record_id_to_str(row.get("out"))
                if not source or not target:
                    continue
                edge_key = (source, target, edge_type)
                edge_map[edge_key] = {
                    "id": f"{edge_type}:{source}->{target}",
                    "source": source,
                    "target": target,
                    "type": edge_type,
                }

        add_edges(authored_edges, "authored_by")
        add_edges(topic_edges, "belongs_to")
        add_edges(citation_edges, "cites")
        add_edges(affiliation_edges, "affiliated_with")
        if mode == "full":
            add_edges(chunk_edges, "has_chunk")

        typed_edges = list(edge_map.values())

        return_nodes = list(nodes_map.values())
        counts = {"nodes": len(return_nodes), "edges": len(typed_edges)}

        return PaperWithRelations(
            paper=paper,
            mode=mode,
            nodes=return_nodes,
            edges=typed_edges,
            counts=counts,
            authors=authors if authors else [],
            topics=topics if topics else [],
            citations=citations if citations else [],
            institutions=institutions if institutions else [],
            chunks=chunks if mode == "full" else [],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get paper: {str(e)}")


@router.get("/stats", response_model=GraphStatsResponse)
async def get_graph_stats(
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Get graph statistics (counts of nodes and edges).
    
    Args:
        db_manager: SurrealDB manager dependency
        
    Returns:
        GraphStatsResponse with counts
    """
    try:
        papers_query = "SELECT COUNT() AS count FROM paper GROUP ALL"
        authors_query = "SELECT COUNT() AS count FROM author GROUP ALL"
        topics_query = "SELECT COUNT() AS count FROM topic GROUP ALL"
        
        papers_result = await db_manager.execute(papers_query)
        authors_result = await db_manager.execute(authors_query)
        topics_result = await db_manager.execute(topics_query)
        
        papers_count = papers_result[0].get("count", 0) if papers_result else 0
        authors_count = authors_result[0].get("count", 0) if authors_result else 0
        topics_count = topics_result[0].get("count", 0) if topics_result else 0
        
        authored_by_result = await db_manager.execute("SELECT COUNT() AS count FROM authored_by GROUP ALL")
        cites_result = await db_manager.execute("SELECT COUNT() AS count FROM cites GROUP ALL")
        belongs_to_result = await db_manager.execute("SELECT COUNT() AS count FROM belongs_to GROUP ALL")
        affiliated_with_result = await db_manager.execute("SELECT COUNT() AS count FROM affiliated_with GROUP ALL")
        has_chunk_result = await db_manager.execute("SELECT COUNT() AS count FROM has_chunk GROUP ALL")

        authored_by_count = authored_by_result[0].get("count", 0) if authored_by_result else 0
        cites_count = cites_result[0].get("count", 0) if cites_result else 0
        belongs_to_count = belongs_to_result[0].get("count", 0) if belongs_to_result else 0
        affiliated_with_count = affiliated_with_result[0].get("count", 0) if affiliated_with_result else 0
        has_chunk_count = has_chunk_result[0].get("count", 0) if has_chunk_result else 0
        edges_count = authored_by_count + cites_count + belongs_to_count + affiliated_with_count + has_chunk_count
        
        return GraphStatsResponse(
            papers=papers_count,
            authors=authors_count,
            topics=topics_count,
            edges=edges_count,
        )
    except Exception as e:
        logger.error(f"Graph stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get graph stats: {str(e)}")


@router.delete("/paper/{paper_id}")
async def delete_paper(
    paper_id: str,
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Delete a paper and its associated chunks/embeddings."""
    try:
        # Fetch chunk IDs
        chunks_res = await db_manager.execute(f"SELECT out FROM has_chunk WHERE in = {paper_id}")
        if chunks_res:
            for row in chunks_res:
                chunk_id = row.get("out")
                if chunk_id:
                    if isinstance(chunk_id, dict) and "tb" in chunk_id and "id" in chunk_id:
                        chunk_id_str = f"{chunk_id['tb']}:{chunk_id['id']}"
                    else:
                        chunk_id_str = str(chunk_id)
                    await db_manager.execute(f"DELETE {chunk_id_str}")
        
        # Delete paper
        await db_manager.execute(f"DELETE {paper_id}")
        
        return {"status": "success", "paper_id": paper_id}
    except Exception as e:
        logger.error(f"Delete paper error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete paper: {str(e)}")


@router.delete("/clear")
async def clear_database(
    db_manager: SurrealDBManager = Depends(get_db),
):
    """Clear all data from the database while keeping schema."""
    try:
        tables = [
            "paper", "author", "topic", "institution", "chunk", "session",
            "authored_by", "cites", "belongs_to", "affiliated_with", "has_chunk"
        ]
        for table in tables:
            await db_manager.execute(f"DELETE {table}")
            
        return {"status": "success", "message": "Cleared all tables"}
    except Exception as e:
        logger.error(f"Clear database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")
