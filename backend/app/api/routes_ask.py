"""API routes for asking the research agent."""

import logging
import json
import re
from typing import Optional
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


def _create_agent_tools(db: SurrealDBManager):
    """Create agent tools with dependencies."""
    from langchain_core.tools import StructuredTool
    
    vector_store = VectorStoreService(db_manager=db)
    vector_search = create_vector_search_tool(vector_store)
    
    graph_query_tool = GraphQueryTool(db_manager=db)
    graph_query = StructuredTool.from_function(
        func=graph_query_tool.ainvoke,
        name="graph_query",
        description=graph_query_tool.description,
        args_schema=graph_query_tool.args_schema,
    )
    
    citation_path_tool = CitationPathTool(db_manager=db)
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
        
        if not session_id:
            session_id = await create_session(user_id="default", db_manager=db)
        
        try:
            await get_session(session_id, db_manager=db)
        except NotFoundError:
            session_id = await create_session(user_id="default", db_manager=db)
        
        query_type = _classify_query_type(request.question)
        
        tools = _create_agent_tools(db)
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
        }
        
        config = get_langgraph_config(session_id)
        
        if ls:
            with ls.tracing_context(
                metadata={
                    "session_id": session_id,
                    "query_type": query_type,
                    "query": request.question,
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
            
            tools = _create_agent_tools(db)
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
            }
            
            config = get_langgraph_config(session_id)
            
            yield f"data: {json.dumps({'type': 'session_id', 'data': session_id})}\n\n"
            
            if ls:
                with ls.tracing_context(
                    metadata={
                        "session_id": session_id,
                        "query_type": query_type,
                        "query": request.question,
                    }
                ):
                    async for event in stream_agent_response(graph, initial_state, config=config):
                        node_name = list(event.keys())[0] if event else None
                        node_data = event.get(node_name, {}) if node_name else {}
                        
                        yield f"data: {json.dumps({'type': 'node', 'node': node_name, 'data': node_data})}\n\n"
            else:
                async for event in stream_agent_response(graph, initial_state, config=config):
            
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
