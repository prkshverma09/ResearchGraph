"""API routes for asking the research agent."""

import json
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI

try:
    import langsmith as ls
except ImportError:
    ls = None

from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.agent.sessions import (
    create_session,
    get_session,
    NotFoundError,
)
from app.config import settings
from app.models.schemas import AskRequest, AskResponse
from app.retrieval.hybrid import HybridRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


def _normalize_paper_ids(paper_ids: List[str]) -> List[str]:
    """Normalize selected paper IDs by trimming empties and de-duplicating."""
    normalized: List[str] = []
    seen = set()
    for paper_id in paper_ids:
        if not isinstance(paper_id, str):
            continue
        value = paper_id.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _insufficient_context_answer(filter_selected_only: bool) -> str:
    scoped_note = (
        "within the selected paper(s)"
        if filter_selected_only else "in the current knowledge base"
    )
    return (
        f"I have insufficient context to answer this request {scoped_note}. "
        "Try broadening the scope, selecting different papers, or asking a more specific question."
    )


async def _run_hybrid_pipeline(
    question: str,
    db: SurrealDBManager,
    filter_selected_only: bool,
    selected_paper_ids: List[str],
) -> Dict[str, Any]:
    """Run deterministic hybrid retrieval and synthesize final answer."""
    retriever = HybridRetriever(db_manager=db)
    scoped_ids = selected_paper_ids if filter_selected_only else None
    retrieval = await retriever.retrieve(question, selected_paper_ids=scoped_ids, k=8)
    contexts = retrieval.get("contexts", [])
    retrieval_debug = retrieval.get("debug", {})

    if not contexts:
        return {
            "answer": _insufficient_context_answer(filter_selected_only),
            "sources": [],
            "retrieval_debug": retrieval_debug,
        }

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )
    context_text = "\n\n".join(
        f"[{idx}] title={ctx.get('title', 'Unknown')} paper_id={ctx.get('paper_id', '')} score={ctx.get('score', 0.0)}\n{ctx.get('content', '')}"
        for idx, ctx in enumerate(contexts, start=1)
    )
    prompt = (
        "You are a research assistant. Answer only using the provided context snippets. "
        "If evidence is weak, say so explicitly. Include paper titles when available.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context_text}"
    )

    if ls:
        with ls.tracing_context(
            metadata={
                "query": question,
                "filter_selected_only": filter_selected_only,
                "selected_paper_ids": selected_paper_ids,
                "hybrid_debug": retrieval_debug,
            }
        ):
            response = await llm.ainvoke(prompt)
    else:
        response = await llm.ainvoke(prompt)

    answer = response.content if hasattr(response, "content") else str(response)
    sources = []
    seen = set()
    for ctx in contexts:
        paper_id = str(ctx.get("paper_id", ""))
        title = str(ctx.get("title", "Unknown"))
        key = (paper_id, title)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "title": title,
                "paper_id": paper_id,
                "relevance_score": float(ctx.get("score", 0.0)),
            }
        )

    return {
        "answer": answer,
        "sources": sources,
        "retrieval_debug": retrieval_debug,
    }


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    db: SurrealDBManager = Depends(get_db),
):
    """Ask the research agent a question.
    
    Args:
        request: AskRequest with question and optional session_id
        db: SurrealDB manager dependency
        
    Returns:
        AskResponse with answer, sources, and session_id
    """
    try:
        session_id = request.session_id
        selected_paper_ids = _normalize_paper_ids(request.selected_paper_ids)

        if request.filter_selected_only and not selected_paper_ids:
            raise HTTPException(
                status_code=400,
                detail="selected_paper_ids is required when filter_selected_only is true",
            )
        
        if not session_id:
            session_id = await create_session(user_id="default", db_manager=db)
        
        try:
            await get_session(session_id, db_manager=db)
        except NotFoundError:
            session_id = await create_session(user_id="default", db_manager=db)
        
        result = await _run_hybrid_pipeline(
            question=request.question,
            db=db,
            filter_selected_only=request.filter_selected_only,
            selected_paper_ids=selected_paper_ids,
        )
        
        return AskResponse(
            answer=result["answer"],
            sources=result["sources"],
            graph_paths=[],
            session_id=session_id,
            retrieval_debug=result["retrieval_debug"] if settings.app_env != "production" else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")


@router.post("/ask/stream")
async def ask_stream(
    request: AskRequest,
    db: SurrealDBManager = Depends(get_db),
):
    """Ask the research agent a question with streaming response (SSE).
    
    Args:
        request: AskRequest with question and optional session_id
        db: SurrealDB manager dependency
        
    Returns:
        StreamingResponse with Server-Sent Events
    """
    selected_paper_ids = _normalize_paper_ids(request.selected_paper_ids)
    if request.filter_selected_only and not selected_paper_ids:
        raise HTTPException(
            status_code=400,
            detail="selected_paper_ids is required when filter_selected_only is true",
        )

    async def generate():
        try:
            session_id = request.session_id
            
            if not session_id:
                session_id = await create_session(user_id="default", db_manager=db)
            
            try:
                await get_session(session_id, db_manager=db)
            except NotFoundError:
                session_id = await create_session(user_id="default", db_manager=db)
            
            yield f"data: {json.dumps({'type': 'session_id', 'data': session_id})}\n\n"

            result = await _run_hybrid_pipeline(
                question=request.question,
                db=db,
                filter_selected_only=request.filter_selected_only,
                selected_paper_ids=selected_paper_ids,
            )
            node_payload = {
                "final_answer": result["answer"],
                "retrieval_debug": result["retrieval_debug"],
            }
            yield f"data: {json.dumps({'type': 'node', 'node': 'hybrid_retrieval', 'data': node_payload})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
