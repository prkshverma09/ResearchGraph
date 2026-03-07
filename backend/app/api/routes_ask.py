"""API routes for asking the research agent."""

import logging
import json
import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
try:
    import langsmith as ls
except ImportError:
    ls = None
from app.dependencies import get_db
from app.db.connection import SurrealDBManager
from app.ingestion.embeddings import VectorStoreService
from app.agent.tools import (
    create_vector_search_tool,
    GraphQueryTool,
    CitationPathTool,
)
from app.agent.workflow import create_agent_graph, stream_agent_response
from app.agent.sessions import (
    create_session,
    get_session,
    get_checkpointer,
    get_langgraph_config,
    NotFoundError,
)
from app.agent.state import ResearchAgentState
from app.config import settings
from app.models.schemas import AskRequest, AskResponse
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agent"])


def _classify_query_type(question: str) -> str:
    """Classify the query type based on question content.
    
    Args:
        question: User's question text
        
    Returns:
        Query type: 'discovery', 'citation', 'author', 'topic', or 'general'
    """
    question_lower = question.lower()
    
    if any(keyword in question_lower for keyword in ['cite', 'citation', 'cited by', 'who cites', 'cites']):
        return 'citation'
    elif any(keyword in question_lower for keyword in ['author', 'written by', 'published by', 'who wrote']):
        return 'author'
    elif any(keyword in question_lower for keyword in ['topic', 'field', 'area', 'research area', 'domain']):
        return 'topic'
    elif any(keyword in question_lower for keyword in ['find', 'search', 'discover', 'papers about', 'papers on']):
        return 'discovery'
    elif any(keyword in question_lower for keyword in ['connect', 'path', 'relationship', 'related', 'link']):
        return 'citation'
    else:
        return 'general'


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


def _create_agent_tools(
    db: SurrealDBManager,
    selected_paper_ids: Optional[List[str]] = None,
):
    """Create agent tools with dependencies."""
    from langchain_core.tools import StructuredTool
    
    vector_store = VectorStoreService(db_manager=db)
    vector_search = create_vector_search_tool(
        vector_store,
        allowed_paper_ids=selected_paper_ids,
    )
    
    graph_query_tool = GraphQueryTool(
        db_manager=db,
        allowed_paper_ids=selected_paper_ids,
    )
    graph_query = StructuredTool.from_function(
        func=graph_query_tool.ainvoke,
        name="graph_query",
        description=graph_query_tool.description,
        args_schema=graph_query_tool.args_schema,
    )
    
    citation_path_tool = CitationPathTool(
        db_manager=db,
        allowed_paper_ids=selected_paper_ids,
    )
    citation_path = StructuredTool.from_function(
        func=citation_path_tool.ainvoke,
        name="citation_path",
        description=citation_path_tool.description,
        args_schema=citation_path_tool.args_schema,
    )
    
    return [vector_search, graph_query, citation_path]


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
        
        query_type = _classify_query_type(request.question)
        
        tools = _create_agent_tools(
            db,
            selected_paper_ids=selected_paper_ids if request.filter_selected_only else None,
        )
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            openai_api_key=settings.openai_api_key,
        )
        checkpointer = get_checkpointer()
        
        graph = create_agent_graph(tools=tools, llm=llm, checkpointer=checkpointer)
        
        initial_state: ResearchAgentState = {
            "messages": [HumanMessage(content=request.question)],
            "query": request.question,
            "final_answer": "",
            "search_results": [],
            "graph_results": [],
            "citation_path": [],
            "session_id": session_id,
            "filter_selected_only": request.filter_selected_only,
            "selected_paper_ids": selected_paper_ids,
        }
        
        config = get_langgraph_config(session_id)
        
        if ls:
            with ls.tracing_context(
                metadata={
                    "session_id": session_id,
                    "query_type": query_type,
                    "query": request.question,
                    "filter_selected_only": request.filter_selected_only,
                    "selected_paper_ids": selected_paper_ids,
                }
            ):
                final_state = await graph.ainvoke(initial_state, config=config)
        else:
            final_state = await graph.ainvoke(initial_state, config=config)
        
        answer = final_state.get("final_answer", "")
        if not answer and final_state.get("messages"):
            last_message = final_state["messages"][-1]
            if hasattr(last_message, "content"):
                answer = last_message.content
        
        sources = []
        search_results = final_state.get("search_results", [])
        graph_results = final_state.get("graph_results", [])
        
        for result in search_results:
            if isinstance(result, dict):
                sources.append({
                    "title": result.get("title", "Unknown"),
                    "paper_id": result.get("paper_id", ""),
                    "relevance_score": result.get("relevance_score", 0.0),
                })
        
        for result in graph_results:
            if isinstance(result, dict):
                sources.append({
                    "title": result.get("title", "Unknown"),
                    "paper_id": result.get("id", ""),
                })
        
        citation_paths = []
        citation_path = final_state.get("citation_path", [])
        if citation_path:
            citation_paths.append(citation_path)
        
        return AskResponse(
            answer=answer,
            sources=sources,
            graph_paths=citation_paths,
            session_id=session_id,
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
            
            query_type = _classify_query_type(request.question)
            
            tools = _create_agent_tools(
                db,
                selected_paper_ids=selected_paper_ids if request.filter_selected_only else None,
            )
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                openai_api_key=settings.openai_api_key,
            )
            checkpointer = get_checkpointer()
            
            graph = create_agent_graph(tools=tools, llm=llm, checkpointer=checkpointer)
            
            initial_state: ResearchAgentState = {
                "messages": [HumanMessage(content=request.question)],
                "query": request.question,
                "final_answer": "",
                "search_results": [],
                "graph_results": [],
                "citation_path": [],
                "session_id": session_id,
                "filter_selected_only": request.filter_selected_only,
                "selected_paper_ids": selected_paper_ids,
            }
            
            config = get_langgraph_config(session_id)
            
            yield f"data: {json.dumps({'type': 'session_id', 'data': session_id})}\n\n"
            
            if ls:
                with ls.tracing_context(
                    metadata={
                        "session_id": session_id,
                        "query_type": query_type,
                        "query": request.question,
                        "filter_selected_only": request.filter_selected_only,
                        "selected_paper_ids": selected_paper_ids,
                    }
                ):
                    async for event in stream_agent_response(graph, initial_state, config=config):
                        node_name = list(event.keys())[0] if event else None
                        node_data = event.get(node_name, {}) if node_name else {}
                        
                        yield f"data: {json.dumps({'type': 'node', 'node': node_name, 'data': node_data})}\n\n"
            else:
                async for event in stream_agent_response(graph, initial_state, config=config):
                    node_name = list(event.keys())[0] if event else None
                    node_data = event.get(node_name, {}) if node_name else {}
                    
                    yield f"data: {json.dumps({'type': 'node', 'node': node_name, 'data': node_data})}\n\n"
            
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
